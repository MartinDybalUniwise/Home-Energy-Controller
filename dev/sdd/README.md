# SDD platform

This directory holds the reusable process and safety tools for Home Energy Controller development.

The purpose is to make step creation, validation, and evidence generation consistent across the repository without changing `dev/hec/` product code.

## Safety invariants

- `controller.enabled=false` in local and preview development
- `tng.write_enabled=false` in local and preview development
- `goodwe.enabled` remains disabled in preview unless a future explicit feature is approved
- no physical write path is enabled by default
- CI validation must be deterministic and fail-closed

## Included tooling

- `new_step.py` creates the next numbered step from templates
- `validate_step.py` checks that a step is structurally complete and traceable
- `validate_repo.py` checks repo hygiene and secret exposure risks
- `preview.py` handles mock and LAN read-only preview startup/safety validation
- `full_validation.py` runs the repository validation workflow

## Workflow

1. Choose the next step number.
2. Analyze and classify the request as SMALL or LARGE.
3. For SMALL requests:
   - prepare a chat plan,
   - wait for explicit human approval,
   - only then implement.
4. For LARGE requests:
   - create the step package BEFORE Gate A using:
     `python dev/sdd/tools/new_step.py`
   - complete REQUEST, REQUIREMENT, PLAN, ACCEPTANCE_CRITERIA,
     TRACEABILITY, STEP.json and RESULT,
   - run structural and ready validation,
   - leave Gate A as PENDING,
   - STOP and request human approval.
5. Gate A is approval of the completed planning package.
6. Only after explicit human approval:
   - set gate_a.status = APPROVED,
   - implementation may begin.
7. Developer implements only the approved scope.
8. Developer runs automated validation and stops before Human Gate.
9. Reviewer verifies implementation against requirements,
   acceptance criteria, traceability and safety.
10. Human Gate is required before DONE.
11. Only after all required gates and evidence pass may the step be marked DONE.

Changed-step CI validation follows the manifest lifecycle: planned or
in-progress steps must pass the `ready` phase, while steps marked `DONE` must
pass the stricter `done` phase.

## Definition of ready

A new request never implies implementation. Before any application code edit,
a human must approve the plan. SMALL changes require a short chat plan and
explicit approval; LARGE steps require their request, requirement, plan,
acceptance criteria, traceability matrix, and `STEP.json` manifest. The plan
must identify substeps, risks, validation, and an explicit approval gate.

## Definition of done

A completed step has passing repository and step validation, evidence for each
mandatory acceptance criterion, a filled `RESULT.md`, and no unresolved
blockers. Automated checks never substitute for a human hardware test.

## UI validation rule

For UI steps, automated validation is valid only when real browser E2E tests
actually execute against the running preview.

A skipped E2E suite is NOT PASS.

A UI step cannot proceed to Reviewer or Human Gate when:
- the page remains in a loading state,
- browser console contains application JavaScript errors,
- required controls are not interactable,
- Playwright reports failures or the suite is skipped.