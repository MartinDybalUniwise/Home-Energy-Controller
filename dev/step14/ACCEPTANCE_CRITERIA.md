# Step 14 acceptance criteria

## Process and CI

- [ ] AC-014-001: Czech and English Playwright navigation tests use isolated
  pre-navigation locale state and pass without depending on
  `navigator.language` from the host or CI runner.
- [ ] AC-014-002: A fully completed synthetic step passes
  `validate_step.py --phase done`.
- [ ] AC-014-003: An incomplete synthetic step fails DONE validation, and
  historical Step12 continues to fail for truthful incomplete-state reasons.
- [ ] AC-014-004: `new_step.py` generates a manifest that passes canonical
  schema validation immediately and preserves existing steps/README content.
- [ ] AC-014-005: CI validates every changed active step with the DONE phase and
  fails a PR containing open gates, unchecked mandatory AC, missing evidence,
  or blockers; unchanged historical incomplete steps are not newly required to
  pass DONE.
- [ ] AC-014-006: The PR workflow and main-branch workflow pass Python 3.11,
  Python 3.12, repository hygiene, SDD validation, mock preview, and
  Playwright checks.
- [ ] AC-014-007: `main` requires a pull request, up-to-date branch, and the
  checks `test (3.11)`, `test (3.12)`, and `sdd-validation`; a controlled
  failing-check PR is blocked from merging.

## Lifecycle and roles

- [ ] AC-014-008: Gate A, Gate B, and Gate C have one documented meaning,
  Gate C is owner approval to create the final PR, and the lifecycle has no
  approval circle.
- [ ] AC-014-009: `NOT_REQUIRED` is accepted only with a non-empty reason and
  cannot bypass a safety-critical or otherwise mandatory validation.
- [ ] AC-014-010: Planner-to-Developer and Developer-to-Reviewer handoffs are
  present in supported VS Code metadata and require human confirmation where
  specified; Reviewer instructions do not require edits it cannot perform.

## Evidence and projection

- [ ] AC-014-011: `render_pr.py` requires an explicit step or safe detection,
  is not Step13-specific, refuses incomplete evidence, and refuses stale
  validation evidence.
- [ ] AC-014-012: `validation.json` records `git_sha`, UTC timestamp, platform,
  Python version, working-tree state, commands, and actual exit results;
  `git_sha` must equal current `HEAD` for final rendering.
- [ ] AC-014-013: Canonical workflow status in `dev/README.md` is generated
  from or validated against `STEP.json`, with a regression test preventing
  drift.
- [ ] AC-014-014: Step13 credential-rotation status and history-remediation
  decision are evidenced without secret values; unresolved owner actions stay
  explicit and are not labeled complete.

## Step14 dogfood and safety

- [ ] AC-014-015: Step14 is validated with ready phase before implementation and
  retains truthful status/gates throughout the work.
- [ ] AC-014-016: Step14 passes focused tests, Ruff, repository hygiene, unit
  tests, mock preview, runtime smoke, and mock Playwright on the final commit.
- [ ] AC-014-017: Step14 has complete requirement-to-work-package,
  work-package-to-acceptance, and acceptance-to-evidence traceability.
- [ ] AC-014-018: Step14 has status `DONE`, Gate A `APPROVED`, Gate B
  `APPROVED` or justified `NOT_REQUIRED`, Gate C `APPROVED`, readiness `YES`,
  and no blocker only after the final validation evidence passes.
- [ ] AC-014-019: Safety invariants remain true: controller disabled, TNG
  writes disabled, no physical-device writes, and no new tracked secrets,
  runtime data, logs, or browser artifacts.
- [ ] AC-014-020: The guarded PR body is generated only after the final
  validation evidence matches `HEAD`, and merge occurs only after required
  GitHub checks are green and branch protection allows it.
