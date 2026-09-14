# Step 20 Traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| REQ-020-001, REQ-020-002 | AC-020-001, AC-020-002 | S01-S03 | E-020-001 | VERIFIED |
| REQ-020-003, REQ-020-004 | AC-020-003, AC-020-004 | S01, S03 | E-020-002 | VERIFIED |
| REQ-020-005, REQ-020-006 | AC-020-005, AC-020-006 | S01, S03-S04 | E-020-003 | VERIFIED |
| REQ-020-007, REQ-020-008, REQ-020-009 | AC-020-007, AC-020-008, AC-020-009 | S01, S04 | E-020-004 | VERIFIED |
| REQ-020-010, NFR-020-001, NFR-020-003, NFR-020-004 | AC-020-010, AC-020-011 | S05-S06 | E-020-005 | VERIFIED |
| NFR-020-002, safety requirements | AC-020-012 | S03, S06 | E-020-006 | VERIFIED |
| validation requirements | AC-020-013 | S06 | E-020-007 | PARTIAL: unrelated Step 16 non-E2E failure |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-020-001 | REQ-020-010 | E-020-001: route/navigation E2E | VERIFIED |
| AC-020-002 | REQ-020-001, REQ-020-002 | E-020-001: status/controller E2E | VERIFIED |
| AC-020-003 | REQ-020-003 | E-020-002: reader state render | VERIFIED |
| AC-020-004 | REQ-020-004 | E-020-002: writer gate render | VERIFIED |
| AC-020-005 | REQ-020-005 | E-020-003: heating/boiler render | VERIFIED |
| AC-020-006 | REQ-020-006 | E-020-003: Shelly/appliance render | VERIFIED |
| AC-020-007 | REQ-020-007 | E-020-003: energy status render | VERIFIED |
| AC-020-008 | REQ-020-008 | E-020-004: 36-hour outlook fallback | VERIFIED |
| AC-020-009 | REQ-020-009 | E-020-004: timestamp labels | VERIFIED |
| AC-020-010 | NFR-020-003 | E-020-005: partial/error state render | VERIFIED |
| AC-020-011 | REQ-020-010, NFR-020-001, NFR-020-004 | E-020-005: responsive/i18n/accessibility E2E | VERIFIED |
| AC-020-012 | safety requirements | E-020-006: preview safety configuration | VERIFIED |
| AC-020-013 | validation requirements | E-020-007: lint, pytest, Playwright, SDD validation | PARTIAL |

## Evidence register

| Evidence | Description | Status |
|---|---|---|
| E-020-001 | Route and controller/planner status browser checks | VERIFIED: Playwright 2 passed |
| E-020-002 | Reader and writer health/gate browser checks | VERIFIED: Playwright 2 passed |
| E-020-003 | Heating, boiler, Shelly, and energy fixture checks | VERIFIED: Playwright 2 passed |
| E-020-004 | Today/tomorrow outlook and timestamp checks | VERIFIED: Playwright 2 passed |
| E-020-005 | Responsive, i18n, accessibility, and fallback checks | VERIFIED: full E2E 25 passed |
| E-020-006 | Preview safety output showing writes disabled | VERIFIED: preview configuration unchanged |
| E-020-007 | Ruff, pytest, Playwright, and Step validation output | PARTIAL: unrelated Step 16 pytest failure |
