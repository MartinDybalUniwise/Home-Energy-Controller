"""Datové struktury sdílené readery, úložištěm a controllerem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .timeutil import age_seconds, now_local, to_iso


@dataclass
class Sample:
    """Jedno měření z jednoho zdroje. Klíč `source` odpovídá názvu readeru."""

    source: str
    values: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=now_local)
    ok: bool = True
    error: str | None = None

    def to_dict(self) -> dict:
        out = {"timestamp": to_iso(self.timestamp), "source": self.source}
        out.update(self.values)
        if not self.ok:
            out["ok"] = False
            out["error"] = self.error
        return out


@dataclass
class ReaderStatus:
    """Provozní stav readeru – podklad pro /api/status a pro safe mode."""

    name: str
    enabled: bool = True
    interval_seconds: int = 60
    last_success: datetime | None = None
    last_attempt: datetime | None = None
    last_error: str | None = None
    error_count: int = 0
    success_count: int = 0

    def stale_after(self) -> float:
        """Data považujeme za zastaralá po trojnásobku intervalu, minimálně 60 s."""
        return max(60.0, self.interval_seconds * 3.0)

    @property
    def age(self) -> float | None:
        return age_seconds(self.last_success)

    @property
    def is_stale(self) -> bool:
        if not self.enabled:
            return False
        age = self.age
        return age is None or age > self.stale_after()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "last_success": to_iso(self.last_success),
            "last_attempt": to_iso(self.last_attempt),
            "last_error": self.last_error,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "age_seconds": None if self.age is None else round(self.age, 1),
            "stale": self.is_stale,
        }


@dataclass
class Decision:
    """Rozhodnutí controlleru. Důvod je překladový klíč, ne hotová věta."""

    rule: str
    action: str
    value: Any = None
    applied: bool = False
    reason_key: str = ""
    reason_params: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=now_local)

    def to_dict(self) -> dict:
        return {
            "timestamp": to_iso(self.timestamp),
            "rule": self.rule,
            "action": self.action,
            "value": self.value,
            "applied": self.applied,
            "reason_key": self.reason_key,
            "reason_params": self.reason_params,
        }
