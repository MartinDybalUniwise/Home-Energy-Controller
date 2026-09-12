# Step 18 Requirement – SDG Log Reader

## Objective

Define and later implement a safe read-only SDG log reader that supplies
GoodWe telemetry from `\\192.168.2.115\Promotic\Apps\SDGeco\Data` while
preserving the current FTE/GoodWe reader as the fallback path.

## Expected outcome

HEC consumes one normalized `goodwe` telemetry stream. A fresh, valid SDG log
sample has priority. If SDG is unavailable, corrupt, incomplete, or stale, the
existing FTE reader remains usable without modification. If both sources fail,
HEC records an unavailable/stale condition instead of inventing values.

## Scope

### In scope

- Configured SDG log root and read-only path handling.
- Read-only DBF/log discovery under `Data`.
- Candidate directories currently observed on the share:
  - `trend\min`
  - `trend\solar`
  - `Event2`
  - `Alarm`
- Data dictionary and timestamp rules based on actual sampled records.
- Normalization to the existing GoodWe telemetry fields.
- Incremental scan/checkpoint and deterministic deduplication.
- Freshness, malformed-record, and source-priority rules.
- Fallback orchestration that leaves the existing FTE reader unchanged.
- Diagnostics, provenance, and focused tests.

### Out of scope

- SDG control, writes, process reconfiguration, or service management.
- GoodWe writes, `GoodWeManager`, `FTEWriter`, or controller changes.
- Changes to FTE reader field mapping or network behavior.
- New optimization decisions or changes to safe mode semantics.
- UI redesign, deployment, hardware write testing, or unrelated readers.

## Functional requirements

- REQ-018-001: Read only from the configured SDG root and never write to the
  share or to SDG files.
- REQ-018-002: Discover and parse only supported SDG log formats after a
  read-only sample confirms their schema, encoding, and timestamp fields.
- REQ-018-003: Normalize supported SDG records into the existing `goodwe`
  telemetry contract without guessing missing or unknown values.
- REQ-018-004: Preserve the original source timestamp and record provenance;
  timestamps must be ISO 8601 with an explicit timezone in HEC storage.
- REQ-018-005: Import incrementally with an atomically persisted checkpoint and
  deterministic deduplication across restart and repeated scans.
- REQ-018-006: Select fresh valid SDG data before the unchanged FTE reader;
  select FTE as backup only when SDG is unavailable, invalid, incomplete, or
  stale according to configured limits.
- REQ-018-007: Mark source status as `sdg`, `fte_backup`, or unavailable and
  expose last success, age, and error reason to existing diagnostics without
  exposing secrets or production paths beyond the configured diagnostic field.
- REQ-018-008: A failure in SDG parsing or access must not stop other readers or
  the scheduler.

## Non-functional requirements

- NFR-018-001: Use `pathlib.Path` and preserve Windows UNC plus Raspberry Pi
  portability through configured paths or mounted equivalents.
- NFR-018-002: Keep the existing `goodwe` history/API consumer contract
  backward-compatible.
- NFR-018-003: Use bounded work per poll and avoid rescanning all historical DBF
  data on every cycle.
- NFR-018-004: Unit tests must use sanitized fixtures and must not depend on the
  production share.
- NFR-018-005: The implementation must be observable through structured log
  events without logging credentials or raw sensitive configuration.

## Safety requirements

- `controller.enabled=false` remains required in local and preview validation.
- `tng.write_enabled=false` remains required in local and preview validation.
- No physical-device write path may be added or enabled.
- The SDG reader must be strictly read-only.
- Fallback must fail closed when freshness or data validity cannot be proven.
- Frozen root prototypes remain unchanged.

## Risks

- SDG DBF schema, encoding, and timestamp semantics are not yet documented;
  S01 must capture a sanitized schema sample before parser implementation.
- A partially written current DBF file may be read during SDG rotation; parser
  errors must be retried later without advancing the checkpoint.
- A stale but syntactically valid SDG record could hide a usable FTE sample;
  freshness must be evaluated before source selection.
- Duplicate records can arise from overlapping file scans or restart; the
  checkpoint and deduplication key must be deterministic and atomic.
- The UNC share may be temporarily unavailable; this must affect only SDG
  status and must not block FTE or unrelated readers.
