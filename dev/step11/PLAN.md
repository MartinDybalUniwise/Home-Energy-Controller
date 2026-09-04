# Step 11 implementation plan

**Status vocabulary:** `PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

| Step | Purpose | Status | Evidence |
|---|---|---|---|
| S01 | Index Step11 and define requirement/plan/result traceability | DONE | `dev/README.md`, Step11 documents |
| S02 | Add repository Copilot safety and SDD instructions | DONE | `.github/copilot-instructions.md` |
| S03 | Define planner/developer/reviewer roles and reusable prompts | DONE | `.github/agents/`, `.github/prompts/` |
| S04 | Add isolated read-only preview on a separate port | DONE | `config.preview.json`, `preview.py`, safety test |
| S05 | Add VS Code tasks and safe debugger profile | DONE | `.vscode/tasks.json`, `.vscode/launch.json` |
| S06 | Add local Python Playwright smoke infrastructure | DONE | `dev/hec/tests/e2e/`, `requirements-dev.txt` |
| S07 | Add test pyramid and fail-fast full validation | DONE | `TESTING_STRATEGY.md`, `full_validation.py` |
| S08 | Add PR evidence and artifact hygiene | DONE | PR template, `.gitignore`, `PR_WORKFLOW.md` |
| S09 | Run validation and record truthful evidence | DONE | `RESULT.md` |

## Approval gates

- **Gate A – Plan approval:** required before implementing a future LARGE
  change. This Step11 plan was approved before implementation.
- **Gate B – Human preview test:** required after automated validation. It is
  still `NOT PERFORMED` for this bootstrap.
- **Gate C – PR approval:** a PR is created only after an explicit user
  instruction such as `CREATE PR` or `FINISH PR`.

## Traceability

The requirement is in `REQUIREMENT.md`; acceptance is in
`ACCEPTANCE_CRITERIA.md`; process rules are in the workflow/testing/PR
documents; actual files and commands are recorded in `RESULT.md`.

## Deviations

Playwright remains local-only because the requested workflow targets a home LAN
and browser artifacts must be reviewed locally. The existing CI workflow was
left unchanged apart from no Playwright job being added.
