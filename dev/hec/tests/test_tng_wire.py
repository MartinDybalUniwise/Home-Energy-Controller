"""Synthetic traffic only: no captured device identifiers or production data."""

import json
import socket
import struct
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from hec.core import config as config_mod
from hec.core import schema
from hec.core.timeutil import now_local, to_iso
from hec.readers.tng import TngReader
from hec.readers.tng_protocol import BIT_MAP, Reader, decode, tzsp_frame
from hec.readers.tng_wire import TngWireReader
from hec.storage.jsonl import JsonlStorage
from hec.web.api import tng_wire_events


def payload(mask=165, minute=0):
    plain = bytearray(130)
    for index, value in {
        80: 151,
        85: 199,
        87: 160,
        88: 182,
        89: 215,
        94: 189,
        95: 197,
        84: 9,
        86: 32,
        93: 1,
        107: minute,
    }.items():
        plain[index] = value
    return bytes(
        sum(((value >> dst) & 1) << src for dst, src in enumerate(BIT_MAP)) ^ mask for value in plain
    )


def packet(body, seq=100, reverse=False):
    a, b = ("203.0.113.5", "192.0.2.10") if reverse else ("192.0.2.10", "203.0.113.5")
    ports = (80, 40000) if reverse else (40000, 80)
    ip = struct.pack(
        "!BBHHHBBH4s4s", 69, 0, 40 + len(body), 0, 0, 64, 6, 0, socket.inet_aton(a), socket.inet_aton(b)
    )
    tcp = struct.pack("!HHIIBBHHH", *ports, seq, 0, 80, 24, 1024, 0, 0)
    return b"\0" * 12 + b"\x08\x00" + ip + tcp + body


def http(body, reverse=False):
    header = (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json"
        if reverse
        else b"POST /api/Communication/TEST-ID HTTP/1.0\r\nContent-Type: application/binary"
    )
    return header + b"\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body


def config(tmp_path):
    data = schema.defaults()
    data["tng_wire"].update(enabled=True, tc_ip="192.0.2.10")
    cfg = config_mod.Config(data, path=tmp_path / "config.json", root=tmp_path)
    cfg.ensure_dirs()
    return cfg


def test_fragmented_out_of_order_retransmitted_pair(tmp_path):
    reader = Reader("192.0.2.10")
    request = http(payload())
    # A trailing segment cannot become a complete request by itself.
    assert reader.feed_messages(now_local().timestamp() + 1001, 1, packet(request[70:], 170)) == []
    messages = reader.feed_messages(now_local().timestamp() + 1002, 1, packet(request[:70], 100))
    assert len(messages) == 1
    assert reader.feed_messages(now_local().timestamp() + 1003, 1, packet(request, 100)) == []
    reply = http(json.dumps(payload(54, 30).hex()).encode(), True)
    assert reader.feed_messages(now_local().timestamp() + 1004, 1, packet(reply[:100], 800, True)) == []
    messages += reader.feed_messages(now_local().timestamp() + 1005, 1, packet(reply[100:], 900, True))
    assert len(messages) == 2
    cfg = config(tmp_path)
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    wire = TngWireReader(cfg, storage)
    samples = [wire.ingest(message) for message in messages]
    assert samples[0].values["buffer_temperature"] == 40.7
    assert samples[1] is None
    assert wire.counts["pairs"] == 1
    assert wire.last_pair["temperatures_equal"]
    records = storage.query("tng_wire_events")
    assert [r["event"] for r in records] == ["request", "response", "exchange"]
    assert records[1]["request_id"] == records[0]["message_id"]
    assert json.loads(records[1]["json_text"]) == payload(54, 30).hex()
    assert "TEST-ID" not in json.dumps(records)
    assert records[-1]["changed_decoded_offsets"] == [107]


def test_refrigerant_branch_stays_unknown_and_samples_are_not_control_eligible(tmp_path):
    cfg = config(tmp_path)
    reader = Reader("192.0.2.10")
    body = bytearray(payload())
    # Decoded 20 would mean 27.6 or 53.2 C; do not guess the branch.
    body[95] = sum(((20 >> dst) & 1) << src for dst, src in enumerate(BIT_MAP)) ^ body[4]
    message = reader.feed_messages(now_local().timestamp() + 1000, 1, packet(http(bytes(body))))[0]
    sample = TngWireReader(cfg).ingest(message)
    assert sample.values["refrigerant_output_temperature"] is None
    assert sample.values["control_eligible"] is False
    assert decode(bytes(body))["temperatures"]["refrigerant_c"] == 27.6


def test_invalid_tzsp_and_lengths_and_sparse_tcp():
    with pytest.raises(ValueError):
        tzsp_frame(b"bad")
    with pytest.raises(ValueError):
        decode(b"\0" * 129)
    reader = Reader("192.0.2.10")
    assert reader.feed_messages(now_local().timestamp() + 1, 1, packet(b"POST ", 10)) == []
    assert reader.feed_messages(now_local().timestamp() + 2, 1, packet(b"xxx", 99999999)) == []
    assert not reader.flows


def test_unpaired_response_and_bad_json_are_kept(tmp_path):
    cfg = config(tmp_path)
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    wire = TngWireReader(cfg, storage)
    reader = Reader("192.0.2.10")
    message = reader.feed_messages(
        now_local().timestamp() + 1000, 1, packet(http(b"not json", True), reverse=True)
    )[0]
    assert wire.ingest(message) is None
    record = storage.query("tng_wire_events")[0]
    assert record["request_id"] is None
    assert record["json_text"] == "not json"
    assert record["decode_error"]


def test_command_audit_and_existing_guard_are_independent(tmp_path):
    cfg = config(tmp_path)
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    reader = TngReader(cfg, storage, connect={})
    reader._post_json_http = Mock(return_value=204)
    reader.post_json("basic_settings", {"BoilerTemp": 50, "HeatPumpHash": "NEVER-STORE"}, "BASIC_SETTINGS")
    records = storage.query("tng_commands")
    assert [r["phase"] for r in records] == ["requested", "dry_run"]
    assert "NEVER-STORE" not in json.dumps(records)
    assert reader.change_gate["basic"]["last_post_at"] is None
    assert reader.command_status()["basic"]["awaiting_confirmation"] is False


def test_log_limits_and_retention_only_touch_wire_events(tmp_path):
    cfg = config(tmp_path)
    cfg.data["tng_wire"]["max_daily_bytes"] = 1
    storage = JsonlStorage(cfg.data_dir, cfg.history_dir)
    wire = TngWireReader(cfg, storage)
    old = to_iso(now_local() - timedelta(days=40))
    storage.append("tng_wire_events", {"timestamp": old, "event": "old"})
    storage.append("tng", {"timestamp": old, "value": 1})
    wire._event({"timestamp": to_iso(now_local()), "event": "test"})
    wire._event({"timestamp": to_iso(now_local()), "event": "over_limit"})
    assert len(storage.query("tng_wire_events")) == 1
    assert len(storage.query("tng")) == 1
    assert wire.counts["log_limit_reached"]


def test_api_rejects_invalid_range_and_returns_bounded_audit(tmp_path):
    cfg = config(tmp_path)
    app = SimpleNamespace(storage=JsonlStorage(cfg.data_dir, cfg.history_dir))
    app.storage.append("tng_wire_events", {"timestamp": to_iso(now_local()), "event": "test"})
    assert tng_wire_events(app, {"hours": "invalid"})[0] == 400
    assert len(tng_wire_events(app, {"hours": "999", "limit": "1"})[1]["events"]) == 1


def test_udp_bind_failure_isolated_from_other_readers(tmp_path):
    reader = TngWireReader(config(tmp_path))
    with patch("hec.readers.tng_wire.socket.socket") as factory:
        factory.return_value.bind.side_effect = OSError("port busy")
        assert not reader.poll().ok
        assert reader.status.error_count == 1
        assert reader.socket is None
