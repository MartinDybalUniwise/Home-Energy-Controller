"""Receive a passive MikroTik TZSP mirror independently of cloud TNG control."""

from __future__ import annotations

import json
import socket
import struct
import time
from datetime import UTC, datetime, timedelta

from ..core.model import Sample
from ..core.timeutil import now_local, parse_iso, to_iso
from .base import BaseReader
from .tng_protocol import Reader, decode, tzsp_frame

TEMPERATURE_FIELDS = {
    "aku_c": "buffer_temperature",
    "outlet_c": "water_output_temperature",
    "inlet_c": "water_input_temperature",
    "boiler_c": "boiler_temperature",
    "outside_c": "outside_temperature",
    "room_c": "room_temperature",
    "refrigerant_c": "refrigerant_output_temperature",
}


class TngWireReader(BaseReader):
    name = "tng_wire"

    def __init__(self, config, storage=None):
        super().__init__(config, storage)
        self.socket = None
        self.decoder = Reader(config.get("tng_wire.tc_ip", "192.168.2.100"))
        self.pending = {}
        self.counts = {"packets": 0, "requests": 0, "responses": 0, "pairs": 0, "invalid": 0}
        self.last_pair = None
        self._pruned_day = None

    def interval_seconds(self):
        return 1

    def schedule_next(self, monotonic_now):
        self._next_at = monotonic_now + 1
        self.status.interval_seconds = 60  # Telemetry cadence, not UDP drain cadence.

    def _event(self, record):
        if not self.storage:
            return
        stamp = parse_iso(record.get("timestamp")) or now_local()
        path = self.storage._day_file("tng_wire_events", stamp)
        maximum = int(self.config.get("tng_wire.max_daily_bytes", 50_000_000))
        if path.exists() and path.stat().st_size >= maximum:
            self.counts["log_limit_reached"] = True
            return
        self.storage.append("tng_wire_events", record)
        # Prune only this reader's dated raw traces, never other histories.
        day = now_local().date()
        if self._pruned_day != day:
            cutoff = day - timedelta(days=int(self.config.get("tng_wire.retention_days", 30)))
            for old in path.parent.glob("????-??-??.jsonl"):
                if old.is_symlink() or not old.is_file():
                    continue
                try:
                    old_day = datetime.strptime(old.stem, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if old_day < cutoff:
                    self.storage.history_changes.mark(old)
                    old.unlink()
            self._pruned_day = day

    def ingest(self, message):
        stamp, body = message["stamp"], message["body"]
        meta = {k: message[k] for k in ("direction", "connection", "message_id")}
        # Keep protocol headers useful for analysis, never cookies/auth/device IDs.
        lines = message["http_header"].split("\r\n")
        header = [line for line in lines[1:] if line.lower().startswith(("content-type:", "content-length:"))]
        record = {
            "timestamp": to_iso(datetime.fromtimestamp(stamp, UTC).astimezone()),
            "event": "request" if meta["direction"] == "tc_to_server" else "response",
            "source": self.name,
            **meta,
            "http_headers": header,
            "http_body_hex": body.hex(),
            "decoder_version": "observed-branches-v1",
        }
        self.pending = {k: v for k, v in self.pending.items() if stamp - v["stamp"] < 180}
        if record["event"] == "request":
            decoded = decode(body)
            record.update(decoded)
            record["wire_hex"] = body.hex()
            self._event(record)
            if len(self.pending) >= 64:
                self.pending.pop(next(iter(self.pending)))
            self.pending[message["connection"]] = {**message, "decoded": decoded}
            self.counts["requests"] += 1
            values = {dest: decoded["temperatures"][key] for key, dest in TEMPERATURE_FIELDS.items()}
            # The higher refrigerant branch is not selected by guessing.
            if "refrigerant_c" in decoded["outside_reference_range"]:
                values["refrigerant_output_temperature"] = None
            values.update(
                sample_time=record["timestamp"],
                online=True,
                field_quality={
                    TEMPERATURE_FIELDS[k]: (
                        "outside_verified_range"
                        if k in decoded["outside_reference_range"]
                        else "photo_validated_provisional"
                    )
                    for k in TEMPERATURE_FIELDS
                },
                decoder_version=record["decoder_version"],
                checksum_verified=False,
                candidate_frequency_or_ack=decoded["candidate_frequency_or_ack"],
                candidate_inputs=decoded["candidate_inputs"],
                candidate_outputs=decoded["candidate_outputs"],
                control_eligible=False,
            )
            sample = Sample(self.name, values, timestamp=parse_iso(record["timestamp"]))
            if self.storage:
                self.storage.append(self.name, sample.to_dict())
                self.storage.write_current(self.name, sample.to_dict())
            return sample
        self.counts["responses"] += 1
        request = self.pending.pop(message["connection"], None)
        record["request_id"] = request["message_id"] if request else None
        record["http_status"] = int(lines[0].split()[1])
        try:
            record["json_text"] = body.decode("utf-8")
            value = json.loads(record["json_text"])
            if not isinstance(value, str):
                raise ValueError("expected_json_hex_string")
            wire = bytes.fromhex(value)
            decoded = decode(wire)
            record.update(decoded)
            record["wire_hex"] = wire.hex()
            if request:
                a = bytes.fromhex(request["decoded"]["decoded_hex"])
                b = bytes.fromhex(decoded["decoded_hex"])
                pair = {
                    "timestamp": record["timestamp"],
                    "source": self.name,
                    "event": "exchange",
                    "request_id": request["message_id"],
                    "response_id": message["message_id"],
                    "request_at": to_iso(datetime.fromtimestamp(request["stamp"], UTC).astimezone()),
                    "response_at": record["timestamp"],
                    "observed_delay_ms": round((stamp - request["stamp"]) * 1000, 3),
                    "temperatures_equal": request["decoded"]["temperatures"] == decoded["temperatures"],
                    "changed_decoded_offsets": [
                        i for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y
                    ],
                }
                self._event(record)
                self._event(pair)
                self.last_pair = pair
                self.counts["pairs"] += 1
                return None
        except (ValueError, UnicodeError) as exc:
            record["decode_error"] = type(exc).__name__
        self._event(record)
        return None

    def status_snapshot(self):
        return {
            **self.counts,
            "last_pair": self.last_pair,
            "last_error": self.status.last_error,
            "port": self.config.get("tng_wire.port", 37008),
        }

    def poll(self):
        self.status.last_attempt = now_local()
        last = Sample(self.name, ok=False, error="no_new_wire_sample")
        try:
            if self.socket is None:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    self.socket.bind(
                        (
                            self.config.get("tng_wire.bind", "0.0.0.0"),
                            int(self.config.get("tng_wire.port", 37008)),
                        )
                    )
                    self.socket.settimeout(0.25)
                except OSError:
                    self.close()
                    raise
            deadline = time.monotonic() + 1
            for _ in range(256):
                if time.monotonic() >= deadline:
                    break
                try:
                    data, sender = self.socket.recvfrom(65535)
                except TimeoutError:
                    break
                if sender[0] != self.config.get("tng_wire.router_ip", "192.168.2.1"):
                    continue
                self.counts["packets"] += 1
                try:
                    frame = tzsp_frame(data)
                    for message in self.decoder.feed_messages(time.time(), 1, frame):
                        sample = self.ingest(message)
                        if sample:
                            last = sample
                            self.status.last_success = sample.timestamp
                            self.status.success_count += 1
                            self.status.last_error = None
                except (ValueError, IndexError, struct.error):
                    self.counts["invalid"] += 1
        except Exception as exc:  # noqa: BLE001 - an optional mirror cannot stop cloud control
            self.status.last_error = f"{type(exc).__name__}: {exc}"
            self.status.error_count += 1
            self.log.warning("wire_receive_failed | error=%s", type(exc).__name__)
        return last

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
