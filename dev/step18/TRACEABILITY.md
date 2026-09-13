# Step 18 Traceability

## Requirement mapping

| Requirement ID | Acceptance IDs | Plan step | Evidence type | Status |
|---|---|---|---|---|
| REQ-018-001 | AC-018-001, AC-018-003 | S01, S02 | E-018-001: 1080p zero-waste layout verification | VERIFIED |
| REQ-018-002 | AC-018-002, AC-018-006 | S02, S03 | E-018-002: Header weather bar rendering check | VERIFIED |
| REQ-018-003 | AC-018-002, AC-018-006 | S03 | E-018-003: Hero recommendation and modal check | VERIFIED |
| REQ-018-004 | AC-018-002, AC-018-006 | S04 | E-018-004: KPI telemetry strip check | VERIFIED |
| REQ-018-005 | AC-018-002, AC-018-006 | S05 | E-018-005: 24h daily rhythm timeline check | VERIFIED |
| REQ-018-006 | AC-018-002, AC-018-006 | S06, S07 | E-018-006: Workspace, donut gauge & chart check | VERIFIED |
| REQ-018-007 | AC-018-006 | S07 | E-018-006: Bottom action bar verification | VERIFIED |
| REQ-018-008 | AC-018-006 | S02, S07 | E-018-002: Navigation and Energy Flow alignment | VERIFIED |
| REQ-018-009 | AC-018-004 | S01, S08 | E-018-007: Backend preservation and fallback check | VERIFIED |
| REQ-018-010 | AC-018-005, AC-018-007, AC-018-008, AC-018-009 | S08 | E-018-008: Playwright and E-018-009: full validation | VERIFIED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-018-001 | REQ-018-001 | E-018-001: Playwright 1920x1080 no-scroll layout test | VERIFIED |
| AC-018-002 | REQ-018-002, REQ-018-003, REQ-018-004, REQ-018-005, REQ-018-006 | E-018-002, E-018-003, E-018-004, E-018-005, E-018-006: Typography and contrast review | VERIFIED |
| AC-018-003 | REQ-018-001 | E-018-001: Touch targets >= 64px and zero-waste audit | VERIFIED |
| AC-018-004 | REQ-018-009 | E-018-007: API contract and missing data fallback tests | VERIFIED |
| AC-018-005 | REQ-018-010 | E-018-008: i18n key completeness and language toggle test | VERIFIED |
| AC-018-006 | REQ-018-002, REQ-018-003, REQ-018-004, REQ-018-005, REQ-018-006, REQ-018-007, REQ-018-008 | E-018-002, E-018-003, E-018-004, E-018-005, E-018-006: Today & Energy Flow UI inspection | VERIFIED |
| AC-018-007 | REQ-018-010 | E-018-008: Playwright multi-viewport suite execution | VERIFIED |
| AC-018-008 | REQ-018-010 | E-018-009: Full repository validation check | VERIFIED |
| AC-018-009 | REQ-018-010 | E-018-009: Gate A approval and human test sign-off | PENDING_HUMAN_GATE |

## Step plan mapping

| Step ID | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Design Tokeny & CSS základy pro Touchscreen | Žádné | COMPLETED |
| S02 | Globální Layout Shellu & Sidebar navigace | S01 | COMPLETED |
| S03 | Topbar meteo widget & Hero Doporučení | S01, S02 | COMPLETED |
| S04 | KPI lišta živé telemetrie (6 karet) | S01, S02 | COMPLETED |
| S05 | Energetický rytmus dne (24h timeline) | S01, S03 | COMPLETED |
| S06 | Doporučení spotřebičů & Donut Gauge odpočet | S01, S05 | COMPLETED |
| S07 | Multi-křivkový graf, Tok energie & Spodní lišta | S01, S06 | COMPLETED |
| S08 | i18n lokalizace (CZ/EN), Playwright testy a validace | S01–S07 | COMPLETED |

## Evidence notes

- In this planning phase, evidence items are planned verification tasks.
- No runtime execution or code modifications have been conducted yet.
