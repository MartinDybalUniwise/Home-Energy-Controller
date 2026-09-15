# Traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| REQ-023-001, REQ-023-002 | AC-023-001, AC-023-002 | S01, S03, S04 | E-023-001: browser request/render regression | PLANNED |
| REQ-023-002, REQ-023-003 | AC-023-003, AC-023-004 | S01, S03, S04 | E-023-002: Prediction payload/error-state regression | PLANNED |
| REQ-023-004 | AC-023-005 | S04 | E-023-003: SDG History compatibility regression | PLANNED |
| REQ-023-005 | AC-023-002, AC-023-004 | S01, S03, S04 | E-023-004: status latency and no-console-error evidence | PLANNED |
| REQ-023-003, REQ-023-005 | AC-023-006, AC-023-007, AC-023-008, AC-023-009 | S02, S05, S06 | E-023-005: validation and owner review evidence | PLANNED |

## Evidence definitions

- E-023-001: Production-shaped browser trace proves page render is not blocked
	by the global status request.
- E-023-002: Valid `/api/prediction` payload renders `Výhled`; missing and
	delayed payload states remain explicit.
- E-023-003: Existing `sdg_history` API/History UI continues to render.
- E-023-004: Repeated status latency and browser console/pageerror checks.
- E-023-005: Exact validation commands, safety output, and owner review.
