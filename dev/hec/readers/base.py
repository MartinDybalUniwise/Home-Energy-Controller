"""Společný základ readerů.

Pravidla, která platí pro každý reader:

* výjimka v jednom readeru nesmí shodit smyčku ani ostatní readery,
* po chybě se čeká déle (exponenciální backoff), aby se nezahltil zdroj,
* každý reader hlásí čas posledního úspěchu, aby controller poznal zastaralá data.
"""

from __future__ import annotations

import re
import time
import unicodedata

from ..core.logging_setup import error_event, event, get_logger
from ..core.model import ReaderStatus, Sample
from ..core.timeutil import now_local, to_iso

MAX_BACKOFF_SECONDS = 600


def slug(text: str) -> str:
    """Bezpečný identifikátor z uživatelského názvu (klíč v souborech a URL)."""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_") or "device"


class BaseReader:
    """Rozhraní readeru. Potomek implementuje `read()` a nic víc nemusí."""

    name = "base"

    def __init__(self, config, storage=None):
        self.config = config
        self.storage = storage
        self.log = get_logger(self.name)
        self.status = ReaderStatus(
            name=self.name,
            enabled=self.is_enabled(),
            interval_seconds=self.interval_seconds(),
        )
        self._failures = 0
        self._next_at = 0.0

    # --- konfigurace -------------------------------------------------------
    def is_enabled(self) -> bool:
        return bool(self.config.get(f"{self.name}.enabled", False))

    def interval_seconds(self) -> int:
        return int(self.config.get(f"polling.{self.name}_seconds", 60))

    # --- implementuje potomek ---------------------------------------------
    def read(self) -> dict:
        raise NotImplementedError

    def history_targets(self, values: dict, sample: Sample) -> list[tuple[str, dict]]:
        """Kam a co zapsat do historie. Výchozí je jeden záznam do vlastního zdroje."""
        return [(self.name, sample.to_dict())]

    # --- běh ---------------------------------------------------------------
    def poll(self) -> Sample:
        """Jedno čtení. Nikdy nevyhodí výjimku – chybu vrací v Sample."""
        started = time.monotonic()
        self.status.last_attempt = now_local()
        try:
            values = self.read()
        except Exception as exc:                              # noqa: BLE001 – izolace readeru
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
        sample = Sample(source=self.name, values=values, timestamp=self.status.last_success)
        self._persist(values, sample)
        event(self.log, "poll_success", duration_ms=int((time.monotonic() - started) * 1000),
              **{k: v for k, v in list(values.items())[:3] if isinstance(v, (int, float))})
        return sample

    def _persist(self, values: dict, sample: Sample) -> None:
        if self.storage is None:
            return
        record = sample.to_dict()
        record["reader_status"] = {"last_success": to_iso(self.status.last_success)}
        self.storage.write_current(self.name, sample.to_dict())
        for source, entry in self.history_targets(values, sample):
            self.storage.append(source, entry)

    # --- plánování ---------------------------------------------------------
    def backoff_seconds(self) -> float:
        if not self._failures:
            return float(self.interval_seconds())
        factor = 2 ** min(self._failures, 6)
        return float(min(MAX_BACKOFF_SECONDS, self.interval_seconds() * factor))

    def due(self, monotonic_now: float) -> bool:
        return monotonic_now >= self._next_at

    def schedule_next(self, monotonic_now: float) -> None:
        self._next_at = monotonic_now + self.backoff_seconds()
        self.status.interval_seconds = self.interval_seconds()
