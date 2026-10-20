# Requirement

## Objective

Make GoodWe onboarding usable from the product Config UI without relying on the
operator to set `HEC_GOODWE_PHYSICAL_IO`, while preserving the existing
artifact-based authorization and GoodWe write safety gates.

## Scope

### In scope

- Remove `HEC_GOODWE_PHYSICAL_IO` from normal GoodWe product read/runtime flow.
- Add a small Config UI GoodWe authorization section with:
	- current authorization status,
	- read-only verification status/details,
	- one button to verify the configured GoodWe device,
	- one explicit `Autorizuji` button to create/update the authorization artifact.
- Add API endpoints or equivalent web actions for read-only verification and
	explicit authorization.
- Keep direct config writes to `goodwe.hardware_authorization` refused.
- Keep write authorization as an artifact in `data/goodwe_hardware_authorization.json`.
- Update tests and docs for the new flow.

### Out of scope

- Physical writes during implementation or automated validation.
- Production controller activation or GoodWe optimization rules.
- Any change to TNG write safety.
- Root prototype changes.
- Complex multi-approver, signed, or remote enterprise authorization flow.

## Functional requirements

- REQ-024-001: GoodWe read access in normal product runtime must be controlled
	by `goodwe.enabled` and connection settings, not by `HEC_GOODWE_PHYSICAL_IO`.
- REQ-024-002: Test processes must still fail closed against accidental real
	GoodWe hardware access unless an injected fake/test client is explicitly used.
- REQ-024-003: GoodWe writes must remain blocked unless all write gates pass:
	`controller.enabled`, `goodwe.enabled`, `goodwe.writer_enabled`,
	`goodwe.verify_after_write`, and `hardware_authorization.status=APPROVED`.
- REQ-024-004: Config UI must show GoodWe authorization status and the latest
	read-only verification result in the GoodWe settings area.
- REQ-024-005: Config UI must provide a read-only verification button that checks
	the configured GoodWe host and reports online/model/firmware or a clear error.
- REQ-024-006: Config UI must provide an explicit `Autorizuji` button that is
	enabled only after successful verification for the configured host.
- REQ-024-007: The authorization action must create or update
	`data/goodwe_hardware_authorization.json` through the existing authorization
	service boundary and must include device host, evidence ID, approver, and
	timestamp.
- REQ-024-008: The generic config save API must continue to reject direct
	`goodwe.hardware_authorization` or `goodwe.hardware_verified` edits.
- REQ-024-009: UI text must use i18n keys for Czech and English.
- REQ-024-010: The implementation must expose enough diagnostics for `/api/status`
	and the Config UI to distinguish `NOT_AUTHORIZED`, `INVALID`, verification
	failure, and authorized states.

## Non-functional requirements

- NFR-024-001: The authorization flow must be simple and local-admin friendly;
	no enterprise approval mechanics are required inside the HEC threat model.
- NFR-024-002: Authorization and verification failures must be visible without
	leaking secrets or connection credentials.
- NFR-024-003: The new flow must preserve Windows/Linux/Raspberry Pi portability.
- NFR-024-004: Automated tests must not require live GoodWe hardware.

## Safety requirements

- TNG write gate remains disabled.
- `controller.enabled=false` remains required in preview/local validation.
- No physical-device writes during automated validation.
- Authorization must not itself perform a GoodWe write.
- The first future physical write still requires the existing GoodWe writer path,
	read-back verification, and human operational responsibility.

## Risks

- BLOCKER: accidentally converting authorization into a plain config checkbox
	could allow irreversible physical writes without a conscious human step.
- BLOCKER: removing the env gate incorrectly could allow tests or preview to
	contact real GoodWe hardware.
- IMPORTANT: UI could show `APPROVED` after a stale verification for a different
	host; the authorization action must bind evidence to the current host.
- MINOR: users may not understand why `Autorizuji` is disabled; status copy must
	be concise and localized.
