"""Read-only SDG log reader.

The production share is never written. DBF access is optional so local and
preview runs can use sanitized injected records without the share or parser
dependency.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.logging_setup import error_event, event
from ..core.model import Sample
from ..core.timeutil import now_local, parse_iso
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


def normalize_record(record: dict[str, Any], *, source_file: str = "") -> dict[str, Any] | None:
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
        super().__init__(config, storage)

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

    def read(self) -> dict:
        newest: dict[str, Any] | None = None
        newest_stamp: datetime | None = None
        for path in self._files():
            for record in self._record_loader(path):
                normalized = normalize_record(record, source_file=str(path))
                stamp = normalized.get("timestamp") if normalized else None
                if normalized and isinstance(stamp, datetime) and (newest_stamp is None or stamp > newest_stamp):
                    newest = normalized
                    newest_stamp = stamp
        if newest is None:
            raise RuntimeError("no valid SDG telemetry record found")
        freshness = int(self.config.get("goodwe.sdg.freshness_seconds", 180))
        if (now_local() - newest_stamp).total_seconds() > freshness:
            raise RuntimeError("SDG telemetry is stale")
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
        record = sample.to_dict()
        record["source"] = "goodwe"
        return [("goodwe", record)]
