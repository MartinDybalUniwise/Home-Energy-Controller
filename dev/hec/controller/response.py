"""Measured room response under confirmed preheat requests; no heat/COP inference."""

from copy import deepcopy
from math import ceil, isfinite

from ..core.timeutil import parse_iso
from ..storage.base import atomic_write_json, read_json


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def required_quarters(first_room, last_room, seconds):
    if not all(number(v) for v in (first_room, last_room, seconds)) or seconds < 3600:
        return 8
    if last_room >= 21.5:
        return 8
    gain = last_room - first_room
    if gain < 0.1:
        return 16
    return max(8, min(16, ceil(max(0, 21.6 - first_room) / gain * seconds / 900) + 1))


def response_state(config):
    return read_json(config.data_dir / "thermal-response.json", {}) or {}


def preheat_quarters(config, moment):
    saved = response_state(config)
    stamp = parse_iso(saved.get("assessed_at"))
    lead = saved.get("lead_quarters")
    if (
        stamp is None
        or not 0 <= (moment - stamp).total_seconds() <= 7 * 86400
        or isinstance(lead, bool)
        or not isinstance(lead, int)
    ):
        return 8
    return max(8, min(16, lead))


def planning_preheat_quarters(config, day, moment):
    # A learned outcome must never move today's completed preheat into the past.
    # Freeze today's published lead; apply new observations to future dates.
    if day == moment.date().isoformat():
        meta = config.get("tng.thermostat.date_overrides", {}).get(day, {}).get("price_shift", {})
        minutes = meta.get("required_preheat_minutes")
        if isinstance(minutes, int) and not isinstance(minutes, bool) and 120 <= minutes <= 240:
            return minutes // 15
    return preheat_quarters(config, moment)


def observe_response(config, state, moment):
    """Called only by the unified thermal resolver on its existing TNG poll."""
    saved = response_state(config)
    original = deepcopy(saved)
    if not (
        config.get("tng.price_shift.enabled", False)
        and config.get("tng.write_enabled", False)
        and config.get("tng.heating.enabled", False)
        and config.get("tng.thermostat.enabled", False)
    ):
        if saved.get("active") and not saved["active"].get("invalid"):
            saved["active"]["invalid"] = True
            atomic_write_json(config.data_dir / "thermal-response.json", saved)
        return saved
    hp = state.get("heatpump") or {}
    stamp = parse_iso(hp.get("sample_time"))
    room = hp.get("room_temperature")
    fresh = (
        stamp is not None
        and 0 <= (moment - stamp).total_seconds() <= 900
        and number(room)
        and 0 <= room <= 40
    )
    if not fresh:
        return saved
    # Schedules use local Prague wall time; telemetry is often UTC.
    from zoneinfo import ZoneInfo

    local = moment.astimezone(ZoneInfo("Europe/Prague"))
    day = local.date().isoformat()
    index = local.hour * 4 + local.minute // 15
    override = config.get("tng.thermostat.date_overrides", {}).get(day, {})
    from .price import fingerprint

    owned = override.get("price_shift", {}).get("schedule_hash") == fingerprint(
        {k: override.get(k) for k in ("default_temperature", "schedule")}
    )
    heating = config.get("tng.heating.date_overrides", {}).get(day, {})
    owned = owned and heating.get("price_shift", {}).get("schedule_hash") == fingerprint(
        {k: heating.get(k) for k in ("default_temperature", "schedule")}
    )
    phases = override.get("price_shift", {}).get("phases", []) if owned else []
    phase = next((p for p in phases if p["kind"] == "preheat" and p["start"] <= index < p["end"]), None)
    active = saved.get("active") or {}
    previous = parse_iso(active.get("last_at"))
    if active and (not phase or active.get("key") != f"{day}:{phase['start']}"):
        first = parse_iso(active.get("first_at"))
        valid = (
            first is not None
            and previous is not None
            and active.get("day") == day
            and owned
            and active.get("count", 0) >= 6
            and not active.get("invalid")
            and 0 <= (stamp - previous).total_seconds() <= 900
        )
        if valid:
            seconds = (previous - first).total_seconds()
            lead = required_quarters(active["first_room"], active["last_room"], seconds)
            if seconds >= 3600:
                saved.update(
                    lead_quarters=max(preheat_quarters(config, moment), lead),
                    assessed_at=moment.isoformat(),
                    last_outcome=dict(
                        day=day,
                        first_room=active["first_room"],
                        last_room=active["last_room"],
                        observed_minutes=seconds / 60,
                        ready=active["last_room"] >= 21.5,
                        evidence="confirmed_thermostat_and_room_samples",
                    ),
                )
        saved.pop("active", None)
        active = {}
    settings = state.get("settings") or {}
    confirmed = (
        state.get("LastSettingsNotConfirmed") is False
        and number(state.get("DayTemperature"))
        and abs(state["DayTemperature"] - 21.7) < .05
        and settings.get("heating_on") is True
        and settings.get("boiler_on") is False
    )
    if phase:
        if confirmed:
            if not active:
                active = dict(
                    key=f"{day}:{phase['start']}",
                    day=day,
                    first_at=stamp.isoformat(),
                    first_room=room,
                    count=0,
                )
            previous = parse_iso(active.get("last_at"))
            if previous is None or stamp > previous:
                if previous and (stamp - previous).total_seconds() > 900:
                    active["invalid"] = True
                active.update(last_at=stamp.isoformat(), last_room=room, count=active["count"] + 1)
            saved["active"] = active
        elif active:
            active["invalid"] = True
    if saved != original:
        atomic_write_json(config.data_dir / "thermal-response.json", saved)
    return saved
