# Step 22 Acceptance Criteria

- [x] AC-022-001: A poll longer than its configured interval does not cause an
	immediate scheduler catch-up loop.
- [x] AC-022-002: A slow or failing SDG reader does not block healthy readers or
	terminate the scheduler.
- [x] AC-022-003: Scheduler stop behavior is bounded, deterministic, and tested.
- [x] AC-022-004: Runtime diagnostics identify process/checkout context,
	reader initialization, poll duration, interval, and latest SDG state without
	exposing secrets.
- [x] AC-022-005: Existing Step 21 `sdg_history` parsing, checkpoint,
	idempotency, storage, and API contracts remain compatible.
- [ ] AC-022-006: Read-only validation against `T:\Home-Energy-Controller` and
	the Promotic share performs no external writes, restart, install, or config
	change.
- [x] AC-022-007: Controller, TNG, and GoodWe write gates remain disabled in
	local, preview, and automated validation.
- [x] AC-022-008: Focused tests, Ruff, relevant pytest, safe preview/browser
	checks where applicable, and Step 22 validation are recorded with exact
	commands and results.
- [ ] AC-022-009: Gate B, Gate C, and DONE remain unrequested until Reviewer
	and Human Gate evidence is explicitly recorded.
