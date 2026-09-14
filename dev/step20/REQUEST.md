# Step 20 Request – Control & Plan monitor

## Summary

Create a separate visual operations page for inspecting the current state and
recent activity of the controller and scheduler/planner. The page must answer
what is running now, what happened today, and what is expected through the end
of the next day, with special focus on heating, hot-water boiler, Shelly
appliances, PV production, grid purchase/sale, and battery state.

The page is an observability surface for a trusted local operator. It must make
enable/disable state, safe mode, stale data, reader health, writer availability,
last decisions, and upcoming recommendations visible without requiring users
to inspect logs or raw API responses.

## Scope

- In scope: a new localized frontend route/page, read-only API bindings to
	existing status/current/history/prices/prediction/decisions endpoints,
	reader and writer health panels, today/tomorrow timeline, and focused E2E
	coverage at desktop and mobile widths.
- Out of scope: backend/API/storage changes, new business rules, changing
	controller or planner behavior, enabling device writes, configuration edits,
	new readers/writers, or replacing Home/Dnes from Step 19.

## Safety constraints

- `controller.enabled=false` in local and preview development.
- `tng.write_enabled=false` in local and preview development.
- GoodWe and all physical-device writers remain disabled in preview.
- The page contains no control that enables writes or bypasses the TNG gate.
- No physical-device writes and no changes to frozen root prototypes.

## Acceptance signal

At the new route, an operator can identify within one viewport whether the
planner, controller, readers, and writers are healthy; inspect today's recent
decisions/events; and see the existing data-backed outlook through the end of
tomorrow. Missing, stale, disabled, and unavailable states are explicit and no
fabricated values are shown.
