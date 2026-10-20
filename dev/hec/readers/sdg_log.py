"""Read-only SDG log reader.

The production share is never written. DBF access is optional so local and
preview runs can use sanitized injected records without the share or parser
dependency.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.logging_setup import error_event, event
from ..core.model import Sample
from ..core.timeutil import now_local, parse_iso
from ..storage.base import atomic_write_json, read_json
from .base import BaseReader

DEFAULT_RELATIVE_DIRS = ("trend/min", "trend/solar", "Event2", "Alarm")
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "datetime", "date_time", "dt", "time", "date"),
    "pv_w": ("pv_w", "pv", "pv_power", "ppv", "ppv_total"),
    "house_w": ("house_w", "house", "load_w", "load", "house_consumption"),
    "grid_w": ("grid_w", "grid", "grid_power", "meter_active_power_total"),
    "battery_w": ("battery_w", "battery", "battery_power", "pbattery1"),
    "battery_soc": ("battery_soc", "soc", "soc_pct", "battery_state_of_charge"),
    "e_day_kwh": ("e_day_kwh", "e_day", "daily_pv_kwh"),
}


def _normal_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.astimezone()
    return parse_iso(str(value)) if value is not None else None


def normalize_record(record: dict[str, Any], *, source_file: str = "", config=None) -> dict[str, Any] | None:
    """Map one verified SDG record without inventing absent values."""
    indexed = {_normal_key(key): value for key, value in record.items()}
    timestamp_value = next((indexed[_normal_key(alias)] for alias in FIELD_ALIASES["timestamp"]
                            if _normal_key(alias) in indexed), None)
    timestamp = _timestamp(timestamp_value)
    if timestamp is None:
        return None

    values: dict[str, Any] = {
        "timestamp": timestamp,
        "telemetry_source": "sdg",
        "sdg_file": source_file,
    }
    for target, aliases in FIELD_ALIASES.items():
        if target == "timestamp":
            continue
        for alias in aliases:
            key = _normal_key(alias)
            if key in indexed:
                value = _number(indexed[key])
                if value is not None:
                    values[target] = value
                    break
    grid = values.get("grid_w")
    if isinstance(grid, (int, float)):
        positive_is_import = bool(config.get("goodwe.grid_positive_is_import", True)) if config else True
        flow = grid if positive_is_import else -grid
        values["grid_import_w"] = max(0.0, flow)
        values["grid_export_w"] = max(0.0, -flow)
    battery = values.get("battery_w")
    if isinstance(battery, (int, float)):
        positive_is_charge = bool(config.get("goodwe.battery_positive_is_charge", True)) if config else True
        flow = battery if positive_is_charge else -battery
        values["battery_charge_w"] = max(0.0, flow)
        values["battery_discharge_w"] = max(0.0, -flow)
    if len(values) == 3:
        return None
    return values


def _dbf_records(path: Path) -> Iterable[dict[str, Any]]:
    try:
        from dbfread import DBF
    except ImportError as exc:  # pragma: no cover - exercised by environment setup
        raise RuntimeError("SDG DBF reader requires the optional 'dbfread' package") from exc
    return DBF(str(path), load=False, char_decode_errors="ignore")


class SdgLogReader(BaseReader):
    """Read the newest valid SDG record from configured DBF files."""

    name = "sdg"

    def __init__(self, config, storage=None, *, record_loader: Callable[[Path], Iterable[dict]] | None = None):
        self._record_loader = record_loader or _dbf_records
        self._state_path = Path(config.data_dir) / "sdg_log_reader_state.json"
        self._file_state: dict[str, dict[str, Any]] = {}
        self._seen_keys: set[str] = set()
        super().__init__(config, storage)
        self._load_state()

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.sdg_seconds", 30))

    def _load_state(self) -> None:
        saved = read_json(self._state_path, {}) or {}
        if isinstance(saved.get("files"), dict):
            for key, value in saved["files"].items():
                if isinstance(value, dict):
                    self._file_state[str(key)] = value
                elif isinstance(value, str):
                    self._file_state[str(key)] = {"fingerprint": value}
        if isinstance(saved.get("seen_keys"), list):
            self._seen_keys = {str(value) for value in saved["seen_keys"]}

    def _save_state(self) -> None:
        atomic_write_json(self._state_path, {
            "version": 1,
            "files": self._file_state,
            "seen_keys": sorted(self._seen_keys)[-5000:],
        })

    def is_enabled(self) -> bool:
        return bool(self.config.get("goodwe.sdg.enabled", False))

    def _root(self) -> Path:
        raw = str(self.config.get("goodwe.sdg.log_root_path", "") or "").strip()
        if not raw:
            raise RuntimeError("goodwe.sdg.log_root_path is not configured")
        return Path(raw)

    def _files(self) -> list[Path]:
        root = self._root()
        files: list[Path] = []
        for relative in self.config.get("goodwe.sdg.directories", DEFAULT_RELATIVE_DIRS):
            directory = root / Path(relative)
            if directory.is_dir():
                files.extend(directory.glob("*.dbf"))
        return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)

    def _relative_file(self, path: Path) -> str:
        try:
            return path.relative_to(self._root()).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def _fingerprint(path: Path) -> str:
        stat = path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def _record_key(self, record: dict[str, Any]) -> str:
        payload = {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in record.items() if key != "dedup_key"
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    @staticmethod
    def _state_record(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in record.items()
        }

    @staticmethod
    def _restore_record(record: dict[str, Any]) -> dict[str, Any] | None:
        restored = dict(record)
        timestamp = parse_iso(restored.get("timestamp"))
        if timestamp is None:
            return None
        restored["timestamp"] = timestamp
        return restored

    def read(self) -> dict:
        newest: dict[str, Any] | None = None
        newest_stamp: datetime | None = None
        next_file_state: dict[str, str] = {}
        scan_failed = False
        for path in self._files():
            relative_file = self._relative_file(path)
            fingerprint = self._fingerprint(path)
            cached = self._file_state.get(relative_file, {})
            normalized = None
            if cached.get("fingerprint") == fingerprint and isinstance(cached.get("latest"), dict):
                normalized = self._restore_record(cached["latest"])
            try:
                if normalized is None:
                    records = self._record_loader(path)
                    for record in records:
                        candidate = normalize_record(record, source_file=relative_file, config=self.config)
                        stamp = candidate.get("timestamp") if candidate else None
                        if candidate and isinstance(stamp, datetime):
                            if normalized is None or stamp > normalized["timestamp"]:
                                normalized = candidate
                    if normalized is not None:
                        normalized["dedup_key"] = self._record_key(normalized)
                if normalized is not None:
                    next_file_state[relative_file] = {
                        "fingerprint": fingerprint,
                        "latest": self._state_record(normalized),
                    }
                    stamp = normalized.get("timestamp")
                    if isinstance(stamp, datetime) and (newest_stamp is None or stamp > newest_stamp):
                        newest = normalized
                        newest_stamp = stamp
            except Exception as exc:  # noqa: BLE001 - isolate one corrupt DBF file
                scan_failed = True
                self.log.warning("sdg_file_skipped | file=%s error=%s", relative_file, type(exc).__name__)
                continue
        if newest is None:
            raise RuntimeError("no valid SDG telemetry record found")
        freshness = int(self.config.get("goodwe.sdg.freshness_seconds", 180))
        if (now_local() - newest_stamp).total_seconds() > freshness:
            raise RuntimeError("SDG telemetry is stale")
        if not scan_failed:
            self._file_state = next_file_state
            self._save_state()
        newest["timestamp"] = newest_stamp
        return newest

    def poll(self) -> Sample:
        """Poll while preserving the timestamp carried by the SDG record."""
        started = time.monotonic()
        self.status.last_attempt = now_local()
        try:
            values = self.read()
            timestamp = values.pop("timestamp")
        except Exception as exc:  # noqa: BLE001 - reader isolation boundary
            self._failures += 1
            self.status.error_count += 1
            self.status.last_error = f"{type(exc).__name__}: {exc}"
            error_event(self.log, "poll_failed", attempt=self._failures,
                        backoff_s=int(self.backoff_seconds()), error=type(exc).__name__)
            return Sample(source=self.name, ok=False, error=self.status.last_error)

        self._failures = 0
        self.status.last_success = now_local()
        self.status.success_count += 1
        self.status.last_error = None
        sample = Sample(source=self.name, values=values, timestamp=timestamp)
        self._persist(values, sample)
        event(self.log, "poll_success", duration_ms=int((time.monotonic() - started) * 1000),
              telemetry_source="sdg")
        return sample

    def history_targets(self, values: dict, sample) -> list[tuple[str, dict]]:
        dedup_key = values.get("dedup_key")
        if dedup_key and dedup_key in self._seen_keys:
            return []
        if dedup_key:
            self._seen_keys.add(dedup_key)
            self._save_state()
        record = sample.to_dict()
        record["source"] = "goodwe"
        return [("goodwe", record)]
