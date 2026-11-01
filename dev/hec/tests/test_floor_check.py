from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from hec.controller.floor import floor_plan
from hec.core.config import Config
from hec.storage.base import read_json

START = datetime.fromisoformat("2026-11-01T17:00:00+01:00")
BASE = dict(
    mode="heating",
    heating_temperature=42,
    boiler_temperature=50,
    room_target=21.5,
    phase="normal",
    planned_at=START.isoformat(),
)


def configured(tmp_path):
    c = Config(
        dict(
            storage={"data_path": str(tmp_path)},
            tng=dict(
                write_enabled=True,
                heating={"enabled": True},
                thermostat={"enabled": True},
                floor_check=dict(enabled=True, activated_at=START.isoformat()),
            ),
        ),
        root=tmp_path,
    )
    return c


def inputs(t, aku=40.5, room=21.6, target=21.5):
    hp = dict(
        sample_time=t.isoformat(), room_temperature=room, water_output_temperature=37, outside_temperature=7
    )
    state = dict(
        heatpump=hp,
        DayTemperature=target,
        LastSettingsNotConfirmed=False,
        settings=dict(
            heating_on=True,
            boiler_on=False,
            heating_set_temperature=42,
            boiler_set_temperature=50,
            last_settings_not_confirmed=False,
            external_circulation_pump=True,
        ),
    )
    wire = dict(
        sample_time=t.isoformat(),
        online=True,
        buffer_temperature=aku,
        room_temperature=room,
        water_output_temperature=37,
        water_input_temperature=36,
        outside_temperature=7,
        field_quality={
            k: "photo_validated_provisional"
            for k in ("buffer_temperature", "water_input_temperature", "water_output_temperature")
        },
    )
    gate = {
        k: dict(awaiting_confirmation=False, last_post_at=None, last_requested={})
        for k in ("basic", "thermostat")
    }
    return state, wire, gate


def resolve(c, t, aku=40.5, room=21.6, target=21.5, gate=None, base=None):
    state, wire, gates = inputs(t, aku, room, target)
    return floor_plan(c, base or BASE, state, wire, gate or gates, t)


def requesting(c):
    resolve(c, START)
    t = START + timedelta(hours=1)
    plan = resolve(c, t)
    assert plan["floor_check"]["phase"] == "preparing"
    t += timedelta(minutes=1)
    plan = resolve(c, t)
    assert plan["room_target"] == 22.1
    state, wire, gate = inputs(t)
    gate["thermostat"].update(last_post_at=t.isoformat(), last_requested={"day_temperature": 22.1})
    return t, gate


def test_hourly_idle_check_and_bounded_temporary_request(tmp_path):
    c = configured(tmp_path)
    first = resolve(c, START)
    assert first["floor_check"]["next_check_at"] == (START + timedelta(hours=1)).isoformat()
    assert resolve(c, START + timedelta(minutes=59))["room_target"] == 21.5
    t, gate = requesting(c)
    plan = resolve(c, t + timedelta(minutes=2), aku=36.5, target=22.1, gate=gate)
    assert plan["floor_check"]["observations"]["2"]["aku_c"] == 36.5
    assert plan["floor_check"]["pump_run_measured"] is False
    assert plan["room_target"] == 22.1 and plan["heating_temperature"] == 42
    plan = resolve(c, t + timedelta(minutes=5), aku=34.5, target=22.1, gate=gate)
    assert plan["phase"] == "floor_reheat" and plan["heating_temperature"] == 42
    assert read_json(c.data_dir / "floor-circulation-state.json")["active"]["below_minimum_seen"]


def test_recovery_needs_minimum_duration_stability_then_restores_current_plan(tmp_path):
    c = configured(tmp_path)
    t, gate = requesting(c)
    for minute in (2, 5, 10, 13, 14):
        plan = resolve(c, t + timedelta(minutes=minute), aku=38.2, target=22.1, gate=gate)
        assert plan["room_target"] == 22.1
    changed = {**BASE, "room_target": 21.2, "heating_temperature": 35, "phase": "coast"}
    plan = resolve(c, t + timedelta(minutes=15), aku=38.2, target=22.1, gate=gate, base=changed)
    assert plan["floor_check"]["phase"] == "restoring"
    assert plan["room_target"] == 21.2 and plan["heating_temperature"] == 35
    # A persisted cycle survives restart; it must await actual restore acknowledgement.
    clone = Config(deepcopy(c.data), root=c.root)
    plan = resolve(clone, t + timedelta(minutes=16), aku=38.2, target=21.2, gate=gate, base=changed)
    assert plan["floor_check"]["phase"] == "idle"
    assert plan["floor_check"]["last_cycle"]["outcome"] == "buffer_stable_and_recovered"


def test_unknown_low_aku_is_not_zero_and_maximum_duration_still_restores(tmp_path):
    c = configured(tmp_path)
    t, gate = requesting(c)
    plan = resolve(c, t + timedelta(minutes=10), aku=33.2, target=22.1, gate=gate)
    assert plan["floor_check"]["aku_c"] is None
    assert plan["floor_check"]["observations"]["10"]["aku_c"] is None
    assert plan["heating_temperature"] == 42
    plan = resolve(c, t + timedelta(minutes=45), aku=33.2, target=22.1, gate=gate)
    assert plan["floor_check"]["phase"] == "restoring" and plan["room_target"] == 21.5


@pytest.mark.parametrize(
    "fault",
    [
        "aku_stale",
        "aku_range",
        "cloud_mismatch",
        "room_stale",
        "boiler",
        "off",
        "writer_off",
        "pump_disabled",
        "room_limit",
        "pending",
    ],
)
def test_no_hourly_request_with_unsafe_or_disabled_input(tmp_path, fault):
    c = configured(tmp_path)
    resolve(c, START)
    t = START + timedelta(hours=1)
    state, wire, gate = inputs(t)
    base = dict(BASE)
    if fault == "aku_stale":
        wire["sample_time"] = (t - timedelta(minutes=4)).isoformat()
    if fault == "aku_range":
        wire["buffer_temperature"] = 43
    if fault == "cloud_mismatch":
        wire["water_output_temperature"] = 20
    if fault == "room_stale":
        state["heatpump"]["sample_time"] = (t - timedelta(minutes=16)).isoformat()
    if fault == "boiler":
        base["mode"] = "boiler"
    if fault == "off":
        base["mode"] = "off"
    if fault == "writer_off":
        c.data["tng"]["write_enabled"] = False
    if fault == "pump_disabled":
        state["settings"]["external_circulation_pump"] = False
    if fault == "room_limit":
        state["heatpump"]["room_temperature"] = 24
    if fault == "pending":
        gate["thermostat"]["awaiting_confirmation"] = True
    plan = floor_plan(c, base, state, wire, gate, t)
    assert plan["room_target"] == 21.5
    assert not read_json(c.data_dir / "floor-circulation-state.json", {}).get("active")


def test_ordinary_confirmed_heating_resets_idle_counter(tmp_path):
    c = configured(tmp_path)
    for minute in (0, 30, 60, 90):
        plan = resolve(c, START + timedelta(minutes=minute), room=21.3)
        assert plan["room_target"] == 21.5
        assert plan["floor_check"]["reason"] == "heating_assumed_from_confirmed_thermostat_demand"
    assert not read_json(c.data_dir / "floor-circulation-state.json").get("active")


def test_mode_change_during_test_keeps_dhw_exclusive(tmp_path):
    c = configured(tmp_path)
    t, gate = requesting(c)
    base = {**BASE, "mode": "boiler"}
    plan = resolve(c, t + timedelta(minutes=5), target=22.1, gate=gate, base=base)
    assert plan["mode"] == "boiler" and plan["room_target"] == 21.5
    assert plan["floor_check"]["phase"] == "restoring"


def test_requests_are_not_mistaken_for_sent_or_acknowledged_commands(tmp_path):
    c = configured(tmp_path)
    t, _ = requesting(c)
    plan = resolve(c, t + timedelta(minutes=5))
    assert plan["floor_check"]["request_sent_at"] is None
    assert plan["floor_check"]["acknowledged_at"] is None
    plan = resolve(c, t + timedelta(minutes=31))
    assert plan["floor_check"]["phase"] == "idle"
    assert plan["floor_check"]["last_cycle"]["outcome"] == "request_not_sent_timeout"
    assert plan["floor_check"]["last_cycle"].get("request_sent_at") is None


def test_tng_cadence_fast_only_during_existing_floor_cycle(tmp_path, tng_connect):
    from test_readers_ote_tng import build_tng

    reader, _, _ = build_tng(tmp_path, tng_connect, floor_check={"enabled": True})
    assert reader.interval_seconds() == 300
    reader.floor_check_status = {"phase": "testing"}
    assert reader.interval_seconds() == 60
    reader.floor_check_status = {"phase": "idle"}
    assert reader.interval_seconds() == 300


def test_preserve_external_pump_flag_in_normal_tng_writer(tmp_path, tng_connect):
    from unittest.mock import patch

    from test_readers_ote_tng import build_tng

    reader, _, _ = build_tng(
        tmp_path, tng_connect, write_enabled=True, heating={"enabled": True, "default_temperature": 42}
    )
    reader.planner = SimpleNamespace(prepare_tng=lambda *args: dict(BASE))
    state, _, _ = inputs(START)
    state["settings"]["heating_set_temperature"] = 35
    with patch.object(reader, "post_json", return_value=204) as post:
        reader.apply(state, moment=START)
    payload = next(c.args[1] for c in post.call_args_list if c.args[0] == "basic_settings")
    assert payload["HeatSet"]["ExternalCirculationPump"] is True


def test_storage_failure_preserves_ordinary_controller_plan(tmp_path, tng_connect, monkeypatch):
    from test_tng_price import BASE as TNG_BASE
    from test_unified_controller import connected

    reader, controller, _, state = connected(tmp_path, tng_connect)

    def fail(*args):
        raise OSError("test persistence failure")

    monkeypatch.setattr("hec.controller.thermal.floor_plan", fail)
    plan = controller.prepare_tng(reader, state, TNG_BASE)
    assert plan["mode"] == "heating" and plan["heating_temperature"] == 35
    assert plan["floor_check"]["phase"] == "error"


def test_live_adapter_keeps_confirmation_and_900s_guard_for_floor_cycle(tmp_path, tng_connect):
    from unittest.mock import patch

    from hec.storage.jsonl import JsonlStorage
    from test_readers_ote_tng import build_tng

    reader, c, _ = build_tng(
        tmp_path,
        tng_connect,
        write_enabled=True,
        floor_check={"enabled": True, "activated_at": START.isoformat()},
        operation={"default_mode": "heating", "schedule": []},
        heating={"enabled": True, "default_temperature": 42, "schedule": []},
        thermostat={"enabled": True, "default_temperature": 21.5, "schedule": []},
    )
    reader.storage = JsonlStorage(c.data_dir, c.history_dir)
    posts = []

    def post(endpoint, payload, kind):
        posts.append((current[0], endpoint, deepcopy(payload)))
        return 204

    current = [START]
    with (
        patch.object(reader, "post_json", side_effect=post),
        patch("hec.readers.tng.now_local", side_effect=lambda: current[0]),
    ):
        for minute in (0, 60, 61, 62, 63, 65, 75, 76, 77, 78):
            now = START + timedelta(minutes=minute)
            current[0] = now
            pulse_sent = any(
                endpoint == "thermostat_settings" and p["DayTemperature"] == 22.1 for _, endpoint, p in posts
            )
            state, wire, _ = inputs(
                now,
                aku=38.2 if minute >= 75 else 34.5 if minute >= 65 else 40.5,
                target=22.1 if pulse_sent else 21.5,
            )
            state["LastSettingsNotConfirmed"] = bool(pulse_sent and minute < 77)
            reader.storage.write_current("tng_wire", wire)
            reader.apply(state, moment=now)
    service = [
        p for _, endpoint, p in posts if endpoint == "thermostat_settings" and p["DayTemperature"] == 22.1
    ]
    assert service, posts
    thermostat_posts = [(t, p) for t, endpoint, p in posts if endpoint == "thermostat_settings"]
    assert thermostat_posts[-1][1]["DayTemperature"] == 21.5
    assert all(
        (b[0] - a[0]).total_seconds() >= 900
        for a, b in zip(thermostat_posts, thermostat_posts[1:], strict=False)
    )
    assert reader.floor_check_status["phase"] == "restoring"


def test_floor_reheat_can_use_same_battery_priority_with_warm_living_room(tmp_path):
    from test_battery_economic import instant, planner, row
    from test_coordinated_peaks import tariff_curve

    p = planner(tmp_path)
    p.memory = {"basis": 7.9232}
    now = instant(6) + timedelta(minutes=44)
    values = row(6)
    values.update(
        timestamp=now.isoformat(),
        inverter_time=now.isoformat(),
        battery_soc=56,
        on_grid_soc_limit_pct=56,
        house_w=3200,
    )
    thermal = dict(
        mode="heating",
        phase="floor_reheat",
        planned_at=now.isoformat(),
        floor_check={"phase": "reheating", "request_sent_at": now.isoformat()},
    )
    tng = dict(heating_on=True, room_temperature=21.6, sample_time=now.isoformat())
    decisions = p.decide(values, tariff_curve(), now, thermal, tng)
    assert decisions and decisions[0].action == "set_on_grid_soc_limit_pct" and decisions[0].value == 20


@pytest.mark.parametrize("aku", [30.0, 33.2, 34.1])
def test_owner_extended_aku_range_latches_reheat(tmp_path, aku):
    c = configured(tmp_path)
    t, gate = requesting(c)
    moment = t + timedelta(minutes=5)
    state, wire, _ = inputs(moment, aku=aku, target=22.1)
    wire["field_quality"]["buffer_temperature"] = "owner_extended_provisional"
    plan = floor_plan(c, BASE, state, wire, gate, moment)
    assert plan["floor_check"]["phase"] == "reheating"
    assert plan["floor_check"]["aku_c"] == aku
    assert plan["floor_check"]["aku_quality"] == "owner_extended_range_cloud_crosschecked"
    assert plan["heating_temperature"] == 42


@pytest.mark.parametrize("aku", [29.9, 41.6])
def test_owner_extended_aku_range_still_rejects_outside(tmp_path, aku):
    from hec.controller.floor import qualified_aku
    state, wire, _ = inputs(START, aku=aku)
    wire["field_quality"]["buffer_temperature"] = "owner_extended_provisional"
    assert qualified_aku(wire, state["heatpump"], START)[0] is None
