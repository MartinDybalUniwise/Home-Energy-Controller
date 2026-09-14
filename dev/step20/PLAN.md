# Step 20 Plan – Control & Plan monitor

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Add a separate read-only operational page for controller/planner observability.
The page should answer "what is happening now, what happened today, and what
is expected through tomorrow" while keeping existing API and safety contracts.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Inventory existing frontend routes, API payloads, and status fields | PLANNED |
| S02 | Define page information architecture and state vocabulary | PLANNED |
| S03 | Implement localized read-only route and status sections | PLANNED |
| S04 | Implement today/tomorrow activity and outlook timeline | PLANNED |
| S05 | Add responsive/accessibility/empty-state behavior | PLANNED |
| S06 | Add focused E2E coverage and run validation | PLANNED |

## Detailed implementation strategy

### S01 – Contract inventory

Objectives:
- Confirm the exact existing fields for `/api/current`, `/api/status`,
	`/api/decisions`, `/api/history`, `/api/prices`, `/api/prediction`,
	`/api/appliances`, and `/api/heatpump`.
- Identify which writer diagnostics are available and avoid implying missing
	data.

Implementation:
- Read-only code and fixture inspection; no product code changes.

Risks:
- A required view may not have enough existing fields; unresolved gaps must be
	recorded as explicit unavailable states, not filled by new backend work.

### S02 – Information architecture

Objectives:
- Define a compact page with: system health header; controller/planner strip;
	device matrix; reader/writer diagnostics; today's activity; 36-hour outlook.
- Prioritize heating, boiler, Shelly, PV/load, purchase/export, and battery.

Implementation:
- Produce a UI contract in the step evidence/design notes before coding.
- Reuse Step 18/19 tokens, navigation, localization, and status semantics.

Risks:
- Too many metrics can reduce scanability; use progressive detail and a
	single consistent status legend.

### S03 – Read-only operational page

Objectives:
- Add the route and view rendering from existing frontend API bindings.
- Show controller/planner enablement and safe mode separately from aggregate
	reader/writer health.

Implementation:
- Frontend-only changes in the established page/router, CSS, and locale files.
- No PUT calls, writer imports, or configuration controls.

Risks:
- A visual enable/disable control could be mistaken for a command; render
	statuses as badges/labels and link to existing settings only if already
	permitted by the established UX contract.

### S04 – Activity and outlook

Objectives:
- Show today's events/decisions with timestamps and applied result.
- Show prices, PV/load outlook, and planned windows through the end of tomorrow
	using existing data and clear missing-data treatment.

Implementation:
- Keep timeline aggregation in the frontend presentation layer only; do not
	add business rules or alter backend timestamps.

Risks:
- Time-zone or horizon ambiguity; use the configured local timezone and label
	the horizon explicitly.

### S05 – Responsive and accessible states

Objectives:
- Preserve touch targets, keyboard focus, Czech/English catalogs, and readable
	dense status tables at desktop and mobile widths.
- Test loading, stale, error, disabled, empty, and partial payloads.

Implementation:
- Add CSS responsive layout and semantic labels/regions; avoid color-only
	status communication.

Risks:
- Dense diagnostics may overflow on mobile; allow local horizontal scrolling
	for the timeline and stack the device sections.

### S06 – Validation and evidence

Objectives:
- Run lint, non-E2E tests, focused Playwright scenarios, step validation, and
	safe preview checks.
- Demonstrate that no physical write path is invoked.

Implementation:
- Add E2E assertions for route visibility, key entities, disabled/write-gate
	labels, refresh behavior, and no console errors.

Risks:
- Browser tests can pass with fixture data while live data is partial; include
	explicit fallback scenarios and record human visual review separately.
