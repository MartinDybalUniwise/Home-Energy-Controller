# Step23 Requirement - Responsive page startup and Prediction rendering

## Objective

Ensure a slow auxiliary status/SDG diagnostic path cannot prevent the selected
frontend page from rendering, and ensure the existing valid prediction payload
is rendered by `Výhled` without a JavaScript exception.

## Scope

### In scope

- Frontend startup and page-render ordering around `/api/status`.
- Status/SDG diagnostic latency and blocking behavior at the application
	boundary identified by production evidence.
- Prediction-page rendering and its direct dependencies, including the
	undefined `formatCurrency` failure.
- Explicit loading, partial, timeout, and error states.
- Focused browser and API-contract regression coverage.

### Out of scope

- Changes to SDG history parsing, checkpointing, or import semantics already
	covered by Step21.
- Changes to prediction mathematics or forecast data contracts.
- Production rollout or service management.
- Any physical-device write path or frozen root prototype.

## Functional requirements

- REQ-023-001: A slow or unavailable `/api/status` or SDG diagnostic operation
	must not leave the selected route permanently in its global loading state.
- REQ-023-002: The Prediction route must request `/api/prediction` and render a
	valid `available=true` payload with forecast days and no uncaught exception.
- REQ-023-003: Missing or failed prediction/weather/price data must render an
	explicit localized partial/error state rather than a blank page.
- REQ-023-004: Existing History rendering for `sdg_history` must remain intact.
- REQ-023-005: Status diagnostics must remain truthful and must not fabricate
	healthy state while an auxiliary reader is slow, stale, or unavailable.

## Non-functional requirements

- NFR-023-001: Page-specific data loading is isolated from optional global
	diagnostics and remains responsive under the measured production latency.
- NFR-023-002: Browser console has no application JavaScript errors on
	`#/prediction`, `#/history`, and `#/control-plan`.
- NFR-023-003: Czech and English rendering, safe preview, and existing API
	contracts remain compatible.

## Safety requirements

- TNG write gate remains disabled.
- `controller.enabled=false` remains required in preview/local validation.
- GoodWe writer remains disabled and no physical-device writes occur.
- Production validation is read-only only.

## Risks

- IMPORTANT: moving status loading out of the startup critical path could hide
	a real system fault; mitigate with visible partial/stale/error indicators.
- IMPORTANT: a frontend fallback could mask a contract mismatch; mitigate with
	an explicit API-shape test and browser assertion for the real payload.
- MINOR: reducing repeated SDG path scans may change diagnostic freshness;
	preserve last-known diagnostics and label their timestamp.
