# Step 21 Traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| REQ-021-001, REQ-021-002 | AC-021-001, AC-021-002 | S01-S03 | E-021-001 | PLANNED |
| REQ-021-003, REQ-021-007 | AC-021-003 | S02, S05 | E-021-002 | PLANNED |
| REQ-021-004, REQ-021-005 | AC-021-004, AC-021-005 | S02, S04 | E-021-003 | PLANNED |
| REQ-021-006 | AC-021-006 | S02, S04-S05 | E-021-004 | PLANNED |
| NFR-021-001, NFR-021-002, NFR-021-003 | AC-021-007 | S03-S04 | E-021-005 | PLANNED |
| safety requirements | AC-021-008, AC-021-009 | S05-S06 | E-021-006 | PLANNED |
| NFR-021-004 | AC-021-010 | S06 | E-021-007 | PLANNED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-021-001 | REQ-021-001 | E-021-001: layout discovery fixture | PLANNED |
| AC-021-002 | REQ-021-002 | E-021-001: timestamp fixtures | PLANNED |
| AC-021-003 | REQ-021-003, REQ-021-007 | E-021-002: API/UI history test | PLANNED |
| AC-021-004 | REQ-021-004 | E-021-003: checkpoint retry test | PLANNED |
| AC-021-005 | REQ-021-005 | E-021-003: idempotency/growth tests | PLANNED |
| AC-021-006 | REQ-021-006 | E-021-004: diagnostics assertions | PLANNED |
| AC-021-007 | NFR-021-001, NFR-021-002, NFR-021-003 | E-021-005: failure/portability tests | PLANNED |
| AC-021-008 | safety requirements | E-021-006: read-only runtime evidence | PLANNED |
| AC-021-009 | safety requirements | E-021-006: safety config validation | PLANNED |
| AC-021-010 | NFR-021-004 | E-021-007: validation command output | PLANNED |

## Evidence register

| Evidence | Description | Status |
|---|---|---|
| E-021-001 | SDGeco layout and timestamp fixture tests | PLANNED |
| E-021-002 | `sdg_history` API/History UI visibility | PLANNED |
| E-021-003 | Checkpoint, retry, idempotency, and growth tests | PLANNED |
| E-021-004 | Import diagnostics and checkpoint evidence | PLANNED |
| E-021-005 | Corruption, missing timestamp, and portability tests | PLANNED |
| E-021-006 | Read-only production validation and safety output | PLANNED |
| E-021-007 | Ruff, pytest, preview/Playwright, and Step validation | PLANNED |
