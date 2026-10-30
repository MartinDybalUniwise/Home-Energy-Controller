from datetime import timedelta
from unittest.mock import patch

from hec.controller.controller import Controller
from hec.core.app import Application
from hec.core.model import Decision
from test_controller import FakeApp, FakeGoodWeWriter
from test_tng_price import BASE, energy, setup


def connected(tmp_path, tng_connect):
    reader, config = setup(tmp_path, tng_connect)
    config.data['controller']['enabled'] = True
    app = FakeApp(config, readers=[reader])
    reader.storage = app.storage
    app.storage.write_current('goodwe', energy())
    controller = Controller(app)
    reader.planner = controller
    state = reader.read_state()
    state['heatpump'].update(sample_time=BASE.isoformat(), room_temperature=21.6)
    state['settings'].update(heating_on=True, boiler_on=False)
    return reader, controller, app, state


def test_controller_resolves_one_target_and_only_adapter_posts(tmp_path, tng_connect):
    reader, controller, app, state = connected(tmp_path, tng_connect)
    with patch.object(reader, 'post_json', return_value=204) as post:
        reader.apply(state, moment=BASE)
        assert [c.args[0] for c in post.call_args_list].count('basic_settings') == 1
        basic = next(c.args[1] for c in post.call_args_list if c.args[0] == 'basic_settings')
        assert basic['HeatTemp_Const'] == 35
        assert basic['HeatSet']['Heat'] and not basic['BoilerSet']['Boiler']
    assert controller.state()['thermal_plan']['phase'] == 'coast'
    assert controller.state()['planner'] == 'unified'
    assert controller.last_decision.action == 'plan_tng'
    assert not controller.last_decision.applied  # resolved target != sent/confirmed command
    assert not any(r.action in ('set_dhw', 'set_heating') for r in controller.rules)
    assert reader.request_boiler_temperature(55, state) == (False, 'central_controller_required')
    assert reader.request_heating_temperature(48, state) == (False, 'central_controller_required')
    with patch.object(reader, 'post_json') as post:
        reader.apply(state, moment=BASE + timedelta(minutes=1))
        post.assert_not_called()  # existing confirmation/minimum interval is authoritative


def test_master_disable_stops_all_automatic_tng_writes(tmp_path, tng_connect):
    reader, controller, _, state = connected(tmp_path, tng_connect)
    controller.config.data['controller']['enabled'] = False
    with patch.object(reader, 'post_json') as post:
        assert reader.apply(state, moment=BASE) == ['skip:controller:disabled']
        post.assert_not_called()
    assert not controller.state()['tng_write_enabled']


def test_comfort_wins_over_dhw_in_same_controller(tmp_path, tng_connect):
    reader, controller, _, state = connected(tmp_path, tng_connect)
    reader.config.data['tng']['operation'] = {'default_mode': 'boiler'}
    reader.comfort_state = {'active': True}
    state['heatpump']['room_temperature'] = 20.8
    plan = controller.prepare_tng(reader, state, BASE)
    assert plan['mode'] == 'heating'
    assert plan['heating_temperature'] == 42 and plan['room_target'] == 21.5
    reader.config.data['tng']['operation'] = {'default_mode': 'off'}
    assert controller.prepare_tng(reader, state, BASE)['mode'] == 'off'


def test_data_loss_cancels_price_optimization_but_preserves_comfort(tmp_path, tng_connect):
    reader, controller, app, state = connected(tmp_path, tng_connect)
    app.storage.write_current('goodwe', energy(BASE - timedelta(minutes=5)))
    plan = controller.prepare_tng(reader, state, BASE)
    assert plan['heating_temperature'] == 42 and plan['room_target'] == 21.5
    assert plan['phase'] == 'stale_energy'


def test_inverter_writes_require_separate_control_permission(tmp_path, tng_connect):
    _, controller, app, _ = connected(tmp_path, tng_connect)
    app.goodwe_writer = FakeGoodWeWriter()
    controller.config.data['controller']['optimization']['goodwe_control']['enabled'] = False
    decision = Decision(rule='charge', action='start_battery_charge', value=50)
    assert not controller.apply(decision).applied
    assert app.goodwe_writer.calls == []


def test_application_binds_reader_to_same_controller(tmp_path, tng_connect, monkeypatch):
    reader, config = setup(tmp_path, tng_connect)
    monkeypatch.setattr('hec.core.app.build_readers', lambda c, s: [reader])
    app = Application(config)
    assert reader.planner is app.controller
    assert app.status()['controller']['planner'] == 'unified'
