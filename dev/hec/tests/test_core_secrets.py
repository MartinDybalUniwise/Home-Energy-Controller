"""Testy práce s tajemstvími – nesmí uniknout do konfigurace, logu ani exportu."""

from __future__ import annotations

import logging

from hec.core import logging_setup, secrets


def test_load_env_does_not_override_existing_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HEC_TNG_PASSWORD", "z prostředí")
    env_file = tmp_path / ".env"
    env_file.write_text("# komentář\nHEC_TNG_PASSWORD=ze souboru\nHEC_NEW=hodnota\n", encoding="utf-8")

    secrets.load_env(env_file)

    import os
    assert os.environ["HEC_TNG_PASSWORD"] == "z prostředí"
    assert os.environ["HEC_NEW"] == "hodnota"


def test_expand_supports_default_and_missing_values():
    env = {"KNOWN": "ano"}
    assert secrets.expand("${KNOWN}", env) == "ano"
    assert secrets.expand("${UNKNOWN:-záloha}", env) == "záloha"
    assert secrets.expand("${UNKNOWN}", env) == ""
    assert secrets.expand("bez placeholderu", env) == "bez placeholderu"


def test_expand_tree_walks_nested_structures():
    env = {"H": "10.0.0.1"}
    tree = {"a": {"host": "${H}"}, "b": ["${H}", 5, True]}
    assert secrets.expand_tree(tree, env) == {"a": {"host": "10.0.0.1"}, "b": ["10.0.0.1", 5, True]}


def test_redact_masks_known_secret_fields():
    data = {"tng": {"username": "tester", "password": "velmi-tajne", "thermostat_key": "ABCDEF123"}}
    redacted = secrets.redact(data)
    assert redacted["tng"]["username"] == "tester"
    assert "velmi-tajne" not in str(redacted)
    assert "ABCDEF123" not in str(redacted)


def test_logger_strips_secret_values(tmp_path):
    logging_setup.register_secrets({"velmi-tajne-heslo"})
    logging_setup.configure(tmp_path, console=False)
    logger = logging_setup.get_logger("test")

    logger.info("login with velmi-tajne-heslo")
    logging.shutdown()

    written = (tmp_path / "hec.log").read_text(encoding="utf-8")
    assert "velmi-tajne-heslo" not in written
    assert "***" in written


def test_event_format_is_key_value(tmp_path):
    logging_setup.configure(tmp_path, console=False)
    logger = logging_setup.get_logger("goodwe")
    logging_setup.event(logger, "poll_success", duration_ms=148, pv_w=4210)
    logging.shutdown()

    line = (tmp_path / "hec.log").read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "hec.goodwe | poll_success | duration_ms=148 pv_w=4210" in line
