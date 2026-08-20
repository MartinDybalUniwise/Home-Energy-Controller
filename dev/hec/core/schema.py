"""Deklarativní schéma konfigurace a jeho validace.

Záměrně bez knihovny jsonschema – systém má běžet na Raspberry Pi s minimem
závislostí a schéma je zde zároveň zdrojem výchozích hodnot a nápovědy pro UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONFIG_VERSION = 1


@dataclass(frozen=True)
class Field:
    kind: str                       # str | int | float | bool | enum | list | dict
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple = ()
    item: Any = None                # schéma položky pro kind="list"
    restart: bool = False           # změna se projeví až po restartu
    secret: bool = False
    help_key: str = ""              # překladový klíč nápovědy v UI


F = Field

SCHEDULE_ITEM = {
    "from": F("str", "00:00"),
    "to": F("str", "06:00"),
    "temperature": F("float", 45.0, minimum=5, maximum=80),
}

SHELLY_DEVICE = {
    "name": F("str", ""),
    "host": F("str", ""),
    # appliance = spotřebič se spínačem, heatpump_meter = Pro 3EM na TČ, meter = obecné měření
    "role": F("enum", "appliance", choices=("appliance", "heatpump_meter", "meter")),
    # Určuje ikonu ve schématu toku energie. Bez zvolení se spotřebič zobrazí
    # jako "ostatní" – to je bezpečný výchozí stav, ne chyba.
    "appliance_type": F("enum", "other",
                        choices=("dishwasher", "washing_machine", "dryer", "fridge", "other")),
    "generation": F("enum", 2, choices=(1, 2)),
    "channel": F("int", 0, minimum=0, maximum=3),
    "enabled": F("bool", True),
}

def _day_profile(day_from: int = 6, day_to: int = 22) -> list[bool]:
    """24 hodin: True = denní teplota. Výchozí profil 6:00–22:00."""
    return [day_from <= hour < day_to for hour in range(24)]


BASIC_SETTINGS_TEMPLATE = {
    "HeatSet": {"Heat": False, "HeatingMode": 0, "EquitCurve": 2, "Boost": False,
                "EmergencyMode": False,
                "ExtendedHeatSet": {"Regulation": 3, "LeadingThermostat": 1}},
    "HeatTemp_Const": 42,
    "HeatTempEqCustom_P20": 24, "HeatTempEqCustom_P10": 29, "HeatTempEqCustom_P0": 32,
    "HeatTempEqCustom_M10": 35, "HeatTempEqCustom_M20": 37,
    "BoilerSet": {"Boiler": True, "Boost": False, "Sensor": True},
    "BoilerTemp": 48,
    "PoolSet": {"Pool": False, "Boost": False},
    "PoolTemp": 37,
    "AccSecure": False,
}

THERMOSTAT_SETTINGS_TEMPLATE = {
    "DayTemperature": 23, "NightTemperature": 21, "DayNightMode": False,
    "Monday": _day_profile(), "Tuesday": _day_profile(), "Wednesday": _day_profile(),
    "Thursday": _day_profile(), "Friday": _day_profile(),
    "Saturday": _day_profile(6, 23), "Sunday": _day_profile(6, 23),
}

SCHEMA: dict[str, Any] = {
    "system": {
        "config_version": F("int", CONFIG_VERSION, restart=True),
        "site_name": F("str", "Home Energy Controller"),
        "timezone": F("str", "Europe/Prague", restart=True),
        "latitude": F("float", 49.8209, minimum=-90, maximum=90),
        "longitude": F("float", 18.2625, minimum=-180, maximum=180),
    },
    "storage": {
        "data_path": F("str", "data", restart=True),
        "logs_path": F("str", "logs", restart=True),
        "history_path": F("str", "history", restart=True),
        "archive_path": F("str", "", help_key="help.storage.archive_path"),
        "archive_after_days": F("int", 30, minimum=1, maximum=3650),
        "compress_archive": F("bool", True),
        "archive_check_hours": F("int", 24, minimum=1, maximum=168),
    },
    "logging": {
        "level": F("enum", "INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR")),
        "max_bytes": F("int", 5_000_000, minimum=100_000, maximum=100_000_000, restart=True),
        "backups": F("int", 5, minimum=1, maximum=50, restart=True),
    },
    "polling": {
        "goodwe_seconds": F("int", 10, minimum=2, maximum=3600),
        "tng_seconds": F("int", 300, minimum=30, maximum=3600),
        "shelly_seconds": F("int", 10, minimum=2, maximum=3600),
        "weather_minutes": F("int", 15, minimum=5, maximum=180),
        "ote_minutes": F("int", 60, minimum=15, maximum=1440),
    },
    "goodwe": {
        "enabled": F("bool", False),
        "host": F("str", "${HEC_GOODWE_HOST}"),
        "family": F("enum", "ET", choices=("ET", "EH", "ES", "DT", "")),
        "timeout": F("int", 2, minimum=1, maximum=30),
        "retries": F("int", 3, minimum=0, maximum=10),
        # Znaménko toků se mezi instalacemi liší, proto je směr konfigurovatelný.
        "grid_positive_is_import": F("bool", True),
        "battery_positive_is_charge": F("bool", True),
    },
    "tng": {
        "enabled": F("bool", True),
        "connect_file": F("str", "connect.json", restart=True),
        "request_timeout_seconds": F("int", 30, minimum=5, maximum=120),
        # Ochrana tepelného čerpadla – nesnižovat bez znalosti důsledků.
        "minimum_change_interval_seconds": F("int", 900, minimum=900, maximum=7200),
        "telemetry_bootstrap_seconds": F("int", 3600, minimum=300, maximum=86400),
        "telemetry_overlap_seconds": F("int", 120, minimum=0, maximum=3600),
        "write_enabled": F("bool", False),
        "heating": {
            "enabled": F("bool", False),
            "default_temperature": F("float", 42, minimum=20, maximum=60),
            "schedule": F("list", [], item=SCHEDULE_ITEM),
        },
        "boiler": {
            "enabled": F("bool", True),
            "default_temperature": F("float", 45, minimum=30, maximum=65),
            "schedule": F("list", [], item=SCHEDULE_ITEM),
        },
        "thermostat": {
            "enabled": F("bool", False),
            "default_temperature": F("float", 23.0, minimum=10, maximum=30),
            "schedule": F("list", [], item=SCHEDULE_ITEM),
        },
        # Šablony payloadů převzaté z ověřené provozní konfigurace. Reader do nich
        # dosazuje jen teploty; ostatní pole musí zůstat, jinak TNG požadavek odmítne.
        "basic_settings_template": F("dict", BASIC_SETTINGS_TEMPLATE),
        "thermostat_settings_template": F("dict", THERMOSTAT_SETTINGS_TEMPLATE),
    },
    "ote": {
        "enabled": F("bool", True),
        "eur_czk_rate": F("float", 25.0, minimum=1, maximum=100),
        "fetch_rate_from_cnb": F("bool", True),
        "distribution_czk_kwh": F("float", 0.0, minimum=0, maximum=20),
        "fees_czk_kwh": F("float", 0.0, minimum=0, maximum=20),
        "vat_rate": F("float", 0.21, minimum=0, maximum=1),
        "export_price_czk_kwh": F("float", 0.0, minimum=0, maximum=20),
    },
    "weather": {
        "enabled": F("bool", True),
        "forecast_days": F("int", 3, minimum=1, maximum=7),
        "location_name": F("str", "Ostrava, CZ"),
    },
    "shelly": {
        "enabled": F("bool", False),
        "request_timeout_seconds": F("int", 5, minimum=1, maximum=60),
        "devices": F("list", [], item=SHELLY_DEVICE),
    },
    "controller": {
        "enabled": F("bool", False),
        # Nad tímto stářím kritických dat se optimalizace zastaví (safe mode).
        "max_data_age_seconds": F("int", 300, minimum=60, maximum=3600),
        "decision_interval_seconds": F("int", 300, minimum=60, maximum=3600),
        "comfort": {
            "room_min_c": F("float", 20.0, minimum=10, maximum=30),
            "room_max_c": F("float", 24.0, minimum=10, maximum=32),
            "dhw_min_c": F("float", 45.0, minimum=35, maximum=60),
            "dhw_max_c": F("float", 52.0, minimum=35, maximum=65),
            "max_preheat_k": F("float", 1.5, minimum=0, maximum=5),
            "quiet_hours_from": F("str", "22:00"),
            "quiet_hours_to": F("str", "06:00"),
        },
        "optimization": {
            "aggressiveness": F("enum", "medium", choices=("off", "low", "medium", "high")),
            "pv_surplus_kw": F("float", 2.0, minimum=0, maximum=20),
            "battery_soc_min_pct": F("float", 60.0, minimum=0, maximum=100),
            "cheap_price_percentile": F("float", 0.25, minimum=0, maximum=1),
            "expensive_price_percentile": F("float", 0.75, minimum=0, maximum=1),
            "priorities": F("list", [
                "house_load", "battery_charge", "dhw", "thermal_storage",
                "flexible_loads", "sharing", "grid_export",
            ]),
        },
    },
    "prediction": {
        "enabled": F("bool", True),
        "pv_peak_kwp": F("float", 10.0, minimum=0, maximum=100),
        "learning_days": F("int", 30, minimum=3, maximum=365),
        "battery_capacity_kwh": F("float", 10.0, minimum=0, maximum=200),
    },
    "web": {
        "host": F("str", "0.0.0.0", restart=True),
        "port": F("int", 8080, minimum=1, maximum=65535, restart=True),
        "password": F("str", "${HEC_WEB_PASSWORD}", secret=True, restart=True),
    },
    "ui": {
        "language": F("enum", "cs", choices=("cs", "en")),
        "languages": F("list", ["cs", "en"]),
        "animations": F("enum", "full", choices=("full", "reduced", "off")),
        "theme": F("enum", "auto", choices=("auto", "dark", "light")),
        "currency": F("enum", "CZK", choices=("CZK", "EUR")),
        "brand_accent": F("str", "#4fb3ff"),
    },
}


def defaults(schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Kompletní konfigurace složená z výchozích hodnot schématu."""
    out: dict[str, Any] = {}
    for key, node in (schema or SCHEMA).items():
        if isinstance(node, Field):
            out[key] = list(node.default) if isinstance(node.default, list) else node.default
        else:
            out[key] = defaults(node)
    return out


def _coerce(value: Any, spec: Field, path: str, errors: list[str]) -> Any:
    kind = spec.kind
    try:
        if kind == "bool":
            if isinstance(value, str):
                value = value.strip().lower() in ("1", "true", "yes", "on", "ano")
            else:
                value = bool(value)
        elif kind == "int":
            value = int(float(value))
        elif kind == "float":
            value = float(value)
        elif kind == "str":
            value = "" if value is None else str(value)
        elif kind == "enum":
            if isinstance(spec.default, int) and not isinstance(value, bool):
                value = int(value)
            if value not in spec.choices:
                errors.append(f"{path}: '{value}' není z {list(spec.choices)}")
                return spec.default
        elif kind == "dict":
            if not isinstance(value, dict):
                errors.append(f"{path}: očekáván objekt")
                return dict(spec.default or {})
        elif kind == "list":
            if not isinstance(value, list):
                errors.append(f"{path}: očekáván seznam")
                return list(spec.default or [])
            if spec.item:
                value = [validate_node(v if isinstance(v, dict) else {}, spec.item,
                                       f"{path}[{i}]", errors)
                         for i, v in enumerate(value)]
    except (TypeError, ValueError):
        errors.append(f"{path}: hodnotu '{value}' nelze převést na {kind}")
        return spec.default

    if spec.minimum is not None and isinstance(value, (int, float)) and value < spec.minimum:
        errors.append(f"{path}: {value} je pod minimem {spec.minimum}")
        return spec.default
    if spec.maximum is not None and isinstance(value, (int, float)) and value > spec.maximum:
        errors.append(f"{path}: {value} je nad maximem {spec.maximum}")
        return spec.default
    return value


def validate_node(data: dict, schema: dict, prefix: str, errors: list[str]) -> dict:
    out: dict[str, Any] = {}
    for key, spec in schema.items():
        path = f"{prefix}.{key}" if prefix else key
        present = isinstance(data, dict) and key in data
        if isinstance(spec, Field):
            if not present or data[key] is None:
                out[key] = list(spec.default) if isinstance(spec.default, list) else spec.default
            else:
                out[key] = _coerce(data[key], spec, path, errors)
        else:
            out[key] = validate_node(data.get(key, {}) if isinstance(data, dict) else {},
                                     spec, path, errors)
    # Neznámé klíče se zachovají – novější konfigurace se starším kódem nesmí ztratit.
    if isinstance(data, dict):
        for key, value in data.items():
            if key not in schema:
                out[key] = value
    return out


def validate(data: dict) -> tuple[dict, list[str]]:
    """Vrátí (normalizovaná konfigurace, seznam chyb). Chybné hodnoty padnou na default."""
    errors: list[str] = []
    return validate_node(data or {}, SCHEMA, "", errors), errors


def describe(schema: dict | None = None, prefix: str = "") -> list[dict]:
    """Popis polí pro nastavení v UI: cesta, typ, rozsah, nutnost restartu."""
    out: list[dict] = []
    for key, node in (schema or SCHEMA).items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(node, Field):
            out.append({
                "path": path, "kind": node.kind, "default": node.default,
                "min": node.minimum, "max": node.maximum,
                "choices": list(node.choices), "restart": node.restart,
                "secret": node.secret, "help_key": node.help_key or f"help.{path}",
            })
        else:
            out.extend(describe(node, path))
    return out
