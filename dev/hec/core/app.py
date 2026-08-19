"""Aplikace: propojení konfigurace, úložiště, readerů a snapshotu.

Snapshot v paměti je jediné místo, kde se potkávají data ze všech zdrojů.
Readery do něj zapisují, controller a webové API z něj čtou – readery se tak
nikdy nevolají navzájem.
"""

from __future__ import annotations

import threading
from typing import Any

from ..readers.registry import build_readers
from ..storage.jsonl import JsonlStorage
from . import config as config_mod
from .logging_setup import configure, event, get_logger, register_secrets
from .model import Sample
from .scheduler import Scheduler
from .secrets import collect_secret_values
from .timeutil import now_local, to_iso


class Application:
    def __init__(self, config=None, *, config_path=None):
        self.config = config or config_mod.load(config_path)
        self.config.ensure_dirs()
        configure(self.config.logs_dir,
                  level=self.config.get("logging.level", "INFO"),
                  max_bytes=int(self.config.get("logging.max_bytes", 5_000_000)),
                  backups=int(self.config.get("logging.backups", 5)))
        register_secrets(collect_secret_values(self.config.data))
        self.log = get_logger("app")

        self.storage = JsonlStorage(self.config.data_dir, self.config.history_dir)
        self._lock = threading.Lock()
        self.snapshot: dict[str, dict] = {}
        self.readers = build_readers(self.config, self.storage)
        self.scheduler = Scheduler(self.readers, on_sample=self.accept)
        self.controller = None            # dosadí se v kroku s optimalizací
        self.started_at = now_local()

        for error in self.config.errors:
            self.log.warning("config_issue | %s", error)
        # Poslední známé hodnoty přežijí restart – UI nezačíná prázdné.
        for reader in self.readers:
            stored = self.storage.latest(reader.name)
            if stored:
                self.snapshot[reader.name] = stored

    # --- data ---------------------------------------------------------------
    def accept(self, sample: Sample, reader=None) -> None:
        if not sample.ok:
            return
        with self._lock:
            self.snapshot[sample.source] = sample.to_dict()
        if self.controller is not None:
            self.controller.on_sample(sample)

    def current(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self.snapshot)
        return {
            "timestamp": to_iso(now_local()),
            "sources": data,
            "status": self.status(),
        }

    def status(self) -> dict[str, Any]:
        statuses = {reader.name: reader.status.to_dict() for reader in self.readers}
        stale = [name for name, value in statuses.items() if value["stale"]]
        controller_state = self.controller.state() if self.controller is not None else {
            "enabled": False, "safe_mode": True, "reason_key": "status.controller_disabled",
        }
        return {
            "started_at": to_iso(self.started_at),
            "readers": statuses,
            "stale_sources": stale,
            "controller": controller_state,
            "site_name": self.config.get("system.site_name"),
        }

    def reader(self, name: str):
        for reader in self.readers:
            if reader.name == name:
                return reader
        return None

    # --- běh ----------------------------------------------------------------
    def run_once(self) -> list[Sample]:
        samples = self.scheduler.run_once()
        for sample in samples:
            event(self.log, "sample", source=sample.source, ok=sample.ok)
        return samples

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()
