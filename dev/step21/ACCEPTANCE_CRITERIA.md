# Step 21 Acceptance Criteria

- [ ] AC-021-001: Actual and legacy SDG DBF layouts are discovered without
	duplicate file entries.
- [ ] AC-021-002: `pm_time` and supported date/time variants normalize to
	timezone-aware ISO 8601 timestamps.
- [ ] AC-021-003: Imported records are stored under `sdg_history` and are
	returned by the existing source/history API and visible in the History UI.
- [ ] AC-021-004: A file with zero valid rows is not irreversibly checkpointed;
	after a parser/data fix it can be retried.
- [ ] AC-021-005: Successful incremental imports remain idempotent across
	repeated polls, file growth, truncation, restart, and duplicate rows.
- [ ] AC-021-006: Diagnostics distinguish discovered files, imported rows,
	skipped rows, duplicates, corrupt files, and last checkpoint state.
- [ ] AC-021-007: Corrupt/unsupported DBF input cannot stop the scheduler or
	other readers, and missing timestamps never produce fabricated records.
- [ ] AC-021-008: Read-only production validation confirms runtime path and
	import state without modifying the share, services, or production config.
- [ ] AC-021-009: Controller/TNG/GoodWe write gates remain disabled in local,
	preview, and automated validation.
- [ ] AC-021-010: Focused tests, Ruff, relevant pytest, safe preview/browser
	checks, and Step 21 validation are recorded with exact results.
# Acceptance criteria

- [ ] The implementation satisfies the objective and scope.
- [ ] Safety invariants remain unchanged.
- [ ] Validation evidence is recorded and has clear commands/results.
- [ ] No write-capable device path is enabled.
- [ ] The work remains within the approved step boundaries.
