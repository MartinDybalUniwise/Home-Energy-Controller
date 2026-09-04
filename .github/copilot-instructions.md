# Home Energy Controller repository instructions

Read `CLAUDE.md` before changing anything. Also use `dev/README.md`,
`dev/sdd/`, `dev/hec/docs/API.md`, and `dev/hec/docs/DEPLOYMENT.md` as the
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

A new user development request is NEVER implicit authorization to implement it.
The first response to every new development request must be analysis/planning
only. Do not edit application code before explicit human approval. This rule
applies to SMALL and LARGE changes.

Classify the request before editing.

**SMALL CHANGE:** text, CSS/layout, a contained validation, test, or local bug
fix with no architectural, API, storage, controller, or security impact. Do not
start implementation immediately. First analyze the relevant repository parts,
classify the request as `SMALL`, produce a short chat plan (what changes,
which files are likely affected, tests to run, and risk), stop, and wait for
explicit human approval. Allowed approval phrases include `APPROVED`,
`SCHVALUJI`, `IMPLEMENT`, or `POKRAČUJ`. Without explicit approval, follow:
`NO CODE EDIT`, `NO TEST MODIFICATION`, and `NO TERMINAL EXECUTION THAT CHANGES REPOSITORY STATE`.

After human approval, the SMALL workflow can continue with implementation,
relevant unit/integration tests, Playwright for UI, a brief summary, and PR only
on explicit request.

**LARGE CHANGE:** a new module/data source, API/storage contract, controller or
write behavior, security mechanism, architecture, or substantial UI redesign.
First create/update `REQUIREMENT.md`, `PLAN.md`, and
`ACCEPTANCE_CRITERIA.md`, split work into `S01...SNN`, identify risks and
tests, and stop for human approval at Gate A. Before Gate A there must be
`NO APPLICATION CODE CHANGES`.

For every implementation, run ruff and relevant pytest tests; run local
Playwright for UI changes. Use the canonical `dev/sdd/tools/preview.py` safe
preview for runtime checks.
Never label automated checks as a human test.

## Completion report

Finish with planned vs implemented work, deviations, exact test commands and
results, safety status, and known limitations. Update related documentation
only when behavior or workflow changes. A PR requires explicit user
instruction; do not push to `main`.
