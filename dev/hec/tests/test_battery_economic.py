from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from hec.controller.battery import BatteryPlanner, charging_windows
from hec.controller.controller import Controller
from hec.controller.price import ZONE, clock
from hec.core.config import Config
from hec.readers.goodwe_manager import GoodWeManager
from hec.storage.base import atomic_write_json

DAY = '2026-10-31'


def curve(low=6, high=10):
    return {'date': DAY, 'periods': [
        {'start': clock(i), 'end': clock(i + 1), 'price_total_czk_kwh': high if 64 <= i < 80 else low}
        for i in range(96)]}


def instant(hour=14):
    return datetime(2026, 10, 31, hour, tzinfo=ZONE)


def row(hour=14):
    return dict(timestamp=instant(hour).isoformat(), online=True, battery_soc=30, pv_w=500,
                house_w=3500, grid_import_w=3000, battery_charge_w=0, battery_v=380,
                battery_temp_c=30, charge_current_limit_a=18, rated_power_w=10000,
                on_grid_soc_limit_pct=20, operation_mode='GENERAL', inverter_time=instant(hour).isoformat())


def planner(tmp_path):
    return BatteryPlanner(Config({'storage': {'data_path': str(tmp_path)}, 'controller': {
        'optimization': {'goodwe_control': {'economic': {'enabled': True}}}}}, root=tmp_path))


def test_economic_windows_include_losses_wear_and_sustained_peak():
    assert charging_windows(curve(6, 10), DAY, {})[0]
    assert charging_windows(curve(7, 8), DAY, {})[0] == []
    payload = curve(7, 7)
    payload['periods'][65]['price_total_czk_kwh'] = 10
    assert charging_windows(payload, DAY, {})[0] == []


@pytest.mark.parametrize('low', [0, -1])
def test_zero_and_negative_prices_are_valid(low):
    assert charging_windows(curve(low, 8), DAY, {})[0]


def test_incomplete_prices_and_dst_fail_closed():
    payload = curve()
    payload['periods'].pop()
    assert charging_windows(payload, DAY, {}) == ([], [])
    payload = curve()
    payload['date'] = '2026-10-25'
    assert charging_windows(payload, '2026-10-25', {}) == ([], [])


def test_charge_has_bounded_time_power_and_soc_and_restart_ownership(tmp_path):
    p = planner(tmp_path)
    d = p.decide(row(), curve(), instant())[0]
    assert d.action == 'start_battery_charge' and d.value <= 20
    assert d.reason_params['stop_soc_pct'] == 60 and d.reason_params['valid_day'] == DAY
    assert d.reason_params['valid_to'] <= '16:00'
    p.prepare_write(d)
    assert planner(tmp_path).memory['owned'] is True


def test_fresh_feedback_suppresses_identical_program(tmp_path):
    p = planner(tmp_path)
    d = p.decide(row(), curve(), instant())[0]
    p.prepare_write(d)
    values = row()
    values['operation_mode'] = 'ECO'
    values['battery_program'] = GoodWeManager._expected_value(d.action, d.reason_params)
    values['timestamp'] = (instant() + timedelta(minutes=6)).isoformat()
    values['inverter_time'] = values['timestamp']
    assert p.decide(values, curve(), instant() + timedelta(minutes=6)) == []


@pytest.mark.parametrize('changes', [
    {'online': False}, {'timestamp': instant(10).isoformat()}, {'battery_temp_c': 50},
    {'charge_current_limit_a': 0}, {'pv_w': 8000}, {'grid_import_w': 8000},
    {'battery_soc': 60}, {'rated_power_w': 0}, {'battery_soc': None}, {'inverter_time': None},
])
def test_unsafe_inputs_stop_owned_charge_without_cooldown(tmp_path, changes):
    p = planner(tmp_path)
    d = p.decide(row(), curve(), instant())[0]
    p.prepare_write(d)
    values = row()
    values.update(operation_mode='ECO', **changes)
    assert p.decide(values, curve(), instant() + timedelta(seconds=60))[0].action == 'stop_battery_control'


def test_missing_prices_stops_owned_charge(tmp_path):
    p = planner(tmp_path)
    d = p.decide(row(), curve(), instant())[0]
    p.prepare_write(d)
    assert p.decide(row(), {}, instant() + timedelta(minutes=1))[0].action == 'stop_battery_control'


def test_bought_energy_held_then_released_as_self_consumption(tmp_path):
    p = planner(tmp_path)
    p.memory = {'basis': 6}
    values = row(15)
    values['battery_soc'] = 60
    held = p.decide(values, curve(), instant(15))[0]
    assert held.action == 'set_on_grid_soc_limit_pct' and held.value == 60
    values = row(17)
    values.update(battery_soc=60, on_grid_soc_limit_pct=60)
    released = p.decide(values, curve(), instant(17))[0]
    assert released.action == 'set_on_grid_soc_limit_pct' and released.value == 20
    assert p.state['force_discharge'] is False


def test_external_manual_mode_is_not_overwritten(tmp_path):
    p = planner(tmp_path)
    values = row()
    values['operation_mode'] = 'ECO_DISCHARGE'
    assert p.decide(values, curve(), instant()) == []
    assert p.state['phase'] == 'external_mode'


def test_reserve_never_raised_above_measured_soc(tmp_path):
    p = planner(tmp_path)
    values = row(21)
    values.update(battery_soc=10, on_grid_soc_limit_pct=10)
    assert p.decide(values, curve(), instant(21)) == []


def test_bounded_schedule_validation_and_exact_readback_target():
    kwargs = dict(valid_day=DAY, valid_from='12:00', valid_to='13:00',
                  power_pct=20, start_soc_pct=10, stop_soc_pct=60)
    GoodWeManager._validate_command('start_battery_charge', kwargs)
    expected = GoodWeManager._expected_value('start_battery_charge', kwargs)
    assert expected['day_bits'] == 64 and expected['power_pct'] == -20
    assert expected['other_groups'] == [0, 0, 0] and expected['work_mode'] == 3
    kwargs['valid_to'] = '01:00'
    with pytest.raises(ValueError):
        GoodWeManager._validate_command('start_battery_charge', kwargs)


def test_cheapest_later_block_replaces_first_merely_eligible_hours():
    windows, _ = charging_windows(curve(), DAY, {})
    assert any(w['from'] <= '14:00' < w['to'] for w in windows)


@pytest.mark.parametrize('success', [True, False])
def test_controller_uses_only_economic_writer_and_reports_result(tmp_path, monkeypatch, success):
    p = planner(tmp_path)
    p.config.data['controller']['enabled'] = True
    p.config.data['controller']['optimization']['goodwe_control']['enabled'] = True
    atomic_write_json(tmp_path / f'ote-{DAY}.json', curve())
    calls, records = [], []

    def charge(**kwargs):
        calls.append(kwargs)
        return {'success': success}

    app = SimpleNamespace(config=p.config, storage=SimpleNamespace(append=lambda *args: records.append(args)),
                          snapshot={'goodwe': row()}, readers=[],
                          goodwe_writer=SimpleNamespace(start_battery_charge=charge))
    controller = Controller(app)
    monkeypatch.setattr('hec.controller.controller.now_local', instant)
    result = controller.run_once()
    assert len(calls) == 1 and calls[0]['valid_day'] == DAY
    assert result['decisions'][0]['applied'] is success
    assert result['safe_mode'] is not success
    assert all(not r['enabled'] for r in controller.state()['rules'] if r['name'].startswith('goodwe_'))
    assert controller.state()['battery_plan']['last_command']['applied'] is success
