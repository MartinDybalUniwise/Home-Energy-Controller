# Requirement

## Objective

Define a reversible architecture transition in which telemetry collection can
survive HEC dashboard or analytics outages, while HEC continues to display the
same data and device writes remain isolated behind existing safety gates.

## Scope

### In scope

- Current-state evidence for all implemented readers and importers.
- A versioned telemetry envelope that preserves source timestamps and raw data.
- Separate telemetry and technical-log concerns, with a migration-compatible
	file-backed implementation first.
- Independent reader service boundaries and a read-only consumer API boundary.
- Explicit reader/writer ownership for TNG and GoodWe.
- Interfaces and rollout order for future WeatherStation, Energy Reader,
	AI Observer, AI Analyst, and Financial Controller components.

### Out of scope

- Big-bang process rewrite or database migration.
- New device integrations in the implementation phase of this step.
- Automatic financial or AI control actions.
- Production deployment, service restart, or hardware validation.

## Functional requirements

- REQ-025-001: Document the actual current runtime: one HEC process, one
	scheduler thread per enabled reader, one maintenance thread, and supervisor
	restart behavior on Linux and Windows.
- REQ-025-002: Classify GoodWe/FTE, TNG, Weather, OTE, Shelly, Sharing,
	FinanceDocument, and SDG history by lifecycle, polling, storage, failure,
	and READ/WRITE responsibility.
- REQ-025-003: Define a target ownership model where readers are read-only,
	writers/controllers are separate, and telemetry is the shared source of truth.
- REQ-025-004: Define a telemetry contract containing event time, ingestion
	time, source, device, metric/value representation, unit, quality, and raw
	provenance without requiring one wide row for every device.
- REQ-025-005: Define handling of missing, stale, duplicate, out-of-order, and
	source-clock-invalid observations, including a common timezone policy.
- REQ-025-006: Define a migration sequence with compatibility adapters,
	shadow/read-only verification, rollback points, and no big-bang cutover.
- REQ-025-007: Define read-only AI Observer and Analyst evidence/spec outputs,
	and a Financial Controller boundary that distinguishes calculation,
	recommendation, planning, and physical write.
- REQ-025-008: Define retention, archival, backup, and capacity checks for
	multi-year telemetry from multiple readers.

## Non-functional requirements

- NFR-025-001: A HEC web/API outage must not be the only reason telemetry
	collection stops after the reader-service migration is complete.
- NFR-025-002: Every migration stage must be independently testable,
	deployable, and reversible while preserving existing output contracts.
- NFR-025-003: A failed source or reader must not stop unrelated sources;
	supervision must restart failed reader processes without duplicate writers.
- NFR-025-004: Local development remains portable across Windows, Linux, and
	Raspberry Pi and keeps standard-library-first dependencies where practical.
- NFR-025-005: Dashboard, analytics, and controllers consume persisted data
	through stable read interfaces rather than device connections.

## Safety requirements

- TNG write gate remains disabled during planning and implementation validation.
- `controller.enabled=false` remains required in preview/local validation.
- GoodWe writes remain behind all existing manager gates and authorization.
- No physical-device writes, production service changes, or root-prototype edits.
- A future TNG writer extraction must preserve the false -> true -> false
	confirmation cycle and the configured minimum interval of at least 900 seconds.
- Findings are evaluated against the private trusted-admin threat model; no
	enterprise controls are treated as blockers.

## Risks

- R-025-001: Two collectors could write the same telemetry during migration,
	causing duplicates or misleading analytics. Mitigate with one active writer,
	source-instance IDs, idempotency, and shadow mode before cutover.
- R-025-002: Reader extraction could change timestamp semantics, especially TNG
	source `sample_time` versus reader ingestion time. Preserve both explicitly.
- R-025-003: Moving TNG writes could bypass its change-gate state. Treat any
	gate regression as a BLOCKER with a concrete device-write scenario.
- R-025-004: JSONL growth and concurrent append/rotation may become operationally
	expensive over years. Measure before selecting SQLite or another store.
- R-025-005: HEC may retain hidden direct-device dependencies through status,
	GoodWe authorization verification, or controller paths. Use dependency tests
	and a read-only consumer contract before disabling in-process readers.
