# Step 15 acceptance criteria

- [ ] AC-015-001: the production target host `192.168.2.115`, URL,
	`hec.service`, port `8080`, installation root, runtime paths, service user,
	and approved access model are documented; unverified values are marked as
	blockers.
- [ ] AC-015-002: the update flow selects an approved revision, records the
	pre-change state, preserves secrets and runtime data, validates before
	restart, and verifies the selected revision after restart.
- [ ] AC-015-003: the rollback procedure preserves the previous release,
	restores application and configuration state without exposing secrets, and
	defines post-rollback health checks and escalation.
- [ ] AC-015-004: the plan states that secrets remain in host-local secure
	storage, are excluded from synchronization and evidence, and are never
	committed to Git.
- [ ] AC-015-005: post-deploy checks cover service state, bounded logs, HTTP
	availability, reader health, and confirmation that no physical-device write
	path was enabled.
- [ ] AC-015-006: local preview validation uses the safe configuration with
	`controller.enabled=false` and `tng.write_enabled=false`, and is explicitly
	separated from production actions.
- [ ] AC-015-007: the complete Step15 artifact set is stored under
	`dev/step15/`, linked from `dev/README.md`, and passes the ready-phase
	structural and traceability validation.
