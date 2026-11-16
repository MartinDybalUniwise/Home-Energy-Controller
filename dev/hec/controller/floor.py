"""Hourly bounded floor-heating checks inside the unified thermal resolver.

Pump activity is an explicit owner assumption from confirmed thermostat demand,
never a measured relay/compressor state. No device IO occurs in this module.
"""

from copy import deepcopy
from datetime import timedelta
from math import isfinite

from ..core.timeutil import parse_iso
from ..storage.base import atomic_write_json, read_json

ACTIVE_PHASES = ("preparing", "requesting", "testing", "reheating", "restoring")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def qualified_aku(wire, heatpump, moment):
    stamp = parse_iso((wire or {}).get("sample_time") or (wire or {}).get("timestamp"))
    cloud = parse_iso(heatpump.get("sample_time"))
    if (
        stamp is None
        or cloud is None
        or not 0 <= (moment - stamp).total_seconds() <= 180
        or not 0 <= (moment - cloud).total_seconds() <= 900
        or (wire or {}).get("online") is not True
    ):
        return None, "stale"
    value = wire.get("buffer_temperature")
    if (
        not number(value)
        or not 30.0 <= value <= 41.5
        or wire.get("field_quality", {}).get("buffer_temperature") != ("owner_extended_provisional" if value < 34.2 else "photo_validated_provisional")
    ):
        return None, "outside_validated_range"
    # Narrow owner-approved use of this photo-checked field. Unresolved packet
    # flags, high-temperature branches and global control_eligible remain unused.
    for key in ("room_temperature", "water_output_temperature", "outside_temperature"):
        a, b = wire.get(key), heatpump.get(key)
        if not number(a) or not number(b) or abs(a - b) > 0.8:
            return None, "cloud_crosscheck_failed"
    return value, ("owner_extended_range_cloud_crosschecked" if value < 34.2 else "photo_range_cloud_crosschecked")


def floor_plan(config, base, state, wire, gates, moment):
    cfg = config.get("tng.floor_check", {})
    path = config.data_dir / "floor-circulation-state.json"
    saved = read_json(path, {}) or {}
    enabled = cfg.get("enabled", False)
    if not enabled and not saved:
        return base
    original = deepcopy(saved)
    plan = dict(base)
    hp, settings = state.get("heatpump") or {}, state.get("settings") or {}
    room = hp.get("room_temperature")
    stamp = parse_iso(hp.get("sample_time"))
    fresh = (
        stamp is not None
        and 0 <= (moment - stamp).total_seconds() <= 900
        and number(room)
        and 0 <= room <= 40
    )
    aku, aku_quality = qualified_aku(wire, hp, moment)
    idle = int(cfg.get("idle_minutes", 60))
    probe = int(cfg.get("probe_minutes", 15))
    maximum = int(cfg.get("max_cycle_minutes", 45))
    minimum = float(cfg.get("minimum_aku_c", 35))
    recovery = float(cfg.get("recovery_aku_c", 38))
    water = float(cfg.get("water_target_c", 42))
    ceiling = float(cfg.get("maximum_room_request_c", 24))
    valid_cfg = (
        60 <= idle <= 240
        and 15 <= probe <= maximum <= 60
        and 34.5 <= minimum < recovery <= 41.5
        and 35 <= water <= 42
        and 21.7 <= ceiling <= 26
    )
    permissions = (
        enabled
        and config.get("tng.write_enabled", False)
        and config.get("tng.heating.enabled", False)
        and config.get("tng.thermostat.enabled", False)
    )
    safe_mode = base.get("mode") == "heating"
    default_start = parse_iso(cfg.get("activated_at")) or moment
    saved.setdefault("last_assumed_activity_at", default_start.isoformat())
    active = saved.get("active")
    reason = "waiting_for_idle_hour"
    phase = "idle"
    adaptive = cfg.get("adaptive_enabled", True)
    cold = fresh and (room <= 21.3 or (aku is not None and aku < minimum))
    coast = base.get("phase") == "coast"
    next_due = None

    def begin_restore(why):
        active.update(stage="restoring", restore_requested_at=moment.isoformat(), outcome=why)

    if active:
        phase = active.get("stage", "requesting")
        if (
            not permissions
            or not valid_cfg
            or not safe_mode
            or not fresh
            or room >= ceiling
            or settings.get("external_circulation_pump") is not True
        ):
            if phase != "restoring":
                begin_restore("interrupted_or_invalid_inputs")
        created = parse_iso(active.get("created_at")) or moment
        sent = parse_iso(active.get("request_sent_at"))
        thermostat_gate = gates.get("thermostat", {})
        posted = parse_iso(thermostat_gate.get("last_post_at"))
        if (
            sent is None
            and posted is not None
            and posted >= created
            and (thermostat_gate.get("last_requested") or {}).get("day_temperature")
            == active["room_request_c"]
        ):
            active["request_sent_at"] = posted.isoformat()
            sent = posted
        acknowledged = (
            sent is not None
            and state.get("LastSettingsNotConfirmed") is False
            and thermostat_gate.get("awaiting_confirmation") is False
            and number(state.get("DayTemperature"))
            and abs(state["DayTemperature"] - active["room_request_c"]) < 0.05
        )
        if acknowledged:
            active.setdefault("acknowledged_at", moment.isoformat())
        if active.get("stage") != "restoring":
            if sent is None and (moment - created).total_seconds() >= 1800:
                begin_restore("request_not_sent_timeout")
            elif sent is not None:
                elapsed = max(0, (moment - sent).total_seconds() / 60)
                active["stage"] = "reheating" if active.get("below_minimum_seen") else "testing"
                if aku is not None:
                    active["minimum_observed_aku_c"] = min(active.get("minimum_observed_aku_c", aku), aku)
                    if aku < minimum:
                        active["below_minimum_seen"] = True
                        active["stage"] = "reheating"
                    sample_at = (wire or {}).get("sample_time") or (wire or {}).get("timestamp")
                    tail = active.setdefault("recent_aku", [])
                    if not tail or tail[-1]["sample_time"] != sample_at:
                        tail.append(dict(sample_time=sample_at, aku_c=aku))
                        del tail[:-5]
                for minute in (2, 5, 10, 15):
                    checks = active.setdefault("observations", {})
                    if elapsed >= minute and str(minute) not in checks:
                        timely = aku is not None and elapsed <= minute + 2
                        quality = (wire or {}).get("field_quality", {})
                        checks[str(minute)] = dict(
                            sample_time=((wire or {}).get("sample_time") or (wire or {}).get("timestamp"))
                            if timely
                            else None,
                            aku_c=aku if timely else None,
                            observed_elapsed_minutes=round(elapsed, 2),
                            quality=aku_quality if timely else "missed_or_invalid_sample",
                            inlet_c=(wire or {}).get("water_input_temperature")
                            if timely
                            and quality.get("water_input_temperature") == "photo_validated_provisional"
                            else None,
                            outlet_c=(wire or {}).get("water_output_temperature")
                            if timely
                            and quality.get("water_output_temperature") == "photo_validated_provisional"
                            else None,
                        )
                tail = active.get("recent_aku", [])
                stable = (
                    len(tail) >= 3
                    and max(x["aku_c"] for x in tail[-3:]) - min(x["aku_c"] for x in tail[-3:]) <= 0.3 + 1e-9
                    and (
                        parse_iso(tail[-1]["sample_time"]) - parse_iso(tail[-3]["sample_time"])
                    ).total_seconds()
                    >= 100
                )
                if elapsed >= maximum:
                    begin_restore("maximum_duration_reached")
                elif (adaptive and coast and not cold and aku is not None
                      and elapsed >= probe and not active.get("below_minimum_seen")):
                    begin_restore("price_coast_without_cold_buffer")
                elif acknowledged and elapsed >= probe and aku is not None and aku >= recovery and stable:
                    begin_restore("buffer_stable_and_recovered")
        if active.get("stage") == "restoring":
            phase, reason = "restoring", active.get("outcome")
            read_at = parse_iso(state.get("timestamp"))
            readback_fresh = read_at is not None and 0 <= (moment - read_at).total_seconds() <= 180
            # Restore the CURRENT common plan, never a stale saved room schedule.
            if (
                (fresh or readback_fresh)
                and state.get("LastSettingsNotConfirmed") is False
                and gates.get("thermostat", {}).get("awaiting_confirmation") is False
                and number(state.get("DayTemperature"))
                and number(base.get("room_target"))
                and abs(state["DayTemperature"] - base["room_target"]) < 0.05
            ):
                saved["last_cycle"] = {k: v for k, v in active.items() if k != "recent_aku"}
                saved["last_cycle"]["restored_at"] = moment.isoformat()
                saved["last_assumed_activity_at"] = moment.isoformat()
                saved.pop("active", None)
                active = None
                phase = "idle"
        else:
            phase = active["stage"]
            plan["heating_temperature"] = water
            basic_ready = (
                settings.get("heating_on") is True
                and settings.get("boiler_on") is False
                and settings.get("heating_set_temperature") == water
                and settings.get("last_settings_not_confirmed") is False
                and gates.get("basic", {}).get("awaiting_confirmation") is False
            )
            if sent is not None or basic_ready:
                plan["room_target"] = active["room_request_c"]
                if sent is None:
                    active["stage"] = phase = "requesting"
            else:
                active["stage"] = phase = "preparing"
            reason = (
                "aku_below_35"
                if active.get("below_minimum_seen")
                else "bounded_heating_request_for_floor_check"
            )
            plan["phase"] = "floor_reheat" if active.get("below_minimum_seen") else "floor_test"
    else:
        if not permissions:
            phase, reason = "disabled", "disabled_or_write_not_allowed"
        elif not valid_cfg:
            phase, reason = "blocked", "invalid_configuration"
        elif not safe_mode:
            phase, reason = "deferred", "exclusive_mode_or_explicit_off"
        elif not fresh:
            phase, reason = "blocked", "stale_room"
        else:
            actual_target = state.get("DayTemperature")
            confirmed = (
                state.get("LastSettingsNotConfirmed") is False
                and settings.get("last_settings_not_confirmed") is False
                and gates.get("thermostat", {}).get("awaiting_confirmation") is False
                and gates.get("basic", {}).get("awaiting_confirmation") is False
            )
            assumed_heating = (
                confirmed
                and settings.get("heating_on") is True
                and settings.get("boiler_on") is False
                and number(actual_target)
                and room <= actual_target
            )
            if assumed_heating:
                if stamp > (parse_iso(saved["last_assumed_activity_at"]) or stamp):
                    saved["last_assumed_activity_at"] = stamp.isoformat()
                reason = "heating_assumed_from_confirmed_thermostat_demand"
            last = parse_iso(saved["last_assumed_activity_at"]) or moment
            due = moment >= last + timedelta(minutes=idle)
            if due and not assumed_heating:
                target = round(min(ceiling, room + float(cfg.get("room_request_offset_c", 0.5))), 1)
                if settings.get("external_circulation_pump") is not True:
                    phase, reason = "blocked", "external_pump_not_enabled"
                elif not confirmed:
                    phase, reason = "deferred", "pending_tng_confirmation"
                elif room >= ceiling or target - room < 0.3 - 1e-9:
                    phase, reason = "blocked", "room_request_ceiling"
                elif aku is None:
                    phase, reason = "blocked", "aku_" + aku_quality
                elif (adaptive and not cold and moment < last + timedelta(minutes=max(idle, 120))
                      and (coast or (aku >= recovery and room >= 21.5)
                           or (saved.get("last_cycle") or {}).get("outcome") == "maximum_duration_reached")):
                    phase, reason = "deferred", "price_coast_or_store_already_warm"
                    next_due = last + timedelta(minutes=max(idle, 120))
                else:
                    saved["active"] = dict(
                        stage="preparing",
                        created_at=moment.isoformat(),
                        room_request_c=target,
                        initial_aku_c=aku,
                        initial_room_c=room,
                        activity_basis="owner_assumption_pump_runs_with_heating",
                    )
                    # Next pass arms through the normal writer; never recurse or send here.
                    phase, reason = "preparing", "hour_without_assumed_heating"
                    plan["heating_temperature"] = water
                    plan["phase"] = "floor_test"
    last = parse_iso(saved.get("last_assumed_activity_at")) or moment
    active = saved.get("active")
    restoring_at = parse_iso((active or {}).get("restore_requested_at"))
    restoration_wait = max(0, (moment - restoring_at).total_seconds() / 60) if restoring_at else 0
    info = dict(
        enabled=bool(enabled),
        phase=phase,
        reason=reason,
        activity_basis="owner_assumption_from_confirmed_thermostat_demand",
        pump_run_measured=False,
        aku_c=aku,
        aku_quality=aku_quality,
        next_check_at=(next_due or max(last + timedelta(minutes=idle), moment + timedelta(seconds=60))).isoformat()
        if not active else None,
        next_evaluation_at=(moment + timedelta(seconds=60 if active else 300)).isoformat(),
        restoration_wait_minutes=round(restoration_wait, 1),
        confirmation_delayed=restoration_wait >= 20,
        adaptive_enabled=adaptive,
        last_cycle=saved.get("last_cycle"),
        request_sent_at=(active or {}).get("request_sent_at"),
        acknowledged_at=(active or {}).get("acknowledged_at"),
        observations=(active or {}).get("observations", {}),
        temporary_room_request_c=(active or {}).get("room_request_c"),
        maximum_duration_minutes=maximum,
    )
    if saved != original:
        atomic_write_json(path, saved)
    plan["floor_check"] = info
    return plan
