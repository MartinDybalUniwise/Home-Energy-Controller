# Step 20 Result

## Summary

Step 20 frontend implementation is complete and remains `IN_PROGRESS` pending
Reviewer and Human Gate. Gate A was approved on 2026-09-14. The new localized
read-only Control & Plan page shows automation state, readers, writer gates,
device metrics, today's decisions, and explicit today/tomorrow fallback cards.

## Planned vs implemented

- Planned: A read-only Control & Plan monitoring page covering current health,
	today's activity, and the outlook through tomorrow for controller, planner,
	readers, writers, heating, boiler, Shelly, PV/load, grid, and battery.
- Implemented: Frontend route, navigation entry, localized CS/EN rendering,
	responsive diagnostics layout, explicit missing-data states, appliance and
	energy cards, activity table, today/tomorrow outlook, focused browser
	coverage, daily GoodWe/SDG-counter energy metrics, and color-coded heating
	and boiler mode badges. No backend/API/storage/reader/writer/controller
	changes.

## Validation

- Command: `HEC_RUN_E2E=1 HEC_BASE_URL=http://127.0.0.1:8181 python -m pytest dev/hec/tests/e2e -o addopts= -m e2e -k 'control_plan' -x -vv`
- Result: PASS, 2 focused Control & Plan browser tests after the approved desktop layout expansion. The route now uses the available workspace width beside the sidebar.
- Command: `HEC_RUN_E2E=1 HEC_BASE_URL=http://127.0.0.1:8181 python -m pytest dev/hec/tests/e2e -o addopts= -m e2e -k 'control_plan' -x -vv`
- Result: PASS, 2 focused Control & Plan browser tests after the approved unified device grid. Heating, hot water, PV, grid, and appliances now share one desktop row; card titles wrap beside the status badge when needed.
- Command: `python -m ruff check .`
- Result: PASS.
- Command: `python -m pytest -m "not e2e"`
- Result: 286 passed, 1 unrelated pre-existing Step 16 GoodWe audit failure,
  25 deselected.
- Command: `HEC_RUN_E2E=1 HEC_BASE_URL=http://127.0.0.1:8181 python -m pytest dev/hec/tests/e2e -o addopts= -m e2e -x -vv`
- Result: PASS, 25 passed.
- Additional browser evidence: daily production/import/export card and two
	heating/boiler mode badges rendered; Control & Plan focused tests 2 passed.
- Command: `python dev/sdd/tools/validate_step.py --phase ready --step dev/step20`
- Result: PASS.

## Safety status

- Controller enabled: false
- TNG write enabled: false
- Physical writes: blocked

## Known limitations

- Scheduler execution status is not exposed by the existing API, so the page
	labels it explicitly as unavailable instead of inferring a running state.
- The existing non-E2E suite contains one unrelated Step 16 GoodWe audit test
	failure; it was not changed by Step 20.

## Completion record

- The current full validation passed with 298 non-E2E tests and 27 Playwright scenarios.
- Gate B: APPROVED by the repository owner / maintainer on 2026-09-14T21:29:43+02:00 after the read-only Control & Plan review.
- Gate C: APPROVED by the repository owner / maintainer on 2026-09-14T21:29:43+02:00 after review of the recorded evidence.
- Final status: DONE.
