# Step 17 plan

## Goal

Prepare a complete and validator-ready Step17 documentation package for a
repository/SDD review step, while keeping the step in the `PLANNED` state and
preserving the rule that future implementation or repo-behavior changes require
separate approval.

## Work packages

| ID | Work package | Main output | Depends on | Status |
|---|---|---|---|---|
| S01 | Confirm the Step17 scope against repository SDD rules and safety boundaries | Request and requirement scope | None | PLANNED |
| S02 | Define the planning contract for the repository/SDD review step | `REQUEST.md`, `REQUIREMENT.md` | S01 | PLANNED |
| S03 | Define execution order, readiness rules, and validation commands | `PLAN.md`, `ACCEPTANCE_CRITERIA.md` | S02 | PLANNED |
| S04 | Define canonical traceability and manifest metadata | `TRACEABILITY.md`, `STEP.json` | S02, S03 | PLANNED |
| S05 | Align repository indexing and planning-only result reporting | `dev/README.md`, `RESULT.md` | S04 | PLANNED |
| S06 | Re-run validator checks and hand off a ready-not-done planning package | Structural and ready validation output | S03, S04, S05 | PLANNED |

## Execution boundaries

- This step is documentation-only and must not modify application code.
- Root production prototypes remain frozen.
- No physical-device write path is enabled or exercised.
- Any future implementation spawned from this step must obtain its own approval
  before code changes.

## Validation commands

```text
python3 dev/sdd/tools/validate_step.py --phase structural --step dev/step17
python3 dev/sdd/tools/validate_step.py --phase ready --step dev/step17
```

## Handoff

When the planning package is complete, Step17 should be `PLANNED` with
`readiness=YES`. That state means the documentation is ready for future work,
not that the step is completed.
