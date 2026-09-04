# Step 13 traceability

## Requirement mapping

| Requirement | Acceptance | Sxx | Evidence | Status |
|---|---|---|---|---|
| REQ-013-001 | AC-013-001 | S01 | E-013-001 | PLANNED |
| REQ-013-002 | AC-013-002, AC-013-003 | S02 | E-013-002 | PLANNED |
| REQ-013-003 | AC-013-004 | S03 | E-013-003 | PLANNED |
| REQ-013-004 | AC-013-005 | S04 | E-013-004 | PLANNED |
| REQ-013-005 | AC-013-006 | S06 | E-013-005 | PLANNED |
| REQ-013-006 | AC-013-008 | S07, S09 | E-013-006 | PLANNED |
| REQ-013-007 | AC-013-009 | S10, S11 | E-013-007 | PLANNED |
| REQ-013-008 | AC-013-010 | S12 | E-013-008 | PLANNED |
| REQ-013-009 | AC-013-011 | S13 | E-013-009 | PLANNED |
| REQ-013-010 | AC-013-012 | S14 | E-013-010 | PLANNED |
| REQ-013-011 | AC-013-013, AC-013-014 | S15 | E-013-011 | PLANNED |

## Acceptance mapping

| Acceptance | Evidence/test | Status |
|---|---|---|
| AC-013-001 | Schema validation test | PLANNED |
| AC-013-002 | Ready-phase validator tests | PLANNED |
| AC-013-003 | Done-phase validator tests | PLANNED |
| AC-013-004 | Step12 negative regression test | PLANNED |
| AC-013-005 | `new_step.py` focused tests | PLANNED |
| AC-013-006 | Repository reference scan | PLANNED |
| AC-013-007 | Instruction discovery and safety scan | PLANNED |
| AC-013-008 | Agent/prompt metadata review | PLANNED |
| AC-013-009 | Full validation and Playwright result | PLANNED |
| AC-013-010 | PR renderer test | PLANNED |
| AC-013-011 | CI and GitHub branch protection evidence | PLANNED |
| AC-013-012 | Owner security action evidence | PLANNED |
| AC-013-013 | Human Gate B/C evidence and done validation | PLANNED |
| AC-013-014 | Safety preflight and repo hygiene evidence | PLANNED |

## Step plan mapping

| Sxx | Output | Requirement(s) | Status |
|---|---|---|---|
| S01-S15 | See PLAN.md detailed strategy | REQ-013-001 through REQ-013-011 | PLANNED |

No requirement or acceptance criterion is intentionally orphaned. A DONE status requires every mandatory row above to be `PASS` with evidence.
