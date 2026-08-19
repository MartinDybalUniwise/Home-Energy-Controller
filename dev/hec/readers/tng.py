"""Reader a zapisovač tepelného čerpadla TNG (tngsmart.cz).

Přenos ověřené logiky z prototypu `tng_controller.py`. Zachováno beze změny:

* přihlášení do ASP.NET WebForms a doplnění cookies TimeZone/acceptCookies,
* čtení stavu z HTML stránek MyThermostat a MyInstallations,
* telemetrie z /api/HeatPumpData s hodnotami v desetinách °C,
* **change-gate**: po zápisu se čeká na cyklus `LastSettingsNotConfirmed`
  false → true → false a na minimální interval 900 s. Bez toho se do TNG
  nesmí zapisovat – je to ochrana čerpadla, ne optimalizace.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..core.logging_setup import register_secrets
from ..core.model import Sample
from ..core.secrets import collect_secret_values, expand_tree
from ..core.timeutil import in_window, now_local, parse_iso, to_iso
from ..storage.base import atomic_write_json, read_json
from .base import BaseReader

SCALAR_RE = re.compile(
    r'["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?\s*:\s*(true|false|null|-?\d+(?:\.\d+)?|["\'][^"\']*["\'])',
    re.I)
WANTED_WORDS = ("temp", "heat", "boiler", "thermostat", "outside", "outdoor", "room", "water",
                "sensor", "boost", "pool", "regulation", "curve", "confirmed", "available",
                "incoming", "changed")
HEATPUMP_RE = re.compile(r'HeatPump\s*=\s*(\{.*?\});\s*CurrentHeatPumpHash', re.S)


def scheduled_value(section: dict, moment: datetime):
    """Teplota podle rozvrhu. Poslední vyhovující okno vyhrává."""
    value = section.get("default_temperature")
    for window in section.get("schedule", []) or []:
        if in_window(moment, window["from"], window["to"]):
            value = window["temperature"]
    return value


class TngReader(BaseReader):
    name = "tng"

    def __init__(self, config, storage=None, session=None, connect=None):
        self.connect = connect if connect is not None else self._load_connect(config)
        self.tng = self.connect.get("tng", {})
        register_secrets(collect_secret_values(self.connect))
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.tng.get("user_agent", "")})
        self.state_path = Path(config.data_dir) / "tng_runtime_state.json"
        self.change_gate = {
            "basic": {"last_post_at": None, "awaiting_confirmation": False,
                      "seen_pending": False, "last_requested": None},
            "thermostat": {"last_post_at": None, "awaiting_confirmation": False,
                           "seen_pending": False, "last_requested": None},
        }
        self.telemetry_state = {"last_sample_time": None}
        self.pending_sent: dict[str, str] = {}
        self._telemetry_records: list[dict] = []
        super().__init__(config, storage)
        self._load_state()

    # --- konfigurace a stav -------------------------------------------------
    @staticmethod
    def _load_connect(config) -> dict:
        path = Path(config.get("tng.connect_file", "connect.json"))
        if not path.is_absolute():
            path = config.root / path
        data = read_json(path, {}) or {}
        return expand_tree(data)

    def interval_seconds(self) -> int:
        return int(self.config.get("polling.tng_seconds", 300))

    def _load_state(self) -> None:
        saved = read_json(self.state_path, {}) or {}
        for kind in ("basic", "thermostat"):
            if isinstance(saved.get(kind), dict):
                for key in ("last_post_at", "awaiting_confirmation", "seen_pending", "last_requested"):
                    if key in saved[kind]:
                        self.change_gate[kind][key] = saved[kind][key]
        if isinstance(saved.get("telemetry"), dict):
            self.telemetry_state["last_sample_time"] = saved["telemetry"].get("last_sample_time")

    def _save_state(self) -> None:
        atomic_write_json(self.state_path, {
            "basic": self.change_gate["basic"],
            "thermostat": self.change_gate["thermostat"],
            "telemetry": self.telemetry_state,
        })

    # --- HTTP --------------------------------------------------------------
    @property
    def timeout(self) -> int:
        return int(self.config.get("tng.request_timeout_seconds", 30))

    def url(self, key: str) -> str:
        endpoint = self.tng["endpoints"][key].format(
            thermostat_key=self.tng.get("thermostat_key", ""),
            basic_key=self.tng.get("basic_key", ""),
            thermostat_id=self.tng.get("thermostat_id", ""),
            heatpump_hash=self.tng.get("heatpump_hash", ""),
            from_ms="{from_ms}", to_ms="{to_ms}")
        return urljoin(self.tng["base_url"], endpoint)

    def login(self) -> None:
        response = self.session.get(self.tng["login_url"], timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        def field(name: str) -> str:
            element = soup.find("input", {"name": name})
            return element.get("value", "") if element else ""

        body = {
            "__EVENTTARGET": "", "__EVENTARGUMENT": "",
            "__VIEWSTATE": field("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": field("__VIEWSTATEGENERATOR"),
            "ctl00$MainContent$UserName": self.tng["username"],
            "ctl00$MainContent$Password": self.tng["password"],
            "ctl00$MainContent$ctl01": "Log In",
        }
        response = self.session.post(
            self.tng["login_url"], data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=self.timeout)
        response.raise_for_status()
        if ".AspNet.ApplicationCookie" not in self.session.cookies:
            raise RuntimeError("TNG login failed: authentication cookie missing")
        self.session.cookies.set(self.tng["timezone_cookie_name"],
                                 self.tng["timezone_cookie_value"], domain="tngsmart.cz", path="/")
        self.session.cookies.set("acceptCookies",
                                 "true" if self.tng.get("accept_cookies", True) else "false",
                                 domain="tngsmart.cz", path="/")
        self.log.info("login_ok")

    def ensure_login(self) -> None:
        if ".AspNet.ApplicationCookie" not in self.session.cookies:
            self.login()

    def _get(self, url: str, accept: str | None = None):
        headers = copy.deepcopy(self.tng.get("headers", {}))
        if accept:
            headers["Accept"] = accept
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        if response.status_code in (401, 403) or "Please Sign In" in getattr(response, "text", ""):
            self.session.cookies.clear()
            self.login()
            response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response

    # --- čtení -------------------------------------------------------------
    def read(self) -> dict:
        self.ensure_login()
        state = self.read_state()
        if self.config.get("tng.write_enabled", False):
            self.apply(state)
        settings = state.get("settings") or {}
        heatpump = state.get("heatpump") or {}
        return {
            "outside_temperature": heatpump.get("outside_temperature"),
            "water_output_temperature": heatpump.get("water_output_temperature"),
            "boiler_temperature": heatpump.get("boiler_temperature"),
            "room_temperature": heatpump.get("room_temperature"),
            "sample_time": heatpump.get("sample_time"),
            "boiler_on": settings.get("boiler_on"),
            "boiler_set_temperature": settings.get("boiler_set_temperature"),
            "heating_on": settings.get("heating_on"),
            "heating_set_temperature": settings.get("heating_set_temperature"),
            "heating_mode": settings.get("heating_mode"),
            "equit_curve": settings.get("equit_curve"),
            "pending_change": settings.get("last_settings_not_confirmed"),
            "write_enabled": bool(self.config.get("tng.write_enabled", False)),
        }

    def read_state(self) -> dict:
        page = self._get(self.url("thermostat_page"))
        out: dict = {"timestamp": to_iso(now_local()), "http": page.status_code}

        raw: dict = {}
        for match in SCALAR_RE.finditer(page.text):
            key, value = match.group(1), match.group(2)
            if not any(word in key.lower() for word in WANTED_WORDS):
                continue
            lowered = value.lower()
            if lowered == "true":
                value = True
            elif lowered == "false":
                value = False
            elif lowered == "null":
                value = None
            elif value[:1] in ("'", '"'):
                value = value[1:-1]
            else:
                try:
                    value = float(value) if "." in value else int(value)
                except ValueError:
                    pass
            raw[key] = value
        out["tng"] = raw
        for key in ("LastSettingsNotConfirmed", "DayTemperature", "NightTemperature"):
            if key in raw:
                out[key] = raw[key]

        out["settings"] = self._read_settings()
        out["heatpump"], samples = self._read_telemetry()
        self._telemetry_records = self._telemetry_history(samples, out["settings"])
        return out

    def _read_settings(self) -> dict:
        endpoint = self.tng["endpoints"].get(
            "installations_page", "/Pages/Account/MyInstallations?HeatPumpHash={heatpump_hash}")
        url = urljoin(self.tng["base_url"],
                      endpoint.format(heatpump_hash=self.tng.get("heatpump_hash", "")))
        response = self._get(url, accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        match = HEATPUMP_RE.search(response.text)
        if not match:
            self.log.warning("settings_not_found | page=MyInstallations")
            return {}

        heatpump = json.loads(match.group(1))
        settings = heatpump.get("Settings") or {}
        boiler_set = settings.get("BoilerSet") or {}
        boiler_temp = settings.get("BoilerTemp") or {}
        heat_set = settings.get("HeatSet") or {}
        heat_temp = settings.get("HeatTemp_Const") or {}
        return {
            "boiler_on": boiler_set.get("Boiler"),
            "boiler_set_temperature": boiler_temp.get("FloatValue", boiler_temp.get("ShortValue")),
            "boiler_sensor": boiler_set.get("Sensor"),
            "boiler_boost": boiler_set.get("Boost"),
            "heating_on": heat_set.get("Heat"),
            "heating_set_temperature": heat_temp.get("FloatValue", heat_temp.get("ShortValue")),
            "heating_mode": heat_set.get("HeatingMode"),
            "equit_curve": settings.get("EquitCurve"),
            "last_settings_not_confirmed": heatpump.get("LastSettingsNotConfirmed"),
            "advanced_settings_not_confirmed": heatpump.get("AdvancedSettingsNotConfirmed"),
        }

    def _read_telemetry(self) -> tuple[dict, list[dict]]:
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        bootstrap = int(self.config.get("tng.telemetry_bootstrap_seconds", 3600))
        overlap = int(self.config.get("tng.telemetry_overlap_seconds", 120))
        from_ms = now_ms - bootstrap * 1000
        cursor = parse_iso(self.telemetry_state.get("last_sample_time"))
        if cursor is not None:
            from_ms = max(0, int(cursor.timestamp() * 1000) - overlap * 1000)

        endpoint = self.tng["endpoints"]["heatpump_data"].format(
            heatpump_hash=self.tng.get("heatpump_hash", ""), from_ms=from_ms, to_ms=now_ms)
        response = self._get(urljoin(self.tng["base_url"], endpoint), accept="*/*")
        samples = response.json().get("First") or []
        if not samples:
            self.log.warning("telemetry_empty | from_ms=%s to_ms=%s", from_ms, now_ms)
            return {"sample_time": None}, []

        last = samples[-1]
        return {
            "sample_time": last.get("time"),
            "outside_temperature": self._tenths(last, "t"),
            "water_output_temperature": self._tenths(last, "tw"),
            "boiler_temperature": self._tenths(last, "tb"),
            "room_temperature": self._tenths(last, "tt"),
        }, samples

    @staticmethod
    def _tenths(sample: dict, key: str):
        """Telemetrie TNG chodí v desetinách stupně."""
        value = sample.get(key)
        return None if value is None else value / 10.0

    def _telemetry_history(self, samples: list[dict], settings: dict) -> list[dict]:
        """Vzorky novější než kurzor. Překryv okna se tak nezapíše dvakrát."""
        cursor_time = self.telemetry_state.get("last_sample_time")
        cursor = parse_iso(cursor_time)
        newest_time, newest = cursor_time, cursor
        records: list[dict] = []

        for sample in samples:
            stamp = parse_iso(sample.get("time"))
            if stamp is None:
                continue
            if cursor is not None and stamp <= cursor:
                continue
            records.append({
                "timestamp": to_iso(now_local()),
                "source": self.name,
                "sample_time": sample.get("time"),
                "outside_temperature": self._tenths(sample, "t"),
                "water_output_temperature": self._tenths(sample, "tw"),
                "boiler_temperature": self._tenths(sample, "tb"),
                "room_temperature": self._tenths(sample, "tt"),
                "boiler_on": settings.get("boiler_on"),
                "boiler_set_temperature": settings.get("boiler_set_temperature"),
                "boiler_sensor": settings.get("boiler_sensor"),
                "boiler_boost": settings.get("boiler_boost"),
                "heating_on": settings.get("heating_on"),
                "heating_set_temperature": settings.get("heating_set_temperature"),
                "heating_mode": settings.get("heating_mode"),
                "equit_curve": settings.get("equit_curve"),
            })
            if newest is None or stamp > newest:
                newest, newest_time = stamp, sample.get("time")

        if newest_time and newest_time != cursor_time:
            self.telemetry_state["last_sample_time"] = newest_time
            self._save_state()
        return records

    def history_targets(self, values: dict, sample: Sample) -> list[tuple[str, dict]]:
        return [(self.name, record) for record in self._telemetry_records]

    # --- change-gate --------------------------------------------------------
    def _seconds_since_last_post(self, kind: str) -> float | None:
        stamp = parse_iso(self.change_gate[kind].get("last_post_at"))
        if stamp is None:
            return None
        return max(0.0, (now_local() - stamp).total_seconds())

    def _gate_update(self, kind: str, pending_flag) -> None:
        """Sleduje potvrzovací cyklus TNG: po zápisu má přijít TRUE a pak FALSE."""
        gate = self.change_gate[kind]
        if not gate["awaiting_confirmation"]:
            return
        if pending_flag is True:
            if not gate["seen_pending"]:
                gate["seen_pending"] = True
                self._save_state()
            return
        if pending_flag is False and gate["seen_pending"]:
            gate["awaiting_confirmation"] = False
            gate["seen_pending"] = False
            self._save_state()
            self.log.info("change_confirmed | kind=%s", kind)
        elif pending_flag is False:
            # Restart procesu mohl fázi TRUE minout; po uplynutí guardu stačí FALSE.
            elapsed = self._seconds_since_last_post(kind)
            minimum = int(self.config.get("tng.minimum_change_interval_seconds", 900))
            if elapsed is not None and elapsed >= minimum:
                gate["awaiting_confirmation"] = False
                self._save_state()
                self.log.info("change_confirmed_recovery | kind=%s elapsed_s=%d", kind, int(elapsed))

    def can_post(self, kind: str, pending_flag) -> tuple[bool, str]:
        self._gate_update(kind, pending_flag)
        gate = self.change_gate[kind]
        if pending_flag is True:
            return False, "TNG reports LastSettingsNotConfirmed=true"
        if gate["awaiting_confirmation"]:
            return False, "waiting for TNG confirmation cycle TRUE -> FALSE"
        minimum = int(self.config.get("tng.minimum_change_interval_seconds", 900))
        elapsed = self._seconds_since_last_post(kind)
        if elapsed is not None and elapsed < minimum:
            return False, f"minimum change interval not reached ({int(elapsed)}s/{minimum}s)"
        return True, "ok"

    def _mark_posted(self, kind: str, requested: dict | None = None) -> None:
        gate = self.change_gate[kind]
        gate["last_post_at"] = to_iso(now_local())
        gate["awaiting_confirmation"] = True
        gate["seen_pending"] = False
        gate["last_requested"] = requested
        self._save_state()

    # --- zápis --------------------------------------------------------------
    def post_json(self, endpoint: str, payload: dict, kind: str) -> int:
        self.ensure_login()
        headers = copy.deepcopy(self.tng.get("headers", {}))
        headers["Content-Type"] = "application/json; charset=UTF-8"
        if not self.config.get("tng.write_enabled", False):
            self.log.info("dry_run | kind=%s payload=%s", kind,
                          json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            return 204

        response = self.session.post(self.url(endpoint), headers=headers, json=payload,
                                     timeout=self.timeout)
        if response.status_code in (401, 403):
            self.session.cookies.clear()
            self.login()
            response = self.session.post(self.url(endpoint), headers=headers, json=payload,
                                         timeout=self.timeout)
        self.log.info("post | kind=%s http=%s", kind, response.status_code)
        if response.status_code != 204:
            raise RuntimeError(f"{kind}: expected HTTP 204, got {response.status_code}")
        return response.status_code

    def apply(self, state: dict | None = None, *, moment: datetime | None = None) -> list[str]:
        """Srovná nastavení TNG s rozvrhem. Vrací seznam provedených nebo přeskočených akcí."""
        moment = moment or datetime.now()
        state = state or {}
        settings = state.get("settings") or {}
        actions: list[str] = []

        boiler = self.config.section("tng.boiler") or self.config.get("tng.boiler", {})
        heating = self.config.get("tng.heating", {})
        thermostat = self.config.get("tng.thermostat", {})

        if boiler.get("enabled") or heating.get("enabled"):
            payload = copy.deepcopy(self.config.get("tng.basic_settings_template", {}))
            matches = True
            if boiler.get("enabled"):
                desired = scheduled_value(boiler, moment)
                payload["BoilerTemp"] = desired
                if settings.get("boiler_set_temperature") != desired:
                    matches = False
            if heating.get("enabled"):
                desired = scheduled_value(heating, moment)
                payload["HeatTemp_Const"] = desired
                if settings.get("heating_set_temperature") != desired:
                    matches = False

            signature = json.dumps(payload, sort_keys=True)
            pending = settings.get("last_settings_not_confirmed")
            self._gate_update("basic", pending)
            if matches:
                self.pending_sent.pop("basic", None)
            elif (self.pending_sent.get("basic") == signature
                  and self.change_gate["basic"]["awaiting_confirmation"]):
                actions.append("skip:basic:awaiting_confirmation")
            else:
                allowed, reason = self.can_post("basic", pending)
                if allowed:
                    self.post_json("basic_settings", payload, "BASIC_SETTINGS")
                    self.pending_sent["basic"] = signature
                    self._mark_posted("basic", {"boiler_temperature": payload.get("BoilerTemp"),
                                                "heating_temperature": payload.get("HeatTemp_Const")})
                    actions.append("post:basic")
                else:
                    actions.append(f"skip:basic:{reason}")

        if thermostat.get("enabled"):
            payload = copy.deepcopy(self.config.get("tng.thermostat_settings_template", {}))
            payload["DayTemperature"] = scheduled_value(thermostat, moment)
            signature = json.dumps(payload, sort_keys=True)
            pending = state.get("LastSettingsNotConfirmed")
            self._gate_update("thermostat", pending)
            if (self.pending_sent.get("thermostat") == signature
                    and self.change_gate["thermostat"]["awaiting_confirmation"]):
                actions.append("skip:thermostat:awaiting_confirmation")
            elif self.pending_sent.get("thermostat") != signature:
                allowed, reason = self.can_post("thermostat", pending)
                if allowed:
                    self.post_json("thermostat_settings", payload, "THERMOSTAT_SETTINGS")
                    self.pending_sent["thermostat"] = signature
                    self._mark_posted("thermostat", {"day_temperature": payload.get("DayTemperature")})
                    actions.append("post:thermostat")
                else:
                    actions.append(f"skip:thermostat:{reason}")
        return actions

    def request_boiler_temperature(self, temperature: float, state: dict) -> tuple[bool, str]:
        """Jednorázový požadavek controlleru na teplotu TUV – prochází stejným gate."""
        settings = (state or {}).get("settings") or {}
        if settings.get("boiler_set_temperature") == temperature:
            return False, "already_set"
        allowed, reason = self.can_post("basic", settings.get("last_settings_not_confirmed"))
        if not allowed:
            return False, reason
        payload = copy.deepcopy(self.config.get("tng.basic_settings_template", {}))
        payload["BoilerTemp"] = temperature
        self.post_json("basic_settings", payload, "BASIC_SETTINGS")
        self._mark_posted("basic", {"boiler_temperature": temperature})
        return True, "ok"
