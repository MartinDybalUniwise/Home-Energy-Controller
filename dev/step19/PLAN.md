# Step 19 Plan

## Goal

Implement a no-scroll 1920x1080 Today cockpit by simplifying information
architecture before reducing spacing. Preserve current HEC styling and data
behavior, remove repetition, and keep Daily Energy Rhythm dominant.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Establish browser geometry baseline and regression assertions | DONE |
| S02 | Compact the shared desktop sidebar without breaking navigation | DONE |
| S03 | Consolidate the recommendation hierarchy into one horizontal band | DONE |
| S04 | Compact the KPI strip and expand Daily Energy Rhythm | DONE |
| S05 | Replace the three-panel workspace with appliances plus chart | DONE |
| S06 | Complete responsive, i18n, fallback, accessibility, and empty-track checks | DONE |
| S07 | Run validation and prepare human 1920x1080 acceptance preview | DONE |

## Detailed strategy

### S01 - Geometry baseline and tests

- Measure rendered Today section bounds at 1920x1080.
- Add a failing E2E assertion for zero vertical overflow, section visibility,
  overlap, and horizontal overflow before implementation.

### S02 - Shared sidebar compaction

- Reduce desktop width to 190-210 px while preserving all links and touch use.
- Replace large health-card treatment with compact status.
- Verify adjacent content and all other routes remain functional.

### S03 - Header and recommendation consolidation

- Preserve one compact horizontal recommendation band with the dominant best
  window and concise Now, Avoid, and PV-peak statuses.
- Keep Why-now as an accessible action in this band.
- Do not restore the former three separate supporting cards.

### S04 - KPI and rhythm density

- Keep six telemetry values in a 90-105 px strip.
- Move production estimate/peak into the rhythm header.
- Remove the standalone estimate card and expand the timeline to 260-290 px.

### S05 - Two-panel lower workspace

- Remove the next-window donut.
- Render appliance recommendations as compact 52-60 px rows.
- Preserve chart series and horizon controls in a 35-40% / 60-65% split.
- Retain only actions with verified existing behavior.

### S06 - Responsive, i18n, fallback, and accessibility

- Test 1920x1080, 1440x900, 1280x800, 1024x768, and 390x844.
- Exercise Czech/English catalogs and missing weather/price/prediction states.
- Preserve focus visibility, keyboard navigation, and touch operation.
- Ensure removed panels leave no empty CSS grid tracks at 1920, 1440, 1280, or
  1024 px widths.

### S07 - Validation and acceptance preview

- Run `python -m ruff check .`.
- Run `python -m pytest -m "not e2e"`.
- Run `python -m pytest dev/hec/tests/e2e -o addopts= -m e2e -x -vv`.
- Run Step 19 ready/done validation and repository full validation at the
  appropriate gates.
- Present the safe 1920x1080 preview for human no-scroll and readability review.

## Expected implementation files

- `dev/hec/web/frontend/js/advisor.js`
- `dev/hec/web/frontend/js/chart.js` only if sizing requires it
- `dev/hec/web/frontend/css/app.css`
- `dev/hec/web/frontend/css/tokens.css` only for reusable dimensions
- `dev/hec/web/frontend/index.html` only if compact status requires it
- `dev/hec/locales/cs.json` and `en.json`
- `dev/hec/tests/e2e/test_smoke.py`

## Gate A

No application code may be changed until the repository owner explicitly
approves this Step 19 package. Approval must be recorded in `STEP.json` before
S01 begins.