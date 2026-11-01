from copy import deepcopy
from datetime import timedelta

import pytest
from hec.controller.battery import charging_windows
from hec.controller.price import build_plan, clock, fingerprint
from hec.controller.response import observe_response, preheat_quarters, required_quarters
from hec.storage.base import atomic_write_json
from test_battery_economic import DAY, instant, planner, row


def tariff_curve():
    periods = []
    for i in range(96):
        nt = not (24 <= i < 28 or 36 <= i < 40 or 52 <= i < 56 or 64 <= i < 68)
        price = 7 if nt else 8.2
        if 68 <= i < 80:
            price = 10
        periods.append(
            dict(
                start=clock(i),
                end=clock(i + 1),
                price_total_czk_kwh=price,
                distribution_tariff="NT" if nt else "VT",
            )
        )
    return dict(date=DAY, periods=periods)


def context(moment):
    return (
        dict(planned_at=moment.isoformat(), mode="heating", phase="comfort_veto"),
        dict(sample_time=moment.isoformat(), room_temperature=21.3, heating_on=True),
    )


def test_native_charge_cannot_cross_nt_end_or_restart_in_vt(tmp_path):
    payload = tariff_curve()
    windows, prices = charging_windows(payload, DAY, {})
    assert windows
    for window in windows:
        indices = [i for i in range(96) if window["from"] <= clock(i) < window["to"]]
        assert all(payload["periods"][i]["distribution_tariff"] == "NT" for i in indices)
    p = planner(tmp_path)
    moment = instant(6)
    values = row(6)
    assert not any(d.action == "start_battery_charge" for d in p.decide(values, payload, moment))
    p.memory = {"owned": True, "basis": 7.9232}
    values["operation_mode"] = "ECO"
    assert p.decide(values, payload, moment)[0].action == "stop_battery_control"


def test_cold_morning_uses_battery_despite_old_cost_basis_and_later_peak(tmp_path):
    p = planner(tmp_path)
    p.memory = {"basis": 7.9232, "owned": False}
    moment = instant(6) + timedelta(minutes=44)
    values = row(6)
    values.update(
        timestamp=moment.isoformat(),
        inverter_time=moment.isoformat(),
        battery_soc=56,
        on_grid_soc_limit_pct=56,
        house_w=3200,
        grid_import_w=3150,
    )
    thermal, tng = context(moment)
    # Even a recent command must not delay lowering the reserve during VT.
    p.last_attempt = moment - timedelta(seconds=30)
    decision = p.decide(values, tariff_curve(), moment, thermal, tng)[0]
    assert decision.action == "set_on_grid_soc_limit_pct" and decision.value == 20
    assert p.state["phase"] == "release" and p.state["release_reason"] == "comfort_peak"
    assert p.state["coordination"]["allowed"]
    assert p.state["force_discharge"] is False
    # Restart and warming must not re-lock energy in the same VT interval.
    p = type(p)(p.config)
    later = moment + timedelta(minutes=6)
    values.update(timestamp=later.isoformat(), inverter_time=later.isoformat(), on_grid_soc_limit_pct=20)
    thermal, tng = context(later)
    tng["room_temperature"] = 21.6
    thermal["phase"] = "coast"
    assert p.decide(values, tariff_curve(), later, thermal, tng) == []
    assert p.state["release_reason"] == "comfort_peak"


@pytest.mark.parametrize(
    "fault",
    ["room_stale", "thermal_stale", "off", "boiler", "warm", "no_refill", "overload", "invalid_prices"],
)
def test_comfort_release_requires_fresh_demand_and_sufficient_refill(tmp_path, fault):
    p = planner(tmp_path)
    p.memory = {"basis": 7.9232}
    moment = instant(6)
    values = row(6)
    values.update(battery_soc=56, on_grid_soc_limit_pct=56)
    payload = tariff_curve()
    thermal, tng = context(moment)
    if fault == "room_stale":
        tng["sample_time"] = (moment - timedelta(minutes=16)).isoformat()
    if fault == "thermal_stale":
        thermal["planned_at"] = (moment - timedelta(minutes=7)).isoformat()
    if fault == "off":
        thermal["mode"] = "off"
    if fault == "boiler":
        thermal["mode"] = "boiler"
    if fault == "warm":
        tng["room_temperature"] = 21.6
    if fault == "no_refill":
        for r in payload["periods"][28:64]:
            r["distribution_tariff"] = "VT"
    if fault == "overload":
        values["house_w"] = 12000
    if fault == "invalid_prices":
        payload["periods"].pop()
    decisions = p.decide(values, payload, moment, thermal, tng)
    assert not any(d.action == "set_on_grid_soc_limit_pct" and d.value == 20 for d in decisions)
    assert not p.state["coordination"]["allowed"]


def test_response_changes_lead_without_raising_temperature_limits(tmp_path):
    assert required_quarters(21.3, 21.3, 6000) == 16
    assert required_quarters(21.0, 21.4, 3600) == 8
    assert required_quarters(21.3, 21.6, 6000) == 8
    assert required_quarters(21.3, 21.3, 600) == 8
    p = planner(tmp_path)
    moment = instant(6)
    atomic_write_json(
        p.config.data_dir / "thermal-response.json", dict(lead_quarters=16, assessed_at=moment.isoformat())
    )
    assert preheat_quarters(p.config, moment) == 16
    assert preheat_quarters(p.config, moment + timedelta(days=8)) == 8
    plan = build_plan(tariff_curve(), DAY, {}, preheat_width=16)
    assert plan["phases"][:2] == [dict(start=8, end=24, kind="preheat"), dict(start=24, end=28, kind="coast")]
    assert all(w["temperature"] <= 42 for w in plan["heating"]["schedule"])
    assert all(w["temperature"] <= 21.7 for w in plan["thermostat"]["schedule"])
    assert all(
        p["start"] >= 28 for p in build_plan(tariff_curve(), DAY, {}, earliest=28, preheat_width=16)["phases"]
    )


def test_only_confirmed_continuous_preheat_teaches_response(tmp_path):
    p = planner(tmp_path)
    c = p.config
    moment = instant(4)
    plan = build_plan(tariff_curve(), DAY, {})
    c.data["tng"] = {"price_shift": {"enabled": True}, "write_enabled": True}
    for key in ("heating", "thermostat"):
        override = deepcopy(plan[key])
        override["price_shift"] = dict(phases=plan["phases"], schedule_hash=fingerprint(plan[key]))
        c.data["tng"][key] = {"enabled": True, "date_overrides": {DAY: override}}

    def state(t, confirmed=True):
        return dict(
            heatpump=dict(sample_time=t.isoformat(), room_temperature=21.3),
            settings=dict(heating_on=True, boiler_on=False),
            DayTemperature=21.7,
            LastSettingsNotConfirmed=not confirmed,
        )

    for i in range(0, 120, 10):
        t = moment + timedelta(minutes=i)
        observe_response(c, state(t), t)
    t = instant(6)
    observe_response(c, state(t), t)
    assert preheat_quarters(c, t) == 16
    # A request that remains unconfirmed supplies no evidence of response.
    (c.data_dir / "thermal-response.json").unlink()
    for i in range(0, 121, 10):
        t = moment + timedelta(minutes=i)
        observe_response(c, state(t, False), t)
    assert preheat_quarters(c, t) == 8


def test_learning_does_not_move_today_completed_preheat_into_the_past(tmp_path):
    from hec.controller.response import planning_preheat_quarters

    p = planner(tmp_path)
    moment = instant(6)
    atomic_write_json(
        p.config.data_dir / "thermal-response.json", dict(lead_quarters=16, assessed_at=moment.isoformat())
    )
    p.config.data["tng"] = {
        "thermostat": {"date_overrides": {DAY: {"price_shift": {"required_preheat_minutes": 120}}}}
    }
    assert planning_preheat_quarters(p.config, DAY, moment) == 8
    assert planning_preheat_quarters(p.config, (moment.date() + timedelta(days=1)).isoformat(), moment) == 16


def test_nt_price_ramp_does_not_hide_nine_oclock_tariff_peak():
    data = tariff_curve()
    data["periods"][35]["price_total_czk_kwh"] = 7.8  # NT ramp at08:45
    plan = build_plan(data, DAY, {}, preheat_width=16)
    coast = next(p for p in plan["phases"] if p["kind"] == "coast" and p["start"] == 36)
    assert coast["end"] == 40
    pre = plan["phases"][plan["phases"].index(coast) - 1]
    assert pre == dict(start=28, end=36, kind="preheat")


def test_repair_uses_remaining_shorter_nt_window_without_backdating():
    plan = build_plan(tariff_curve(), DAY, {}, earliest=29, preheat_width=16)
    coast = next(p for p in plan["phases"] if p["kind"] == "coast" and p["start"] == 36)
    pre = plan["phases"][plan["phases"].index(coast) - 1]
    assert pre == dict(start=29, end=36, kind="preheat")
    assert all(p["start"] >= 29 for p in plan["phases"])
