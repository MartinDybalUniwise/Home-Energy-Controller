"""Práce s časem. Všechny značky jsou ISO 8601 s časovou zónou."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

ISO = "%Y-%m-%dT%H:%M:%S%z"


def now_local() -> datetime:
    """Aktuální čas s lokálním offsetem."""
    return datetime.now().astimezone()


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat()


def parse_iso(value: str | datetime | None) -> datetime | None:
    """Tolerantní parser: přijímá i 'Z' na konci a čas bez zóny."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt


def age_seconds(value: str | datetime | None, now: datetime | None = None) -> float | None:
    """Stáří značky v sekundách. None, když je značka nečitelná nebo chybí."""
    dt = parse_iso(value)
    if dt is None:
        return None
    return max(0.0, ((now or now_local()) - dt).total_seconds())


def day_key(dt: datetime | None = None) -> str:
    """Klíč denního souboru historie."""
    return (dt or now_local()).strftime("%Y-%m-%d")


def month_key(dt: datetime | None = None) -> str:
    return (dt or now_local()).strftime("%Y-%m")


def floor_to(dt: datetime, seconds: int) -> datetime:
    """Zaokrouhlení dolů na násobek intervalu – pro agregaci časových řad."""
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = int((dt - epoch).total_seconds())
    return epoch + timedelta(seconds=delta - delta % seconds)


def in_window(now: datetime, start: str, end: str) -> bool:
    """Je čas uvnitř okna HH:MM–HH:MM? Okno smí přecházet přes půlnoc."""
    t = now.strftime("%H:%M")
    return start <= t < end if start <= end else (t >= start or t < end)
