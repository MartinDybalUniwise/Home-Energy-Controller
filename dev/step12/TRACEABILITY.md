# Step 12 traceability

## Requirement mapping

| Requirement ID | Acceptance IDs | Plan step | Evidence type | Status |
|---|---|---|---|---|
| REQ-SDD-001 | AC-SDD-001, AC-SDD-002 | S02 | directory structure + validator output | PLANNED |
| REQ-SDD-002 | AC-SDD-003, AC-SDD-004 | S03, S04 | template files + `STEP.json` | PLANNED |
| REQ-SDD-003 | AC-GATE-001, AC-GATE-002 | S07 | validator output + CI config | PLANNED |
| REQ-SDD-004 | AC-SEC-001, AC-SEC-002 | S01, S08 | repo hygiene check | PLANNED |
| REQ-SDD-005 | AC-PREVIEW-001, AC-PREVIEW-002 | S12 | preview config + safety validation | PLANNED |
| REQ-SDD-006 | AC-CI-001, AC-CI-002 | S14 | CI workflow config | PLANNED |
| REQ-SDD-007 | AC-SAFE-001, AC-SAFE-002 | S11, S12 | safety rules + preview validation | PLANNED |
| REQ-SDD-008 | AC-GATE-003 | S09, S10 | agent role docs + prompt metadata | PLANNED |
| REQ-SDD-009 | AC-SEC-005 | S01 | history cleanup plan | PLANNED |
| REQ-SDD-010 | AC-DOGFOOD-001 | S20 | Step12 execution evidence | PLANNED |

## Acceptance mapping

| Acceptance ID | Requirement link | Test or evidence | Status |
|---|---|---|---|
| AC-SEC-001 | REQ-SDD-004 | repo hygiene validation | PLANNED |
| AC-SEC-002 | REQ-SDD-004 | secret scan + Git state check | PLANNED |
| AC-SDD-001 | REQ-SDD-001 | `dev/sdd/` structure | PLANNED |
| AC-SDD-002 | REQ-SDD-001 | Step11 historical evidence check | PLANNED |
| AC-SDD-003 | REQ-SDD-002 | template presence | PLANNED |
| AC-SDD-004 | REQ-SDD-002 | `STEP.json` schema validation | PLANNED |
| AC-GATE-001 | REQ-SDD-003 | `validate_step.py` non-zero fail output | PLANNED |
| AC-GATE-002 | REQ-SDD-003 | traceability completeness | PLANNED |
| AC-PREVIEW-001 | REQ-SDD-005 | mock preview pass | PLANNED |
| AC-PREVIEW-002 | REQ-SDD-005 | fail-closed preview guard | PLANNED |
| AC-CI-001 | REQ-SDD-006 | CI workflow definition | PLANNED |
| AC-CI-002 | REQ-SDD-006 | CI mock preview run | PLANNED |
| AC-SAFE-001 | REQ-SDD-007 | write-disabled configuration | PLANNED |
| AC-SAFE-002 | REQ-SDD-007 | no write path in preview mode | PLANNED |
| AC-GATE-003 | REQ-SDD-008 | agent and prompt boundaries | PLANNED |
| AC-DOGFOOD-001 | REQ-SDD-010 | execution of the Step12 workflow on itself | PLANNED |

## Step plan mapping

| Step ID | Purpose | Dependencies | Status |
|---|---|---|---|
| S01 | Security cleanup and repo hygiene | none | PLANNED |
| S02 | Extract `dev/sdd/` platform | S01 | PLANNED |
| S03 | Templates | S02 | PLANNED |
| S04 | Manifest | S03 | PLANNED |
| S05 | Traceability | S03, S04 | PLANNED |
| S06 | `new_step.py` | S03, S04 | PLANNED |
| S07 | `validate_step.py` | S03-S06 | PLANNED |
| S08 | `validate_repo.py` | S01 | PLANNED |
| S09 | Agent hardening | S03 | PLANNED |
| S10 | Prompt hardening | S03, S09 | PLANNED |
| S11 | Path-specific safety | S09, S10 | PLANNED |
| S12 | Preview modes | S02, S08 | PLANNED |
| S13 | Python compatibility | CI baseline | PLANNED |
| S14 | CI SDD gate | S07, S08 | PLANNED |
| S15 | GitHub main protection | S14 | PLANNED |
| S16 | DoR / DoD | S03, S07 | PLANNED |
| S17 | ADR | S02, S12 | PLANNED |
| S18 | PR renderer | S04, S05, S07, S19 | PLANNED |
| S19 | Runtime evidence | S14, S18 | PLANNED |
| S20 | Dogfood Step12 | all prior steps | PLANNED |

## Evidence storage

- Canonical evidence files live under `dev/step12/`.
- Runtime validation evidence may be stored under ignored runtime folders only.
- PR evidence is generated from the final Step manifest, traceability, and result outputs.
