"""Testy konfigurace: validace, výchozí hodnoty, zálohy, cesty."""

from __future__ import annotations

import json

from hec.core import config as config_mod
from hec.core import schema


def test_defaults_cover_every_section():
    data = schema.defaults()
    assert data["polling"]["goodwe_seconds"] == 10
    assert data["tng"]["minimum_change_interval_seconds"] == 900
    assert data["ui"]["languages"] == ["cs", "en"]


def test_sharing_forecast_economics_are_safe_by_default():
    """dev/step09 fáze A: sdílení energie se nesmí zapnout samo."""
    data = schema.defaults()
    assert data["sharing"]["enabled"] is False
    assert data["sharing"]["consumers"] == []
    assert data["forecast"]["enabled"] is True
    assert data["economics"]["sharing_value_czk_kwh"] == 0.0


def test_sharing_consumer_allocation_is_validated():
    data, errors = schema.validate({"sharing": {"consumers": [
        {"ean": "859...", "name": "Velké Bílovice", "allocation_percent": 35},
        {"ean": "111...", "name": "Bad", "allocation_percent": 150},
    ]}})
    consumers = data["sharing"]["consumers"]
    assert consumers[0]["allocation_percent"] == 35
    assert consumers[1]["allocation_percent"] == 0    # nad maximem -> default
    assert errors


def test_invalid_value_falls_back_to_default_and_reports_error():
    data, errors = schema.validate({"polling": {"tng_seconds": 5}})
    assert data["polling"]["tng_seconds"] == 300
    assert errors and "polling.tng_seconds" in errors[0]


def test_change_gate_interval_cannot_be_lowered_below_the_safe_limit():
    """Ochrana TČ: kratší interval než 900 s schéma nepřijme."""
    data, errors = schema.validate({"tng": {"minimum_change_interval_seconds": 60}})
    assert data["tng"]["minimum_change_interval_seconds"] == 900
    assert errors


def test_unknown_keys_are_preserved():
    data, _ = schema.validate({"future_section": {"whatever": 1}})
    assert data["future_section"] == {"whatever": 1}


def test_list_items_are_validated(monkeypatch):
    data, errors = schema.validate({"shelly": {"devices": [
        {"name": "myčka", "host": "10.0.0.5", "role": "appliance"},
        {"name": "bad", "host": "10.0.0.6", "role": "nonsense"},
    ]}})
    devices = data["shelly"]["devices"]
    assert devices[0]["generation"] == 2          # doplněno z výchozích hodnot
    assert devices[1]["role"] == "appliance"      # neplatná role padá na default
    assert errors


def test_load_expands_environment_placeholders(tmp_path, monkeypatch):
    monkeypatch.setenv("HEC_GOODWE_HOST", "192.168.1.50")
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"goodwe": {"host": "${HEC_GOODWE_HOST}"}}), encoding="utf-8")

    config = config_mod.load(path, root=tmp_path)
    assert config.get("goodwe.host") == "192.168.1.50"


def test_save_creates_backup_and_rejects_invalid_data(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(schema.defaults()), encoding="utf-8")
    config = config_mod.load(path, root=tmp_path)

    errors = config_mod.save(config, {**config.data, "web": {"port": 70000}})
    assert errors and json.loads(path.read_text(encoding="utf-8"))["web"]["port"] == 8080

    assert config_mod.save(config, {**config.data, "web": {**config.section("web"), "port": 9090}}) == []
    assert json.loads(path.read_text(encoding="utf-8"))["web"]["port"] == 9090
    assert list(tmp_path.glob("config.backup-*.json"))


def test_paths_are_platform_neutral(tmp_path):
    config = config_mod.Config(schema.defaults(), path=tmp_path / "c.json", root=tmp_path)
    assert config.data_dir == tmp_path / "data"

    config.data["storage"]["history_path"] = "/mnt/nas/history"
    assert str(config.history_dir) == "/mnt/nas/history"

    config.data["storage"]["archive_path"] = ""
    assert config.archive_dir is None


def test_public_dict_hides_secrets():
    config = config_mod.Config(schema.defaults())
    config.data["web"]["password"] = "super-secret-value"
    assert "super-secret-value" not in json.dumps(config.to_public_dict())
