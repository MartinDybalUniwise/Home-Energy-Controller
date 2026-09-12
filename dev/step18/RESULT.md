# Step 18 Result – SDG Log Reader

## Status

Step18 is `IN_PROGRESS` with Gate A `APPROVED`. The read-only implementation
and automated validation are complete for the current scope; review remains
open for production DBF schema coverage and incremental import hardening.

## Planning-only outcome

- Scope is limited to read-only SDG log access and source selection.
- The SDG root was verified as readable through PowerShell:
  `\\192.168.2.115\Promotic\Apps\SDGeco\Data`.
- The share contains the observed candidate directories `trend\min`,
  `trend\solar`, `Event2`, and `Alarm`, with DBF files present.
- Existing FTE/GoodWe reading remains the planned backup path and is explicitly
  outside the planned edit set.
- No root prototype or physical-device write behavior has changed.

## Implementation outcome

- Added `SdgLogReader` with read-only DBF access, explicit field aliases,
  timestamp preservation, freshness checks, and source provenance.
- Registered SDG as a disabled-by-default reader.
- Added SDG/FTE source arbitration while preserving the public `goodwe`
  snapshot and leaving `dev/hec/readers/goodwe.py` unchanged.
- Added safe schema/example/preview configuration for the verified SDG root.
- Added sanitized unit coverage for normalization, newest-record selection,
  SDG priority, and FTE fallback.

## Validation evidence

- Ruff: PASS (`python -m ruff check .`).
- Unit tests: PASS (`264 passed, 5 deselected`).
- Full SDD validation: PASS before final metadata-only updates, including safe
  preview, repository hygiene, and mock Playwright.

## Open review items

- Confirm actual DBF field names and timestamp semantics against sanitized
  production samples.
- Add durable incremental checkpoints and deterministic deduplication before
  marking the step DONE.
- Repeat full validation after reviewer-approved mapping/checkpoint changes.

## Open before implementation

- Complete S01 with sanitized DBF schema, encoding, timestamp, unit, and sign
  evidence.
- Obtain explicit Gate A approval and record it in `STEP.json`.
- Do not copy production logs or credentials into the repository.

## Planned evidence

- E-018-001: read-only SDG path and safety review.
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

## Validation status

Validation will be run after the planning package is created. No PASS status is
claimed here before the commands complete.
