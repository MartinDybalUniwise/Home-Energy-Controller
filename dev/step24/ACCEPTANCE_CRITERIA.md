# Acceptance criteria

- [ ] AC-024-001: Normal GoodWe product read access no longer requires
	`HEC_GOODWE_PHYSICAL_IO`.
- [ ] AC-024-002: Unit tests still prove real hardware access is blocked during
	pytest unless an explicit fake/test client is injected.
- [ ] AC-024-003: GoodWe writes remain refused unless all configured write gates
	and `hardware_authorization.status=APPROVED` pass.
- [ ] AC-024-004: Generic config save still rejects direct authorization fields.
- [ ] AC-024-005: Config UI displays GoodWe authorization status and read-only
	verification status.
- [ ] AC-024-006: Config UI has exactly the simple authorization controls needed
	for this step: verify button and `Autorizuji` button.
- [ ] AC-024-007: `Autorizuji` remains disabled or refused until current-host
	read-only verification succeeds.
- [ ] AC-024-008: Authorization creates/updates the existing local artifact with
	status, host, evidence ID, approver, and timestamp.
- [ ] AC-024-009: Authorization action itself performs no GoodWe write.
- [ ] AC-024-010: UI text is localized in Czech and English.
- [ ] AC-024-011: Focused API/unit tests cover verification, approval, refusal,
	and write-gate behavior without live hardware.
- [ ] AC-024-012: Focused Playwright coverage proves the Config UI status and
	buttons render and behave correctly in safe preview.
- [ ] AC-024-013: Ruff and relevant pytest validation pass.
- [ ] AC-024-014: Safety invariants remain unchanged: `controller.enabled=false`,
	`tng.write_enabled=false`, no physical writes in automated validation, and no
	root prototype changes.
- [ ] AC-024-015: Step24 evidence records exact commands/results and any known
	limitations.
