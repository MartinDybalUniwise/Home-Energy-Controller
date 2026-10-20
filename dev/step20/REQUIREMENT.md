# Requirement – Control & Plan monitor

## Objective

Provide a dedicated, read-only operational view that makes HEC automation
understandable and auditable for a local operator. It must combine status,
recent activity, and near-term outlook without duplicating the main daily
cockpit or inventing a second decision engine.

## Scope

### In scope

- New navigation destination and localized frontend page.
- Existing API data only: current/status, decisions, history, prices,
	prediction, appliances, and relevant heat-pump/summary data where already
	available.
- Explicit states for enabled, disabled, safe mode, stale, error, no data, and
	writer unavailable.

### Out of scope

- Any backend contract, storage schema, controller rule, scheduler interval,
	reader implementation, writer implementation, or device command.
- A UI switch that enables controller, TNG, GoodWe, or other physical writes.
- Claims of future behavior when no existing prediction or schedule data exists.

## Functional requirements

- REQ-020-001: The page shows planner/scheduler status, last successful cycle,
	next expected cycle when exposed by existing data, and stale/error state.
- REQ-020-002: The page shows controller enabled state, safe mode, reason,
	last run, last decision, applied/not-applied result, and decision reason.
- REQ-020-003: The page shows each configured reader with enabled state,
	freshness/age, last success/error, and a concise error indication.
- REQ-020-004: The page shows each writer separately with enabled state,
	availability, last attempt/result, and write gate status; unavailable writer
	data is labeled as unavailable rather than inferred.
- REQ-020-005: The page highlights heating and boiler state, including current
	measured/set values when available, operating mode, and controller action
	state without issuing commands.
- REQ-020-006: The page shows Shelly appliance status and today's detected or
	recent activity using existing appliance/history data.
- REQ-020-007: The page shows PV production, household load, battery SoC and
	power, grid purchase, and grid export using existing snapshot/history fields.
- REQ-020-008: A timeline or grouped outlook shows today through the end of the
	following day for available prices, PV/load prediction, and existing planned
	decisions; unavailable portions are visibly marked.
- REQ-020-009: The page distinguishes event time, planned time, and last
	observed time, and provides a clear current-time marker.
- REQ-020-010: The page refreshes through the existing frontend data flow and
	preserves Czech/English localization, keyboard access, and touch operation.

## Non-functional requirements

- NFR-020-001: The primary desktop view is scannable in one viewport at
	1920x1080; responsive layouts remain usable at 1280x800 and 390x844.
- NFR-020-002: No new API endpoint or fabricated fallback value is introduced.
- NFR-020-003: Loading, partial, stale, error, empty, and disabled states are
	testable and do not leave misleading green/healthy indicators.
- NFR-020-004: The page uses existing HEC visual tokens and does not obscure
	the global navigation or status indicator.

## Safety requirements

- TNG write gate remains disabled in local/preview validation.
- `controller.enabled=false` remains required in local/preview validation.
- GoodWe and other physical-device writes remain disabled.
- No page action may mutate configuration or call a writer.

## Risks

- IMPORTANT: inconsistent or partial source data could make a combined status
	appear healthier than its weakest dependency; mitigate with per-source state
	and fail-closed aggregate health.
- IMPORTANT: exposing planned/applied wording incorrectly could mislead an
	operator; mitigate by reusing decision fields and labeling observed versus
	planned versus applied.
- MINOR: the 36-hour timeline may be dense on mobile; mitigate with stacked
	sections and horizontal time scrolling only inside the timeline.
- MINOR: writer diagnostics may not expose a complete last-attempt history;
	show the available status and explicitly label missing diagnostics.
