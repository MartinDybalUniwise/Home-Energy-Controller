# Plan

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `CANCELLED`.

## Goal

Replace the GoodWe environment-variable gate with normal product read access and
add a minimal Config UI authorization flow: status display, `Ověřit` button, and
`Autorizuji` button. The workflow stays deliberately small while preserving the
existing artifact-based write authorization.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Remove `HEC_GOODWE_PHYSICAL_IO` from normal GoodWe product flow | PLANNED |
| S02 | Add read-only GoodWe verification API and evidence model | PLANNED |
| S03 | Add explicit GoodWe authorization API using the existing artifact service | PLANNED |
| S04 | Add simple Config UI controls and localized status text | PLANNED |
| S05 | Add regression and browser coverage | PLANNED |
| S06 | Run safe validation and record evidence | PLANNED |

## Detailed implementation strategy

### S01 - Runtime gate cleanup

Objectives:
- Let normal product GoodWe reading depend on `goodwe.enabled` and configured
	connection values instead of `HEC_GOODWE_PHYSICAL_IO`.
- Keep tests fail-closed against accidental real hardware.

Implementation:
- Remove environment-variable promotion from the production reader registry.
- Simplify `GoodWeManager` so `physical_io` is not a required product gate for
	normal operation.
- Keep `PYTEST_CURRENT_TEST` protection and fake-client test paths.

Risks:
- If the test guard is weakened, unit tests could attempt LAN hardware access.

### S02 - Read-only verification API

Objectives:
- Provide a small server-side action that checks the configured GoodWe device
	without performing writes.
- Return status suitable for both `/api/status` and Config UI.

Implementation:
- Add a dedicated API path such as `POST /api/goodwe/authorization/verify`.
- Reuse `GoodWeManager.read_runtime()` or a narrow equivalent to collect online,
	host, model, firmware, timestamp, and an evidence ID.
- Store only non-secret verification evidence needed to enable the next UI step.

Risks:
- Verification must not become a write path and must not expose credentials.

### S03 - Explicit authorization API

Objectives:
- Let the user create the existing authorization artifact from the Config UI by
	pressing `Autorizuji` after successful verification.
- Keep authorization separate from generic config save.

Implementation:
- Add a dedicated API path such as `POST /api/goodwe/authorization/approve`.
- Require successful current-host verification evidence before calling
	`authorize(config, device_host=..., evidence_id=..., approved_by=..., verification=...)`.
- Continue rejecting direct config writes to `hardware_authorization` and
	`hardware_verified`.

Risks:
- The approval must bind to the currently configured host so stale evidence for
	another device cannot authorize the wrong inverter.

### S04 - Config UI

Objectives:
- Keep the UI simple: status, `Ověřit`, then `Autorizuji`.
- Avoid adding a complex wizard or enterprise approval model.

Implementation:
- Extend the GoodWe settings section with authorization status and verification
	status.
- Add one verification button and one `Autorizuji` button.
- Disable `Autorizuji` until verification for the current host succeeds.
- Add Czech and English i18n keys.

Risks:
- A disabled button without explanation may look broken; show concise state text.

### S05 - Tests

Objectives:
- Cover the behavior without live hardware.
- Verify the safety gates remain intact.

Implementation:
- Add/adjust unit tests for GoodWe read without `HEC_GOODWE_PHYSICAL_IO`.
- Add API tests for verification success/failure, authorization success, stale
	host refusal, and direct config-write refusal.
- Add focused Playwright coverage for the Config UI status/buttons.

Risks:
- Mock-only tests could miss real GoodWe library import behavior; keep the live
	hardware runbook as manual evidence, not automated validation.

### S06 - Validation and evidence

Objectives:
- Validate code and UI while preserving local safety invariants.
- Record commands and results in Step24.

Implementation:
- Run Ruff, focused unit/API tests, safe preview, and focused Playwright tests.
- Do not enable controller, TNG writes, or GoodWe writes during automated checks.
- Record any optional read-only production observation separately and only if
	explicitly approved.

Risks:
- Preview still intentionally keeps `goodwe.enabled=false`; this step changes
	normal product runtime, not the safe preview invariant.
