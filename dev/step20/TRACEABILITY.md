# Step 20 Traceability

| Requirement | Acceptance | Plan step | Evidence | Status |
|---|---|---|---|---|
| REQ-020-001, REQ-020-002 | AC-020-001, AC-020-002 | S01-S03 | E-020-001 | PLANNED |
| REQ-020-003, REQ-020-004 | AC-020-003, AC-020-004 | S01, S03 | E-020-002 | PLANNED |
| REQ-020-005, REQ-020-006 | AC-020-005, AC-020-006 | S01, S03-S04 | E-020-003 | PLANNED |
| REQ-020-007, REQ-020-008, REQ-020-009 | AC-020-007, AC-020-008, AC-020-009 | S01, S04 | E-020-004 | PLANNED |
| REQ-020-010, NFR-020-001, NFR-020-003, NFR-020-004 | AC-020-010, AC-020-011 | S05-S06 | E-020-005 | PLANNED |
| NFR-020-002, safety requirements | AC-020-012 | S03, S06 | E-020-006 | PLANNED |
| validation requirements | AC-020-013 | S06 | E-020-007 | PLANNED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-020-001 | REQ-020-010 | route/navigation E2E | PLANNED |
| AC-020-002 | REQ-020-001, REQ-020-002 | status/controller E2E | PLANNED |
| AC-020-003 | REQ-020-003 | reader state E2E | PLANNED |
| AC-020-004 | REQ-020-004 | writer gate E2E | PLANNED |
| AC-020-005 | REQ-020-005 | heating/boiler fixture E2E | PLANNED |
| AC-020-006 | REQ-020-006 | Shelly/appliance fixture E2E | PLANNED |
| AC-020-007 | REQ-020-007 | energy status fixture E2E | PLANNED |
| AC-020-008 | REQ-020-008 | 36-hour outlook E2E | PLANNED |
| AC-020-009 | REQ-020-009 | timestamp labels E2E | PLANNED |
| AC-020-010 | NFR-020-003 | partial/error state E2E | PLANNED |
| AC-020-011 | REQ-020-010, NFR-020-001, NFR-020-004 | responsive/i18n/accessibility E2E | PLANNED |
| AC-020-012 | safety requirements | E-020-006: preview safety validation | PLANNED |
| AC-020-013 | validation requirements | E-020-007: lint, pytest, Playwright, SDD validation | PLANNED |

## Evidence register

| Evidence | Description | Status |
|---|---|---|
| E-020-001 | Route and controller/planner status browser checks | PLANNED |
| E-020-002 | Reader and writer health/gate browser checks | PLANNED |
| E-020-003 | Heating, boiler, Shelly, and energy fixture checks | PLANNED |
| E-020-004 | Today/tomorrow outlook and timestamp checks | PLANNED |
| E-020-005 | Responsive, i18n, accessibility, and fallback checks | PLANNED |
| E-020-006 | Preview safety output showing writes disabled | PLANNED |
| E-020-007 | Ruff, pytest, Playwright, and Step validation output | PLANNED |
