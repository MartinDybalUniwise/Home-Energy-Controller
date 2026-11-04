"""Conservative price arbitrage using bounded charging and General self-consumption.

No forced discharge/export. Capacity and PV forecasts are deliberately not treated
as measured energy; a 60% grid ceiling leaves solar headroom. Model economics are
estimates, never a claim of realised savings.
"""

from datetime import timedelta
from math import ceil, isfinite

from ..core.model import Decision
from ..core.timeutil import parse_iso
from ..storage.base import atomic_write_json, read_json
from .price import build_plan, clock


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def peak_reservation(prices, index, row, capacity, minimum, ceiling):
    """Reserve estimated energy for a sustained dearer peak, not the first profit.

    Capacity is configured and demand is estimated from current house power.
    Neither is presented as measured future consumption. No device writes here.
    """
    result = dict(active=False, basis="configured_capacity_current_house_load_estimate")
    if not prices or not number(row.get("house_w")) or not number(row.get("battery_soc")):
        return result
    end = min(96, index + 49)
    hours = [(sum(prices[j:j + 4]) / 4, j) for j in range(index + 1, end - 3)]
    if not hours:
        return result
    # On a flat expensive plateau, reserve for its beginning, not its final
    # hour; otherwise the estimated protected demand is understated.
    price, start = max(hours, key=lambda pair: pair[0])
    if price < prices[index] + max(0.6, abs(prices[index]) * 0.08):
        return result
    slots = [j for j in range(start, end) if prices[j] >= price - 0.3]
    required = max(0.5, row["house_w"] / 1000) * len(slots) / 4
    soc = row["battery_soc"]
    reserve = min(ceiling, int(soc))
    if number(capacity) and capacity > 0:
        reserve = min(reserve, max(minimum, ceil(minimum + required / (capacity * 0.9) * 100)))
    result.update(active=reserve > minimum, reserve_pct=reserve, peak_from=clock(start),
                  peak_mean_czk_kwh=round(price, 4), estimated_required_kwh=round(required, 3))
    return result


def charging_windows(payload, day, settings):
    if not build_plan(payload, day, {})["prices_valid"]:
        return [], []
    prices = [row["price_total_czk_kwh"] for row in payload["periods"]]
    eta = settings.get("roundtrip_efficiency", 0.90)
    wear = settings.get("wear_czk_kwh", 0.30)
    margin = settings.get("minimum_profit_czk_kwh", 0.50)
    if not 0.5 <= eta <= 1 or wear < 0 or margin < 0.3:
        return [], []
    # Require a sustained future peak (one hour), within twelve hours. A single
    # price spike is insufficient justification to charge a battery.
    eligible = []
    for i, price in enumerate(prices):
        peaks = [sum(prices[j : j + 4]) / 4 for j in range(i + 4, min(93, i + 49))]
        eligible.append(
            payload["periods"][i].get("distribution_tariff") != "VT"
            and bool(peaks)
            and max(peaks) - price / eta - wear >= margin
        )
    windows = []
    i = 0
    while i < 95:
        if not eligible[i]:
            i += 1
            continue
        start = i
        while i < 95 and eligible[i]:
            i += 1
        # Pick the cheapest contiguous block, preferring a later nearly equal
        # block. Don't miss a midday valley by taking the first merely eligible
        # three hours of a long run; never repeat blocks within that run.
        if i - start >= 4:
            width = min(12, i - start)
            costs = {j: sum(prices[j : j + width]) / width for j in range(start, i - width + 1)}
            cheapest = min(costs.values())
            chosen = max(j for j, cost in costs.items() if cost <= cheapest + 0.10)
            windows.append(
                {
                    "from": clock(chosen),
                    "to": clock(chosen + width),
                    "max_price": max(prices[chosen : chosen + width]),
                }
            )
    return windows, prices


def comfort_supply(payload, windows, prices, moment, thermal, tng, row, power, efficiency=0.90):
    """Prioritise present comfort during VT if a cheaper refill can cover demand.

    Demand/refill quantities are estimates from current measured house power,
    not a claim of future load, capacity or solar production. No forced discharge.
    """
    thermal, tng = thermal or {}, tng or {}
    stamp = parse_iso(tng.get("sample_time"))
    planned = parse_iso(thermal.get("planned_at"))
    room = tng.get("room_temperature")
    floor = thermal.get('floor_check') or {}
    floor_need = (floor.get('phase') in ('testing', 'reheating')
                  and floor.get('request_sent_at') is not None)
    index = moment.hour * 4 + moment.minute // 15
    result = dict(allowed=False, demand_quality="estimate_from_current_house_power")
    if (
        not prices
        or payload["periods"][index].get("distribution_tariff") != "VT"
        or stamp is None
        or not 0 <= (moment - stamp).total_seconds() <= 900
        or planned is None
        or not 0 <= (moment - planned).total_seconds() <= 360
        or thermal.get("mode") != "heating"
        or tng.get("heating_on") is not True
        or not number(room)
        or not 0 <= room < (24 if floor_need else 21.5)
        or thermal.get("phase") not in ("comfort_veto", "comfort_guard", "normal", "schedule", "floor_test", "floor_reheat")
        or not number(row.get("house_w"))
        or not number(row.get("rated_power_w"))
        or power < 5
    ):
        return result
    end = index + 1
    while end < 96 and payload["periods"][end].get("distribution_tariff") == "VT":
        end += 1
    prior = [
        prices[i]
        for i in range(max(0, index - 24), index)
        if payload["periods"][i].get("distribution_tariff") == "NT"
    ]
    if not prior or prices[index] - min(prior) < max(0.6, abs(min(prior)) * 0.08):
        return result
    remaining_hours = (end * 15 - moment.hour * 60 - moment.minute) / 60
    required = max(0, row["house_w"]) / 1000 * remaining_hours
    for window in windows:
        start = int(window["from"][:2]) * 4 + int(window["from"][3:]) // 15
        stop = int(window["to"][:2]) * 4 + int(window["to"][3:]) // 15
        if not end <= start < min(96, index + 24):
            continue
        # A genuine cheaper, still-profitable refill, before the later peak.
        if window["max_price"] >= prices[index] - 0.10:
            continue
        refill = (stop - start) / 4 * row["rated_power_w"] / 1000 * power / 100 * efficiency
        if refill < required * 1.1:
            continue
        until = moment.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=end * 15)
        result.update(
            allowed=True,
            until=until.isoformat(),
            refill_window=window,
            estimated_required_kwh=round(required, 3),
            estimated_refill_kwh=round(refill, 3),
        )
        break
    return result


class BatteryPlanner:
    def __init__(self, config):
        self.config = config
        self.path = config.data_dir / "battery-economic-state.json"
        self.memory = read_json(self.path, {}) or {}
        self.state = None
        self.last_attempt = None
        self.last_result = None

    def remember(self, decision, applied):
        if not applied:
            return
        if decision.action == "start_battery_charge":
            self.memory.update(
                owned=True,
                basis=max(self.memory.get("basis", float("-inf")), decision.reason_params["basis"]),
                purchased_day=decision.timestamp.date().isoformat(),
            )
            self.memory["hold_until"] = (decision.timestamp + timedelta(hours=12)).isoformat()
        elif decision.action == "stop_battery_control":
            self.memory["owned"] = False
        atomic_write_json(self.path, self.memory)

    def prepare_write(self, decision):
        # Persist ownership before the hardware write: a crash after acceptance
        # must not leave a program that a restarted controller thinks is manual.
        if decision.action == "start_battery_charge":
            self.remember(decision, True)

    def decide(self, values, payload, moment, thermal=None, tng=None):
        settings = self.config.get("controller.optimization.goodwe_control.economic", {})
        windows, prices = charging_windows(payload, moment.date().isoformat(), settings)
        row = values or {}
        stamp = parse_iso(row.get("timestamp"))
        fresh = (
            row.get("online") is True and stamp is not None and -30 <= (moment - stamp).total_seconds() <= 90
        )
        fields = (
            "battery_soc",
            "pv_w",
            "house_w",
            "grid_import_w",
            "battery_charge_w",
            "battery_v",
            "battery_temp_c",
            "charge_current_limit_a",
            "rated_power_w",
            "on_grid_soc_limit_pct",
        )
        valid = fresh and all(number(row.get(key)) for key in fields)
        index = moment.hour * 4 + moment.minute // 15
        price = prices[index] if prices else None
        current = next((w for w in windows if w["from"] <= moment.strftime("%H:%M") < w["to"]), None)
        eta = settings.get("roundtrip_efficiency", 0.90)
        wear = settings.get("wear_czk_kwh", 0.30)
        margin = settings.get("minimum_profit_czk_kwh", 0.50)
        ceiling = min(60, max(20, int(settings.get("grid_target_soc_pct", 60))))
        minimum = min(20, max(10, int(settings.get("minimum_soc_pct", 20))))
        mode = row.get("operation_mode")
        phase, reason = "self_consumption", "No profitable charging window"
        action, value, params = None, None, {}
        soc = row.get("battery_soc")
        reserve = row.get("on_grid_soc_limit_pct")
        owned = self.memory.get("owned", False)
        basis = self.memory.get("basis")
        usable_basis = number(basis)
        deadline = parse_iso(self.memory.get("hold_until"))
        expired = deadline is not None and moment >= deadline
        release = (
            valid and price is not None and usable_basis and (expired or price - basis / eta - wear >= margin)
        )
        safe = (
            valid
            and prices
            and 0 <= soc <= 100
            and 10 <= row["battery_temp_c"] <= 45
            and row["battery_v"] > 100
            and row["charge_current_limit_a"] > 0
        )
        device_clock = parse_iso(row.get("inverter_time"))
        clock_ok = device_clock is not None and abs((moment - device_clock).total_seconds()) <= 120
        safe = safe and clock_ok
        # Native charging is stopped before restoring normal discharge reserves.
        # Unknown/manual non-General modes are never silently commandeered.
        grid_limit = min(7000, settings.get("max_grid_import_w", 7000))
        headroom = (grid_limit - row["grid_import_w"] + row["battery_charge_w"]) if valid else 0
        power = (
            min(
                20,
                settings.get("charge_power_pct", 20),
                int(max(0, headroom - 500) / row["rated_power_w"] * 100),
                int(row["battery_v"] * row["charge_current_limit_a"] * 0.8 / row["rated_power_w"] * 100),
            )
            if valid and row["rated_power_w"] > 0
            else 0
        )
        pv_surplus = valid and row["pv_w"] >= row["house_w"] + 300
        coordination = comfort_supply(payload, windows, prices, moment, thermal, tng, row, power, eta)
        thermal_stamp = parse_iso((thermal or {}).get("planned_at"))
        thermal_fresh = (
            thermal_stamp is not None
            and 0 <= (moment - thermal_stamp).total_seconds() <= 360
            and (thermal or {}).get("mode") == "heating"
        )
        until = parse_iso(self.memory.get("comfort_supply_until"))
        comfort_release = (
            valid
            and safe
            and thermal_fresh
            and until is not None
            and moment < until
            and payload["periods"][index].get("distribution_tariff") == "VT"
        )
        if valid and safe and coordination.get("allowed"):
            comfort_release = True
            deadline_text = coordination["until"]
            if self.memory.get("comfort_supply_until") != deadline_text:
                self.memory["comfort_supply_until"] = deadline_text
                atomic_write_json(self.path, self.memory)
        release = release or comfort_release
        peak = peak_reservation(prices, index, row,
                                self.config.get("prediction.battery_capacity_kwh", 10), minimum, ceiling)
        if expired or comfort_release or not usable_basis:
            peak["active"] = False
        charge = (
            safe
            and current is not None
            and soc < ceiling - 2
            and power >= 5
            and not pv_surplus
            and payload["periods"][index].get("distribution_tariff") != "VT"
        )
        if not valid or not prices:
            phase, reason = "safe_mode", "Missing/stale GoodWe data or complete published prices"
        elif not safe:
            phase, reason = "safe_mode", "Battery temperature/BMS/voltage or inverter clock veto"
        elif pv_surplus:
            phase, reason = "solar", "Measured PV covers consumption; prefer natural solar charging"
        if owned and (not charge or row.get("grid_import_w", 0) > grid_limit):
            action, value = "stop_battery_control", None
        elif charge and (owned or mode == "GENERAL"):
            phase, reason = "charge", "Cheap now; sustained later peak covers model losses, wear and margin"
            # Lock the original end/power while this native schedule is valid;
            # only reduce power materially if grid headroom/BMS requires it.
            program = row.get("battery_program") or {}
            matches = (
                owned
                and mode == "ECO"
                and program.get("enabled") is True
                and isinstance(program.get("valid_from"), str)
                and program["valid_from"] <= moment.strftime("%H:%M")
                and program.get("valid_to") == current["to"]
                and program.get("day_bits") == 1 << ((moment.weekday() + 1) % 7)
                and program.get("stop_soc_pct") == ceiling
                and program.get("work_mode") == 3
                and program.get("other_groups") == [0, 0, 0]
                and number(program.get("power_pct"))
                and 5 <= -program["power_pct"] <= power + 2
            )
            if not matches:
                action, value = "start_battery_charge", power
                params = dict(
                    power_pct=power,
                    start_soc_pct=int(soc),
                    stop_soc_pct=ceiling,
                    valid_from=moment.strftime("%H:%M"),
                    valid_to=current["to"],
                    valid_day=moment.date().isoformat(),
                    basis=current["max_price"],
                )
        elif safe and mode == "GENERAL":
            # Hold bought energy until it is worth using; PV energy can still fill
            # the remaining capacity. No forced export, no inferred PV forecast.
            hold = usable_basis and soc > minimum and not release and prices
            target = min(ceiling, int(soc)) if hold else min(minimum, int(soc))
            if peak.get("active"):
                target = max(target, peak["reserve_pct"])
                hold = True
            phase = "hold" if hold else ("release" if release else phase)
            if hold:
                reason = ("Reserve estimated house demand for the later sustained dearer peak"
                          if peak.get("active") else
                          "Retain purchased energy for a profitable price; General mode still accepts PV")
            elif comfort_release:
                reason = "Current comfort heating in VT has priority; sufficient cheaper refill precedes the later peak"
            elif release:
                reason = (
                    "Hold deadline passed; restore normal self-consumption, no forced export"
                    if expired
                    else "Profitable consumption now; General mode supplies the house, no forced export"
                )
            if reserve != target and (not hold or abs(reserve - target) >= 5):
                action, value = "set_on_grid_soc_limit_pct", target
            if soc <= minimum and usable_basis and not owned:
                self.memory.pop("basis", None)
                atomic_write_json(self.path, self.memory)
        elif valid and not owned and mode != "GENERAL":
            phase, reason = "external_mode", "External/manual inverter mode; HEC will not overwrite it"
        self.state = dict(
            timestamp=moment.isoformat(),
            date=moment.date().isoformat(),
            phase=phase,
            reason=reason,
            prices_valid=bool(prices),
            data_valid=bool(valid),
            windows=windows,
            price_czk_kwh=price,
            grid_target_soc_pct=ceiling,
            minimum_soc_pct=minimum,
            charge_power_limit_pct=min(20, settings.get("charge_power_pct", 20)),
            efficiency_assumption=eta,
            wear_assumption_czk_kwh=wear,
            minimum_profit_czk_kwh=margin,
            planned_charge_price_basis=basis,
            actual_mode=mode,
            actual_soc=soc,
            actual_reserve_pct=reserve,
            last_command=self.last_result,
            force_discharge=False,
            next_action=action,
            coordination=coordination,
            peak_reservation=peak,
            release_reason="comfort_peak" if comfort_release else None,
        )
        urgent_release = comfort_release and action == "set_on_grid_soc_limit_pct" and value < reserve
        if action is None or (
            action != "stop_battery_control"
            and not urgent_release
            and self.last_attempt
            and moment - self.last_attempt < timedelta(seconds=300)
        ):
            return []
        self.last_attempt = moment
        return [
            Decision(
                rule="battery_economic",
                action=action,
                value=value,
                reason_key="reason.battery_economic",
                reason_params={**params, "explanation": reason},
                timestamp=moment,
            )
        ]
