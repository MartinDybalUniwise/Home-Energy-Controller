# Step 20 Acceptance Criteria

- [ ] AC-020-001: A separate localized Control & Plan route is reachable from
	the existing navigation without changing Home/Dnes behavior.
- [ ] AC-020-002: The page visibly reports planner/scheduler and controller
	enabled state, safe mode, reason, last run, and last decision.
- [ ] AC-020-003: Every configured reader has an explicit enabled,
	fresh/stale/error/disabled/no-data state.
- [ ] AC-020-004: Every available writer has an explicit enabled/disabled,
	available/unavailable, and write-gate state; unavailable diagnostics are not
	fabricated.
- [ ] AC-020-005: Heating and boiler state are visible with available current,
	setpoint, mode, and controller-action information.
- [ ] AC-020-006: Shelly appliance activity is visible for today using existing
	appliance/history data.
- [ ] AC-020-007: PV production, household load, battery SoC/power, purchase,
	and export are visible with units and timestamps where available.
- [ ] AC-020-008: The outlook covers the remainder of today and the full next
	day for existing prices/predictions/planned decisions, with an explicit
	unavailable state for missing data.
- [ ] AC-020-009: Observed, planned, and applied events are distinguishable and
	show local timestamps.
- [ ] AC-020-010: Loading, partial, stale, error, empty, and disabled states
	render without misleading healthy indicators.
- [ ] AC-020-011: Czech and English UI, keyboard focus, semantic labels, touch
	targets, and responsive layouts pass focused browser checks.
- [ ] AC-020-012: No page action changes configuration or calls a physical
	device writer; local preview keeps controller/TNG/GoodWe writes disabled.
- [ ] AC-020-013: Ruff, relevant pytest tests, focused Playwright tests, safe
	preview validation, and Step 20 ready validation pass with recorded output.
