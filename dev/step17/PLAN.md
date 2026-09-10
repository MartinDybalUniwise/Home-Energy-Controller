# Step 17 plan

## Goal

Prepare an implementation-ready redesign plan for the HEC pages Dnes, Výhled,
and Tok energie that improves clarity and visual consistency while preserving
the existing frontend architecture, local API contracts, and no-write safety
rules.

## Work packages

| ID | Work package | Main output | Depends on |
|---|---|---|---|
| S01 | Current-state inventory | map of existing pages, data sources, and UI gaps | None |
| S02 | Shared page framework | shared stripe/card/layout rules for the three pages | S01 |
| S03 | Dnes redesign | target hierarchy, components, and states for Dnes | S02 |
| S04 | Výhled redesign | target hierarchy, forecast cards, and data mapping | S02 |
| S05 | Tok energie redesign | target flow diagram behavior and supporting details | S02 |
| S06 | Responsive, i18n, and accessibility rules | cross-page interaction and presentation rules | S03-S05 |
| S07 | Implementation surface | likely file list, ownership, and change boundaries | S03-S06 |
| S08 | Validation strategy | focused tests, preview flow, and evidence plan | S07 |
| S09 | Gate A handoff | concise approval package before any app-code edit | S01-S08 |

## Detailed plan

### S01 – Current-state inventory

- inspect the existing implementations of Dnes, Výhled, and Tok energie
  without changing behavior;
- map which current endpoints feed each page, limited to existing contracts such
  as `/api/current`, `/api/status`, `/api/prices`, `/api/weather`,
  `/api/prediction`, and `/api/decisions`;
- identify where current UI hierarchy, explanation, responsiveness, or visual
  consistency diverge from `dev/step01/UI_DESIGN.md`;
- keep this inventory architectural, not a backend redesign.

### S02 – Shared page framework

- define a common page skeleton based on the Step01 stripe, detail-card, and
  panel principles;
- define how the three pages share headings, summaries, stale-data handling,
  empty states, safe-mode warnings, and explanation blocks;
- preserve existing frontend architecture and route/page registration patterns;
- keep color assignments bound to entities, not page-local ordering.

### S03 – Dnes redesign

- define Dnes as the operational “what is happening now” page;
- prioritize current power, SOC, grid direction, key price context, and latest
  decision explanation;
- define what belongs in the top stripe versus supporting cards and detail
  blocks;
- define fallback behavior for partial data, stale data, or safe mode;
- avoid introducing new backend aggregates if the current API can compose the view.

### S04 – Výhled redesign

- define Výhled as the near-future “what will likely happen next” page;
- use the Step01 card/forecast grammar for hourly or day slices, according to
  the current prediction and weather data that already exist;
- show expected production, consumption, relevant price outlook, and advisory
  windows without dual-axis ambiguity;
- define how confidence or uncertainty is explained if the existing API exposes
  only limited forecast detail;
- preserve the current API contract and document any UI-only derived formatting.

### S05 – Tok energie redesign

- define Tok energie as the energy-flow explanation page;
- use the Step01 SVG flow concept for FVE, battery, house, grid, and heat pump;
- define direction, thickness, labels, animation levels, and numeric hierarchy;
- define the relationship between the live flow diagram and supporting context
  such as source freshness, safe mode, or notable decisions;
- keep semantics aligned with current signs/meanings in the existing data model.

### S06 – Responsive, i18n, and accessibility rules

- define desktop, tablet, and mobile behavior consistent with Step01, including
  scrollable stripe behavior where needed;
- require keyboard access, focus visibility, reduced-motion support, and
  non-color state cues;
- keep all page labels and messages on translation keys, with CZ/EN number and
  unit formatting preserved;
- preserve current terminology discipline across Dnes, Výhled, and Tok energie.

### S07 – Implementation surface

- identify likely future implementation files:
  - `dev/hec/web/frontend/js/pages.js`
  - `dev/hec/web/frontend/js/advisor.js`
  - `dev/hec/web/frontend/js/flow.js`
  - `dev/hec/web/frontend/css/app.css`
  - optionally `dev/hec/web/frontend/index.html`
  - optionally locale catalogs under `dev/hec/locales/`
- describe each file as a likely touchpoint, not an approved edit yet;
- keep backend Python modules, API handlers, storage formats, and controller
  code out of the default implementation scope unless a later approved change
  proves they are necessary.

### S08 – Validation strategy

- future implementation must run only safe, existing validation flows;
- require Ruff, relevant pytest coverage, and local Playwright for affected UI;
- use `dev/sdd/tools/preview.py` for safe preview/runtime checks;
- verify that local preview keeps `controller.enabled=false` and
  `tng.write_enabled=false`;
- verify no API contract regressions and no new write path exposure.

### S09 – Gate A handoff

- package the redesign as a planning-only step with explicit scope,
  out-of-scope, risks, validation, and safety invariants;
- keep Gate A pending after these documents are added;
- do not implement application/frontend code before explicit approval terms such
  as `APPROVED`, `SCHVALUJI`, `IMPLEMENT`, or `POKRAČUJ`.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| redesign drifts from approved visual language | keep Step01 UI rules as the design source of truth |
| implementation pressure expands into backend changes | preserve API and architecture boundary explicitly |
| flow diagram becomes visually attractive but semantically wrong | bind labels, direction, and sign meaning to current contracts |
| page redesign hides safe mode or stale data | make degraded states first-class on every page |
| accessibility drops in favor of animation | require reduced motion, keyboard support, contrast, and non-color cues |
| localization is broken by hard-coded copy | require translation keys and locale-aware formatting only |
| preview accidentally enables device writes | keep controller and TNG write-disabled invariants explicit |

## Validation commands

Future implementation validation should use the smallest existing commands that
cover the redesign:

```text
python -m ruff check .
python -m pytest -m "not e2e"
python dev/sdd/tools/validate_step.py --phase ready --step dev/step17
python dev/sdd/tools/preview.py start
HEC_RUN_E2E=1 HEC_BASE_URL=http://127.0.0.1:8181 python -m pytest dev/hec/tests/e2e -m e2e
python dev/sdd/tools/preview.py stop
```

If the final implementation changes only selected frontend behavior, prefer a
targeted pytest or Playwright selector over a broader run. No validation in
this plan may enable physical-device writes.

## Delivery order

1. Approve this redesign plan at Gate A.
2. Inventory the current page implementations and confirm API usage.
3. Implement shared layout and page-specific UI in the approved frontend files.
4. Validate with Ruff, relevant pytest coverage, safe preview, and Playwright.
5. Review safety invariants, evidence, and final UX before any PR step.
