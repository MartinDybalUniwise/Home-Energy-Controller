# Step23 Acceptance Criteria

- [ ] AC-023-001: `#/prediction` renders a valid observed prediction payload
	with forecast cards and no application `pageerror` or console exception.
- [ ] AC-023-002: A delayed `/api/status` or SDG diagnostic response does not
	leave `#/prediction`, `#/history`, or `#/control-plan` permanently loading.
- [ ] AC-023-003: The confirmed `formatCurrency is not defined` failure is
	eliminated through a focused browser regression test.
- [ ] AC-023-004: Partial, stale, timeout, and unavailable diagnostic states are
	visible and localized; no fabricated healthy status or forecast is shown.
- [ ] AC-023-005: Existing `sdg_history` History UI/API rendering remains
	functional with the production-shaped data fixture.
- [ ] AC-023-006: Existing `/api/prediction`, `/api/status`, weather, and price
	contracts remain compatible.
- [ ] AC-023-007: Ruff, relevant pytest, safe preview, focused Playwright, and
	Step23 validation pass with exact evidence recorded.
- [ ] AC-023-008: Controller/TNG/GoodWe write gates remain disabled and no
	production write/restart/install/configuration change occurs.
- [ ] AC-023-009: Owner review confirms the corrected page-loading behavior at
	the production-shaped desktop viewport before Gate B/C completion.
