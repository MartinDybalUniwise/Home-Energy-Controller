# Step 14 traceability

## Requirement mapping

| Requirement ID | Acceptance IDs | Plan step | Evidence type | Status |
|---|---|---|---|---|
| REQ-014-001 | AC-014-001, AC-014-006 | S01 | Playwright output and CI run | PLANNED |
| REQ-014-002 | AC-014-002, AC-014-003 | S02 | validator tests and phase output | PLANNED |
| REQ-014-003 | AC-014-004 | S03 | generator test and schema output | PLANNED |
| REQ-014-004 | AC-014-005, AC-014-006 | S04 | changed-step validator and CI run | PLANNED |
| REQ-014-005 | AC-014-007, AC-014-020 | S05 | GitHub settings and controlled PR evidence | PLANNED |
| REQ-014-006 | AC-014-008, AC-014-009 | S06 | lifecycle documentation and validator tests | PLANNED |
| REQ-014-007 | AC-014-010 | S07 | VS Code metadata and role review | PLANNED |
| REQ-014-008 | AC-014-011, AC-014-020 | S08 | renderer refusal tests and PR body | PLANNED |
| REQ-014-009 | AC-014-012, AC-014-020 | S09 | validation JSON and SHA comparison | PLANNED |
| REQ-014-010 | AC-014-013 | S10 | README/manifest consistency test | PLANNED |
| REQ-014-011 | AC-014-014 | S11 | non-secret owner confirmation | PLANNED |
| REQ-014-012 | AC-014-015, AC-014-016, AC-014-017, AC-014-018, AC-014-019 | S12 | final validation, gates, and manifest | PLANNED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-014-001 | REQ-014-001 | isolated locale Playwright tests | PLANNED |
| AC-014-002 | REQ-014-002 | complete synthetic step DONE validation | PLANNED |
| AC-014-003 | REQ-014-002 | incomplete and Step12 negative fixtures | PLANNED |
| AC-014-004 | REQ-014-003 | `new_step.py` schema regression test | PLANNED |
| AC-014-005 | REQ-014-004 | changed-step CI failure test | PLANNED |
| AC-014-006 | REQ-014-001, REQ-014-004 | PR and main workflow runs | PLANNED |
| AC-014-007 | REQ-014-005 | branch protection and controlled PR | PLANNED |
| AC-014-008 | REQ-014-006 | lifecycle contract and manifest validation | PLANNED |
| AC-014-009 | REQ-014-006 | `NOT_REQUIRED` reason tests | PLANNED |
| AC-014-010 | REQ-014-007 | VS Code handoff metadata and reviewer scope | PLANNED |
| AC-014-011 | REQ-014-008 | guarded renderer refusal tests | PLANNED |
| AC-014-012 | REQ-014-009 | commit-bound validation evidence | PLANNED |
| AC-014-013 | REQ-014-010 | README/STEP manifest consistency test | PLANNED |
| AC-014-014 | REQ-014-011 | non-secret Step13 owner evidence | PLANNED |
| AC-014-015 | REQ-014-012 | ready validation before implementation | PLANNED |
| AC-014-016 | REQ-014-012 | full local and CI validation | PLANNED |
| AC-014-017 | REQ-014-012 | final traceability validation | PLANNED |
| AC-014-018 | REQ-014-012 | final Step14 manifest and done output | PLANNED |
| AC-014-019 | REQ-014-012 | safety and repository hygiene output | PLANNED |
| AC-014-020 | REQ-014-005, REQ-014-008, REQ-014-009 | guarded PR generation and merge evidence | PLANNED |

## Step plan mapping

| Step ID | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Deterministic locale tests | none | PLANNED |
| S02 | Phase-aware DONE validation | none | PLANNED |
| S03 | Canonical `new_step.py` manifest | S02 | PLANNED |
| S04 | Changed-step DONE validation in CI | S02, S03 | PLANNED |
| S05 | GitHub main branch protection | S04 | PLANNED |
| S06 | Gate lifecycle and `NOT_REQUIRED` semantics | S02 | PLANNED |
| S07 | Agent handoffs and reviewer contract | S06 | PLANNED |
| S08 | Generic guarded PR renderer | S02, S04 | PLANNED |
| S09 | Commit-bound validation evidence | S08 | PLANNED |
| S10 | README status synchronization | S03 | PLANNED |
| S11 | Step13 security-owner evidence | none | PLANNED |
| S12 | Step14 dogfood and final gates | S01-S11 | PLANNED |

## Evidence storage

- Final evidence belongs in Step14 documentation and ignored runtime output.
- Runtime validation and browser artifacts stay under ignored runtime folders.
- No credential values, production data, logs, or browser artifacts belong in
  the repository.
