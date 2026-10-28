# Passive TNG evidence

The existing `tng` cloud reader and its control/confirmation gates remain authoritative
for control. `tng_wire` receives only MikroTik TZSP/UDP mirrors; it never connects to
the LAN controller or transmits a device command. It is disabled by default.

Configure `tng_wire.enabled`, `bind`, `port` (37008), `tc_ip` and `router_ip`.
The standalone validation logger must be stopped before HEC claims the same port.
Keep the existing MikroTik stream to the HEC host. Allow inbound UDP from that
router to the exact port; no firewall disabling or broad grants are required.

## Records

- `history/tng_wire/YYYY-MM-DD.jsonl`: TČ-originating provisional sensor samples.
- `history/tng_wire_events/YYYY-MM-DD.jsonl`: request, response and exchange records.
  Both original HTTP bodies are stored as hex. Responses additionally preserve
  `json_text`, the inner 130-byte `wire_hex`, and versioned `decoded_hex`.
  Pair IDs connect records from the same TCP connection. Exchanges list changed
  decoded offsets and equality of sensor values. Missing counterparts stay unpaired.
- `history/tng_commands/YYYY-MM-DD.jsonl`: allowlisted cloud setting payloads,
  requested/sent/failed/dry-run outcomes, pending-seen and confirmed-cycle/recovery
  observations. The original false→true→false gate and minimum 900 s are unchanged.
- `data/current_tng_wire.json` and `current_tng_command.json`: latest snapshots.
- `GET /api/tng-wire/events?hours=1&limit=100`: authenticated bounded raw/command view,
  maximum 24 h and 500 records of each kind; GET only.

Trace bodies remain private operational data, never Git fixtures or diagnostic
exports. HTTP credentials, cookies and device IDs in paths are not logged. Defaults:
daily raw trace files, 30-day retention for raw wire events only, 50 MB/day cap.
Sensor history and command evidence are not pruned by that raw retention routine.
Packet reassembly, pending pairs and per-poll processing are bounded. Time labels
are collector receive times, not verified controller clocks. Observed reply delay
may include collector processing and is not a guaranteed network RTT.

## Decode status and UI

The independently photo-checked AKU sensor is byte 80. Outlet byte 85 is a separate
sensor; never substitute it for AKU, floor-loop water or floor surface temperature.
XOR reference byte 4 plus bit permutation is followed by observed temperature
branches. CRC, high-bit selection, negative temperatures and candidate operating
bits remain unresolved. Refrigerant outside its checked branch is null in the UI;
the raw candidate remains in evidence. Never infer a branch by always adding 25.6 C.

The overview panel mirrors the physical display. `?` denotes a candidate field;
unknown fields are `—`. Cloud-derived fields are marked API. Passive samples expire
after 180 s, cloud after 900 s, with per-field cloud fallback for common temperatures.
AKU has no cloud substitute. Decoder data are explicitly not control-eligible.
The adjacent command panel separates current plan, last delivery, gate status and
reported cloud settings. A completed gate is not proof that the compressor runs.

## Twice-daily review

08:00 and 20:00 Europe/Prague: inspect new bounded evidence since the previous
checkpoint, compare real cloud commands to wire replies and later physical effects,
and report verified findings/unknowns. Do not generate commands for experimentation.
Use original timed photos and independent cloud/Shelly evidence; phase-fault Shelly
can support temporal observations, not valid energy/COP. Proven observational
decoder changes require regression tests and the normal backup/PR/deploy process.
