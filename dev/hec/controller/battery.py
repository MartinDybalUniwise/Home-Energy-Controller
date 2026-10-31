"""Conservative price arbitrage using bounded charging and General self-consumption.

No forced discharge/export. Capacity and PV forecasts are deliberately not treated
as measured energy; a 60% grid ceiling leaves solar headroom. Model economics are
estimates, never a claim of realised savings.
"""
from datetime import timedelta
from math import isfinite

from ..core.model import Decision
from ..core.timeutil import parse_iso
from ..storage.base import atomic_write_json, read_json
from .price import build_plan, clock


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def charging_windows(payload, day, settings):
    if not build_plan(payload, day, {})['prices_valid']:
        return [], []
    prices = [row['price_total_czk_kwh'] for row in payload['periods']]
    eta = settings.get('roundtrip_efficiency', .90)
    wear = settings.get('wear_czk_kwh', .30)
    margin = settings.get('minimum_profit_czk_kwh', .50)
    if not .5 <= eta <= 1 or wear < 0 or margin < .3:
        return [], []
    # Require a sustained future peak (one hour), within twelve hours. A single
    # price spike is insufficient justification to charge a battery.
    eligible = []
    for i, price in enumerate(prices):
        peaks = [sum(prices[j:j + 4]) / 4 for j in range(i + 4, min(93, i + 49))]
        eligible.append(bool(peaks) and max(peaks) - price / eta - wear >= margin)
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
            costs = {j: sum(prices[j:j + width]) / width for j in range(start, i - width + 1)}
            cheapest = min(costs.values())
            chosen = max(j for j, cost in costs.items() if cost <= cheapest + .10)
            windows.append({'from': clock(chosen), 'to': clock(chosen + width),
                            'max_price': max(prices[chosen:chosen + width])})
    return windows, prices


class BatteryPlanner:
    def __init__(self, config):
        self.config = config
        self.path = config.data_dir / 'battery-economic-state.json'
        self.memory = read_json(self.path, {}) or {}
        self.state = None
        self.last_attempt = None
        self.last_result = None

    def remember(self, decision, applied):
        if not applied:
            return
        if decision.action == 'start_battery_charge':
            self.memory.update(owned=True, basis=max(self.memory.get('basis', float('-inf')),
                                                   decision.reason_params['basis']),
                               purchased_day=decision.timestamp.date().isoformat())
            self.memory['hold_until'] = (decision.timestamp + timedelta(hours=12)).isoformat()
        elif decision.action == 'stop_battery_control':
            self.memory['owned'] = False
        atomic_write_json(self.path, self.memory)

    def prepare_write(self, decision):
        # Persist ownership before the hardware write: a crash after acceptance
        # must not leave a program that a restarted controller thinks is manual.
        if decision.action == 'start_battery_charge':
            self.remember(decision, True)

    def decide(self, values, payload, moment):
        settings = self.config.get('controller.optimization.goodwe_control.economic', {})
        windows, prices = charging_windows(payload, moment.date().isoformat(), settings)
        row = values or {}
        stamp = parse_iso(row.get('timestamp'))
        fresh = (row.get('online') is True and stamp is not None
                 and -30 <= (moment - stamp).total_seconds() <= 90)
        fields = ('battery_soc', 'pv_w', 'house_w', 'grid_import_w', 'battery_charge_w',
                  'battery_v', 'battery_temp_c', 'charge_current_limit_a', 'rated_power_w',
                  'on_grid_soc_limit_pct')
        valid = fresh and all(number(row.get(key)) for key in fields)
        index = moment.hour * 4 + moment.minute // 15
        price = prices[index] if prices else None
        current = next((w for w in windows if w['from'] <= moment.strftime('%H:%M') < w['to']), None)
        eta = settings.get('roundtrip_efficiency', .90)
        wear = settings.get('wear_czk_kwh', .30)
        margin = settings.get('minimum_profit_czk_kwh', .50)
        ceiling = min(60, max(20, int(settings.get('grid_target_soc_pct', 60))))
        minimum = min(20, max(10, int(settings.get('minimum_soc_pct', 20))))
        mode = row.get('operation_mode')
        phase, reason = 'self_consumption', 'No profitable charging window'
        action, value, params = None, None, {}
        soc = row.get('battery_soc')
        reserve = row.get('on_grid_soc_limit_pct')
        owned = self.memory.get('owned', False)
        basis = self.memory.get('basis')
        usable_basis = number(basis)
        deadline = parse_iso(self.memory.get('hold_until'))
        expired = deadline is not None and moment >= deadline
        release = (valid and price is not None and usable_basis
                   and (expired or price - basis / eta - wear >= margin))
        safe = (valid and prices and 0 <= soc <= 100 and 10 <= row['battery_temp_c'] <= 45
                and row['battery_v'] > 100 and row['charge_current_limit_a'] > 0)
        device_clock = parse_iso(row.get('inverter_time'))
        clock_ok = device_clock is not None and abs((moment - device_clock).total_seconds()) <= 120
        safe = safe and clock_ok
        # Native charging is stopped before restoring normal discharge reserves.
        # Unknown/manual non-General modes are never silently commandeered.
        grid_limit = min(7000, settings.get('max_grid_import_w', 7000))
        headroom = (grid_limit - row['grid_import_w'] + row['battery_charge_w']) if valid else 0
        power = (min(20, settings.get('charge_power_pct', 20),
                     int(max(0, headroom - 500) / row['rated_power_w'] * 100),
                     int(row['battery_v'] * row['charge_current_limit_a'] * .8
                         / row['rated_power_w'] * 100)) if valid and row['rated_power_w'] > 0 else 0)
        pv_surplus = valid and row['pv_w'] >= row['house_w'] + 300
        charge = safe and current is not None and soc < ceiling - 2 and power >= 5 and not pv_surplus
        if not valid or not prices:
            phase, reason = 'safe_mode', 'Missing/stale GoodWe data or complete published prices'
        elif not safe:
            phase, reason = 'safe_mode', 'Battery temperature/BMS/voltage or inverter clock veto'
        elif pv_surplus:
            phase, reason = 'solar', 'Measured PV covers consumption; prefer natural solar charging'
        if owned and (not charge or row.get('grid_import_w', 0) > grid_limit):
            action, value = 'stop_battery_control', None
        elif charge and (owned or mode == 'GENERAL'):
            phase, reason = 'charge', 'Cheap now; sustained later peak covers model losses, wear and margin'
            # Lock the original end/power while this native schedule is valid;
            # only reduce power materially if grid headroom/BMS requires it.
            program = row.get('battery_program') or {}
            matches = (owned and mode == 'ECO' and program.get('enabled') is True
                       and program.get('valid_to') == current['to']
                       and program.get('day_bits') == 1 << ((moment.weekday() + 1) % 7)
                       and program.get('stop_soc_pct') == ceiling
                       and program.get('work_mode') == 3 and program.get('other_groups') == [0, 0, 0]
                       and number(program.get('power_pct'))
                       and 5 <= -program['power_pct'] <= power + 2)
            if not matches:
                action, value = 'start_battery_charge', power
                params = dict(power_pct=power, start_soc_pct=int(soc), stop_soc_pct=ceiling,
                              valid_from=moment.strftime('%H:%M'), valid_to=current['to'],
                              valid_day=moment.date().isoformat(), basis=current['max_price'])
        elif valid and mode == 'GENERAL':
            # Hold bought energy until it is worth using; PV energy can still fill
            # the remaining capacity. No forced export, no inferred PV forecast.
            hold = usable_basis and soc > minimum and not release and prices
            target = min(ceiling, int(soc)) if hold else min(minimum, int(soc))
            phase = 'hold' if hold else ('release' if release else phase)
            if hold:
                reason = 'Retain purchased energy for a profitable price; General mode still accepts PV'
            elif release:
                reason = ('Hold deadline passed; restore normal self-consumption, no forced export' if expired
                          else 'Profitable consumption now; General mode supplies the house, no forced export')
            if reserve != target and (not hold or abs(reserve - target) >= 5):
                action, value = 'set_on_grid_soc_limit_pct', target
            if soc <= minimum and usable_basis and not owned:
                self.memory.pop('basis', None)
                atomic_write_json(self.path, self.memory)
        elif valid and not owned and mode != 'GENERAL':
            phase, reason = 'external_mode', 'External/manual inverter mode; HEC will not overwrite it'
        self.state = dict(timestamp=moment.isoformat(), phase=phase, reason=reason,
                          prices_valid=bool(prices), data_valid=bool(valid), windows=windows,
                          price_czk_kwh=price, grid_target_soc_pct=ceiling, minimum_soc_pct=minimum,
                          efficiency_assumption=eta, wear_assumption_czk_kwh=wear,
                          minimum_profit_czk_kwh=margin, planned_charge_price_basis=basis,
                          actual_mode=mode, actual_soc=soc, actual_reserve_pct=reserve,
                          last_command=self.last_result,
                          force_discharge=False, next_action=action)
        if action is None or (action != 'stop_battery_control' and self.last_attempt
                              and moment - self.last_attempt < timedelta(seconds=300)):
            return []
        self.last_attempt = moment
        return [Decision(rule='battery_economic', action=action, value=value,
                         reason_key='reason.battery_economic', reason_params={**params, 'explanation': reason},
                         timestamp=moment)]
