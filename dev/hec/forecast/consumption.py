"""Whole-house demand estimates; heating is a component, never added twice."""
from datetime import date
from math import isfinite
from statistics import median

from ..core.timeutil import parse_iso


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def weather_consumption(history, target, temperature, fallback, heat):
    rows = []
    for row in history:
        try:
            age = (target - date.fromisoformat(row["date"])).days
        except (KeyError, ValueError):
            continue
        if 0 < age <= 7 and number(row.get("house_kwh")) and row["house_kwh"] > 0:
            rows.append(row)
    paired = [r for r in rows if number(r.get("heatpump_kwh"))
              and 0 <= r["heatpump_kwh"] <= r["house_kwh"]
              and (r.get("heatpump_quality") or {}).get("valid_samples", 0) >= 2
              and (r.get("heatpump_quality") or {}).get("quality") not in ("unavailable", "phase", "invalid")]
    if number(heat) and len(paired) >= 3:
        base = median(r["house_kwh"] - r["heatpump_kwh"] for r in paired)
        return round(base + heat, 2), dict(model="measured_heat_component", base_kwh=round(base, 2),
                                         weather_sensitive_kwh=heat, samples=len(paired))
    weather = [r for r in rows if number(r.get("mean_outside_c"))]
    if len(weather) >= 5 and number(temperature):
        pairs = [(max(0, 18 - r["mean_outside_c"]), r["house_kwh"]) for r in weather]
        slopes = [(b[1] - a[1]) / (b[0] - a[0]) for i, a in enumerate(pairs)
                  for b in pairs[i + 1:] if abs(b[0] - a[0]) >= 1.5]
        if slopes:
            slope = max(0, median(slopes))
            base = median(y - slope * x for x, y in pairs)
            if base < 0:
                return fallback, dict(model="recent_matching_day_median", weather_fit_rejected="negative_base",
                                      separate_heat_meter_valid=False)
            empirical = base + slope * max(0, 18 - temperature)
            middle = median(y for _, y in pairs)
            total = round(max(middle * .5, min(middle * 1.5, empirical)), 2)
            return total, dict(model="whole_house_weather_estimate", base_kwh=round(base, 2),
                               weather_sensitive_kwh=round(max(0, total - base), 2), samples=len(weather),
                               separate_heat_meter_valid=False)
    return fallback, dict(model="recent_matching_day_median", separate_heat_meter_valid=False)


def today_consumption(storage, config, moment, baseline):
    from zoneinfo import ZoneInfo
    zone = ZoneInfo(config.get("system.timezone", "Europe/Prague"))
    raw = storage.latest("goodwe") or {}
    values = raw.get("values", raw)
    stamp = parse_iso(raw.get("timestamp"))
    measured = values.get("e_load_day_kwh")
    if (stamp is None or stamp.astimezone(zone).date() != moment.astimezone(zone).date()
            or not 0 <= (moment - stamp).total_seconds() <= 120
            or not number(measured) or measured < 0):
        return baseline, dict(measured_kwh=None, remaining_kwh=None, model="baseline_without_fresh_counter")
    local = moment.astimezone(zone)
    elapsed = (local.hour * 3600 + local.minute * 60 + local.second) / 86400
    remaining = None
    if number(baseline) and baseline > 0:
        correction = min(1.5, max(.75, measured / (baseline * elapsed))) if elapsed >= .25 else 1
        remaining = baseline * (1 - elapsed) * correction
    total = round(measured + remaining, 2) if remaining is not None else None
    return total, dict(measured_kwh=measured, remaining_kwh=round(remaining, 2) if remaining is not None else None,
                       baseline_kwh=baseline, measurement_at=stamp.isoformat(),
                       model="measured_plus_time_weighted_remaining", remaining_is_estimate=True)
