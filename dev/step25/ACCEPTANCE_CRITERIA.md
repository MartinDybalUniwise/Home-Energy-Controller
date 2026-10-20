# Acceptance criteria

- [ ] AC-025-001: Current-state inventory covers GoodWe/FTE, TNG, Weather, OTE, Shelly,
	Sharing, FinanceDocument, and SDG history with source files, startup,
	runtime model, config, polling, storage, logging, failure, restart, HEC
	dependencies, and READ/WRITE responsibilities.
- [ ] AC-025-002: The actual current architecture is documented as a single HEC process
	with reader threads, maintenance thread, snapshot, JSONL store, API/UI,
	controller, writer, and OS supervisor.
- [ ] AC-025-003: Coupling findings distinguish shared lifecycle, shared config/storage,
	direct device/API access, reader/controller mixing, and parallel file caches.
- [ ] AC-025-004: Target architecture defines independent collection, durable telemetry,
	read-only analytics, separate decision/planning, explicit writers, and HEC
	as a consumer.
- [ ] AC-025-005: Runtime design specifies service/process boundaries, startup, restart,
	supervision, config ownership, read-only communication, and storage writes.
- [ ] AC-025-006: Telemetry design specifies source and ingestion timestamps, timezone,
	source clock policy, quality, missing/stale/duplicate handling, raw values,
	retention, archive, backup, and capacity measurement.
- [ ] AC-025-007: Future WeatherStation, multi-device Shelly, Energy Reader, AI Observer,
	AI Analyst, and Financial Controller have bounded interfaces and no implicit
	device-write authority.
- [ ] AC-025-008: Migration has small, testable, reversible stages with shadow comparison,
	duplicate prevention, rollback, and compatibility projections.
- [ ] AC-025-009: TNG confirmation cycle and minimum 900-second interval remain explicit
	safety invariants for every future writer move.
- [ ] AC-025-010: Validation commands and results are recorded; no physical write, runtime
	change, production connection, or frozen root prototype edit is performed.
- [ ] AC-025-011: `STEP.json` contains all requirement, acceptance, and evidence IDs and
	remains `PLANNED` with Gate A `PENDING` until explicit human approval.
