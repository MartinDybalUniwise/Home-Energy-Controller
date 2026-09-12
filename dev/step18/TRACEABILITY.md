# Step 18 Traceability – SDG Log Reader

## Requirement mapping

| Requirement ID | Acceptance IDs | Plan step | Evidence type | Status |
|---|---|---|---|---|
| REQ-018-001 | AC-018-003 | S01, S05 | E-018-001: read-only path and safety review | PLANNED |
| REQ-018-002 | AC-018-002, AC-018-004, AC-018-007 | S01, S02, S06 | E-018-002: sanitized schema and parser fixtures | PLANNED |
| REQ-018-003 | AC-018-004, AC-018-005 | S02, S06 | E-018-003: normalized contract tests | PLANNED |
| REQ-018-004 | AC-018-005 | S01, S02, S06 | E-018-004: timestamp and provenance tests | PLANNED |
| REQ-018-005 | AC-018-006, AC-018-007 | S03, S06 | E-018-005: restart/checkpoint/dedup tests | PLANNED |
| REQ-018-006 | AC-018-008, AC-018-009, AC-018-010, AC-018-011 | S04, S06 | E-018-006: source-priority and fallback tests | PLANNED |
| REQ-018-007 | AC-018-012 | S05, S06 | E-018-007: diagnostics and sanitized logging review | PLANNED |
| REQ-018-008 | AC-018-013, AC-018-014 | S04, S06 | E-018-008: scheduler-isolation tests | PLANNED |
| NFR-018-001 | AC-018-003 | S01, S05 | E-018-009: cross-platform path tests | PLANNED |
| NFR-018-002 | AC-018-004, AC-018-008 | S02, S04, S06 | E-018-010: existing consumer and FTE regression tests | PLANNED |
| NFR-018-003 | AC-018-006 | S03, S06 | E-018-011: bounded incremental-scan test | PLANNED |
| NFR-018-004 | AC-018-014, AC-018-015 | S06 | E-018-012: sanitized fixture and validation review | PLANNED |
| NFR-018-005 | AC-018-012, AC-018-013 | S05, S06 | E-018-013: structured logging review | PLANNED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-018-001 | REQ-018-001, REQ-018-006 | E-018-001, E-018-006 | PLANNED |
| AC-018-002 | REQ-018-002 | E-018-002 | PLANNED |
| AC-018-003 | REQ-018-001, NFR-018-001 | E-018-001, E-018-009 | PLANNED |
| AC-018-004 | REQ-018-002, REQ-018-003, NFR-018-002 | E-018-002, E-018-003, E-018-010 | PLANNED |
| AC-018-005 | REQ-018-004 | E-018-004 | PLANNED |
| AC-018-006 | REQ-018-005, NFR-018-003 | E-018-005, E-018-011 | PLANNED |
| AC-018-007 | REQ-018-002, REQ-018-005 | E-018-002, E-018-005 | PLANNED |
| AC-018-008 | REQ-018-006, NFR-018-002 | E-018-006, E-018-010 | PLANNED |
| AC-018-009 | REQ-018-006 | E-018-006 | PLANNED |
| AC-018-010 | REQ-018-006 | E-018-006 | PLANNED |
| AC-018-011 | REQ-018-006 | E-018-006 | PLANNED |
| AC-018-012 | REQ-018-007, NFR-018-005 | E-018-007, E-018-013 | PLANNED |
| AC-018-013 | REQ-018-008, NFR-018-005 | E-018-008, E-018-013 | PLANNED |
| AC-018-014 | REQ-018-003, REQ-018-005, REQ-018-008, NFR-018-004 | E-018-003, E-018-005, E-018-008, E-018-012 | PLANNED |
| AC-018-015 | NFR-018-004 | E-018-012 | PLANNED |
| AC-018-016 | REQ-018-001, REQ-018-006 | E-018-001, E-018-006 | PLANNED |

## Step plan mapping

| Step ID | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Confirm schema and read-only access | none | PLANNED |
| S02 | Define normalized record contract | S01 | PLANNED |
| S03 | Define incremental state and deduplication | S01, S02 | PLANNED |
| S04 | Define source priority and FTE fallback | S02, S03 | PLANNED |
| S05 | Define configuration and diagnostics | S02, S04 | PLANNED |
| S06 | Implement focused tests and validation evidence | S01-S05 | PLANNED |
| S07 | Gate A handoff | S01-S06 | PLANNED |

## Evidence notes

- Current evidence confirms the UNC root is readable and contains the observed
  candidate directories and DBF files; it does not yet establish the DBF field
  schema.
- Evidence is intentionally limited to read-only access and planning. No
  production data, credentials, or runtime artifacts are committed.
