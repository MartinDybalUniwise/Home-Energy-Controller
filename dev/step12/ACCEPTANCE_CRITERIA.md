# Step 12 acceptance criteria

## Security and repository hygiene

- [ ] Any tracked `connect.json` and other secret-bearing files are removed from the current repository state and the secrets are rotated.
- [ ] `.gitignore` explicitly blocks `connect.json`, `.env`, `data/`, `logs/`, `history/`, `archive/`, runtime artifacts, and Playwright outputs.
- [ ] Production runtime data and logs are no longer tracked; test fixtures are isolated under a fixture path.
- [ ] A repo hygiene validator rejects forbidden tracked files and obvious secret patterns.
- [ ] Any history cleanup follows credential rotation and is treated as a separate controlled security task.

## SDD platform and workflow

- [ ] A canonical `dev/sdd/` platform exists for reusable SDD tooling and templates.
- [ ] `dev/step11/` remains historical evidence and is no longer the runtime dependency for future steps.
- [ ] Canonical templates exist for REQUEST, REQUIREMENT, PLAN, ACCEPTANCE_CRITERIA, TRACEABILITY, and RESULT.
- [ ] Every LARGE step has a `STEP.json` manifest with status and gate fields.
- [ ] A `validate_step.py` validator enforces planning and completion requirements and returns non-zero on failure.
- [ ] A `new_step.py` generator creates the next step with the standard structure and keeps step numbering correct.

## Gate enforcement and traceability

- [ ] Gate A is machine-readable and required before implementation begins.
- [ ] Gate B and Gate C are explicitly evidenced and not treated as optional text-only statements.
- [ ] Every requirement has at least one acceptance criterion and traceability link.
- [ ] Traceability is complete across requirement → step → test/evidence → result.
- [ ] `RESULT.md` and `TRACEABILITY.md` reflect actual execution status, not aspirational intent.

## Preview safety and mode split

- [ ] A mock preview mode exists and is deterministic, isolated, and safe for CI use.
- [ ] A LAN read-only preview mode exists for local validation, but it is fail-closed and never allows device writes.
- [ ] The app refuses to start when dangerous write flags are detected.
- [ ] `controller.enabled=false` and `tng.write_enabled=false` remain required in all preview and local test modes.
- [ ] GoodWe write capability is treated as disabled by default and is not expanded in this step.
- [ ] The safety validation is executed before preview start.

## CI and developer workflow

- [ ] The SDD validation job runs in CI and fails on invalid repository or workflow state.
- [ ] Ruff and pytest remain baseline checks for Python workflow scripts.
- [ ] Mock preview / smoke tests are accepted in CI; LAN read-only validation remains local-only unless explicitly approved.
- [ ] VS Code tasks and debug profiles use the reusable SDD tooling path instead of the historical Step11 location.
- [ ] Prompt metadata and agent boundaries are explicit for Planner / Developer / Reviewer.

## Python and environment

- [ ] Supported Python versions are explicitly documented and aligned with the CI matrix.
- [ ] Platform-neutral tests are fixed so the local Windows developer flow is not blocked by false failures.
- [ ] Full validation commands are green on the standard developer environment used for HEC.

## Dogfood and final readiness

- [ ] Step 12 itself is executed using the workflow it introduces.
- [ ] The step is reviewed and ready only after evidence, traceability, and gate checks are complete.
- [ ] `readiness` is `YES` only after all mandatory gates and ACs are satisfied.
