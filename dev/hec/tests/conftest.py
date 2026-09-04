"""Společné pomůcky testů.

Testy nesmí sahat na síť ani na provozní data – všechny externí služby
(tngsmart.cz, OTE, Open-Meteo, Shelly, GoodWe) nahrazují falešné odpovědi.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEV_ROOT = PROJECT_ROOT / "dev"
for path in (str(PROJECT_ROOT), str(DEV_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


def pytest_collection_modifyitems(config, items):
    """Keep browser tests opt-in without shadowing this shared conftest."""
    del config
    if os.environ.get("HEC_RUN_E2E") == "1":
        return
    skip = pytest.mark.skip(reason="E2E requires HEC_RUN_E2E=1 and a running safe preview")
    for item in items:
        if "e2e" in item.nodeid:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure pytest-playwright for the local preview when E2E is enabled."""
    return {
        **browser_context_args,
        "base_url": os.environ.get("HEC_BASE_URL", "http://127.0.0.1:8181"),
        "ignore_https_errors": False,
    }


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200, payload=None, url: str = ""):
        self.text = text
        self.status_code = status_code
        self._payload = payload
        self.url = url

    def json(self):
        return self._payload if self._payload is not None else json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeCookies(dict):
    def set(self, name, value, **_kwargs):
        self[name] = value


class FakeSession:
    """Náhrada requests.Session – odpovědi se vybírají podle podřetězce v URL."""

    def __init__(self, routes: dict[str, FakeResponse]):
        self.routes = routes
        self.headers: dict[str, str] = {}
        self.cookies = FakeCookies({".AspNet.ApplicationCookie": "fake"})
        self.calls: list[tuple[str, str]] = []

    def _match(self, url: str) -> FakeResponse:
        for marker, response in self.routes.items():
            if marker in url:
                response.url = url
                return response
        raise AssertionError(f"Neočekávaný požadavek na {url}")

    def get(self, url, **_kwargs):
        self.calls.append(("GET", url))
        return self._match(url)

    def post(self, url, **_kwargs):
        self.calls.append(("POST", url))
        return self._match(url)


class FakeLog:
    """Zachytává log místo zápisu na disk."""

    def __init__(self):
        self.lines: list[str] = []

    def info(self, msg, *args):
        self.lines.append(str(msg) % args if args else str(msg))

    warning = info
    error = info

    def exception(self, msg, *args):
        self.lines.append("EXC " + (str(msg) % args if args else str(msg)))

    def has(self, needle: str) -> bool:
        return any(needle in line for line in self.lines)


@pytest.fixture
def fake_log():
    return FakeLog


@pytest.fixture
def tng_connect():
    """Přístupové údaje ve tvaru connect.json – smyšlené hodnoty."""
    return {
        "tng": {
            "base_url": "https://tngsmart.cz",
            "login_url": "https://tngsmart.cz/Pages/Login",
            "username": "tester",
            "password": "secret-password",
            "thermostat_id": 1,
            "thermostat_key": "THERMO-KEY",
            "timezone_cookie_name": "TimeZone-TEST",
            "timezone_cookie_value": "7200000",
            "accept_cookies": True,
            "user_agent": "test-agent",
            "headers": {"Accept": "application/json"},
            "endpoints": {
                "thermostat_settings": "/api/HeatPumpInsertThermostatSettings/{thermostat_key}",
                "basic_settings": "/api/HeatPumpInsertBasicSettings_v3/{basic_key}",
                "thermostat_page": "/Pages/Account/MyThermostat?ThermostatId={thermostat_id}",
                "heatpump_data": "/api/HeatPumpData/{heatpump_hash}-{from_ms}-{to_ms}-0",
                "installations_page": "/Pages/Account/MyInstallations?HeatPumpHash={heatpump_hash}",
            },
            "basic_key": "BASIC-KEY",
            "heatpump_hash": "HASH",
        }
    }


@pytest.fixture
def tng_config(tmp_path):
    """Minimální runtime konfigurace pro tng_controller."""
    return {
        "runtime": {
            "check_interval_seconds": 300,
            "request_timeout_seconds": 30,
            "dry_run": True,
            "minimum_change_interval_seconds": 900,
            "state_file": str(tmp_path / "runtime_state.json"),
            "telemetry_bootstrap_seconds": 3600,
            "telemetry_overlap_seconds": 120,
        },
        "logging": {"action_log": "logs/a.txt", "state_log": "logs/s.jsonl", "error_log": "logs/e.txt"},
        "heating": {"enabled": False, "default_temperature": 42, "schedule": []},
        "boiler": {"enabled": True, "default_temperature": 45,
                   "schedule": [{"from": "00:30", "to": "05:30", "temperature": 51}]},
        "thermostat": {"enabled": False, "default_temperature": 23.0, "schedule": []},
        "basic_settings_template": {"BoilerTemp": 48, "HeatTemp_Const": 42},
        "thermostat_settings_template": {"DayTemperature": 26, "NightTemperature": 24},
    }
