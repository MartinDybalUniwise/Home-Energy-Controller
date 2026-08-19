"""Regresní testy funkčního chování tng_controller.py.

Tyto testy vznikly PŘED refaktorem a popisují stav, který musí zůstat zachován.
Nejcennější je change-gate: potvrzovací cyklus a minimální interval chrání
tepelné čerpadlo před zahlcením zápisy.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from conftest import FakeLog, FakeResponse, FakeSession

import tng_controller as legacy

THERMOSTAT_HTML = """
<html><script>
  var data = {"LastSettingsNotConfirmed": false, "DayTemperature": 26,
              "NightTemperature": 24, "SettingsAvailable": true,
              "RoomTemperature": 24.9, "BoilerTemperature": 51.4};
</script></html>
"""

INSTALLATIONS_HTML = """
<script>
HeatPump = {"Settings":{"BoilerSet":{"Boiler":true,"Sensor":true,"Boost":false},
"BoilerTemp":{"ShortValue":51,"FloatValue":51.0},
"HeatSet":{"Heat":false,"HeatingMode":0},
"HeatTemp_Const":{"ShortValue":42,"FloatValue":42.0},"EquitCurve":2},
"LastSettingsNotConfirmed":false,"AdvancedSettingsNotConfirmed":false}; CurrentHeatPumpHash = "HASH";
</script>
"""

TELEMETRY = {"First": [
    {"time": "2026-08-18T10:51:23Z", "t": 234, "tw": 309, "tb": 514, "tt": 249},
    {"time": "2026-08-18T10:56:23Z", "t": 236, "tw": 311, "tb": 515, "tt": 250},
]}


def build(tng_connect, tng_config, routes=None):
    action, state, error = FakeLog(), FakeLog(), FakeLog()
    controller = legacy.TNG(tng_connect, tng_config, action, state, error)
    controller.s = FakeSession(routes or {
        "MyThermostat": FakeResponse(THERMOSTAT_HTML),
        "MyInstallations": FakeResponse(INSTALLATIONS_HTML),
        "HeatPumpData": FakeResponse(payload=TELEMETRY),
    })
    return controller, action, state, error


# --- časová okna a rozvrhy -------------------------------------------------

@pytest.mark.parametrize("time_str,start,end,expected", [
    ("01:00", "00:30", "05:30", True),
    ("05:30", "00:30", "05:30", False),   # horní hranice je vyloučená
    ("00:30", "00:30", "05:30", True),    # dolní hranice je zahrnutá
    ("23:00", "22:00", "06:00", True),    # okno přes půlnoc
    ("03:00", "22:00", "06:00", True),
    ("07:00", "22:00", "06:00", False),
])
def test_in_window(time_str, start, end, expected):
    now = datetime.strptime(f"2026-08-18 {time_str}", "%Y-%m-%d %H:%M")
    assert legacy.in_window(now, start, end) is expected


def test_scheduled_value_uses_default_outside_windows():
    section = {"default_temperature": 45, "schedule": [{"from": "00:30", "to": "05:30", "temperature": 51}]}
    assert legacy.scheduled_value(section, datetime(2026, 8, 18, 12, 0)) == 45
    assert legacy.scheduled_value(section, datetime(2026, 8, 18, 1, 0)) == 51


def test_scheduled_value_last_matching_window_wins():
    section = {"default_temperature": 45, "schedule": [
        {"from": "00:00", "to": "12:00", "temperature": 48},
        {"from": "10:00", "to": "11:00", "temperature": 52},
    ]}
    assert legacy.scheduled_value(section, datetime(2026, 8, 18, 10, 30)) == 52


# --- change-gate: ochrana tepelného čerpadla -------------------------------

def test_gate_blocks_while_tng_reports_pending(tng_connect, tng_config):
    controller, _, _, _ = build(tng_connect, tng_config)
    allowed, reason = controller._can_post("basic", True)
    assert allowed is False
    assert "LastSettingsNotConfirmed" in reason


def test_gate_requires_true_false_confirmation_cycle(tng_connect, tng_config):
    controller, action, _, _ = build(tng_connect, tng_config)
    controller._mark_posted("basic", {"boiler_temperature": 51})

    # Bezprostředně po zápisu se čeká na potvrzení.
    assert controller._can_post("basic", False)[0] is False
    # Čerpadlo potvrdí převzetí (pending TRUE) …
    controller._gate_update("basic", True)
    assert controller.change_gate["basic"]["seen_pending"] is True
    # … a po návratu na FALSE je cyklus uzavřen.
    controller._gate_update("basic", False)
    assert controller.change_gate["basic"]["awaiting_confirmation"] is False
    assert action.has("CONFIRMED")


def test_gate_enforces_minimum_interval_after_confirmation(tng_connect, tng_config):
    controller, _, _, _ = build(tng_connect, tng_config)
    controller._mark_posted("basic", {"boiler_temperature": 51})
    controller._gate_update("basic", True)
    controller._gate_update("basic", False)

    allowed, reason = controller._can_post("basic", False)
    assert allowed is False
    assert "minimum change interval" in reason


def test_gate_recovers_when_true_phase_was_missed(tng_connect, tng_config):
    """Po restartu procesu se fáze TRUE nemusí zachytit – po 900 s stačí FALSE."""
    controller, action, _, _ = build(tng_connect, tng_config)
    controller._mark_posted("basic", {"boiler_temperature": 51})
    stale = datetime.now().astimezone() - timedelta(seconds=1000)
    controller.change_gate["basic"]["last_post_at"] = stale.isoformat()

    controller._gate_update("basic", False)
    assert controller.change_gate["basic"]["awaiting_confirmation"] is False
    assert action.has("CONFIRMED_RECOVERY")
    assert controller._can_post("basic", False)[0] is True


def test_runtime_state_survives_restart(tng_connect, tng_config):
    controller, _, _, _ = build(tng_connect, tng_config)
    controller._mark_posted("thermostat", {"day_temperature": 23})

    reloaded, _, _, _ = build(tng_connect, tng_config)
    assert reloaded.change_gate["thermostat"]["awaiting_confirmation"] is True
    assert reloaded.change_gate["thermostat"]["last_requested"] == {"day_temperature": 23}


# --- čtení stavu -----------------------------------------------------------

def test_read_state_parses_settings_and_telemetry(tng_connect, tng_config):
    controller, _, state, _ = build(tng_connect, tng_config)
    out = controller.read_state()

    assert out["settings"]["boiler_on"] is True
    assert out["settings"]["boiler_set_temperature"] == 51.0
    assert out["settings"]["heating_on"] is False
    assert out["settings"]["equit_curve"] == 2
    # Telemetrie TNG chodí v desetinách stupně.
    assert out["heatpump"]["outside_temperature"] == 23.6
    assert out["heatpump"]["boiler_temperature"] == 51.5
    assert out["heatpump"]["room_temperature"] == 25.0


def test_read_state_writes_one_jsonl_line_per_sample(tng_connect, tng_config):
    controller, _, state, _ = build(tng_connect, tng_config)
    controller.read_state()

    assert len(state.lines) == 2
    record = json.loads(state.lines[0])
    assert record["sample_time"] == "2026-08-18T10:51:23Z"
    assert record["boiler_temperature"] == 51.4
    assert record["boiler_set_temperature"] == 51.0
    assert record["timestamp"].endswith(("+02:00", "+01:00", "+00:00"))


def test_read_state_does_not_repeat_already_stored_samples(tng_connect, tng_config):
    """Kurzor telemetrie zabraňuje duplicitám při překryvu dotazovaného okna."""
    controller, _, state, _ = build(tng_connect, tng_config)
    controller.read_state()
    state.lines.clear()

    controller.read_state()
    assert state.lines == []
    assert controller.telemetry_state["last_sample_time"] == "2026-08-18T10:56:23Z"


def test_apply_skips_post_when_tng_already_matches_schedule(tng_connect, tng_config):
    """Nastavení, které v TNG už platí, se znovu neposílá."""
    tng_config["boiler"]["schedule"] = [{"from": "00:00", "to": "23:59", "temperature": 51}]
    controller, action, _, _ = build(tng_connect, tng_config)
    state = controller.read_state()

    controller.apply(state)
    assert not any("POST" in line or "DRY_RUN" in line for line in action.lines)
