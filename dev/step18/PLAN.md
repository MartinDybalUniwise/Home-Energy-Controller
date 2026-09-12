# Step 18 Plan – SDG Log Reader

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Add the first, read-only SDG integration boundary. SDG logs become the
preferred telemetry source when a valid fresh record is available. The current
FTE/GoodWe reader remains unchanged and is selected as a backup when SDG cannot
provide trustworthy data.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Confirm SDG file schema, timestamps, and read-only access contract | DONE |
| S02 | Define normalized SDG record and provenance contract | DONE |
| S03 | Define incremental scan, checkpoint, and deduplication behavior | DONE |
| S04 | Define SDG/FTE source priority and fail-closed fallback | DONE |
| S05 | Define configuration, diagnostics, and logging boundaries | DONE |
| S06 | Define focused tests and safe validation evidence | DONE |
| S07 | Gate A handoff before application code changes | DONE |

## Detailed implementation strategy

### S01 – Schema and access contract

Objectives:
- verify read-only access to `\\192.168.2.115\Promotic\Apps\SDGeco\Data`;
- inspect sanitized metadata and records from `trend\min`, `trend\solar`,
  `Event2`, and `Alarm`;
- determine DBF encoding, field names/types, timestamp fields, timezone/DST
  semantics, file rotation, and whether a file can be read while growing;
- document which directories are telemetry candidates and which are diagnostic
  event sources.

Implementation boundary:
- no production file is copied into Git;
- use metadata, redacted samples, or generated fixtures;
- do not change the application during this substep.

Risks:
- the observed directory structure may contain multiple incompatible DBF
  schemas; unsupported variants remain explicitly unsupported.

### S02 – Normalized record and provenance

Objectives:
- map only verified SDG fields to existing `goodwe` fields;
- retain original timestamp and add a non-breaking source marker;
- distinguish missing, unsupported, invalid, and zero values;
- define quality metadata sufficient for source selection and diagnostics.

Implementation boundary:
- preserve existing API/storage field meanings;
- never infer power direction, SOC, or energy from an undocumented field.

Risks:
- different SDG files may report different sign conventions or units; each
  mapping requires evidence and explicit conversion rules.

### S03 – Incremental import and deduplication

Objectives:
- scan only new or changed files after the checkpoint;
- persist checkpoint state atomically under the configured HEC data/state path;
- define a stable record identity using source, file identity, original
  timestamp, and verified record identity fields;
- avoid advancing the checkpoint when a file is incomplete or corrupt.

Implementation boundary:
- checkpoint is HEC-owned state, not written to the SDG share;
- restart and repeated scans must be idempotent.

Risks:
- file replacement or clock changes can invalidate a simple filename cursor;
  use file metadata plus record-level deduplication and document limitations.

### S04 – Source priority and fallback

Objectives:
- define a configurable SDG freshness limit;
- prefer fresh valid SDG data;
- select the unchanged existing FTE/GoodWe reader as `fte_backup` only when
  SDG is not trustworthy;
- mark both-source failure as unavailable/stale and preserve safe mode;
- prevent stale SDG data from overwriting fresh FTE data.

Implementation boundary:
- no changes to `dev/hec/readers/goodwe.py` are planned;
- source selection must not introduce GoodWe writes or controller decisions.

Risks:
- asynchronous readers can complete in a different order; selection must be
  based on sample timestamp and validity, not thread completion order.

### S05 – Configuration, diagnostics, and logging

Objectives:
- add only the minimum configuration needed for SDG enablement, root path,
  polling/scan interval, and freshness limit;
- default SDG to disabled in local and preview environments;
- report active source, last SDG success, age, checkpoint/error state, and
  fallback reason through existing safe diagnostics;
- log structured events for scan success, skipped/corrupt files, fallback, and
  recovery without credentials or raw secrets.

Implementation boundary:
- no UI redesign or deployment changes;
- UNC paths remain configuration values and are never hardcoded outside defaults
  or examples.

Risks:
- diagnostics can disclose infrastructure details; expose only the configured
  path and sanitized status, not credentials or file contents.

### S06 – Tests and validation evidence

Objectives:
- create sanitized DBF/log fixtures after S01 schema confirmation;
- test valid mapping, missing fields, unsupported schema, corrupt/incomplete
  files, stale records, repeated scans, restart, and deduplication;
- test source priority: fresh SDG, stale/unavailable SDG with FTE backup, and
  both unavailable;
- verify scheduler isolation and unchanged FTE reader behavior.

Required validation:
- `python -m ruff check .`;
- `python -m pytest -m "not e2e"`;
- `python dev/sdd/tools/validate_step.py --phase ready --step dev/step18`;
- safe preview with controller and TNG writes disabled when runtime code is
  eventually implemented.

No test may access the production share or perform a physical-device write.

### S07 – Gate A handoff

- record the plan package and verified access evidence;
- keep `STEP.json` Gate A `PENDING` until explicit human approval;
- after approval, update the manifest before any application code edit;
- implement only the approved read-only SDG reader and fallback boundary.

## Likely future implementation surface

- `dev/hec/readers/sdg_log.py` or equivalent read-only reader module;
- `dev/hec/readers/registry.py` only if a separate reader registration is
  required;
- `dev/hec/core/schema.py` for minimal SDG configuration and validation;
- existing scheduler/storage integration only where required by the normalized
  contract;
- focused tests under `dev/hec/tests/`.

The existing `dev/hec/readers/goodwe.py` remains outside the planned edit set.

## Delivery order

1. Approve this planning package at Gate A.
2. Complete S01 with sanitized schema evidence.
3. Implement and test S02-S05 within the approved read-only boundary.
4. Run S06 validation and record evidence.
5. Do not mark the step done until acceptance criteria and required review
   evidence are complete.
