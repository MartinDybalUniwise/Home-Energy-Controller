# Home Energy Controller repository instructions

Read `CLAUDE.md` before changing anything. Also use `dev/README.md`,
`dev/step11/`, `dev/hec/docs/API.md`, and `dev/hec/docs/DEPLOYMENT.md` as the
repository sources of truth. The root scripts are frozen production prototypes.

## Scope and safety

- Preserve the existing `dev/hec/` architecture; do not refactor unrelated
  code.
- Never commit `.env`, credentials, tokens, `connect.json` values, production
  data, logs, runtime caches, or Playwright artifacts.
- Never perform a physical-device write. Keep `controller.enabled=false` and
  `tng.write_enabled=false` in local development; never bypass the TNG
  confirmation cycle or its 900-second minimum interval.
- Preserve safe mode, i18n keys, atomic storage writes, ISO timestamps, and
  Windows/Linux/Raspberry Pi portability.

## Change protocol

Classify the request before editing.

**SMALL CHANGE:** text, CSS/layout, a contained validation, test, or local bug
fix with no architectural, API, storage, controller, or security impact. Make
the minimum change and run relevant tests.

**LARGE CHANGE:** a new module/data source, API/storage contract, controller or
write behavior, security mechanism, architecture, or substantial UI redesign.
First create/update `REQUIREMENT.md`, `PLAN.md`, and
`ACCEPTANCE_CRITERIA.md`, split work into `S01...SNN`, identify risks and
tests, and stop for human approval. Do not implement before approval.

For every implementation, run ruff and relevant pytest tests; run local
Playwright for UI changes. Use the Step11 safe preview for runtime checks.
Never label automated checks as a human test.

## Completion report

Finish with planned vs implemented work, deviations, exact test commands and
results, safety status, and known limitations. Update related documentation
only when behavior or workflow changes. A PR requires explicit user
instruction; do not push to `main`.
