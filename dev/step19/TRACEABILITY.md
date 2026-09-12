# Step 19 Traceability

| Requirement | Acceptance | Plan | Planned evidence | Status |
|---|---|---|---|---|
| REQ-019-001 | AC-019-001, AC-019-014 | S01, S07 | E-019-001 browser bounds; E-019-010 human review | PLANNED |
| REQ-019-002 | AC-019-002, AC-019-011 | S02, S06 | E-019-002 sidebar geometry/routes/input | PLANNED |
| REQ-019-003 | AC-019-003 | S03 | E-019-003 header bounds/content | PLANNED |
| REQ-019-004 | AC-019-004 | S03 | E-019-004 recommendation composition | PLANNED |
| REQ-019-005 | AC-019-005 | S04 | E-019-005 KPI count/bounds/data | PLANNED |
| REQ-019-006, REQ-019-007 | AC-019-006 | S04 | E-019-006 rhythm content/bounds | PLANNED |
| REQ-019-008, REQ-019-009 | AC-019-007, AC-019-008 | S05 | E-019-007 lower grid/appliance rows | PLANNED |
| REQ-019-010 | AC-019-009 | S05 | E-019-008 chart series/controls | PLANNED |
| REQ-019-011 | AC-019-004, AC-019-006, AC-019-007 | S03-S05 | E-019-004, E-019-006, E-019-007 uniqueness checks | PLANNED |
| REQ-019-012, REQ-019-013 | AC-019-010 through AC-019-013 | S06, S07 | E-019-009 automated validation/safety | PLANNED |

## Step mapping

| Step | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Geometry baseline and assertions | None | PLANNED |
| S02 | Shared sidebar compaction | S01 | PLANNED |
| S03 | Header and recommendation consolidation | S01 | PLANNED |
| S04 | KPI and rhythm density | S03 | PLANNED |
| S05 | Two-panel lower workspace | S03, S04 | PLANNED |
| S06 | Responsive, i18n, fallback, accessibility | S02-S05 | PLANNED |
| S07 | Validation and human preview | S01-S06 | PLANNED |

## Evidence register

| Evidence | Description | Status |
|---|---|---|
| E-019-001 | 1920x1080 overflow, bounds, overlap, and visibility | PLANNED |
| E-019-002 | Sidebar dimensions, routes, focus, and touch | PLANNED |
| E-019-003 | Header dimensions and content uniqueness | PLANNED |
| E-019-004 | Recommendation dimensions and uniqueness | PLANNED |
| E-019-005 | Telemetry strip dimensions and bindings | PLANNED |
| E-019-006 | Rhythm content, dimensions, and summary | PLANNED |
| E-019-007 | Lower workspace ratio, rows, and donut removal | PLANNED |
| E-019-008 | Chart series, controls, and rendered size | PLANNED |
| E-019-009 | Ruff, pytest, Playwright, SDD/full validation, safety | PLANNED |
| E-019-010 | Human 1920x1080 visual/touch acceptance | PLANNED |