from datetime import datetime, timedelta
from unittest.mock import patch

from hec.readers.tng_comfort import evaluate_comfort
from test_readers_ote_tng import build_tng

BASE = datetime.fromisoformat('2026-10-29T14:00:00+01:00')


def sample(state, minutes, room, heating=False):
    moment = BASE + timedelta(minutes=minutes)
    return evaluate_comfort(state, {'sample_time': moment.isoformat(),
                                    'room_temperature': room}, moment, heating)


def test_sustained_low_and_hysteresis():
    state = sample({}, 0, 20.9)
    assert not state.get('active')
    for minute in (5, 10, 15):
        state = sample(state, minute, 20.8)
    assert state['active']
    state = sample(state, 20, 21.1)
    assert state['active']
    assert not sample(state, 25, 21.5)['active']


def test_ventilation_recovers_without_boost_or_times_out():
    state = sample({}, 0, 21.5, True)
    state = sample(state, 5, 20.8, True)
    for minute in (10, 15, 20, 25, 30):
        state = sample(state, minute, 20.8, True)
        assert not state.get('active')
    assert sample(state, 35, 20.8, True)['active']
    assert not sample(state, 35, 21.1, True).get('active')


def test_missing_stale_duplicates_and_gaps_do_not_prove_continuous_cold():
    state = sample({}, 0, 20.8)
    for value in (None, float('nan'), -200):
        assert evaluate_comfort(state, {'sample_time': BASE.isoformat(),
            'room_temperature': value}, BASE + timedelta(minutes=20), True) == state
    assert evaluate_comfort(state, {'sample_time': BASE.isoformat(), 'room_temperature': 20.8},
                            BASE + timedelta(minutes=20), True) == state
    assert not sample(state, 20, 20.8).get('active')


def test_guard_interrupts_boiler_without_bypassing_gate_and_survives_restart(tmp_path, tng_connect):
    reader, _, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
        heating={'enabled': True, 'default_temperature': 40, 'schedule': []},
        boiler={'enabled': True, 'default_temperature': 45, 'schedule': []},
        operation={'default_mode': 'boiler'})
    state = reader.read_state()
    state['settings'].update(heating_on=False, boiler_on=True)
    reader.comfort_state = sample({}, 0, 20.8)
    for minute in (5, 10):
        reader.comfort_state = sample(reader.comfort_state, minute, 20.8)
    state['heatpump'].update(sample_time=(BASE + timedelta(minutes=15)).isoformat(), room_temperature=20.8)
    with patch.object(reader, 'post_json', return_value=204) as post:
        reader.apply(state, moment=BASE + timedelta(minutes=15))
        payload = post.call_args.args[1]
        assert payload['HeatSet']['Heat'] is True
        assert payload['BoilerSet']['Boiler'] is False
        assert payload['HeatTemp_Const'] == 42
    with patch.object(reader, 'post_json') as post:
        reader.apply(state, moment=BASE + timedelta(minutes=16))
        post.assert_not_called()
    restarted, _, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
        heating={'enabled': True}, operation={'default_mode': 'boiler'})
    assert restarted.comfort_state['active']
    assert reader._comfort_operation(BASE) == 'heating'
    assert reader.request_boiler_temperature(45, state) == (False, 'exclusive_operation_window')


def test_guard_respects_disabled_heat_off_mode_and_minimum_interval(tmp_path, tng_connect):
    reader, config, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
        heating={'enabled': True, 'default_temperature': 40, 'schedule': []},
        boiler={'enabled': True, 'default_temperature': 45, 'schedule': []},
        operation={'default_mode': 'boiler'})
    reader.comfort_state = {'active': True}
    config.data['tng']['operation']['default_mode'] = 'off'
    assert reader._comfort_operation(BASE) == 'off'
    config.data['tng']['operation']['default_mode'] = 'boiler'
    config.data['tng']['heating']['enabled'] = False
    assert reader._comfort_operation(BASE) == 'boiler'
    config.data['tng']['heating']['enabled'] = True
    state = reader.read_state()
    reader._mark_posted('basic', {'heating_temperature': 40})
    reader.change_gate['basic']['awaiting_confirmation'] = False
    with patch.object(reader, 'post_json') as post:
        actions = reader.apply(state, moment=BASE)
        post.assert_not_called()
        assert any('minimum change interval' in action for action in actions)
