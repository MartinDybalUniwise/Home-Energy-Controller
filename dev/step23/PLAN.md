# Step23 Plan - Responsive page startup and Prediction rendering

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `CANCELLED`.

## Goal

Remove the measured frontend startup bottleneck and repair the Prediction route
without changing SDG import semantics or forecast calculations.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Reproduce production request ordering, status latency, and Prediction console error | DONE |
| S02 | Define page-loading, diagnostic, timeout, and partial-state contracts | DONE |
| S03 | Implement the smallest frontend/status-boundary correction | DONE |
| S04 | Add Prediction, History, and slow-status regression coverage | DONE |
| S05 | Run safe local validation and authorized read-only production observation | PLANNED |
| S06 | Record evidence and prepare Reviewer/Human Gate handoff | IN_PROGRESS |

## Detailed implementation strategy

### S01 - Reproduce and classify

Objectives:
- Capture browser request order and console errors for `#/prediction`.
- Measure `/api/status`, `/api/prediction`, `/api/weather`, and `/api/prices`.
- Confirm whether SDG path discovery/diagnostics blocks status responses.

Implementation:
- Use browser DevTools/Playwright and read-only API requests.
- Preserve the current user change in `preview.mock.json`; do not normalize it
	during planning.

Risks:
- Production timing may vary; record repeated observations and distinguish a
	deterministic failure from transient network latency.

### S02 - Loading and error contract

Objectives:
- Define which data is critical for each route and which diagnostics are
	optional.
- Define visible stale/partial/error labels and bounded waiting behavior.

Implementation:
- Reuse existing i18n/status semantics and API payloads.
- Do not invent forecast values or mark blocked diagnostics healthy.

Risks:
- A faster page must not suppress a safety-relevant controller or writer fault.

### S03 - Smallest correction

Objectives:
- Remove the global status request from the critical path where it blocks page
	rendering, or make its blocking boundary bounded and explicit.
- Repair the confirmed `formatCurrency is not defined` Prediction dependency.

Implementation:
- Prefer local frontend/module dependency fixes and isolated status handling.
- Avoid parser, predictor, storage, or device-control refactors.

Risks:
- A module fix may expose additional stale browser-cache/versioning issues;
	validate served asset versions and hard reload behavior.

### S04 - Regression coverage

Objectives:
- Assert valid prediction payload renders forecast cards and no pageerror.
- Assert a delayed status response does not keep Prediction permanently loading.
- Assert History `sdg_history` still renders and Control & Plan retains truthful
	status/error labels.

Implementation:
- Add focused Playwright/API tests with controlled delayed responses and real
	fixture payloads.

Risks:
- Tests that only use empty fixtures may miss the production-shaped payload
	mismatch; include the observed two-day prediction shape.

### S05 - Validation

Objectives:
- Run focused tests, Ruff, relevant pytest, safe preview, and browser checks.
- Perform only authorized read-only production observation if required.

Implementation:
- Keep all write gates disabled; do not restart, install, deploy, or edit the
	production host.

Risks:
- Network/share access may remain unavailable; record it as evidence gap rather
	than fabricating a pass.

### S06 - Handoff

Objectives:
- Update traceability/result evidence with actual commands and observations.
- Leave Gate B/C pending until human review of the corrected pages.

Implementation:
- Step21 remains separate for SDG import semantics; Step23 consumes its data.
