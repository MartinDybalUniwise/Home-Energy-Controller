from __future__ import annotations

import json
import struct
import threading
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from hec.controller.controller import Controller
from hec.core import config as config_mod
from hec.core import schema
from hec.core.goodwe_hardware_authorization import authorize
from hec.core.model import Decision
from hec.readers.fte_reader import FTEReader
from hec.readers.goodwe_manager import GoodWeManager
from hec.readers.registry import build_readers
from hec.readers.sdg_history_reader import SDGHistoryReader
from hec.storage.jsonl import JsonlStorage
from hec.web import api
from hec.writers.fte_writer import FTEWriter


def make_config(tmp_path, **sections):
    data = schema.defaults()
    data["storage"]["data_path"] = str(tmp_path / "data")
    data["storage"]["history_path"] = str(tmp_path / "history")
    data["storage"]["logs_path"] = str(tmp_path / "logs")
    for section, values in sections.items():
        data[section].update(values)
    return config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)


class FakeInverter:
    def __init__(self, *, mismatch=False, fail_writes=0, slow=False):
        self.model_name = "FAKE-ET"
        self.firmware = "1.2.3"
        self.grid_export = False
        self.export_limit = 5000
        self.dod = 90
        self.mode = "GENERAL"
        self.mismatch = mismatch
        self.fail_writes = fail_writes
        self.slow = slow
        self.write_calls = 0
        self.active = 0
        self.max_active = 0
        self.mode_calls = []
        self._lock = threading.Lock()

    async def read_runtime_data(self):
        return {"ppv": 1200, "battery_soc": 75, "active_power": -150,
                "work_mode_label": self.mode, "temperature": 41}

    async def read_setting(self, name):
        return {"grid_export": self.grid_export}.get(name)

    async def write_setting(self, name, value):
        await self._enter()
        try:
            if self.slow:
                await __import__("asyncio").sleep(0.01)
            self.write_calls += 1
            if self.fail_writes:
                self.fail_writes -= 1
                raise TimeoutError("simulated timeout")
            if name == "grid_export":
                self.grid_export = bool(value)
        finally:
            self._leave()

    async def set_grid_export_limit(self, value):
        await self.write_setting("grid_export_limit", value)
        self.export_limit = int(value)

    async def get_grid_export_limit(self):
        return self.export_limit if not self.mismatch else self.export_limit + 1

    async def set_ongrid_battery_dod(self, value):
        await self.write_setting("dod", value)
        self.dod = int(value)

    async def get_ongrid_battery_dod(self):
        return self.dod

    async def set_operation_mode(self, mode, eco_mode_power=100, eco_mode_soc=100):
        await self.write_setting("mode", mode)
        self.mode_calls.append((getattr(mode, "name", str(mode)), eco_mode_power, eco_mode_soc))
        self.mode = getattr(mode, "name", str(mode))

    async def get_operation_mode(self):
        class Mode:
            def __init__(self, name):
                self.name = name
        return Mode(self.mode)

    async def _enter(self):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

    def _leave(self):
        with self._lock:
            self.active -= 1


class FakeClient:
    hec_test_fake = True

    def __init__(self, inverter):
        self.inverter = inverter

    def __call__(self, **kwargs):
        return self.inverter


def write_dbf(path: Path, rows: list[tuple[str, int, str]]):
    fields = [("timestamp", "C", 25), ("power", "N", 8), ("status", "C", 8)]
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(field[2] for field in fields)
    header = bytearray(32)
    header[0] = 0x03
    struct.pack_into("<I", header, 4, len(rows))
    struct.pack_into("<H", header, 8, header_len)
    struct.pack_into("<H", header, 10, record_len)
    body = bytearray(header)
    for _index, (name, field_type, length) in enumerate(fields):
        descriptor = bytearray(32)
        descriptor[:len(name)] = name.encode("ascii")
        descriptor[11] = ord(field_type)
        descriptor[16] = length
        body.extend(descriptor)
    body.append(0x0D)
    for timestamp, power, status in rows:
        record = bytearray(record_len)
        cursor = 1
        for value, length in ((timestamp, 25), (str(power), 8), (status, 8)):
            encoded = value.encode("ascii")[:length]
            record[cursor:cursor + length] = encoded.rjust(length)
            cursor += length
        body.extend(record)
    body.append(0x1A)
    path.write_bytes(body)


def enabled_config(tmp_path, **goodwe):
    config = make_config(tmp_path, controller={"enabled": True},
                         goodwe={"enabled": True, "writer_enabled": True, **goodwe})
    authorize(config, device_host="192.168.2.116", evidence_id="test-s07-artifact",
              approved_by="automated-test", verification=lambda: True)
    return config


def test_registry_uses_new_reader_and_sdg_reader(tmp_path):
    config = enabled_config(tmp_path, sdg={"enabled": True, "log_root_path": str(tmp_path)})
    readers = build_readers(config, JsonlStorage(config.data_dir, config.history_dir))
    assert type(next(reader for reader in readers if reader.name == "goodwe")) is FTEReader
    assert any(reader.name == "sdg_history" for reader in readers)


def test_reader_normalizes_metadata_and_offline_payload(tmp_path):
    config = enabled_config(tmp_path)
    inverter = FakeInverter()
    reader = FTEReader(config, client=FakeClient(inverter), test_fake=True)
    values = reader.read()
    assert values["pv_w"] == 1200
    assert values["model"] == "FAKE-ET"
    assert values["firmware"] == "1.2.3"
    assert values["online"] is True
    assert values["e_day_kwh"] is None

    class BrokenClient:
        hec_test_fake = True

        def __call__(self, **kwargs):
            raise TimeoutError("offline")

    offline = FTEReader(config, client=BrokenClient(), test_fake=True).read()
    assert offline["online"] is False
    assert offline["pv_w"] is None
    assert "error" in offline


def test_manager_all_supported_commands_use_real_api_and_readback(tmp_path):
    config = enabled_config(tmp_path)
    inverter = FakeInverter()
    storage = JsonlStorage(config.data_dir, config.history_dir)
    manager = GoodWeManager(config, storage=storage, client=FakeClient(inverter), test_fake=True)
    writer = FTEWriter(config, manager=manager)
    results = [
        writer.set_export_limit_enabled(True),
        writer.set_export_limit_w(4000),
        writer.set_on_grid_soc_limit_pct(20),
        writer.start_battery_charge(50, 20, 80, "00:00", "01:00"),
        writer.start_battery_discharge(30, 80, 20, "01:00", "02:00"),
        writer.stop_battery_control(),
    ]
    assert all(result["success"] for result in results)
    assert len(writer.audit_log) == 6
    assert inverter.write_calls >= 6
    assert {call[0] for call in inverter.mode_calls} == {"ECO", "GENERAL"}
    assert storage.last("goodwe_audit", 20)


def test_writer_diagnostics_reads_authorization_artifact_not_config(tmp_path):
    config = enabled_config(tmp_path)
    manager = GoodWeManager(config, client=FakeClient(FakeInverter()), test_fake=True)
    writer = FTEWriter(config, manager=manager)
    diagnostics = writer.status_snapshot()
    assert diagnostics["hardware_authorization"]["status"] == "APPROVED"
    assert "hardware_verified" not in diagnostics


def test_audit_serializes_nested_datetime_payload_as_valid_json(tmp_path):
    config = enabled_config(tmp_path)
    storage = JsonlStorage(config.data_dir, config.history_dir)
    manager = GoodWeManager(config, storage=storage, client=FakeClient(FakeInverter()), test_fake=True)
    before = {"timestamp": datetime(2026, 9, 13, 23, 30, tzinfo=UTC), "value": 10000}
    write_result = {"completed": date(2026, 9, 13), "values": (10000,)}
    readback = {"observed_at": datetime(2026, 9, 13, 23, 30, 1, tzinfo=UTC), "value": 10000}
    manager._record_attempt(
        command_id="s07-audit-regression",
        command="set_export_limit_w",
        requested={"value": 10000},
        gates={"writer_enabled": True},
        before=before,
        attempt=1,
        write_result=write_result,
        readback=readback,
        final_status="success",
    )
    audit_path = storage.history_dir / "goodwe_audit" / "2026-09-13.jsonl"
    raw = audit_path.read_text(encoding="utf-8").strip()
    parsed = json.loads(raw)
    assert parsed["command_id"] == "s07-audit-regression"
    assert parsed["before"]["timestamp"] == "2026-09-13T23:30:00+00:00"
    assert parsed["write_result"]["completed"] == "2026-09-13"
    assert parsed["readback"]["observed_at"] == "2026-09-13T23:30:01+00:00"
    assert parsed["final_status"] == "success"


def test_manager_serializes_writes_and_retries(tmp_path):
    config = enabled_config(tmp_path, retries=2)
    inverter = FakeInverter(fail_writes=1, slow=True)
    manager = GoodWeManager(config, client=FakeClient(inverter), test_fake=True)
    errors: list[Exception] = []

    def write():
        try:
            manager.execute("set_export_limit_w", value=4000)
        except Exception as exc:  # pragma: no cover - assertion below catches failures
            errors.append(exc)

    threads = [threading.Thread(target=write) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert inverter.max_active == 1
    assert manager.status_snapshot()["retry_count"] >= 1


def test_manager_rejects_unsupported_and_readback_mismatch(tmp_path):
    config = enabled_config(tmp_path, retries=0)
    manager = GoodWeManager(config, client=FakeClient(FakeInverter(mismatch=True)), test_fake=True)
    with pytest.raises(ValueError, match="Unsupported GoodWe command"):
        manager.execute("set_unknown", value=1)
    with pytest.raises(RuntimeError, match="read-back mismatch"):
        manager.execute("set_export_limit_w", value=4000)


@pytest.mark.parametrize("gate", ["controller.enabled", "goodwe.enabled",
                                   "goodwe.writer_enabled", "hardware_authorization",
                                   "goodwe.verify_after_write"])
def test_manager_enforces_each_write_gate(tmp_path, gate):
    config = enabled_config(tmp_path)
    if gate == "hardware_authorization":
        (config.data_dir / "goodwe_hardware_authorization.json").unlink()
    else:
        section, key = gate.split(".")
        config.data[section][key] = False
    manager = GoodWeManager(config, client=FakeClient(FakeInverter()), test_fake=True)
    with pytest.raises(PermissionError, match="safety gate"):
        manager.execute("set_export_limit_w", value=4000)


def test_physical_io_is_locked_out_without_explicit_runtime_mode(tmp_path, monkeypatch):
    config = enabled_config(tmp_path)
    called = False

    def forbidden_connect(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("physical GoodWe connect must not be called")

    monkeypatch.setattr("goodwe.connect", forbidden_connect)
    manager = GoodWeManager(config)
    with pytest.raises(PermissionError, match="physical I/O"):
        manager.read_runtime()
    with pytest.raises(PermissionError, match="physical_io"):
        manager.execute("set_export_limit_w", value=4000)
    assert called is False


def test_test_runtime_allows_only_explicitly_marked_fake_client(tmp_path):
    config = enabled_config(tmp_path)
    fake = FakeClient(FakeInverter())
    assert GoodWeManager(config, client=fake, test_fake=True).read_runtime()["ppv"] == 1200

    class PhysicalLikeClient:
        def __call__(self, **kwargs):
            raise AssertionError("physical-like client must be rejected before use")

    with pytest.raises(PermissionError, match="test mode"):
        GoodWeManager(config, client=PhysicalLikeClient(), test_fake=False).read_runtime()

    with pytest.raises(PermissionError, match="test mode"):
        GoodWeManager(config, client=fake, test_fake=False).read_runtime()


def test_config_api_cannot_create_or_change_hardware_authorization(tmp_path):
    config = make_config(tmp_path)
    app = SimpleNamespace(config=config)
    status, payload = api.config_put(app, {"config": {"goodwe": {"hardware_verified": True}}})
    assert status == 400
    assert payload["error"] == "hardware_authorization_read_only"
    assert not (config.data_dir / "goodwe_hardware_authorization.json").exists()


def test_offline_sample_is_not_success_and_controller_enters_safe_mode(tmp_path):
    config = make_config(tmp_path, controller={"enabled": True}, goodwe={"enabled": True})

    class BrokenClient:
        hec_test_fake = True

        def __call__(self, **kwargs):
            raise TimeoutError("offline")

    reader = FTEReader(config, client=BrokenClient(), test_fake=True)
    sample = reader.poll()
    assert sample.ok is False
    assert sample.values["online"] is False
    assert reader.status.last_success is None
    app = SimpleNamespace(config=config, storage=JsonlStorage(config.data_dir, config.history_dir),
                          snapshot={"goodwe": sample.values}, readers=[reader])
    controller = Controller(app)
    result = controller.run_once()
    assert result["safe_mode"] is True


def test_controller_dispatches_goodwe_action_to_writer(tmp_path):
    config = make_config(tmp_path, controller={"enabled": True})
    calls = []
    writer = SimpleNamespace(set_export_limit_w=lambda **kwargs: calls.append(kwargs))
    app = SimpleNamespace(config=config, storage=JsonlStorage(config.data_dir, config.history_dir),
                          snapshot={}, readers=[], goodwe_writer=writer)
    controller = Controller(app)
    decision = Decision(rule="test", action="set_export_limit_w", value=3000)
    applied = controller.apply(decision)
    assert applied.applied is True
    assert calls == [{"value": 3000}]


def test_date_and_time_fields_are_combined_and_same_size_change_is_detected(tmp_path):
    assert SDGHistoryReader._timestamp({"date": "2026-09-13", "time": "10:05:00"}) == "2026-09-13T10:05:00+00:00"
    root = tmp_path / "sdg" / "Data" / "trend" / "min"
    root.mkdir(parents=True)
    source = root / "sample.dbf"
    write_dbf(source, [("2026-09-13 10:00:00", 100, "OK")])
    config = enabled_config(tmp_path, sdg={"log_root_path": str(tmp_path / "sdg")})
    storage = JsonlStorage(config.data_dir, config.history_dir)
    reader = SDGHistoryReader(config, storage)
    assert reader.import_history()["imported"] == 1
    write_dbf(source, [("2026-09-13 10:00:00", 999, "OK")])
    result = reader.import_history()
    assert result["imported"] == 1


def test_sdg_reader_discovers_sdgeco_installation_layout(tmp_path):
    root = tmp_path / "Promotic" / "Apps" / "SDGeco" / "Data" / "Event2"
    root.mkdir(parents=True)
    source = root / "Events22026-09-14.dbf"
    write_dbf(source, [("2026-09-14 10:00:00", 100, "OK")])
    config = enabled_config(tmp_path, sdg={"log_root_path": str(tmp_path / "Promotic")})
    reader = SDGHistoryReader(config)
    assert reader.paths() == [source]


def test_sdg_import_is_incremental_deduplicated_and_tolerates_corruption(tmp_path):
    root = tmp_path / "sdg" / "Data" / "trend" / "min"
    root.mkdir(parents=True)
    source = root / "sample.dbf"
    write_dbf(source, [("2026-09-13 10:00:00", 100, "OK"),
                       ("2026-09-13 10:05:00", 110, "OK")])
    config = enabled_config(tmp_path, sdg={"log_root_path": str(tmp_path / "sdg")})
    storage = JsonlStorage(config.data_dir, config.history_dir)
    reader = SDGHistoryReader(config, storage)
    first = reader.import_history()
    second = reader.import_history()
    assert first["imported"] == 2
    assert second["imported"] == 0
    assert second["duplicates"] == 0
    assert len(storage.last("sdg_history", 10)) == 2

    source.write_bytes(b"broken")
    result = reader.import_history()
    assert result["corrupt_files"] == 1
