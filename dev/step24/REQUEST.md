# Request

## Summary

GoodWe currently has two user-hostile blockers for normal product operation:
real GoodWe access is gated by the process environment variable
`HEC_GOODWE_PHYSICAL_IO`, and the local hardware authorization artifact can be
created only by a supervised Python/service call with no product UI path.

The requested change is to remove `HEC_GOODWE_PHYSICAL_IO` from the normal
product flow and add a simple Config UI authorization flow: a button to verify
GoodWe, a status display, and a second explicit button labeled `Autorizuji` to
write the existing authorization artifact.

## Scope

- In scope:
	- GoodWe read access no longer requires `HEC_GOODWE_PHYSICAL_IO` in normal
		product runtime.
	- GoodWe Config UI shows the current authorization state and read-only
		verification result.
	- GoodWe Config UI provides one verification button and one explicit
		`Autorizuji` authorization button.
	- Authorization still writes `data/goodwe_hardware_authorization.json`
		through the existing authorization boundary, not through raw config edit.
	- Tests and documentation cover the new UI/API workflow and retained write
		gates.
- Out of scope:
	- Enabling automatic GoodWe control rules.
	- Performing production physical writes.
	- Editing frozen root prototypes.
	- Replacing the GoodWeManager/FTEWriter safety boundary.
	- Cryptographic signing or enterprise-grade approval controls.

## Safety constraints

- `controller.enabled=false`
- `tng.write_enabled=false`
- No physical-device writes during implementation or automated validation
- No changes to frozen root prototypes
- GoodWe writes remain blocked unless `controller.enabled`, `goodwe.enabled`,
	`goodwe.writer_enabled`, `goodwe.verify_after_write`, and the authorization
	artifact are all valid.

## Acceptance signal

Success is recognized when the app can perform normal GoodWe read access without
`HEC_GOODWE_PHYSICAL_IO`, the Config UI exposes a simple two-step GoodWe
authorization path (`Ověřit` / `Autorizuji`) with status feedback, the artifact
is created only after successful read-only verification plus explicit user
authorization, and GoodWe writes remain refused without all required write gates.
