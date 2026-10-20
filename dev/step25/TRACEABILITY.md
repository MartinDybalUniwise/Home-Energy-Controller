# Traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| REQ-025-001 | AC-025-001, AC-025-002 | S01 | E-025-001 current runtime inventory | PLANNED |
| REQ-025-002 | AC-025-001, AC-025-003 | S01 | E-025-002 reader matrix | PLANNED |
| REQ-025-003 | AC-025-004, AC-025-005, AC-025-009, AC-025-010, AC-025-011 | S03, S07 | E-025-003 target boundary review; E-025-009 outage isolation test; E-025-010 supervisor/failure tests; E-025-011 Windows/Linux/Pi validation; E-025-012 consumer contract tests | PLANNED |
| REQ-025-004 | AC-025-006 | S02 | E-025-004 telemetry contract tests | PLANNED |
| REQ-025-005 | AC-025-006 | S02 | E-025-005 time/quality edge-case tests | PLANNED |
| REQ-025-006 | AC-025-008 | S04, S05, S06 | E-025-006 migration and rollback evidence | PLANNED |
| REQ-025-007 | AC-025-007 | S08 | E-025-007 read-only output contract tests | PLANNED |
| REQ-025-008 | AC-025-006, AC-025-007, AC-025-008 | S08, S09 | E-025-008 retention and restore measurement; E-025-007 read-only output contract tests; E-025-006 migration and rollback evidence | PLANNED |

## Non-functional traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| NFR-025-001 | AC-025-004, AC-025-005 | S03, S06 | E-025-009 outage isolation test | PLANNED |
| NFR-025-002 | AC-025-008 | S04-S06 | E-025-006 staged cutover evidence | PLANNED |
| NFR-025-003 | AC-025-001, AC-025-008 | S03-S05 | E-025-010 supervisor/failure tests | PLANNED |
| NFR-025-004 | AC-025-005 | S03-S09 | E-025-011 Windows/Linux/Pi validation | PLANNED |
| NFR-025-005 | AC-025-004, AC-025-005 | S06 | E-025-012 consumer contract tests | PLANNED |
