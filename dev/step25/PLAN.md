# Plan

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `CANCELLED`.

## Goal

Create a telemetry-centered architecture plan and migrate incrementally from
the current HEC-owned reader threads without changing observable behavior first.
The first implementation stages add contracts and adapters; process extraction
and storage replacement are separate decisions, not assumptions.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Freeze current contracts and add architecture evidence | PLANNED |
| S02 | Introduce telemetry envelope and technical-log taxonomy | PLANNED |
| S03 | Add a reader runtime adapter with persisted-health/read-only IPC | PLANNED |
| S04 | Extract one low-risk reader in shadow mode | PLANNED |
| S05 | Extract remaining read-only readers and importers | PLANNED |
| S06 | Split HEC dashboard/analytics into telemetry-store consumers | PLANNED |
| S07 | Isolate TNG and GoodWe writers without changing gates | PLANNED |
| S08 | Add Observer, Analyst, and Financial Controller read-only contracts | PLANNED |
| S09 | Measure retention and choose the next storage implementation | PLANNED |

## Detailed implementation strategy

### S01 - Current-state contract and dependency freeze

Objectives:
- Capture current JSONL, `current_*.json`, OTE, weather, TNG, SDG, and audit
	formats as compatibility contracts.
- Add tests that detect direct device access from dashboard/analytics paths.
- Record process, thread, supervisor, and restart behavior without changing it.

Implementation:
- Use existing reader, storage, API, deployment, and test surfaces as evidence.
- Define source names, timestamp meanings, and required backward-compatible
	fields before introducing new adapters.

Risks:
- Incorrectly freezing an accidental field as a public contract. Mark fields
	as legacy, canonical, or internal explicitly.

### S02 - Telemetry and technical-log contract

Objectives:
- Add a minimal envelope with `event_time`, `ingested_at`, `source`,
	`device_id`, `metric`, `value`, `unit`, `quality`, and `raw_ref`.
- Keep existing wide payloads available through an adapter during transition.

Implementation:
- Preserve timezone-aware ISO 8601 values and retain TNG `sample_time`.
- Define quality values for `ok`, `stale`, `missing`, `invalid`, `offline`,
	and `estimated`; do not replace unknown values with zero.

Risks:
- Double storage or ambiguous joins. Start with source/device/metric keys and
	measure volume before normalizing historical data.

### S03 - Reader runtime adapter

Objectives:
- Define process health, bounded polling, backoff, shutdown, and restart
	contracts independently of HEC web lifecycle.
- Keep the adapter read-only and safe by default.

Implementation:
- Prefer one supervised reader service boundary with per-source workers only
	where needed; do not create one OS service per small source prematurely.
- Use local file/IPC or a local HTTP read interface that preserves atomic
	publication and prevents writer/controller commands from entering readers.

Risks:
- A new IPC path becomes an accidental device-control path. Enforce a read-only
	schema and integration tests that reject commands.

### S04-S05 - Shadow extraction and source migration

Objectives:
- Extract low-risk Weather/OTE/Shelly first, then Sharing/Finance/SDG, and
	extract GoodWe/TNG only after their read/write boundaries are proven.
- Compare old and new outputs without changing the active dashboard source.

Implementation:
- Run one collector as the active producer; shadow readers use separate output
	namespaces or comparison sinks and never write devices.
- Cut over one source at a time, with duplicate detection, rollback to the
	in-process reader, and evidence of equal timestamps/values.

Risks:
- Two active pollers can overload a device or remote endpoint. Do not run dual
	physical polling for GoodWe/TNG without an approved rate budget.

### S06 - HEC as consumer

Objectives:
- Make `/api/current`, history, analysis, and UI read from the persisted
	telemetry store, retaining last-known state and truthful stale status.
- Remove direct reader construction from HEC only after consumer tests pass.

Implementation:
- Keep a compatibility projection for existing frontend payloads.
- Ensure HEC outage does not delete or truncate telemetry.

Risks:
- Snapshot freshness and status can diverge from store state. Define source
	health from persisted ingestion metadata, not only in-process objects.

### S07-S09 - Writers, AI/finance boundaries, and retention decision

Objectives:
- Extract controller/writer command contracts separately from read contracts.
- Add read-only evidence outputs for Observer and Analyst and economic outputs
	for Financial Controller before any recommendation can become a command.
- Measure multi-year storage and backup requirements before changing backend.

Implementation:
- TNG commands remain behind the existing confirmation cycle and interval;
	GoodWe remains behind `GoodWeManager` and authorization gates.
- AI outputs must include evidence, expected/observed behavior, confidence,
	verification, affected components, rollback, and acceptance criteria.
- Select a future backend only from measured write rate, query latency, disk
	growth, backup/restore tests, and Pi resource limits.

Risks:
- Financial optimization can conflict with technical comfort or safety. Keep
	calculation, recommendation, plan, and physical write as separate states.
