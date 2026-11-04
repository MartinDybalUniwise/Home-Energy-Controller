"""Conditional second ordinary DHW window inside the single thermal resolver."""
from ..core.timeutil import in_window, parse_iso
from ..storage.base import atomic_write_json, read_json
from .floor import number


def dhw_mode(config, state, moment, mode, target):
    operation = config.get("tng.operation", {})
    info = dict(skipped=False, reason="scheduled_window")
    # Explicit dated owner operation/temperature plans and high-temperature
    # hygienic windows retain their exact meaning.
    if (mode != "boiler" or not config.get("tng.heating.enabled", False)
            or operation.get("default_mode", "heating") != "heating"
            or moment.date().isoformat() in operation.get("date_overrides", {})
            or moment.date().isoformat() in config.get("tng.boiler.date_overrides", {})
            or not number(target) or target > 50):
        return mode, info
    windows = [w for w in operation.get("schedule", []) if w.get("mode") == "boiler"]
    active = next((w for w in windows if in_window(moment, w["from"], w["to"])), None)
    if active is None or sum(w["from"] < active["from"] for w in windows) < 1:
        return mode, info
    hp = state.get("heatpump") or {}
    stamp, value = parse_iso(hp.get("sample_time")), hp.get("boiler_temperature")
    if (stamp is None or not 0 <= (moment - stamp).total_seconds() <= 900
            or not number(value) or not 0 <= value <= 80):
        return mode, dict(skipped=False, reason="stale_or_unknown_boiler")
    path = config.data_dir / "dhw-readiness-state.json"
    saved = read_json(path, {}) or {}
    key = f"{moment.date().isoformat()}:{active['from']}:{active['to']}"
    skip = bool(saved.get("skipped")) if saved.get("key") == key else False
    if value >= target:
        skip = True
    elif value <= target - 2:
        skip = False
    updated = dict(key=key, skipped=skip)
    if updated != saved:
        atomic_write_json(path, updated)
    return ("heating" if skip else mode), dict(
        skipped=skip, reason="already_at_target" if skip else "needs_reheat",
        measured_c=value, target_c=target, hysteresis_c=2,
        usable_hot_water_volume_known=False,
    )
