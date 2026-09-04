# Step 11 acceptance criteria

## Repository and safety

- [x] `dev/step11/` is indexed and contains requirement, plan, acceptance,
  workflow, local development, testing, PR, and result documents.
- [x] Root frozen prototypes are unchanged.
- [x] Existing `dev/hec/` architecture and CI ruff/pytest checks are retained.
- [x] New runtime paths and Playwright artifacts are ignored.
- [x] No new credentials or secrets are present.

## Copilot and SDD

- [x] Repository instructions reference `CLAUDE.md`, `dev/README.md`,
  Step11, and HEC API/deployment documentation.
- [x] Planner, developer, and reviewer roles have explicit boundaries.
- [x] Reusable prompts cover feature, fix, human feedback, and PR completion.
- [x] LARGE changes require requirement, plan, acceptance criteria, and human
  approval before implementation.

## Local development

- [x] A single existing HEC codebase starts with a safe profile on
  `127.0.0.1:8181`.
- [x] The profile uses isolated `.runtime` data/log/history paths.
- [x] Controller, TNG writes, GoodWe, and other physical readers are disabled.
- [x] VS Code tasks and a debugger launch the same safe profile.

## Tests

- [x] Existing pytest and ruff commands remain the baseline.
- [ ] Full pytest suite passes; blocked by the pre-existing Windows Python 3.14
  `test_paths_are_platform_neutral` failure recorded in `RESULT.md`.
- [x] A runtime smoke checks HTTP health and safety flags.
- [x] Python Playwright tests cover dashboard shell, Settings navigation,
  Czech/English catalog loading, desktop, wall/full-HD, and mobile viewports.
- [x] Playwright failure output is ignored and configured for screenshot/trace.
- [x] Full validation fails fast and always attempts preview cleanup.

## Human and PR gates

- [x] Human testing is explicitly separate from automated PASS results.
- [x] Feedback is classified SMALL or LARGE; LARGE feedback returns to planning.
- [x] PR evidence records planned work, deviations, commands, safety, human
  test status, and known limitations.
- [ ] Human preview test performed and approved (not performed by this agent).
