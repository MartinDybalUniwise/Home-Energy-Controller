"""Synthetic regressions for the Nov15 failure; never load private telemetry."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from hec.controller.comfort import evaluate_comfort
from hec.controller.dhw import catchup_plan
from hec.controller.recovery import observe_recovery
from hec.storage.base import read_json
from test_floor_check import START, configured, inputs
from test_tng_price import BASE, evaluate, seed_confirmed_readiness, setup


def test_single_warm_sample_gap_and_repeated_samples_do_not_release_guard():
    saved = dict(active=True)
    for minute in range(0, 30, 5):
        now = START + timedelta(minutes=minute)
        saved = evaluate_comfort(saved, dict(sample_time=now.isoformat(), room_temperature=21.5), now, True)
        assert saved['active']
    late = START + timedelta(minutes=50)
    saved = evaluate_comfort(saved, dict(sample_time=late.isoformat(), room_temperature=21.5), late, True)
    assert saved['active']  # >15min unknown gap restarts the recovery clock
    assert saved['recovered_since'] == late.isoformat()


def test_cold_day_latch_survives_new_price_window_and_restart(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    state, _, gates = inputs(BASE, room=20.9)
    observe_recovery(config, state, gates, {'active': True}, BASE)
    later = BASE.replace(hour=17)
    state, _, gates = inputs(later, room=21.8)
    safety = observe_recovery(config, state, gates, {}, later)
    assert read_json(config.data_dir / 'thermal-recovery-state.json')['day_blocked']
    status, _ = evaluate(config, later, 21.8, {'key': 'old', 'blocked': True}, safety=safety)
    assert status['phase'] == 'readiness_veto' and status['heating_temperature'] == 42


def test_good_preheat_admits_coast_but_no_sample_cannot_admit_it(tmp_path, tng_connect):
    _, config = setup(tmp_path, tng_connect)
    seed_confirmed_readiness(config)
    state, _, gates = inputs(BASE, room=21.6)
    safety = observe_recovery(config, state, gates, {}, BASE)
    assert safety['coast_ready']
    status, saved = evaluate(config, safety=safety)
    assert status['phase'] == 'coast'
    # Warm-history duration expires during coast; admission itself was verified.
    status, _ = evaluate(config, BASE + timedelta(minutes=25), 21.4, saved,
                         safety={**safety, 'coast_ready': False})
    assert status['phase'] == 'coast'


@pytest.mark.parametrize('fault', ['short', 'expired_model', 'stale', 'gate'])
def test_coast_denies_short_unconfirmed_or_unverified_preheat(tmp_path, tng_connect, fault):
    _, config = setup(tmp_path, tng_connect)
    seed_confirmed_readiness(config)
    state, _, gates = inputs(BASE, room=21.6)
    if fault == 'short':
        from hec.storage.base import atomic_write_json
        saved = read_json(config.data_dir / 'thermal-recovery-state.json')
        saved['preheat']['minutes'] = 7
        atomic_write_json(config.data_dir / 'thermal-recovery-state.json', saved)
    elif fault == 'expired_model':
        (config.data_dir / 'thermal-response.json').unlink()
    elif fault == 'stale':
        state['heatpump']['sample_time'] = (BASE - timedelta(hours=1)).isoformat()
    else:
        gates['basic']['awaiting_confirmation'] = True
        # Outstanding delivery invalidates the continuous lead, even with warm room.
        state['heatpump']['sample_time'] = (BASE - timedelta(minutes=1)).isoformat()
        saved = read_json(config.data_dir / 'thermal-recovery-state.json')
        saved.pop('preheat')
        from hec.storage.base import atomic_write_json
        atomic_write_json(config.data_dir / 'thermal-recovery-state.json', saved)
    safety = observe_recovery(config, state, gates, {}, BASE)
    assert not safety['coast_ready']


def test_confirmed_42_without_room_response_alerts_and_persists(tmp_path):
    c = configured(tmp_path)
    for minute in range(0, 61, 5):
        now = START + timedelta(minutes=minute)
        state, _, gates = inputs(now, room=20.9, target=21.5)
        safety = observe_recovery(c, state, gates, {}, now)
    assert safety['response_fault'] and safety['day_blocked']
    assert not safety['pump_run_measured']
    late = now + timedelta(hours=1)
    state['heatpump']['sample_time'] = now.isoformat()
    assert observe_recovery(c, state, gates, {}, late)['response_fault']


def test_dhw_debt_waits_for_comfort_then_stops_on_wall_deadline_after_restart(tmp_path):
    c = configured(tmp_path)
    c.data['tng'].update(boiler={'enabled': True}, operation={'default_mode': 'heating'})
    now = START
    state, _, gates = inputs(now, room=21.1)
    state['heatpump']['boiler_temperature'] = 29
    mode, _, info = catchup_plan(c, state, gates, now, 'heating', 'heating', 30, True, {})
    assert mode == 'heating' and info['debt'] and not info['active']
    now += timedelta(hours=1)
    state, _, gates = inputs(now, room=21.5)
    state['heatpump']['boiler_temperature'] = 29
    mode, target, info = catchup_plan(c, state, gates, now, 'heating', 'heating', 30,
                                     False, {'stable_recovery': True})
    assert mode == 'boiler' and target == 50 and info['active']
    later = now + timedelta(minutes=45)
    state['heatpump']['sample_time'] = later.isoformat()
    mode, _, info = catchup_plan(c, state, gates, later, 'heating', 'heating', 30, False, {})
    assert mode == 'heating' and info['reason'] == 'restore_heating'


def test_catchup_does_not_stack_before_upcoming_scheduled_dhw(tmp_path):
    c = configured(tmp_path)
    c.data['tng'].update(boiler={'enabled': True}, operation={'default_mode': 'heating', 'schedule': [
        dict(mode='boiler', **{'from': '18:00', 'to': '19:00'})]})
    state, _, gates = inputs(START, room=21.6)
    state['heatpump']['boiler_temperature'] = 29
    mode, _, info = catchup_plan(c, state, gates, START, 'heating', 'heating', 30,
                                False, {'stable_recovery': True})
    assert mode == 'heating' and info['reason'] == 'scheduled_dhw_soon'


@pytest.mark.parametrize('fault', ['off', 'dated', 'cold', 'pending', 'stale', 'disabled', 'minimum_interval'])
def test_dhw_catchup_obeys_permissions_freshness_and_guards(tmp_path, fault):
    c = configured(tmp_path)
    c.data['tng'].update(boiler={'enabled': True}, operation={'default_mode': 'heating'})
    state, _, gates = inputs(START, room=21.5)
    state['heatpump']['boiler_temperature'] = 29
    scheduled, comfort = 'heating', False
    if fault == 'off':
        scheduled = 'off'
    if fault == 'dated':
        c.data['tng']['operation']['date_overrides'] = {START.date().isoformat(): {}}
    if fault == 'cold':
        comfort = True
    if fault == 'pending':
        gates['basic']['awaiting_confirmation'] = True
    if fault == 'minimum_interval':
        gates['basic']['last_post_at'] = (START - timedelta(minutes=14)).isoformat()
    if fault == 'stale':
        state['heatpump']['sample_time'] = (START - timedelta(hours=1)).isoformat()
    if fault == 'disabled':
        c.data['tng']['boiler']['enabled'] = False
    mode, _, info = catchup_plan(c, state, gates, START, scheduled, scheduled, 30,
                                comfort, {'stable_recovery': True})
    assert mode != 'boiler' and not info['active']


@pytest.mark.parametrize('value', [True, False, None])
def test_writer_preserves_pump_configuration_and_audits_source(tmp_path, tng_connect, value):
    from types import SimpleNamespace

    from test_readers_ote_tng import build_tng
    reader, _, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
                            heating={'enabled': True, 'default_temperature': 42})
    reader.planner = SimpleNamespace(prepare_tng=lambda *a: dict(
        mode='heating', boiler_temperature=50, heating_temperature=42, room_target=21.5))
    state, _, _ = inputs(START)
    state['settings'].update(external_circulation_pump=value, heating_set_temperature=35)
    with patch.object(reader, 'post_json', return_value=204) as post, patch.object(reader, '_command_audit') as audit:
        reader.apply(state, moment=START)
    payload = next(call.args[1] for call in post.call_args_list if call.args[0] == 'basic_settings')
    if value is not None:
        assert payload['HeatSet']['ExternalCirculationPump'] is value
    observation = next(call.args[0] for call in audit.call_args_list
                       if call.args[0].get('phase') == 'circulation_configuration')
    assert observation['origin'] == 'cloud_settings_readback' and not observation['pump_run_measured']
