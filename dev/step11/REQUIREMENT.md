# Step 11 requirement

## Source

`HEC_Copilot_AI_First_Bootstrap_Prompt.md` and the approved Step11 plan.

## Objective

Make local HEC development repeatable in VS Code with a documented
Requirement → Plan → Approval → Development → Tests → Preview → Playwright →
Human Test → Feedback → Result → PR workflow.

## In scope

- repository-level Copilot rules and role boundaries;
- reusable prompts for feature work, fixes, human feedback, and PR finishing;
- traceable Step11 documentation;
- an isolated preview using the existing HEC configuration loader;
- safe VS Code tasks/debugging;
- local Python Playwright smoke infrastructure;
- fail-fast local validation and PR evidence hygiene.

## Out of scope

- energy business logic, forecast, finance, API contracts, or UI redesign;
- changes to root prototypes or the TNG change-gate;
- automatic controller/device writes, production deployment, or CI Playwright;
- claims that a human test was performed.

## Safety requirements

The preview must use separate runtime paths, bind to `127.0.0.1:8181`, keep
`controller.enabled=false`, `tng.write_enabled=false`, and disable physical
readers by default. Secrets, production data, logs, and browser artifacts must
remain outside the commit.

## Approval and completion

This implementation follows the approved plan in `PLAN.md`. A human must still
perform the preview test before a future PR is approved; automated checks do
not satisfy that gate.
