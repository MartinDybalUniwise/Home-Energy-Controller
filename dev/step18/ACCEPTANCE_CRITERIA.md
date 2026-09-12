# Step 18 Acceptance Criteria – SDG Log Reader

## Planning and scope

- [x] AC-018-001: The step is limited to read-only SDG log access and source
  selection; no SDG/FTE/GoodWe write behavior is in scope.
- [x] AC-018-002: The actual UNC root and observed directory layout are recorded,
  while DBF schema details are supported by sanitized read-only evidence before
  parser implementation.

## SDG reader contract

- [x] AC-018-003: The reader accesses only the configured SDG root and never
  writes to the share or changes SDG state.
- [x] AC-018-004: Supported SDG records are normalized into the existing
  `goodwe` telemetry contract with explicit units, signs, timestamps, and
  missing/unsupported-value behavior.
- [x] AC-018-005: Original source timestamps are preserved as ISO 8601 values
  with an explicit timezone and source provenance identifies `sdg`.
- [x] AC-018-006: Incremental scanning, atomic checkpoints, and deterministic
  deduplication are demonstrated across repeated scans and restart.
- [x] AC-018-007: Corrupt, incomplete, inaccessible, or unsupported files are
  skipped or retried safely without advancing invalid checkpoint state.

## FTE fallback

- [x] AC-018-008: The existing FTE/GoodWe reader remains available and its
  implementation and field mapping are unchanged.
- [x] AC-018-009: Fresh valid SDG data has priority over FTE data regardless of
  asynchronous completion order.
- [x] AC-018-010: Stale, missing, invalid, or unavailable SDG data selects FTE
  as `fte_backup` without generating synthetic values.
- [x] AC-018-011: When both sources are unusable, the result is marked
  unavailable/stale and does not hide safe-mode conditions.

## Diagnostics and quality

- [x] AC-018-012: Diagnostics expose active source, last successful read, data
  age, and fallback/error reason without credentials or raw log contents.
- [x] AC-018-013: Failures in SDG access or parsing do not stop other readers or
  the scheduler.
- [x] AC-018-014: Sanitized unit tests cover mapping, missing fields, malformed
  data, freshness, checkpointing, deduplication, fallback, and both-source
  failure.
- [x] AC-018-015: Ruff, non-E2E tests, and the relevant safe preview/validation
  evidence pass; no test accesses the production share or writes to hardware.
- [x] AC-018-016: Human review confirms the implementation stays within the
  approved read-only scope before the step can be marked DONE.

## Safety invariants

- [x] `controller.enabled=false` remains required in local and preview runs.
- [x] `tng.write_enabled=false` remains required in local and preview runs.
- [x] No physical-device write path is added, enabled, or tested as a real write.
- [x] Frozen root prototypes remain unchanged.
