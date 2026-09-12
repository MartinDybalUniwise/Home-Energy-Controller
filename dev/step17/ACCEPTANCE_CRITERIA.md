# Step 17 acceptance criteria

- [ ] AC-017-001: `dev/step17/REQUIREMENT.md`, `PLAN.md`, and
  `ACCEPTANCE_CRITERIA.md` define a planning-only LARGE step for redesigning
  Dnes, Výhled, and Tok energie.
- [ ] AC-017-002: the step documents clear in-scope and out-of-scope boundaries
  and explicitly preserves the existing `dev/hec/` architecture and local API
  contracts.
- [ ] AC-017-003: the plan is split into numbered work packages `S01...SNN`
  covering current-state inventory, shared layout, page-specific redesign,
  implementation surface, validation, and Gate A handoff.
- [ ] AC-017-004: the documents identify likely future implementation files,
  including `js/pages.js`, `js/advisor.js`, `js/flow.js`, and `css/app.css`,
  with optional `index.html` and locale catalog changes.
- [ ] AC-017-005: the redesign plan references the relevant repository sources
  of truth, especially `CLAUDE.md`, `dev/README.md`, `dev/sdd/README.md`,
  `dev/hec/docs/API.md`, `dev/hec/docs/DEPLOYMENT.md`, and
  `dev/step01/UI_DESIGN.md`.
- [ ] AC-017-006: explicit no-write safety invariants are documented, including
  `controller.enabled=false`, `tng.write_enabled=false`, no physical-device
  writes, preserved TNG confirmation behavior, and no secrets or runtime data
  committed to Git.
- [ ] AC-017-007: the plan defines future validation using existing repository
  tools only, including Ruff, relevant pytest coverage, safe preview, and local
  Playwright for affected UI behavior.
- [ ] AC-017-008: the plan defines responsive, i18n, accessibility, safe-mode,
  stale-data, and reduced-motion expectations for the redesigned pages.
- [ ] AC-017-009: `dev/README.md` contains a Czech Step 17 row that links to
  `step17/` and marks the step as planned.
- [ ] AC-017-010: Gate A approval remains explicitly pending after this planning
  step, and no application/frontend code changes are included in Step17 before
  explicit human approval.
