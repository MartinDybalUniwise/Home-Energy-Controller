"""Conservative day-ahead load shifting. No inferred heat inventory or meter input."""

import json
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
from math import isfinite
from statistics import median
from zoneinfo import ZoneInfo

from ..core import config as config_mod
from ..core.electricity_price import load_priced_day
from ..core.timeutil import in_window, parse_iso
from ..storage.base import read_json
from .response import planning_preheat_quarters

VERSION = "price-shift-v1"
POLICY = "coordinated-peaks-v4"
ZONE = ZoneInfo("Europe/Prague")


def clock(index):
    return f"{index // 4:02}:{index % 4 * 15:02}"


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def operation_at(section, day, index):
    section = {**section, **section.get("date_overrides", {}).get(day, {})}
    mode = section.get("default_mode", "heating")
    for window in section.get("schedule", []):
        if in_window(datetime.fromisoformat(day + "T" + clock(index)), window["from"], window["to"]):
            mode = window["mode"]
    return mode


def earliest_quarter(config, day):
    stamps = [parse_iso(config.get(f"tng.price_shift.{key}")) for key in ("activated_at", "revised_at")]
    stamps = [stamp.astimezone(ZONE) for stamp in stamps if stamp is not None]
    if not stamps:
        return 0
    activated = max(stamps)
    return (activated.hour * 4 + activated.minute // 15 + 1) if activated.date().isoformat() == day else 0


def build_plan(payload, day, operation, earliest=0, preheat_width=8):
    """Require a complete unambiguous 24-hour published curve. DST days fall back."""
    periods = (payload or {}).get("periods", [])
    prices = []
    if (payload or {}).get("date") == day and len(periods) == 96:
        for index, row in enumerate(periods):
            price = row.get("price_total_czk_kwh")
            if (
                row.get("start") != clock(index)
                or row.get("end") != clock(index + 1)
                or isinstance(price, bool)
                or not isinstance(price, (int, float))
                or not isfinite(price)
            ):
                break
            prices.append(price)
    start = datetime.fromisoformat(day).replace(tzinfo=ZONE)
    if (start + timedelta(days=1)).utcoffset() != start.utcoffset():
        prices = []
    valid = len(prices) == 96
    phases = []
    if valid:
        index = 0
        while index < 96:
            # A dear evening must not hide a smaller morning rise. Compare each
            # local peak with the preceding six hours; freeze its entry threshold.
            baseline = median(prices[max(0, index - 24) : index]) if index else prices[0]
            threshold = baseline + 0.6
            if prices[index] < threshold:
                index += 1
                continue
            group_start = index
            peak_level = prices[index]
            while index < 96:
                # A material valley ends this peak even when midday stays a
                # little above the night baseline; otherwise two peaks merge.
                floor = max(threshold, peak_level - max(0.6, abs(peak_level) * 0.08))
                if prices[index] < floor:
                    break
                peak_level = max(peak_level, prices[index])
                index += 1
            group_end = index
            if group_end - group_start < 3:
                continue
            width = min(12, group_end - group_start)
            if group_end - group_start <= 12:
                price_start, end = group_start, group_end
                # Cover the rising edge too, rather than restarting during it.
                tariff_edge = (
                    periods[group_start].get("distribution_tariff") == "VT"
                    and group_start > 0
                    and periods[group_start - 1].get("distribution_tariff") == "NT"
                )
                coast_start = group_start if tariff_edge else max(0, group_start - 3, end - 12)
                # An NT price ramp immediately before VT must not consume the
                # very NT slots needed for preheat. Anchor at the first VT edge.
                tariff_edges = [j for j in range(group_start, group_end)
                                if j > 0 and periods[j].get('distribution_tariff') == 'VT'
                                and periods[j - 1].get('distribution_tariff') == 'NT']
                if tariff_edges:
                    price_start = coast_start = tariff_edges[0]
            else:
                price_start = max(
                    range(group_start, group_end - width + 1), key=lambda i: sum(prices[i : i + width])
                )
                coast_start, end = price_start, price_start + width
            if not all(operation_at(operation, day, j) == "heating" for j in range(coast_start, end)):
                coast_start = price_start
            if not all(operation_at(operation, day, j) == "heating" for j in range(coast_start, end)):
                continue
            if phases and coast_start <= phases[-1]["end"]:
                # A brief valley must not trigger another preheat or reset the
                # comfort latch. Join adjacent guards only within the same cap.
                previous = phases[-1]
                if end - previous["start"] <= 12:
                    previous["end"] = end
                continue
            expensive = sum(prices[price_start:end]) / (end - price_start)
            eligible = []
            # Use measured lead time when cheap/exclusive heating slots permit;
            # otherwise retain the longest feasible cheaper block, never VT.
            for pre_width in range(max(8, min(16, preheat_width)), 3, -1):
                candidates = [
                    i
                    for i in range(max(earliest, coast_start - 24), coast_start - pre_width + 1)
                    if all(operation_at(operation, day, j) == "heating" for j in range(i, i + pre_width))
                    and all(periods[j].get("distribution_tariff") != "VT" for j in range(i, i + pre_width))
                    and all(not (p["start"] < i + pre_width and p["end"] > i) for p in phases)
                ]
                averages = {i: sum(prices[i : i + pre_width]) / pre_width for i in candidates}
                eligible = [
                    i
                    for i in candidates
                    if expensive - averages[i] + 1e-9 >= max(0.6, abs(averages[i]) * 0.08)
                ]
                if eligible:
                    break
            if not eligible:
                continue
            cheapest = min(averages[i] for i in eligible)
            # Keep the store warm near the rise: up to 0.10 CZK/kWh is allowed
            # for a later preheat, while retaining the full minimum price gap.
            pre = max(i for i in eligible if averages[i] <= cheapest + 0.1 + 1e-9)
            phases.extend(
                [
                    {"start": pre, "end": pre + pre_width, "kind": "preheat"},
                    {"start": coast_start, "end": end, "kind": "coast"},
                ]
            )
    result = {
        "version": VERSION,
        "policy": POLICY,
        "prices_valid": valid,
        "phases": phases,
        "required_preheat_minutes": max(8, min(16, preheat_width)) * 15,
    }
    for name, normal in (("heating", 42), ("thermostat", 21.5)):
        result[name] = {
            "default_temperature": normal,
            "schedule": [
                {
                    "from": clock(p["start"]),
                    "to": clock(p["end"]),
                    "temperature": (42 if p["kind"] == "preheat" else 35)
                    if name == "heating"
                    else (21.7 if p["kind"] == "preheat" else 21.2),
                }
                for p in phases
            ],
        }
    result["input_hash"] = fingerprint([payload, operation, VERSION, POLICY, earliest, preheat_width])
    return result


def refresh_plans(config, moment):
    """Publish dated overrides; leave owner-edited dates alone. Never touch DHW."""
    with config_mod.WRITE_LOCK:
        return _refresh_plans_locked(config, moment)


def _refresh_plans_locked(config, moment):
    if not config.get("tng.price_shift.enabled", False):
        return []
    changes = []
    for delta in (0, 1):
        day = (moment.astimezone(ZONE).date() + timedelta(days=delta)).isoformat()
        operation = config.get("tng.operation", {})
        payload = load_priced_day(config, day)
        plan = build_plan(
            payload, day, operation, earliest_quarter(config, day), planning_preheat_quarters(config, day, moment)
        )
        existing = {
            name: config.get(f"tng.{name}.date_overrides", {}).get(day) for name in ("heating", "thermostat")
        }
        # Ownership is explicit and checked on every poll, not only on price changes.
        if any(
            value is not None
            and (
                value.get("price_shift", {}).get("version") != VERSION
                or value.get("price_shift", {}).get("schedule_hash")
                != fingerprint({k: value.get(k) for k in ("default_temperature", "schedule")})
            )
            for value in existing.values()
        ):
            continue
        if all(
            value and value.get("price_shift", {}).get("input_hash") == plan["input_hash"]
            for value in existing.values()
        ):
            continue
        raw = read_json(config.path, {})
        if not raw:
            continue
        for name in ("heating", "thermostat"):
            override = deepcopy(plan[name])
            override["price_shift"] = {
                k: plan[k] for k in ("version", "policy", "input_hash", "prices_valid", "phases", "required_preheat_minutes")
            }
            override["price_shift"]["schedule_hash"] = fingerprint(plan[name])
            raw.setdefault("tng", {}).setdefault(name, {}).setdefault("date_overrides", {})[day] = override
        # Save raw configuration to preserve environment references and private settings.
        saved = config_mod.Config(raw, path=config.path, root=config.root)
        errors = config_mod.save(saved, raw)
        if errors:
            raise ValueError("Invalid price-shift dated plan")
        for name in ("heating", "thermostat"):
            config.data["tng"][name]["date_overrides"] = deepcopy(saved.get(f"tng.{name}.date_overrides"))
        changes.append({"date": day, **plan})
    return changes


def solar_available(energy, moment, saved, room):
    """Start only on sustained measured export; never spend battery on extra heat.

    The heat-pump meter is intentionally absent: its phase fault prevents a
    reliable HP-only power estimate. Reserve 3 kW of actual export instead.
    """
    state = dict(saved)
    day = moment.astimezone(ZONE).date().isoformat()
    if state.get("day") != day:
        state = {"day": day, "used_seconds": 0}
    stamp = parse_iso((energy or {}).get("timestamp"))
    fields = ("pv_w", "house_w", "grid_export_w", "grid_import_w", "battery_discharge_w", "battery_soc")
    fresh = (
        stamp is not None
        and 0 <= (moment - stamp).total_seconds() <= 120
        and energy.get("online") is True
        and all(
            isinstance(energy.get(k), (int, float))
            and not isinstance(energy[k], bool)
            and isfinite(energy[k])
            and energy[k] >= 0
            for k in fields
        )
        and energy["battery_soc"] <= 100
    )
    if not fresh:
        state.pop("surplus_since", None)
        state.pop("active_at", None)
        return False, state, "stale_energy"
    previous = parse_iso(state.get("last_sample"))
    distinct = previous is None or stamp > previous
    if previous and (stamp - previous).total_seconds() > 600:
        state.pop("surplus_since", None)
        state.pop("active_at", None)
    active = parse_iso(state.get("active_at"))
    if active and distinct:
        state["used_seconds"] += max(0, min(600, (stamp - active).total_seconds()))
    permitted = (
        energy["battery_soc"] >= 20
        and energy["battery_discharge_w"] <= 100
        and energy["grid_import_w"] <= 200
        and room < 21.7
        and state["used_seconds"] < 7200
        and not state.get("ceiling_reached")
    )
    first = parse_iso(state.get("first_started"))
    if first is not None and (stamp - first).total_seconds() >= 7200:
        permitted = False
    if active and room >= 21.7:
        state["ceiling_reached"] = True
    if active:
        permitted = permitted and energy["pv_w"] >= energy["house_w"] - 200
    else:
        permitted = (
            permitted and energy["grid_export_w"] >= 3000 and energy["pv_w"] - energy["house_w"] >= 3000
        )
    if not permitted:
        state.pop("surplus_since", None)
        state.pop("active_at", None)
    elif distinct:
        state.setdefault("surplus_since", stamp.isoformat())
        if active or (stamp - parse_iso(state["surplus_since"])).total_seconds() >= 600:
            state["active_at"] = stamp.isoformat()
            state.setdefault("first_started", stamp.isoformat())
    if distinct:
        state["last_sample"] = stamp.isoformat()
    return bool(state.get("active_at")), state, "valid"


def evaluate_shift(config, heatpump, moment, saved, comfort_active, mode, energy=None, safety=None):
    """Runtime comfort veto overrides the saved price plan, never the TNG gates."""
    day = moment.astimezone(ZONE).date().isoformat()
    overrides = [
        config.get(f"tng.{name}.date_overrides", {}).get(day, {}) for name in ("heating", "thermostat")
    ]
    if any(
        o.get("price_shift", {}).get("version") != VERSION
        or o["price_shift"].get("schedule_hash")
        != fingerprint({k: o.get(k) for k in ("default_temperature", "schedule")})
        for o in overrides
    ):
        return None, saved
    state = deepcopy(saved)
    status = {"phase": "normal", "heating_temperature": 42, "room_target": 21.5}
    if not config.get("tng.price_shift.enabled", False):
        status["phase"] = "disabled"
        return status, state
    if mode != "heating" or not config.get("tng.heating.enabled") or not config.get("tng.thermostat.enabled"):
        status["phase"] = "exclusive_mode"
        state.get("solar", {}).pop("active_at", None)
        state.get("solar", {}).pop("surplus_since", None)
        return status, state
    room = heatpump.get("room_temperature")
    stamp = parse_iso(heatpump.get("sample_time"))
    if (
        stamp is None
        or not 0 <= (moment - stamp).total_seconds() <= 900
        or isinstance(room, bool)
        or not isinstance(room, (int, float))
        or not isfinite(room)
        or not 0 <= room <= 40
    ):
        status["phase"] = "stale_room"
        # Missing samples break evidence that a coast can safely continue.
        state["blocked"] = True
        return status, state
    if comfort_active:
        status["phase"] = "comfort_guard"
        state["blocked"] = True
        return status, state
    solar, solar_state, energy_quality = solar_available(energy, moment, state.get("solar", {}), room)
    state["solar"] = solar_state
    status["energy_quality"] = energy_quality
    if energy_quality != "valid":
        status["phase"] = "stale_energy"
        state["blocked"] = True
        return status, state
    meta = overrides[0]["price_shift"]
    payload = load_priced_day(config, day)
    plan = build_plan(
        payload,
        day,
        config.get("tng.operation", {}),
        earliest_quarter(config, day),
        planning_preheat_quarters(config, day, moment),
    )
    if not plan["prices_valid"] or plan["input_hash"] != meta.get("input_hash"):
        status["phase"] = "invalid_prices"
        return status, state
    if solar:
        status.update(phase="solar_preheat", room_target=21.7)
        return status, state
    local = moment.astimezone(ZONE)
    index = local.hour * 4 + local.minute // 15
    for phase in meta["phases"]:
        if not phase["start"] <= index < phase["end"]:
            continue
        key = f"{day}:{phase['start']}:{phase['kind']}"
        if state.get("key") != key:
            state.update(key=key, blocked=False)
            if safety is not None:
                state['readiness_accepted'] = bool(safety.get('coast_ready'))
            if phase["kind"] == "coast" and room < 21.5:
                state["blocked"] = True
        if phase["kind"] == "preheat":
            if room >= 21.7:
                state["blocked"] = True
            if not state["blocked"]:
                status.update(phase="preheat", room_target=21.7)
        else:
            # Do not stack an economic coast with the next DHW interruption.
            # No heat-inventory model can prove that the combined break is safe.
            dhw_follows = safety is not None and any(
                operation_at(config.get('tng.operation', {}), day, j) == 'boiler'
                for j in range(phase['end'], min(96, phase['end'] + 4)))
            readiness_veto = safety is not None and (
                not state.get('readiness_accepted') or safety.get('day_blocked')
                or safety.get('response_fault') or dhw_follows)
            if readiness_veto:
                state['blocked'] = True
                status['coast_readiness'] = safety
                status['dhw_follows_coast'] = dhw_follows
            if room <= 21.3:
                state["blocked"] = True
            if not state["blocked"]:
                status.update(phase="coast", heating_temperature=35, room_target=21.2)
            else:
                status["phase"] = "readiness_veto" if readiness_veto else "comfort_veto"
        break
    return status, state
