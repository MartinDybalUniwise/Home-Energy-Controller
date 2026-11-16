"""Regressions from Nov1-4 daily reviews: execution, comfort and opportunity cost."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from hec.controller.battery import peak_reservation
from hec.controller.comfort import evaluate_comfort
from hec.controller.dhw import dhw_mode
from hec.controller.floor import floor_plan
from hec.forecast.consumption import today_consumption, weather_consumption
from hec.storage.base import read_json
from test_battery_economic import curve, instant, planner, row
from test_floor_check import BASE, START, configured, inputs, requesting, resolve
from test_readers_ote_tng import build_tng


def test_battery_keeps_limited_energy_for_later_sustained_peak(tmp_path):
    p = planner(tmp_path)
    p.memory = {"basis": 6}
    payload = curve(6, 11)
    for index in range(48, 52):
        payload["periods"][index]["price_total_czk_kwh"] = 8
    values = row(12)
    values.update(battery_soc=60, on_grid_soc_limit_pct=20)
    decisions = p.decide(values, payload, instant(12))
    assert decisions[0].action == "set_on_grid_soc_limit_pct"
    assert decisions[0].value == 60
    assert p.state["peak_reservation"]["active"]
    values = row(17)
    values.update(battery_soc=60, on_grid_soc_limit_pct=60)
    decisions = p.decide(values, payload, instant(17))
    assert decisions[0].value == 20


def test_peak_reservation_allows_surplus_and_ignores_single_spike():
    prices = [8] * 96
    prices[64:68] = [11] * 4
    result = peak_reservation(prices, 48, {"house_w": 500, "battery_soc": 60}, 10, 20, 60)
    assert 20 < result["reserve_pct"] < 60
    prices[64:68] = [8, 8, 11, 8]
    # A single spike's one-hour average is not a materially dearer sustained hour.
    prices[66] = 10
    assert not peak_reservation(prices, 48, {"house_w": 500, "battery_soc": 60}, 10, 20, 60)["active"]


def test_hourly_evaluation_defers_warm_store_but_not_beyond_two_hours(tmp_path):
    c = configured(tmp_path)
    c.data["tng"]["floor_check"]["adaptive_enabled"] = True
    plan = resolve(c, START + timedelta(minutes=60))
    assert plan["floor_check"]["phase"] == "deferred"
    assert plan["room_target"] == 21.5
    assert plan["floor_check"]["next_check_at"] == (START + timedelta(minutes=120)).isoformat()
    assert resolve(c, START + timedelta(minutes=120))["floor_check"]["phase"] == "preparing"


@pytest.mark.parametrize("aku,room", [(34.5, 21.6), (40, 21.2)])
def test_coast_cannot_defer_cold_buffer_or_room(tmp_path, aku, room):
    c = configured(tmp_path)
    c.data["tng"]["floor_check"]["adaptive_enabled"] = True
    t = START + timedelta(minutes=60)
    state, wire, gate = inputs(t, aku=aku, room=room, target=21.1)
    plan = floor_plan(c, {**BASE, "phase": "coast"}, state, wire, gate, t)
    assert plan["floor_check"]["phase"] == "preparing"


def test_confirmed_restore_can_complete_despite_unavailable_room_telemetry(tmp_path):
    c = configured(tmp_path)
    t, gate = requesting(c)
    assert resolve(c, t + timedelta(minutes=45), target=22.1, gate=gate)["floor_check"]["phase"] == "restoring"
    now = t + timedelta(minutes=46)
    state, wire, _ = inputs(now, target=21.5)
    state["heatpump"]["sample_time"] = (now - timedelta(hours=1)).isoformat()
    state["timestamp"] = now.isoformat()
    assert floor_plan(c, BASE, state, wire, gate, now)["floor_check"]["phase"] == "idle"
    assert "active" not in read_json(c.data_dir / "floor-circulation-state.json")


def test_matching_thermostat_readback_does_not_reopen_gate(tmp_path, tng_connect):
    import json
    from hashlib import sha256
    reader, _, _ = build_tng(tmp_path, tng_connect, write_enabled=True,
                            thermostat={"enabled": True, "default_temperature": 21.5})
    state = reader.read_state()
    state["DayTemperature"] = 21.5
    state["LastSettingsNotConfirmed"] = False
    template = dict(reader.config.get("tng.thermostat_settings_template"))
    template["DayTemperature"] = 21.5
    fingerprint = sha256(json.dumps(template, sort_keys=True).encode()).hexdigest()
    reader.change_gate["thermostat"]["last_requested"] = {"day_temperature": 21.5, "payload_signature": fingerprint}
    with patch.object(reader, "post_json") as post:
        reader.apply(state, moment=START)
    assert not any(call.args[0] == "thermostat_settings" for call in post.call_args_list)
    assert reader.change_gate["thermostat"]["last_post_at"] is None
    # A matching day target must not hide a genuine change to the night/profile template.
    reader.config.data["tng"]["thermostat_settings_template"]["NightTemperature"] = 19
    reader.pending_sent.clear()
    with patch.object(reader, "post_json", return_value=204) as post:
        reader.apply(state, moment=START)
    assert any(call.args[0] == "thermostat_settings" for call in post.call_args_list)


def test_slow_cooling_anticipates_comfort_floor_but_ventilation_does_not():
    first = {"sample_time": START.isoformat(), "room_temperature": 21.3}
    saved = evaluate_comfort({}, first, START, True)
    later = START + timedelta(minutes=10)
    saved = evaluate_comfort(saved, {"sample_time": later.isoformat(), "room_temperature": 21.2}, later, True)
    assert saved["active"]
    saved = evaluate_comfort({}, {"sample_time": START.isoformat(), "room_temperature": 21.8}, START, True)
    saved = evaluate_comfort(saved, {"sample_time": later.isoformat(), "room_temperature": 21.2}, later, True)
    assert not saved.get("active")


def dhw_config(tmp_path):
    c = configured(tmp_path)
    c.data["tng"]["operation"] = {"default_mode": "heating", "schedule": [
        {"from": "10:00", "to": "11:30", "mode": "boiler"},
        {"from": "14:00", "to": "15:30", "mode": "boiler"}]}
    return c


def test_second_dhw_skips_warm_probe_and_resumes_with_hysteresis(tmp_path):
    c = dhw_config(tmp_path)
    now = START.replace(hour=14)
    state = {"heatpump": {"sample_time": now.isoformat(), "boiler_temperature": 52.5}}
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "heating"
    state["heatpump"]["boiler_temperature"] = 44
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "heating"
    state["heatpump"]["boiler_temperature"] = 43
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "boiler"
    state["heatpump"].update(boiler_temperature=55, sample_time=(now - timedelta(hours=1)).isoformat())
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "boiler"


def test_dhw_preserves_first_hygienic_and_explicit_dated_windows(tmp_path):
    c = dhw_config(tmp_path)
    now = START.replace(hour=10)
    state = {"heatpump": {"sample_time": now.isoformat(), "boiler_temperature": 60}}
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "boiler"
    now = now.replace(hour=14)
    state["heatpump"]["sample_time"] = now.isoformat()
    assert dhw_mode(c, state, now, "boiler", 55)[0] == "boiler"
    c.data["tng"]["operation"]["date_overrides"] = {now.date().isoformat(): {}}
    assert dhw_mode(c, state, now, "boiler", 45)[0] == "boiler"


def test_today_load_is_measured_plus_remaining_not_below_observed(tmp_path):
    from types import SimpleNamespace
    c = configured(tmp_path)
    now = START.replace(hour=19)
    storage = SimpleNamespace(latest=lambda _: {"timestamp": now.isoformat(), "e_load_day_kwh": 45.8})
    value, details = today_consumption(storage, c, now, 30)
    assert value > 45.8
    assert details["remaining_kwh"] > 0 and details["remaining_is_estimate"]
    stale = SimpleNamespace(latest=lambda _: {"timestamp": (now - timedelta(days=1)).isoformat(), "e_load_day_kwh": 80})
    assert today_consumption(stale, c, now, 30)[0] == 30


def test_weather_total_contains_heat_once_and_no_fake_cop():
    target = START.date()
    history = [{"date": (target - timedelta(days=i)).isoformat(), "house_kwh": 20,
                "heatpump_kwh": 10, "heatpump_quality": {"valid_samples": 100, "quality": "measured"}}
               for i in range(1, 6)]
    value, components = weather_consumption(history, target, 8, 20, 20)
    assert value == 30 and components["base_kwh"] == 10
    history = [{"date": (target - timedelta(days=i)).isoformat(), "house_kwh": 10 + 2 * i,
                "mean_outside_c": 18 - i, "heatpump_kwh": None} for i in range(1, 8)]
    value, components = weather_consumption(history, target, 10, 30, None)
    assert value == 26
    assert components["separate_heat_meter_valid"] is False


def test_legacy_signed_or_unqualified_heat_never_teaches_heat_forecast(tmp_path):
    from hec.controller.predictor import Predictor
    from test_predictor import make
    c, storage = make(tmp_path)
    p = Predictor(c, storage)
    assert p.heat_slope([{"heatpump_kwh": -10, "degree_days": 5},
                         {"heatpump_kwh": 10, "degree_days": 5},
                         {"heatpump_kwh": 10, "degree_days": 5,
                          "heatpump_quality": {"valid_samples": 0, "quality": "phase"}}]) == (None, 0)


def test_boiler_skip_respects_disabled_heat_and_explicit_off_default(tmp_path):
    c = dhw_config(tmp_path)
    now = START.replace(hour=14)
    state = {"heatpump": {"sample_time": now.isoformat(), "boiler_temperature": 55}}
    c.data["tng"]["heating"]["enabled"] = False
    assert dhw_mode(c,state,now,"boiler",45)[0] == "boiler"
    c.data["tng"]["heating"]["enabled"] = True
    c.data["tng"]["operation"]["default_mode"] = "off"
    assert dhw_mode(c,state,now,"boiler",45)[0] == "boiler"


def test_recent_consumption_adapts_without_losing_day_kind(tmp_path):
    from hec.controller.predictor import Predictor
    from test_predictor import make
    config, storage = make(tmp_path)
    target = START.date() + timedelta(days=1)
    history = [{"date": (target - timedelta(days=i)).isoformat(),
                "house_kwh": 55 if i <= 7 else 25} for i in range(1, 29)]
    value, samples = Predictor(config,storage).consumption_estimate(target,history)
    assert value == 55 and 3 <= samples <= 7
