# Step 14 plan

## Goal

Make the SDD workflow operationally fail-closed so that an incomplete or
stale step cannot be presented as merge-ready. Keep the implementation narrow:
repair the concrete gaps identified after Step13 and dogfood the repaired
workflow on Step14.

## Work packages

| ID | Work package | Main output | Depends on |
|---|---|---|---|
| S01 | Deterministic locale tests | Isolated Czech and English Playwright scenarios | None |
| S02 | Phase-aware DONE validation | Complete synthetic step passes; incomplete step fails | None |
| S03 | Canonical step generation | `new_step.py` emits a schema-valid manifest | S02 |
| S04 | Changed-step merge validation | CI runs DONE validation for changed active steps | S02, S03 |
| S05 | Branch protection | `main` requires PR and named checks | S04 |
| S06 | Gate lifecycle | Gate meanings and `NOT_REQUIRED` are encoded and tested | S02 |
| S07 | Agent handoffs | Planner, Developer, and Reviewer contracts match metadata | S06 |
| S08 | Guarded PR rendering | Renderer requires complete and current evidence | S02, S04 |
| S09 | Commit-bound validation evidence | `validation.json` records and checks `HEAD` | S08 |
| S10 | Status source of truth | README status is generated or validated from manifests | S03 |
| S11 | Security-owner closure | Step13 actions have non-secret evidence or explicit blocker | None |
| S12 | Step14 dogfood | Step14 reaches DONE only after all gates and checks pass | S01-S11 |

## Detailed plan

### S01 – Fix deterministic Playwright locale tests

- Set `hec_lang` with `page.add_init_script` before the first application
  navigation, or use isolated browser contexts with init state.
- Split Czech and English navigation checks so each scenario owns its locale.
- Assert the document language and the complete navigation catalog without
  depending on the CI runner's `navigator.language`.
- Run the focused e2e test locally and in the workflow.

### S02 – Fix phase-aware acceptance validation

- Separate structural/ready requirements from done requirements.
- Structural and ready phases require declared AC IDs and valid mappings.
- Done requires no unchecked mandatory AC, all mandatory AC to be PASS, and
  valid evidence; it must not also require an unchecked checkbox to exist.
- Add synthetic fixtures for complete, incomplete, blocked, and historical
  Step12 states.
- Preserve the negative regression that Step12 cannot pass DONE.

### S03 – Make `new_step.py` canonical

- Generate the exact schema-compatible manifest fields and gate objects.
- Preserve existing steps and insert the next README row safely.
- Fail before partial writes when the target or README state is ambiguous.
- Test the generated `STEP.json` through the validator's schema path, not only
  by checking selected keys.

### S04 – Enforce DONE for changed steps in CI

- Add a focused `validate_changed_steps.py` tool under `dev/sdd/tools/`.
- Determine changed `dev/stepNN/` directories from the base and head SHAs.
- Ignore unchanged historical steps such as Step12, while validating every
  changed active step with `validate_step.py --phase done`.
- Fail closed when a changed step is incomplete, malformed, or cannot be
  classified safely.
- Keep local authoring validation at `ready`; reserve changed-step DONE checks
  for PR/merge validation.

### S05 – Configure and verify `main` protection

- Require a pull request, up-to-date branch, and these checks:
  `test (3.11)`, `test (3.12)`, and `sdd-validation`.
- Block direct pushes and do not weaken safety to accommodate a failing check.
- Inspect the resulting GitHub configuration through the API/CLI.
- Verify behavior with a controlled failing-check PR, then with the corrected
  check. Record configuration evidence without committing transient artifacts.

### S06 – Clarify gate lifecycle and optional human gates

- Document Gate A as plan approval, Gate B as human preview approval, and Gate
  C as owner approval to create the final PR.
- Add `NOT_REQUIRED` only where the change genuinely has no relevant UI or
  runtime behavior, and require a non-empty reason.
- Accept `APPROVED` or justified `NOT_REQUIRED` where the gate is optional;
  never allow it for a safety-critical validation by omission.
- Add validator tests for missing reasons, valid optional gates, and circular
  lifecycle regressions.

### S07 – Add real agent handoffs and align reviewer scope

- Add explicit Planner-to-Developer and Developer-to-Reviewer handoffs in
  supported VS Code frontmatter with human confirmation retained.
- Verify tool IDs against the installed VS Code customization surface.
- Keep Reviewer read/test oriented; remove claims that it edits `RESULT.md`.
- Generate deterministic evidence files through tooling rather than requiring
  a read-only Reviewer to write them.

### S08 – Make PR rendering generic and guarded

- Require `--step`; remove the Step13-specific default and wording.
- Run or require a successful done/review-ready validation before rendering.
- Refuse to render when gates, AC, traceability, blockers, or required evidence
  are incomplete.
- Refuse to render when the validation evidence is stale.
- Keep output under ignored runtime storage and derive its content only from
  repository artifacts and validation results.

### S09 – Bind validation evidence to `HEAD`

- Add `git_sha`, UTC timestamp, platform, Python version, and working-tree
  state to `validation.json`.
- Capture actual subprocess results and preserve non-zero failure status.
- Before rendering or final validation, compare recorded `git_sha` with
  current `HEAD`; stale evidence must fail.
- Ensure runtime output remains ignored and is cleaned where required.

### S10 – Synchronize workflow status

- Make `STEP.json` the workflow source of truth.
- Either generate the `dev/README.md` status table or validate every canonical
  row against its manifest.
- Add a regression test so a status change cannot silently drift in README.
- Preserve historic prose where it is not a canonical workflow status.

### S11 – Close Step13 owner actions

- Ask the repository owner to confirm credential rotation status without
  providing secret values.
- Record only actor, date, action, and outcome in the appropriate evidence.
- Record the history-remediation decision separately; do not rewrite history
  automatically.
- If either action remains unresolved, keep the blocker explicit and do not
  claim Step13 DONE. Step14 may still prove that the new enforcement works.

### S12 – Dogfood Step14

- Obtain Gate A before implementation and keep the manifest honest throughout.
- Run focused tests after each implementation slice, then repository hygiene,
  Ruff, unit tests, mock preview, runtime smoke, and Playwright.
- Obtain human Gate B or justified `NOT_REQUIRED`, then Gate C owner approval.
- Run changed-step DONE validation and final full validation against the same
  commit; verify `validation.json.git_sha == HEAD`.
- Confirm all mandatory traceability rows and AC are PASS, set Step14 to DONE,
  and only then use the guarded renderer and merge workflow.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| CI validates only document existence | Changed-step tool invokes the DONE phase in PR validation |
| Complete steps remain impossible to validate | Synthetic complete fixture is a required regression test |
| Old steps break after stricter rules | Validate only changed active steps; retain Step12 negative coverage |
| PR evidence is reused after edits | Store and compare the exact Git SHA |
| Gate lifecycle becomes circular | Define Gate C before PR creation and keep GitHub merge approval separate |
| Human test is silently skipped | Require explicit `APPROVED` or reasoned `NOT_REQUIRED` |
| Branch protection cannot be configured | Record the exact permissions/plan blocker; never weaken local checks |
| Security evidence leaks secrets | Store only non-secret confirmation metadata |
| Preview accidentally writes to hardware | Keep controller and TNG writes disabled and run mock/isolated validation |

## Validation commands

Focused and final validation must include, as applicable:

```text
python -m ruff check .
python -m pytest -m "not e2e"
python dev/sdd/tools/validate_step.py --phase ready --step dev/step14
python dev/sdd/tools/validate_step.py --phase done --step dev/step14
python dev/sdd/tools/validate_changed_steps.py --base <base-sha> --head <head-sha>
python dev/sdd/tools/full_validation.py
python -m pytest dev/hec/tests/e2e -m e2e
```

The exact final commands and their results belong in Step14 evidence. Automated
checks must not be labeled as human approval.

## Delivery order

1. Approve this plan as Gate A.
2. Implement S01-S04 and their focused tests.
3. Implement S05-S10 and validate the local merge gate.
4. Resolve or explicitly record S11 security-owner actions.
5. Run S12 dogfooding, obtain human gates, and validate the final commit.
6. Merge only after GitHub required checks and branch protection permit it.
