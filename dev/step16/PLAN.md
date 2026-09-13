# Step 16 plan

## Goal

Execute the approved GoodWe integration refactor in a controlled implementation
phase. The design and specification for S01–S05 are complete and frozen as the
accepted implementation contract, while S06 is the actual implementation work
and S07 remains the human and hardware verification gate before any live write
activity is approved.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Confirm GoodWe library API and communication ownership | COMPLETED / SPECIFIED |
| S02 | Design the shared manager and read-only reader boundary | COMPLETED / SPECIFIED |
| S03 | Specify writer commands, confirmation gates, and audit records | COMPLETED / SPECIFIED |
| S04 | Specify SDG history import and path configuration | COMPLETED / SPECIFIED |
| S05 | Define configuration, diagnostics, i18n, and test contracts | COMPLETED / SPECIFIED |
| S06 | Implement the approved GoodWeManager, reader, writer, SDG import, diagnostics, and validation coverage | IN_PROGRESS / REVIEW |
| S07 | Perform guarded human and hardware verification before enabling live writes | PENDING |

## Implementation scope

### S06 – implementation phase

Implement the approved design in the HEC codebase, limited to the approved GoodWe
integration surface and safety constraints:

- `GoodWeManager` with serialized communication, retry/backoff policy, timeout
  handling, reconnect logic, read-back verification, persistent audit, and
  auditable state transitions.
- `FTEReader` using the GoodWe library as primary data source, with a normalized
  output model and graceful degradation for unsupported data and communication
  failures.
- `FTEWriter` with idempotent command layer, read-back verification, persistent
  audit, explicit safety gates, and no bypass of the TNG confirmation cycle.
- All controller components, including reader and writer paths, must print their
  current status to the terminal during operation so the operational state is
  visible in local development and diagnostics.
- `SDGHistoryReader` for incremental, deduplicated, and tolerant import of SDG
  historical diagnostics and DBF logs.
- Configuration and schema updates for GoodWe host, intervals, timeouts, retry
  policy, SDG root path, and diagnostics payloads.
- Diagnostics and web settings updates covering connection status, read/write
  timing, firmware/model state, writer status, export/control limits, battery
  metrics, SDG status/checkpoint, and read-only hardware authorization state.
- Unit tests and mock-preview coverage for failure, retry, validation, and
  safety behavior.

### S07 – human/hardware verification

- Mandatory human review and hardware verification before any live inverter write
  or controller activation is considered approved.
- No runtime GoodWe write operations may be executed without separate human and
  hardware evidence.

### Required before S07

- Complete GoodWe/SDG Settings and diagnostics UI.
- Resolve the canonical timeout/read-interval/retry configuration naming and
  default mismatch.
- Remove stale `hardware_verified` configuration diagnostics and expose only
  the local authorization evidence as read-only state.
- Make traceability and RESULT evidence point to actual tests and commands.

### Explicitly outside Step16

- Production GoodWe optimization decision rules.
- Cryptographic or immutable authorization evidence.
- Detailed DBF header fingerprint hardening.
- Extra unsupported metadata beyond stable `None` values.
- Distribution-level jitter tests and additional traceability hardening.

## Safety boundaries

- `controller.enabled=false` and `tng.write_enabled=false` remain unchanged.
- No GoodWe write path, physical-device access, or controller enablement is
  considered approved by this planning step alone.
- The TNG confirmation cycle and 900-second minimum interval remain mandatory.
- Unsupported device values must be represented explicitly, never guessed.
- `writer_enabled` is explicit, but physical I/O remains disabled in every
  automated/test runtime.
- Every GoodWe write goes through GoodWeManager, performs read-back, and emits
  persistent audit evidence.
- Implementation may proceed only within the approved safe design and validation
  gates; the hardware verification stage remains separate.

## Validation plan

Implementation will require focused unit tests, Ruff, repository hygiene, safe
mock preview, Playwright smoke, and a separately recorded human hardware test.
Automated checks will not be used as hardware evidence.