"""Consumption meter quality; raw readings are never corrected or rewritten."""

from __future__ import annotations

from math import isfinite

from ..core.timeutil import parse_iso
from ..storage.series import numeric, record_values

MAX_GAP_SECONDS = 900
RUNNING_W = 200.0


def meter_quality(values: dict) -> str:
    watts = numeric(values.get("power_w"))
    if watts is None or not isfinite(watts):
        return "missing"
    if watts < 0:
        return "negative"
    for phase in ("l1", "l2", "l3"):
        voltage = numeric(values.get(f"{phase}_v"))
        if f"{phase}_v" in values and (voltage is None or not isfinite(voltage) or voltage <= 0):
            return "phase"
    return "valid"


def consumption_report(records: list[dict], field: str, quality_field: str | None = None) -> dict:
    """Integrate only adjacent valid samples; invalid/missing data break intervals.

    Running time uses a left-held state between adjacent samples. Gaps over 15min
    and invalid values contribute neither energy nor run time; no extrapolation.
    """
    previous = None
    energy_ws = covered = running = 0.0
    invalid = missing = valid = 0
    for record in records:
        values = record_values(record)
        watts = numeric(values.get(field))
        quality = values.get(quality_field) if quality_field else None
        stamp = parse_iso(record.get("timestamp"))
        if watts is None or not isfinite(watts) or stamp is None:
            missing += 1
            previous = None
            continue
        if watts < 0 or quality not in (None, "valid"):
            invalid += 1
            previous = None
            continue
        valid += 1
        if previous is not None:
            before, power = previous
            gap = (stamp - before).total_seconds()
            if 0 < gap <= MAX_GAP_SECONDS:
                covered += gap
                energy_ws += (power + watts) / 2 * gap
                if power >= RUNNING_W:
                    running += gap
        previous = stamp, watts
    available = covered > 0
    return {
        "energy_kwh": round(energy_ws / 3_600_000, 4) if available else None,
        "run_hours": round(running / 3600, 2) if available else None,
        "covered_seconds": round(covered, 1),
        "valid_samples": valid,
        "invalid_samples": invalid,
        "missing_samples": missing,
        "quality": "partial" if available and (invalid or missing) else "valid" if available else "unavailable",
        "method": "adjacent-valid-v1",
    }
