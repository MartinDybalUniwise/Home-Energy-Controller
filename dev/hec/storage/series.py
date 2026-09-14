"""Práce s časovými řadami: podvzorkování a agregace pro API a grafy.

Mobil nesmí stahovat 96 000 řádků – zhuštění dělá server.
"""

from __future__ import annotations

from collections.abc import Callable
from statistics import mean
from typing import Any

from ..core.timeutil import floor_to, parse_iso, to_iso

AGGREGATIONS: dict[str, Callable[[list[float]], float]] = {
    "mean": lambda values: mean(values),
    "max": max,
    "min": min,
    "sum": sum,
    "last": lambda values: values[-1],
    "first": lambda values: values[0],
}


def numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def record_values(record: dict) -> dict[str, Any]:
    """Vrátí kompatibilní plochý pohled na top-level a vnořené hodnoty."""
    values = record.get("values")
    if not isinstance(values, dict):
        return record
    flattened = {key: value for key, value in record.items() if key != "values"}
    flattened.update(values)
    return flattened


def series_row(record: dict, fields: list[str]) -> dict:
    values = record_values(record)
    return {"timestamp": record.get("timestamp"),
            **{field: values[field] for field in fields if field in values}}


def downsample(records: list[dict], fields: list[str], bucket_seconds: int,
               how: str | dict[str, str] = "mean") -> list[dict]:
    """Zhustí vzorky do časových košů. Prázdný koš se nevytváří."""
    if bucket_seconds <= 0 or not records:
        return [series_row(record, fields) for record in records]

    buckets: dict[str, dict[str, list[float]]] = {}
    order: list[str] = []
    for record in records:
        stamp = parse_iso(record.get("timestamp"))
        if stamp is None:
            continue
        key = to_iso(floor_to(stamp, bucket_seconds))
        if key not in buckets:
            buckets[key] = {}
            order.append(key)
        values = record_values(record)
        for field in fields:
            value = numeric(values.get(field))
            if value is not None:
                buckets[key].setdefault(field, []).append(value)

    out: list[dict] = []
    for key in order:
        row: dict[str, Any] = {"timestamp": key}
        for field, values in buckets[key].items():
            mode = how.get(field, "mean") if isinstance(how, dict) else how
            row[field] = round(AGGREGATIONS.get(mode, mean)(values), 3)
        out.append(row)
    return out


def series_fields(records: list[dict], skip: tuple[str, ...] = ("timestamp", "source")) -> list[str]:
    """Zjistí, které číselné veličiny se ve vzorcích vyskytují."""
    found: list[str] = []
    for record in records[:50]:
        for key, value in record_values(record).items():
            if key in skip or key in found:
                continue
            if numeric(value) is not None:
                found.append(key)
    return found


def integrate_kwh(records: list[dict], field: str, *, max_gap_seconds: int = 900) -> float:
    """Energie [kWh] z výkonových vzorků [W] lichoběžníkovou metodou.

    Mezery delší než `max_gap_seconds` se nepočítají – při výpadku měření se
    hodnota nedomýšlí (pravidlo: raději méně dat než vymyšlená data).
    """
    total_ws = 0.0
    previous_time = None
    previous_value = None
    for record in records:
        stamp = parse_iso(record.get("timestamp"))
        value = numeric(record_values(record).get(field))
        if stamp is None or value is None:
            continue
        if previous_time is not None:
            gap = (stamp - previous_time).total_seconds()
            if 0 < gap <= max_gap_seconds:
                total_ws += (value + previous_value) / 2.0 * gap
        previous_time, previous_value = stamp, value
    return round(total_ws / 3_600_000.0, 4)
