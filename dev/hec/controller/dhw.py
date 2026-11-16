"""Conditional second ordinary DHW window inside the single thermal resolver."""
from datetime import timedelta

from ..core.timeutil import in_window, parse_iso
from ..storage.base import atomic_write_json, read_json
from .floor import number
from .recovery import fresh_sample


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


def catchup_plan(config, state, gates, moment, scheduled, mode, target, comfort, safety):
    """A bounded debt window, resolved here and transported by the same writer.

    Wall-clock deadlines survive restarts. They limit the requested window;
    native restoration still needs the unchanged 900s/ack gates and live service.
    """
    path = config.data_dir / 'dhw-catchup-state.json'
    saved = read_json(path, {}) or {}
    original = dict(saved)
    day = moment.date().isoformat()
    if saved.get('day') != day:
        # Never carry a previous day's active command/deadline into a new window.
        saved = dict(day=day, debt=False, attempts=0)
    hp = state.get('heatpump') or {}
    stamp = fresh_sample(hp, moment)
    value = hp.get('boiler_temperature')
    valid = stamp is not None and number(value) and 0 <= value <= 80
    operation = config.get('tng.operation', {})
    explicit = (day in operation.get('date_overrides', {})
                or day in config.get('tng.boiler.date_overrides', {}))
    eligible = (config.get('tng.write_enabled', False)
                and config.get('tng.heating.enabled', False)
                and config.get('tng.boiler.enabled', False)
                and config.get('tng.thermostat.enabled', False)
                and scheduled != 'off' and operation.get('default_mode') == 'heating' and not explicit)
    if scheduled == 'boiler' and comfort:
        saved['debt'] = True
    if valid and moment.hour >= 16 and value < 43:
        saved['debt'] = True
    if valid and value >= 50:
        saved['debt'] = False
    start = parse_iso(saved.get('started_at'))
    reason = 'no_debt'
    if start:
        elapsed = (moment - start).total_seconds()
        if (not eligible or not valid or comfort or scheduled != 'heating'
                or value >= 50 or elapsed < 0 or elapsed >= 2700):
            saved.pop('started_at', None)
            saved['last_end_at'] = moment.isoformat()
            reason = 'restore_heating'
        else:
            mode, target, reason = 'boiler', 50, 'bounded_catchup'
    elif saved.get('debt'):
        reason = 'deferred_for_comfort'
        upcoming = False
        for window in operation.get('schedule', []):
            if window.get('mode') != 'boiler':
                continue
            hour, minute = map(int, window['from'].split(':'))
            scheduled_start = moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled_start <= moment:
                scheduled_start += timedelta(days=1)
            upcoming = upcoming or (scheduled_start - moment).total_seconds() <= 5400
        ended = parse_iso(saved.get('last_end_at'))
        cooldown = ended is None or (moment - ended).total_seconds() >= 3600
        settings = state.get('settings') or {}
        minimum = max(900, config.get('tng.minimum_change_interval_seconds', 900))
        clear = (state.get('LastSettingsNotConfirmed') is False
                 and settings.get('last_settings_not_confirmed') is False
                 and settings.get('heating_on') is True and settings.get('boiler_on') is False)
        for key in ('basic', 'thermostat'):
            gate = gates.get(key, {})
            posted = parse_iso(gate.get('last_post_at'))
            clear = (clear and gate.get('awaiting_confirmation') is False
                     and (posted is None or (moment - posted).total_seconds() >= minimum))
        if (eligible and valid and scheduled == mode == 'heating' and not comfort
                and safety.get('stable_recovery') and not safety.get('response_fault')
                and not upcoming
                and hp['room_temperature'] >= 21.5 and 11 <= moment.hour < 22
                and value < 48 and saved.get('attempts', 0) < 2 and cooldown and clear):
            saved.update(started_at=moment.isoformat(), attempts=saved.get('attempts', 0) + 1)
            mode, target, reason = 'boiler', 50, 'bounded_catchup'
        elif explicit or not eligible:
            reason = 'owner_schedule_or_disabled'
        elif not valid:
            reason = 'stale_or_unknown_boiler'
        elif saved.get('attempts', 0) >= 2:
            reason = 'daily_attempt_limit'
        elif upcoming:
            reason = 'scheduled_dhw_soon'
    if saved != original:
        atomic_write_json(path, saved)
    return mode, target, dict(debt=bool(saved.get('debt')), active=reason == 'bounded_catchup',
                             reason=reason, started_at=saved.get('started_at'),
                             attempts=saved.get('attempts', 0), maximum_minutes=45,
                             target_c=50, measured_c=value if valid else None,
                             usable_hot_water_volume_known=False)
