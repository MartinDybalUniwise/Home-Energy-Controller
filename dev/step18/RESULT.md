# Step 18 Result – SDG Log Reader

## Status

Step18 is `DONE`. Gate A is approved, and the production read-only validation against
`S:\Apps\SDGeco\Data` confirms the SDG share is reachable and contains the expected
telemetry DBF files. The implementation remains limited to read-only log access and
source selection; no SDG, GoodWe, or TNG write path is added.

## Production validation evidence

The validation command used was a directory-level read-only check against the live
share:

- `cmd /c if exist "S:\Apps\SDGeco\Data" (...)`

Observed output from the production share:

- Root exists: `EXISTS=1`
- Candidate directories: `Alarm`, `Event`, `Event1`, `Event2`, `Event3`, `PEK`,
  `PSK`, `trend`, `Web`
- DBF files are present in the expected telemetry branches, including:
  - `S:\Apps\SDGeco\Data\trend\min\min2025-08-09_00-00-02.dbf`
  - `S:\Apps\SDGeco\Data\Event2\Events22026-09-12_12-00-10.dbf`
  - `S:\Apps\SDGeco\Data\Alarm\AlTest2025-03-23_14-13-03.dbf`

This is read-only validation only; the repository contains no copied production
DBF files, no credentials, and no runtime state from the SDG share.

## Implementation outcome

- Added `SdgLogReader` with read-only DBF access, explicit field aliases,
  timestamp preservation, freshness checks, and source provenance.
- Registered SDG as a disabled-by-default reader.
- Added SDG/FTE source arbitration while preserving the public `goodwe`
  snapshot and leaving `dev/hec/readers/goodwe.py` unchanged.
- Added safe schema/example/preview configuration for the verified SDG root.
- Added sanitized unit coverage for normalization, newest-record selection,
  SDG priority, FTE fallback, registration, flow signs, checkpoint, and
  restart-safe deduplication.
- Fixed registry activation so `goodwe.sdg.enabled` actually creates the SDG
  reader.
- Added HEC-owned atomic checkpoint state with per-file fingerprints and latest
  normalized records; the SDG share remains read-only.
- Added deterministic record keys and repeated-scan/restart deduplication.
- Added explicit grid and battery flow derivation using the existing GoodWe
  sign configuration.

## Validation evidence

- `python -m ruff check .`: PASS
- `python -m pytest -m "not e2e"`: PASS
- `python dev/sdd/tools/validate_step.py --phase done --step dev/step18`: PASS
- Production share validation: PASS (`S:\Apps\SDGeco\Data` reachable and DBF
  telemetry files discovered without copying or modifying production data)

## Evidence set

- E-018-001: production SDG share access and read-only safety review.
- E-018-002: sanitized schema and parser fixtures.
- E-018-003: normalized contract tests.
- E-018-004: timestamp and provenance tests.
- E-018-005: checkpoint and deduplication tests.
- E-018-006: source-priority and FTE fallback tests.
- E-018-007: diagnostics and structured logging review.
- E-018-008: scheduler-isolation tests.
- E-018-009: cross-platform path tests.
- E-018-010: existing consumer and FTE regression tests.
- E-018-011: bounded incremental-scan test.
- E-018-012: sanitized fixture and validation review.
- E-018-013: structured logging review.

