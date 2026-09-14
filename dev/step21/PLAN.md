# Step 21 Plan - Reliable SDG history import

Describe the change and why it is needed.
Repair SDG history ingestion at the parser, discovery, checkpoint, and
history-display boundaries. The implementation must remain read-only against
the Promotic share and must not activate any device writer.

## Step sequence
| Step | Purpose | Status |
| S01 | Inventory real SDG DBF layouts, fields, and current runtime evidence | PLANNED |
| S02 | Define timestamp, source, checkpoint, and diagnostics contracts | PLANNED |
| S03 | Implement tolerant DBF discovery and timestamp normalization | PLANNED |
| S04 | Repair checkpoint/retry/idempotency behavior | PLANNED |
| S05 | Verify API/history visibility and read-only production validation | PLANNED |
| S06 | Run focused and repository validation; prepare Reviewer handoff | PLANNED |
### S01 - Data contract inventory

Objectives:
- Capture the actual `Promotic/Apps/SDGeco/Data` directory shape, DBF suffix
	casing, field names, timestamp examples, and current checkpoint contents.
- Confirm the intended canonical history source is `sdg_history`.

Implementation:
- Use fixture copies and read-only inspection only. Do not modify the UNC share,
  production checkout, or live service.

Risks:
- A production DBF variant may differ from current fixtures; preserve unknown
	fields rather than silently dropping them.

### S02 - Contract and failure semantics

Objectives:
- Specify timezone-aware ISO timestamps, invalid-row handling, file identity,
  append offset, and retry eligibility.
- Define diagnostics for discovered files, imported/skipped/duplicate rows,
  corrupt files, and checkpoint state.

Implementation:
- Add tests/fixtures before implementation; keep existing JSONL compatibility.

Risks:
- Reprocessing old files can create duplicates; fingerprints and stable file
	offsets must remain deterministic.

### S03 - Discovery and parsing

Objectives:
- Support legacy and actual SDGeco layouts with `pathlib` and case-insensitive
	DBF extension matching.
- Normalize `pm_time`, date/time pairs, and existing timestamp variants.

Implementation:
- Keep parser tolerant, retain decoded values, and skip only rows without a
	valid timestamp or with a structural decode failure.

Risks:
- Locale or malformed timestamp strings can be misinterpreted; reject rather
	than fabricate a measurement.

### S04 - Checkpoint and retry

Objectives:
- Never permanently advance a file checkpoint when all rows were skipped or
	import failed due to a parser issue.
- Handle file growth, truncation, unchanged files, restart, and duplicate
	records without repeated imports.

Implementation:
- Add focused tests for zero-valid-row retry, successful checkpoint advance,
  corruption recovery, and duplicate fingerprints.

Risks:
- Re-reading a large network file can be expensive; use bounded known roots and
	preserve successful offsets.

### S05 - History and read-only validation

Objectives:
- Ensure `/api/sources`, `/api/history`, and the History page expose imported
	`sdg_history` records and meaningful empty/error states.
- Validate the configured production share read-only if available.

Implementation:
- Use the existing API/UI; no new production writes or deployment changes.

Risks:
- A live process may use a different checkout or stale Python modules; record
	the runtime path/version in diagnostics without changing the host.

### S06 - Validation and handoff

Objectives:
- Run focused SDG tests, Ruff, non-E2E tests, safe preview, Playwright, and
	Step 21 validation.
- Record deviations and leave Gate B/C for Reviewer/Human Gate.

Implementation:
- Production evidence is read-only command output only; no restart or install
	is performed by this step.

Risks:
- Full suite may contain unrelated failures; classify them against the SDD
	severity model and do not conceal them.
# Plan

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Describe the change and why it is needed.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 |  | PLANNED |
| S02 |  | PLANNED |

## Detailed implementation strategy

### S01 –

Objectives:
- 

Implementation:
- 

Risks:
- 
