"""Passive TNG wire decoding. No sockets, control, or automatic branch guessing.

Byte positions are zero-based in the 130-byte body. CRC/high-bit selection
remain unresolved; field confidence must survive every presentation layer.
"""

from __future__ import annotations

import hashlib
import ipaddress
import struct


def tcp_packet(linktype, packet):
    if linktype == 1:
        if len(packet) < 14:
            return None
        proto = struct.unpack_from("!H", packet, 12)[0]
        start = 14
        while proto in (0x8100, 0x88A8):
            proto = struct.unpack_from("!H", packet, start + 2)[0]
            start += 4
        if proto != 0x800:
            return None
    elif linktype in (101, 228):
        start = 0
    elif linktype == 113:
        if struct.unpack_from("!H", packet, 14)[0] != 0x800:
            return None
        start = 16
    else:
        return None
    ip = packet[start:]
    if len(ip) < 20 or ip[0] >> 4 != 4 or ip[9] != 6:
        return None
    size = struct.unpack_from("!H", ip, 2)[0]
    header = (ip[0] & 15) * 4
    if struct.unpack_from("!H", ip, 6)[0] & 0x1FFF:
        return None
    tcp = ip[header:size]
    if len(tcp) < 20:
        return None
    sport, dport, seq = struct.unpack_from("!HHI", tcp)
    tcp_header = (tcp[12] >> 4) * 4
    return (
        (str(ipaddress.ip_address(ip[12:16])), sport, str(ipaddress.ip_address(ip[16:20])), dport),
        seq,
        tcp[tcp_header:],
    )


def reassemble(segments):
    ordered = sorted(segments, key=lambda segment: (segment[0], segment[1]))
    start = ordered[0][0]
    out = bytearray()
    gaps = []
    conflicts = 0
    duplicates = 0
    for seq, _stamp, payload in ordered:
        relative = seq - start
        if relative > len(out):
            gaps.append((len(out), relative))
            out.extend(b"\0" * (relative - len(out)))
        overlap = min(len(payload), max(0, len(out) - relative))
        if overlap:
            duplicates += overlap
            if out[relative : relative + overlap] != payload[:overlap]:
                conflicts += 1
        if overlap < len(payload):
            out.extend(payload[overlap:])
    return bytes(out), gaps, conflicts, duplicates


BIT_MAP = (5, 3, 4, 1, 7, 6, 2, 0)
FIELDS = {
    "aku_c": (80, 256, 35.2, 41.3),
    "outlet_c": (85, 256, 26.2, 46.1),
    "outside_c": (87, 0, 3.3, 19.6),
    "boiler_c": (88, 256, 28.3, 46.2),
    "room_c": (89, 0, 20.6, 21.8),
    "inlet_c": (94, 256, 33.1, 45.1),
    "refrigerant_c": (95, 256, 37.2, 50.7),
}


def decode(body):
    if len(body) != 130:
        raise ValueError("Expected 130-byte TNG body")
    plain = bytes(sum(((b ^ body[4]) >> src & 1) << dst for dst, src in enumerate(BIT_MAP)) for b in body)
    temps = {key: (plain[offset] + branch) / 10 for key, (offset, branch, low, high) in FIELDS.items()}
    outside = [key for key, (_, _, low, high) in FIELDS.items() if not low <= temps[key] <= high]
    return {
        "temperatures": temps,
        "quality": "provisional_outside_reference_range" if outside else "provisional_reference_range",
        "outside_reference_range": outside,
        "checksum_verified": False,
        "decoder_version": "xor-permutation-observed-branches-v1",
        "decoded_hex": plain.hex(),
        "candidate_frequency_or_ack": plain[86],
        "candidate_outputs": plain[84],
        "candidate_inputs": plain[93],
        "buffer_adjacent_byte": plain[81],
    }


def tzsp_frame(data):
    if len(data) < 5 or data[:2] != b"\x01\x00" or data[2:4] != b"\x00\x01":
        raise ValueError("Expected TZSP v1 received Ethernet packet")
    pos = 4
    while pos < len(data):
        tag = data[pos]
        pos += 1
        if tag == 1:
            return data[pos:]
        if tag == 0:
            continue
        if pos >= len(data):
            break
        size = data[pos]
        pos += 1 + size
    raise ValueError("Incomplete TZSP tags")


class Reader:
    def __init__(self, tc_ip):
        self.tc_ip = tc_ip
        self.flows = {}
        self.done = {}
        self.conflicts = 0

    def feed(self, stamp, linktype, packet):
        """Compatibility temperature stream: TČ-originating requests only."""
        return [
            (m["stamp"], m["body"])
            for m in self.feed_messages(stamp, linktype, packet)
            if m["direction"] == "tc_to_server"
        ]

    def feed_messages(self, stamp, linktype, packet):
        parsed = tcp_packet(linktype, packet)
        if not parsed:
            return []
        key, seq, payload = parsed
        outgoing = key[0] == self.tc_ip and key[3] == 80
        incoming = key[2] == self.tc_ip and key[1] == 80
        if not (outgoing or incoming) or not payload:
            return []
        # Expire connections and deduplication entries; memory stays bounded.
        self.flows = {k: v for k, v in self.flows.items() if stamp - v["last"] < 180}
        self.done = {k: v for k, v in self.done.items() if stamp - v < 600}
        if key not in self.flows:
            if len(self.flows) >= 64:
                self.flows.pop(next(iter(self.flows)))
            self.flows[key] = {"last": stamp, "segments": []}
        flow = self.flows[key]
        flow["last"] = stamp
        flow["segments"].append((seq, stamp, payload))
        segments = flow["segments"]
        if (
            len(segments) > 128
            or sum(len(s[2]) for s in segments) > 65536
            or max(s[0] for s in segments) - min(s[0] for s in segments) > 65536
        ):
            del self.flows[key]
            return []
        stream, gaps, conflicts, _ = reassemble(segments)
        if gaps or conflicts:
            self.conflicts += bool(conflicts)
            return []
        result = []
        start = 0
        while True:
            start = stream.find(b"POST " if outgoing else b"HTTP/", start)
            if start < 0:
                break
            end = stream.find(b"\r\n\r\n", start)
            if end < 0:
                break
            lines = stream[start:end].split(b"\r\n")
            headers = dict(line.split(b":", 1) for line in lines[1:] if b":" in line)
            headers = {k.lower().strip(): v.strip() for k, v in headers.items()}
            try:
                size = int(headers.get(b"content-length", b"0"))
            except ValueError:
                start = end + 4
                continue
            accepted = (outgoing and size == 130 and b"/Communication/" in lines[0]) or (
                incoming and b"application/json" in headers.get(b"content-type", b"") and 0 < size <= 4096
            )
            if not accepted:
                start = end + 4
                continue
            body = stream[end + 4 : end + 4 + size]
            if len(body) < size:
                break
            identity = (key, min(s[0] for s in segments) + start, hashlib.sha256(body).digest())
            if identity not in self.done:
                self.done[identity] = stamp
                base = min(s[0] for s in segments)
                packet_time = min(
                    s[1] for s in segments if s[0] < base + end + 4 + size and s[0] + len(s[2]) > base + start
                )
                canonical = key if outgoing else (key[2], key[3], key[0], key[1])
                connection = f"{canonical[0]}:{canonical[1]}>{canonical[2]}:{canonical[3]}"
                message_id = hashlib.sha256(
                    (connection + str(key) + str(base + start)).encode() + body
                ).hexdigest()[:24]
                result.append(
                    {
                        "stamp": packet_time,
                        "body": body,
                        "direction": "tc_to_server" if outgoing else "server_to_tc",
                        "connection": connection,
                        "message_id": message_id,
                        "http_header": stream[start:end].decode("latin1"),
                    }
                )
            start = end + 4 + size
        return result
