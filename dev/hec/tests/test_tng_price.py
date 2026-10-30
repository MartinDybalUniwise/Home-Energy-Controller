from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from hec.readers.tng_price import (
    build_plan,
    clock,
    evaluate_shift,
    refresh_plans,
    solar_available,
)
from hec.storage.base import atomic_write_json, read_json
from test_readers_ote_tng import build_tng

DAY = '2026-10-30'
BASE = datetime.fromisoformat(DAY + 'T06:00:00+01:00')


def curve(day=DAY):
    return {'date': day, 'periods': [
        {'start': clock(i), 'end': clock(i + 1),
         'price_total_czk_kwh': 10 if 24 <= i < 36 or 68 <= i < 80 else (6 if i < 24 else 7)}
        for i in range(96)]}


def energy(moment=BASE, **kwargs):
    return {'timestamp': moment.isoformat(), 'online': True, 'pv_w': 0, 'house_w': 2500,
            'grid_import_w': 2500, 'grid_export_w': 0,
            'battery_discharge_w': 0, 'battery_soc': 50, **kwargs}


def setup(tmp_path, tng_connect):
    reader, config, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
        price_shift={'enabled': True},
        heating={'enabled': True, 'default_temperature': 42, 'schedule': [], 'date_overrides': {}},
        thermostat={'enabled': True, 'default_temperature': 21.5, 'schedule': [], 'date_overrides': {}},
        boiler={'enabled': True, 'default_temperature': 50, 'schedule': []},
        operation={'default_mode': 'heating', 'schedule': []})
    atomic_write_json(config.path, config.data)
    atomic_write_json(config.data_dir / f'ote-{DAY}.json', curve())
    refresh_plans(config, BASE)
    return reader, config


def evaluate(config, moment=BASE, room=21.6, saved=None, **kwargs):
    return evaluate_shift(config, {'sample_time': moment.isoformat(), 'room_temperature': room},
                          moment, saved or {}, False, 'heating', energy(moment), **kwargs)


def test_preheat_precedes_real_peaks_and_coast_is_bounded():
    plan = build_plan(curve(), DAY, {'default_mode': 'heating'})
    assert plan['prices_valid']
    assert len(plan['phases']) == 4
    first, coast, second, evening = plan['phases']
    assert first == {'start': 16, 'end': 24, 'kind': 'preheat'}
    assert coast == {'start': 24, 'end': 30, 'kind': 'coast'}
    assert second['end'] <= evening['start']
    assert all(p['end'] - p['start'] <= (8 if p['kind'] == 'preheat' else 6) for p in plan['phases'])
    assert max(w['temperature'] for w in plan['heating']['schedule']) <= 42


@pytest.mark.parametrize('fault', ['missing', 'nan', 'duplicate', 'wrong_day', 'gap', 'dst'])
def test_invalid_prices_never_produce_optimization(fault):
    payload = curve()
    day = DAY
    if fault == 'missing':
        payload['periods'].pop()
    elif fault == 'nan':
        payload['periods'][3]['price_total_czk_kwh'] = float('nan')
    elif fault == 'duplicate':
        payload['periods'][4] = payload['periods'][3]
    elif fault == 'wrong_day':
        payload['date'] = '2026-10-31'
    elif fault == 'gap':
        payload['periods'][4]['end'] = '01:30'
    else:
        day = '2026-10-25'
        payload['date'] = day
    result = build_plan(payload, day, {})
    assert not result['prices_valid']
    assert result['phases'] == []


def test_flat_prices_and_dhw_off_do_not_generate_fake_opportunities():
    payload = curve()
    for row in payload['periods']:
        row['price_total_czk_kwh'] = 7
    assert build_plan(payload, DAY, {})['phases'] == []
    assert build_plan(curve(), DAY, {'default_mode': 'boiler'})['phases'] == []
    assert build_plan(curve(), DAY, {'default_mode': 'off'})['phases'] == []


def test_coast_selects_most_expensive_part_of_long_peak():
    payload = curve()
    for i in range(30, 36):
        payload['periods'][i]['price_total_czk_kwh'] = 12
    coast = build_plan(payload, DAY, {})['phases'][1]
    assert coast == {'start': 30, 'end': 36, 'kind': 'coast'}


def test_installation_never_claims_missed_preheat_was_planned():
    phases = build_plan(curve(), DAY, {}, earliest=32)['phases']
    assert all(p['start'] >= 32 for p in phases)


def test_disabling_feature_cancels_already_saved_coast(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    config.data['tng']['price_shift']['enabled'] = False
    status, _ = evaluate(config)
    assert status == {'phase': 'disabled', 'heating_temperature': 42, 'room_target': 21.5}


def test_dated_plans_preserve_dhw_owner_edits_and_raw_secrets(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    before = deepcopy(config.get('tng.boiler'))
    assert refresh_plans(config, BASE) == []
    assert config.get('tng.boiler') == before
    tomorrow = config.get('tng.heating.date_overrides')['2026-10-31']
    assert tomorrow['schedule'] == []  # no invented tomorrow prices
    config.data['tng']['heating']['date_overrides'][DAY]['default_temperature'] = 40
    assert refresh_plans(config, BASE) == []
    assert evaluate(config)[0] is None


def test_tomorrow_published_later_replaces_fallback(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    atomic_write_json(config.data_dir / 'ote-2026-10-31.json', curve('2026-10-31'))
    assert [p['date'] for p in refresh_plans(config, BASE)] == ['2026-10-31']
    assert config.get('tng.heating.date_overrides')['2026-10-31']['schedule']


def test_coast_requires_comfort_and_stays_vetoed_after_cooling(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    status, state = evaluate(config)
    assert status['phase'] == 'coast' and status['heating_temperature'] == 35
    status, state = evaluate(config, BASE + timedelta(minutes=5), 21.3, state)
    assert status['phase'] == 'comfort_veto' and status['heating_temperature'] == 42
    assert evaluate(config, BASE + timedelta(minutes=10), 21.6, state)[0]['phase'] == 'comfort_veto'
    assert evaluate(config, room=21.4)[0]['phase'] == 'comfort_veto'


def test_preheat_ceiling_stays_latched(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    pre = BASE - timedelta(hours=1)
    assert evaluate(config, pre)[0]['room_target'] == 21.7
    status, state = evaluate(config, pre, 21.7)
    assert status['room_target'] == 21.5
    assert evaluate(config, pre + timedelta(minutes=5), 21.6, state)[0]['room_target'] == 21.5


@pytest.mark.parametrize('kind', ['room', 'energy', 'prices', 'guard', 'off'])
def test_invalid_inputs_guard_and_explicit_off_cancel_price_shift(tmp_path, tng_connect, kind):
    _, config = setup(tmp_path, tng_connect)
    hp = {'sample_time': BASE.isoformat(), 'room_temperature': 21.6}
    power = energy()
    if kind == 'room':
        hp['sample_time'] = (BASE - timedelta(minutes=16)).isoformat()
    if kind == 'energy':
        power.pop('battery_soc')
    if kind == 'prices':
        atomic_write_json(config.data_dir / f'ote-{DAY}.json', {})
    status, _ = evaluate_shift(config, hp, BASE, {}, kind == 'guard',
                               'off' if kind == 'off' else 'heating', power)
    assert status['heating_temperature'] == 42 and status['room_target'] == 21.5


def test_solar_requires_sustained_export_and_can_override_price_peak(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    state = {}
    for minute in (0, 5, 10):
        moment = BASE + timedelta(minutes=minute)
        power = energy(moment, pv_w=6500, house_w=2000, grid_import_w=0, grid_export_w=4500)
        status, state = evaluate_shift(config, {'sample_time': moment.isoformat(), 'room_temperature': 21.6},
                                      moment, state, False, 'heating', power)
        assert status['phase'] == ('solar_preheat' if minute == 10 else 'coast')
    # After HP starts, remaining export falls; no start/stop oscillation.
    moment += timedelta(minutes=5)
    power = energy(moment, pv_w=6500, house_w=6200, grid_import_w=0, grid_export_w=300)
    status, state = evaluate_shift(config, {'sample_time': moment.isoformat(), 'room_temperature': 21.6},
                                  moment, state, False, 'heating', power)
    assert status['phase'] == 'solar_preheat'
    power['battery_discharge_w'] = 500
    assert evaluate_shift(config, {'sample_time': moment.isoformat(), 'room_temperature': 21.6},
                          moment, state, False, 'heating', power)[0]['phase'] != 'solar_preheat'


@pytest.mark.parametrize('fault', ['import', 'battery', 'low_soc', 'missing', 'stale', 'duplicate', 'ceiling'])
def test_solar_never_treats_gross_pv_or_bad_data_as_surplus(fault):
    state = {}
    for minute in (0, 5, 10):
        moment = BASE + timedelta(minutes=minute)
        power = energy(moment, pv_w=6000, house_w=2000, grid_import_w=0, grid_export_w=4000)
        room = 21.6
        if fault == 'import':
            power.update(house_w=6500, grid_import_w=500, grid_export_w=0)
        elif fault == 'battery':
            power['battery_discharge_w'] = 1000
        elif fault == 'low_soc':
            power['battery_soc'] = 10
        elif fault == 'missing':
            power.pop('grid_export_w')
        elif fault == 'stale':
            power['timestamp'] = (moment - timedelta(minutes=3)).isoformat()
        elif fault == 'duplicate':
            power['timestamp'] = BASE.isoformat()
        else:
            room = 21.7
        active, state, _ = solar_available(power, moment, state, room)
        assert not active


def test_solar_window_persists_and_expires_after_two_hours():
    moment = BASE
    power = energy(moment, pv_w=6500, house_w=2000, grid_import_w=0, grid_export_w=4500)
    state = {'day': DAY, 'used_seconds': 0, 'first_started': (BASE - timedelta(hours=2)).isoformat()}
    assert not solar_available(power, moment, state, 21.6)[0]


def test_real_apply_preserves_gates_exclusivity_and_runtime_after_restart(tmp_path, tng_connect):
    reader, config = setup(tmp_path, tng_connect)
    from hec.storage.jsonl import JsonlStorage
    reader.storage = JsonlStorage(config.data_dir, config.history_dir)
    reader.storage.write_current('goodwe', energy())
    state = reader.read_state()
    state['heatpump'].update(sample_time=BASE.isoformat(), room_temperature=21.6)
    state['settings'].update(heating_on=True, boiler_on=False)
    with patch.object(reader, 'post_json', return_value=204) as post:
        reader.apply(state, moment=BASE)
        basic = next(c.args[1] for c in post.call_args_list if c.args[0] == 'basic_settings')
        assert basic['HeatSet']['Heat'] and not basic['BoilerSet']['Boiler']
        assert basic['HeatTemp_Const'] == 35
    with patch.object(reader, 'post_json') as post:
        reader.apply(state, moment=BASE + timedelta(minutes=1))
        post.assert_not_called()
    saved = read_json(reader.state_path)
    assert saved['price_shift']['key'].endswith(':coast')
    assert saved['basic']['awaiting_confirmation']


def test_plan_preserves_environment_references(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    raw = read_json(config.path)
    raw['example_secret'] = '${KEEP_PRIVATE}'
    atomic_write_json(config.path, raw)
    payload = curve()
    payload['periods'][0]['price_total_czk_kwh'] = 5.5
    atomic_write_json(config.data_dir / f'ote-{DAY}.json', payload)
    refresh_plans(config, BASE)
    assert read_json(config.path)['example_secret'] == '${KEEP_PRIVATE}'
