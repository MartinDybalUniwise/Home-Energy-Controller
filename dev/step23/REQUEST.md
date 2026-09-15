# Step23 Request - Responsive page startup and working Prediction view

## Summary

Production data is available: `/api/prediction` returns valid forecast days and
the SDG history is visible in History. Nevertheless, pages can remain on
`Načítám…`, and `Výhled` can fail with `ReferenceError: formatCurrency is not
defined`. The user impact is that valid operational data is inaccessible even
though the backend payload exists.

## Scope

- In scope: diagnose and correct the shared frontend startup/status dependency,
	make slow SDG status diagnostics unable to block page rendering, repair the
	Prediction-page JavaScript exception, and add browser coverage for the two
	failure modes.
- Out of scope: SDG DBF parser redesign, new prediction algorithms, new API
	contracts unless a measured blocking boundary requires a narrow change,
	production deployment, device control, and visual redesign.

## Safety constraints

- `controller.enabled=false` in local and preview validation.
- `tng.write_enabled=false` in local and preview validation.
- GoodWe and all physical-device writers remain disabled in preview.
- Production inspection is read-only; no restart, install, configuration change,
	or physical-device write is allowed.
- Frozen root prototypes remain unchanged.

## Acceptance signal

On a slow or unavailable status/SDG diagnostic path, the selected page still
renders its own data or an explicit partial/error state. `Výhled` requests and
renders valid prediction data without a console exception, while History keeps
displaying existing `sdg_history` records.
