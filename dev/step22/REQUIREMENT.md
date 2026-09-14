# Step 22 Requirements - Stable SDG runtime scheduling

## Objective

Make slow, read-only SDG history polling predictable and make the runtime
state unambiguous. A slow network import must not create an immediate repeated
poll loop, and an operator must be able to distinguish an inactive HEC process
from an initialized reader with no usable data.

## Scope

### In scope

- Scheduler timing and lifecycle behavior affecting `sdg_history`.
- Reader/application status and logs needed for read-only diagnosis.
- Focused automated tests and production read-only evidence.

### Out of scope

- DBF parser semantics already covered by Step 21.
- Any device control, write path, or external configuration change.
- Changes to `T:\Home-Energy-Controller` or the Promotic share.

## Functional requirements

- REQ-022-001: A reader poll that takes longer than its configured interval
	must schedule its next attempt from a defined completion-safe policy and
	must not enter an immediate catch-up loop.
- REQ-022-002: The scheduler must preserve isolation between readers; a slow
	SDG poll must not prevent other readers from polling or stop the scheduler.
- REQ-022-003: Application stop must signal and join scheduler threads within
	the documented timeout without enabling any write path.
- REQ-022-004: Runtime status/log evidence must identify reader initialization,
	poll success/failure, poll duration, configured interval, and application
	process/checkout identity without exposing secrets.
- REQ-022-005: `sdg_history` must remain optional, read-only, and compatible
	with the Step 21 storage, checkpoint, and API contracts.

## Non-functional requirements

- NFR-022-001: The implementation must use the existing scheduler/reader
	abstractions and remain portable on Windows and Raspberry Pi.
- NFR-022-002: Slow or unavailable UNC storage must degrade to a diagnosable
	reader failure/backoff and must not terminate unrelated readers.
- NFR-022-003: Evidence must be reproducible with focused pytest/Ruff and a
	safe preview; production validation must be read-only.
- NFR-022-004: No new user-visible hardcoded text; diagnostics use existing
	logging/status conventions and i18n where UI text is needed.

## Safety requirements

- `controller.enabled=false` in local and preview validation.
- `tng.write_enabled=false` in local and preview validation.
- `goodwe.writer_enabled=false` and no physical-device writes.
- External checkout, UNC share, services, and production configuration are
	read-only inspection targets only.
- Frozen root prototypes remain unchanged.

## Risks

- A scheduler timing change could increase or reduce polling frequency if the
	policy is not tested against both fast and slow readers.
- Runtime diagnostics could expose credentials or UNC details; redact secrets
	and preserve only the minimum path identity needed for diagnosis.
- A long network scan can still make one SDG sample slow; this step controls
	scheduling and observability, not network performance itself.

Within the repository threat model, the primary severity is IMPORTANT if a
slow SDG reader degrades normal telemetry, and BLOCKER only if the change
could enable uncontrolled physical writes or prevent the application from
starting. Trusted-administrator bypasses are out of scope.
