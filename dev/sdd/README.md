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
2. Analyze the request and classify it as SMALL or LARGE.
3. For SMALL requests, prepare a short plan and wait for explicit human approval
   before editing application code.
4. For LARGE requests, run `python dev/sdd/tools/new_step.py` only after the
   requirement, plan, and acceptance criteria are prepared and Gate A is
   approved.
5. Validate with `python dev/sdd/tools/validate_step.py`.
6. Run repository hygiene checks and preview validation.
7. Record execution evidence before marking a step done.

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
