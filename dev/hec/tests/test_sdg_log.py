"""Focused tests for the read-only SDG log reader and source contract."""

from __future__ import annotations

import threading
from datetime import timedelta

from hec.core import config as config_mod
from hec.core import schema
from hec.core.app import Application
from hec.core.model import Sample
from hec.core.timeutil import now_local
from hec.readers.registry import build_readers
from hec.readers.sdg_log import SdgLogReader, normalize_record
from hec.storage.jsonl import JsonlStorage


def make_config(tmp_path):
    data = schema.defaults()
    for section in ("tng", "ote", "weather", "shelly", "sharing", "finance"):
        data[section]["enabled"] = False
    data["goodwe"]["sdg"].update({
        "enabled": True,
        "log_root_path": str(tmp_path / "sdg"),
        "freshness_seconds": 180,
    })
    return config_mod.Config(data, path=tmp_path / "config.json", root=tmp_path)


def test_normalize_record_keeps_timestamp_and_skips_unknown_fields():
    stamp = now_local().replace(microsecond=0)
    values = normalize_record({
        "Date_Time": stamp.isoformat(), "PPV": "4210", "SOC": 91,
        "undocumented_value": 999,
    }, source_file="solar.dbf")

    assert values["timestamp"] == stamp
    assert values["pv_w"] == 4210.0
    assert values["battery_soc"] == 91
    assert "undocumented_value" not in values
    assert values["telemetry_source"] == "sdg"


def test_normalize_record_uses_goodwe_flow_sign_configuration(tmp_path):
    config = make_config(tmp_path)
    values = normalize_record({
        "timestamp": now_local().isoformat(), "grid": -850, "battery": 900,
    }, config=config)

    assert values["grid_import_w"] == 0
    assert values["grid_export_w"] == 850
    assert values["battery_charge_w"] == 900
    assert values["battery_discharge_w"] == 0


def test_reader_selects_newest_fresh_record_without_writing_share(tmp_path):
    root = tmp_path / "sdg" / "trend" / "solar"
    root.mkdir(parents=True)
    file_path = root / "solar.dbf"
    file_path.write_bytes(b"fixture")
    stamp = now_local().replace(microsecond=0)
    records = {
        file_path: [
            {"timestamp": (stamp - timedelta(seconds=10)).isoformat(), "pv": 100},
            {"timestamp": stamp.isoformat(), "pv": 200},
        ]
    }

    reader = SdgLogReader(make_config(tmp_path), record_loader=lambda path: records[path])
    values = reader.read()

    assert values["pv_w"] == 200.0
    assert values["telemetry_source"] == "sdg"
    assert file_path.read_bytes() == b"fixture"


def test_registry_uses_goodwe_sdg_enabled_flag(tmp_path):
    config = make_config(tmp_path)
    readers = build_readers(config, None)

    assert [reader.name for reader in readers] == ["sdg"]


def test_repeated_poll_and_restart_do_not_duplicate_history(tmp_path):
    root = tmp_path / "sdg" / "trend" / "solar"
    root.mkdir(parents=True)
    file_path = root / "solar.dbf"
    file_path.write_bytes(b"fixture")
    stamp = now_local().replace(microsecond=0)
    records = {file_path: [{"timestamp": stamp.isoformat(), "pv": 200}]}
    config = make_config(tmp_path)
    storage = JsonlStorage(config.data_dir, config.history_dir)

    reader = SdgLogReader(config, storage=storage, record_loader=lambda path: records[path])
    reader.poll()
    reader.poll()
    restarted = SdgLogReader(config, storage=storage, record_loader=lambda path: records[path])
    restarted.poll()

    assert len(storage.query("goodwe")) == 1
    state = (config.data_dir / "sdg_log_reader_state.json").read_text(encoding="utf-8")
    assert '"fingerprint"' in state and '"latest"' in state


def test_application_prefers_sdg_over_older_fte_sample(tmp_path):
    app = object.__new__(Application)
    app.snapshot = {}
    app._lock = threading.Lock()
    app.config = make_config(tmp_path)
    app.controller = None
    stamp = now_local().replace(microsecond=0)

    app.accept(Sample("sdg", {"pv_w": 100}, stamp))
    app.accept(Sample("goodwe", {"pv_w": 50}, stamp + timedelta(seconds=5)))

    assert app.snapshot["goodwe"]["pv_w"] == 100
    assert app.snapshot["goodwe"]["telemetry_source"] == "sdg"


def test_application_marks_fte_as_backup_when_sdg_is_enabled(tmp_path):
    app = object.__new__(Application)
    app.snapshot = {}
    app._lock = threading.Lock()
    app.config = make_config(tmp_path)
    app.controller = None
    app.accept(Sample("goodwe", {"pv_w": 50}, now_local()))

    assert app.snapshot["goodwe"]["pv_w"] == 50
    assert app.snapshot["goodwe"]["telemetry_source"] == "fte_backup"
