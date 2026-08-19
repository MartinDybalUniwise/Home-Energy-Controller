"""Testy sdílených datových struktur: ReaderStatus.state, EnergyInterval."""

from __future__ import annotations

from datetime import timedelta

from hec.core.model import EnergyInterval, ReaderStatus
from hec.core.timeutil import now_local


def test_reader_status_state_disabled_wins_over_everything():
    status = ReaderStatus(name="x", enabled=False, interval_seconds=10)
    status.last_error = "boom"
    assert status.state == "disabled"


def test_reader_status_state_error_when_last_attempt_failed():
    """last_error se čistí při úspěchu (BaseReader.poll) – jeho přítomnost
    vždy znamená, že poslední pokus selhal, bez ohledu na stáří dat."""
    status = ReaderStatus(name="x", enabled=True, interval_seconds=10,
                          last_success=now_local(), last_error="timeout")
    assert status.state == "error"


def test_reader_status_state_stale_when_data_too_old():
    status = ReaderStatus(name="x", enabled=True, interval_seconds=10,
                          last_success=now_local() - timedelta(hours=1))
    assert status.state == "stale"


def test_reader_status_state_ok_when_fresh_and_no_error():
    status = ReaderStatus(name="x", enabled=True, interval_seconds=60,
                          last_success=now_local())
    assert status.state == "ok"
    assert status.to_dict()["state"] == "ok"


def test_energy_interval_leaves_unknown_fields_as_none_not_zero():
    """Nikdy nefabrikovat nulu – nezměřené pole zůstává None."""
    interval = EnergyInterval(timestamp=now_local(), source="edc",
                              ean="859...", role="consumer", consumption_kwh=0.42)
    payload = interval.to_dict()
    assert payload["consumption_kwh"] == 0.42
    assert payload["production_kwh"] is None
    assert payload["shared_received_kwh"] is None
    assert payload["shared_sent_kwh"] is None
    assert payload["source"] == "edc" and payload["role"] == "consumer"
