# Step 17 requirement

## Title

UI redesign for pages Dnes, Výhled, and Tok energie

## Problem

The current frontend provides the required HEC data, but the pages Dnes,
Výhled, and Tok energie are not yet defined as one coherent redesign step based
on the approved visual language from `dev/step01/UI_DESIGN.md`. The repository
needs an implementation-ready plan that improves layout, hierarchy, readability,
responsiveness, and explanation of energy decisions without changing the local
API, storage contracts, controller behavior, or the existing `dev/hec/`
architecture.

## Objective

Prepare a LARGE, planning-only redesign step for the three user-facing pages so
future implementation can proceed safely after Gate A approval, with preserved
API contracts, i18n behavior, and no write-capable runtime changes.

## Outcome

Step17 defines the target UX, scope boundaries, work packages, risks,
validation, likely implementation files, and safety invariants for a future
frontend implementation. After these documents are created, Gate A approval
remains pending and no application/frontend code changes are authorized yet.

## Scope

### In scope

- redesign definition for pages **Dnes**, **Výhled**, and **Tok energie**;
- mapping the Step01 visual language to the existing HEC frontend architecture;
- page-level information hierarchy, shared layout patterns, and component reuse;
- use of existing local API endpoints and current data contracts only;
- states for loading, stale data, safe mode, empty data, and degraded sources;
- responsive behavior for desktop, tablet, and mobile/PWA;
- i18n, accessibility, chart-color, and reduced-motion requirements from Step01;
- identification of likely future implementation files and validation strategy.

### Out of scope

- backend endpoint additions, removals, or contract changes;
- storage format changes or snapshot schema redesign;
- controller logic, optimization logic, TNG behavior, or device integrations;
- any physical-device write path or configuration that enables writes;
- deployment, branch protection, or production host workflow changes;
- redesign of unrelated pages outside Dnes, Výhled, and Tok energie.

## Architecture and contract constraints

- Preserve the existing `dev/hec/` architecture and keep the redesign in the
  frontend layer.
- Preserve current local API contracts documented in `dev/hec/docs/API.md`.
- Preserve deployment assumptions from `dev/hec/docs/DEPLOYMENT.md`: no new
  Node, database, Docker, or host-runtime requirement may become mandatory.
- Keep all user-visible text on translation keys; do not introduce hard-coded
  Czech or English UI strings.
- Keep chart and layout rules from `dev/step01/UI_DESIGN.md`, including stable
  entity colors and no double Y axis.

## Explicit safety invariants

- `controller.enabled=false` remains required in local and preview development.
- `tng.write_enabled=false` remains required in local and preview development.
- No physical-device write path is enabled, tested, or simulated as a real write.
- The TNG confirmation cycle and 900-second minimum interval remain untouched.
- No redesign work may require calling write-capable device APIs.
- No secrets, tokens, production data, logs, caches, or browser artifacts are
  committed to Git.
- Frozen root prototypes remain unchanged.

## Likely future implementation files

- `dev/hec/web/frontend/js/pages.js`
- `dev/hec/web/frontend/js/advisor.js`
- `dev/hec/web/frontend/js/flow.js`
- `dev/hec/web/frontend/css/app.css`
- optionally `dev/hec/web/frontend/index.html`
- optionally locale catalogs under `dev/hec/locales/`

## Sources of truth

- `CLAUDE.md`
- `dev/README.md`
- `dev/sdd/README.md`
- `dev/hec/docs/API.md`
- `dev/hec/docs/DEPLOYMENT.md`
- `dev/step01/UI_DESIGN.md`

## Requirement IDs

- **REQ-017-001 – Shared redesign model:** define a shared visual and interaction
  model for Dnes, Výhled, and Tok energie that follows Step01 design rules.
- **REQ-017-002 – Dnes page:** define a layout that answers what is happening
  now, why it is happening, and what requires user attention, using current
  snapshot/status/decision data only.
- **REQ-017-003 – Výhled page:** define a layout for near-future outlook using
  the current prediction, weather, and price contracts without backend changes.
- **REQ-017-004 – Tok energie page:** define a readable energy-flow presentation
  that preserves the current energy entities, signs, and meanings.
- **REQ-017-005 – Responsive and accessible behavior:** define desktop, tablet,
  and mobile behavior, keyboard access, contrast, reduced motion, and non-color
  cues.
- **REQ-017-006 – I18n and terminology:** keep all user text translatable and
  preserve CZ/EN formatting and terminology discipline.
- **REQ-017-007 – Implementation boundary:** identify the likely future frontend
  files and preserve local API and architecture boundaries.
- **REQ-017-008 – Validation plan:** define the future validation commands and
  evidence needed before the redesign can be marked done.
- **REQ-017-009 – Safety boundary:** state explicit no-write invariants and
  prohibit any change that weakens them.

## Completion boundary

For this planning step, completion means the requirement, plan, and acceptance
criteria exist under `dev/step17/` and `dev/README.md` links the step as
planned. Implementation remains blocked until explicit human Gate A approval.
