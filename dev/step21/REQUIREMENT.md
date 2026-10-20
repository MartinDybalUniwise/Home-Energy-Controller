# Step 21 Requirement - Reliable SDG history import

## Objective

Make SDG historical import reliable and observable without changing device
control behavior. A successful reader poll must mean that the importer has
either imported records or explicitly reported why no valid records exist.

## Scope

### In scope

- SDG DBF import and its persisted history contract.
- Read-only diagnostics and focused tests.

### Out of scope

- SDG source file format beyond the stable fields needed for timestamp and
	record identity.
- Physical devices, writer paths, controller rules, and production rollout.

## Functional requirements

- REQ-021-001: Discover both the legacy `root/Data/...` layout and the actual
	`root/Apps/SDGeco/Data/...` layout, with case-insensitive `.dbf` matching and
	deterministic de-duplication of discovered files.
- REQ-021-002: Normalize `pm_time` values such as `YYYY.MM.DD HH:MM:SS` and
	existing supported date/time representations to timezone-aware ISO 8601
	timestamps.
- REQ-021-003: Store imported records under the canonical `sdg_history` source
	used by the reader status, History page, API, and diagnostics.
- REQ-021-004: Persist checkpoint progress only after a file has been parsed
	successfully and its valid records have been handled; files with zero valid
	records remain eligible for a later retry or emit an explicit diagnostic.
- REQ-021-005: Preserve idempotency and deduplication across repeated polls,
	file growth, unchanged files, and a checkpoint restart.
- REQ-021-006: Expose imported, skipped, duplicate, corrupt-file, discovered
	file, and last-import status without exposing secrets or raw credentials.
- REQ-021-007: Keep the existing History API/UI able to select and display
	`sdg_history` records with their timestamp and SDG payload.

## Non-functional requirements

- NFR-021-001: A reader exception or corrupt DBF must not stop other readers or
	the scheduler.
- NFR-021-002: Parsing is portable across Windows UNC paths, Linux paths, and
	Raspberry Pi deployments using `pathlib`.
- NFR-021-003: No fabricated measurements are created when a row lacks a valid
	timestamp; such rows are counted as skipped.
- NFR-021-004: Automated tests cover real directory shape, timestamp formats,
	checkpoint behavior, duplicate handling, and no-data diagnostics.

## Safety requirements

- TNG write gate remains disabled.
- `controller.enabled=false` remains required in preview/local validation.
- No physical-device writes.

## Risks

- IMPORTANT: checkpointing a file after all rows are skipped can permanently
	hide data after a parser fix; mitigate with explicit checkpoint eligibility
	and a regression test.
- IMPORTANT: importing malformed or misinterpreted numeric fields can produce
	misleading energy history; preserve raw normalized values and skip only rows
	that lack a valid timestamp or cannot be decoded.
- MINOR: large historical DBF scans can be slow on a network share; keep
	incremental offsets and avoid broad recursive scans outside known SDG roots.
