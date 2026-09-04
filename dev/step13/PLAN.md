# Step 13 plan

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Turn the reusable `dev/sdd/` foundation into an enforced, evidence-backed workflow for HEC development. Step13 must prove that incomplete requirements, gates, traceability, acceptance criteria, validation, or security actions cannot be represented as a completed step or merged implementation.

## Decision boundaries

- LAN read-only preview is deferred to a separate Step14 because it introduces real-network and device-safety concerns.
- Step12 remains historical evidence. Its documents are not rewritten to claim completion.
- Credentials are rotated by the repository owner or security owner. History rewrite is a separate explicit decision after rotation.
- The current Python CI matrix (3.11 and 3.12) is the support contract for this step unless the owner approves a broader matrix.
- No root prototype or `dev/hec/` product behavior is changed.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Define canonical `STEP.json` schema and schema validation | PLANNED |
| S02 | Implement `validate_step --phase ready` and `--phase done` | PLANNED |
| S03 | Add regression coverage proving Step12 cannot validate as DONE | PLANNED |
| S04 | Repair `new_step.py` and add focused generation tests | PLANNED |
| S05 | Validate machine-readable requirement, acceptance, plan, and evidence traceability | PLANNED |
| S06 | Migrate active VS Code and canonical validation references from Step11 to `dev/sdd/` | PLANNED |
| S07 | Migrate Copilot instructions, prompts, and role bindings to `dev/sdd/` | PLANNED |
| S08 | Move path-specific safety instructions to `.github/instructions/` | PLANNED |
| S09 | Add explicit agent tools and human-approved handoffs | PLANNED |
| S10 | Add mock Playwright to canonical full validation and cleanup | PLANNED |
| S11 | Emit machine-readable validation evidence from real commands | PLANNED |
| S12 | Add evidence-based PR renderer | PLANNED |
| S13 | Verify CI and configure `main` merge protection | PLANNED |
| S14 | Record and verify credential rotation/history-remediation owner actions | PLANNED |
| S15 | Human preview, reviewer approval, and Step13 dogfood completion | PLANNED |

## Detailed implementation strategy

### S01-S02 – Canonical manifest and enforcement phases

Objectives:
- Add `dev/sdd/schema/step.schema.json`.
- Make the validator reject missing/invalid canonical fields.
- Keep structural checks for all phases, with stricter ready and done rules.

Implementation:
- Define stable fields for step identity, classification, status, gates, readiness, requirements, acceptance, evidence, and notes.
- Use `--step` and `--phase` arguments with a deterministic default that validates all discovered steps structurally.
- Ready requires Gate A approval and complete planning mappings.
- Done requires `status=DONE`, `readiness=YES`, approved gates, completed mandatory Sxx/AC/mappings, result/evidence, and no blocker.

Risks:
- Existing historical manifests may fail stricter rules; preserve that behavior and test it explicitly.

### S03-S05 – Regression tests and traceability enforcement

Objectives:
- Make false-positive completion impossible.
- Verify orphan, missing, blocked, and unchecked mappings fail the appropriate phase.

Implementation:
- Add focused tests for Step12, valid/invalid manifests, acceptance checkboxes, plan statuses, evidence IDs, and traceability rows.
- Parse the controlled Markdown tables/IDs rather than relying only on substring presence.
- Keep the test fixtures free of credentials and runtime artifacts.

Risks:
- Overly permissive Markdown parsing could reintroduce false positives; include negative fixtures for each mandatory relation.

### S04 – `new_step.py`

Objectives:
- Generate a canonical next step without hardcoded `step12` assumptions.

Implementation:
- Use the same manifest schema as validation.
- Insert the new README row after the last `stepNN` row.
- Fail before modifying files if the target directory or README state is ambiguous.
- Add tests for numbering, schema, immutability, README insertion, and existing-target failure.

Risks:
- README formatting varies across historic rows; use a narrow row matcher and test the current file.

### S06-S09 – Canonical tooling and agent safety

Objectives:
- Ensure active developer workflows resolve through `dev/sdd/`.
- Ensure role boundaries are discoverable and enforceable where VS Code supports them.

Implementation:
- Update `.vscode/tasks.json`, `.vscode/launch.json`, repository instructions, planners, developers, reviewers, and prompt files.
- Move path-specific instruction files to `.github/instructions/*.instructions.md` with `applyTo` frontmatter.
- Retain stop conditions in prompt bodies and use only supported prompt metadata.
- Configure Planner handoff to Developer with human approval retained; keep Reviewer primarily read/test oriented.

Risks:
- Existing user customizations may be present in these files; preserve unrelated settings and validate references with a repository search.

### S10-S12 – Validation evidence and PR projection

Objectives:
- Make full validation exercise the same mock workflow used for merge decisions.
- Generate reproducible evidence and PR text from files, not narrative invention.

Implementation:
- Add mock Playwright invocation after mock preview/runtime smoke and before cleanup.
- Write `dev/sdd/.runtime/validation.json` atomically with command results and counts.
- Add `render_pr.py` that reads Step13 artifacts and validation evidence and writes `.runtime/pr_body.md`.
- Exclude runtime output and browser artifacts from Git.

Risks:
- A failed command must not be recorded as PASS; use explicit subprocess return codes and fail closed.

### S13 – CI and main merge protection

Objectives:
- Make failed tests or SDD validation block merge.

Implementation:
- Verify CI publishes stable names for Python 3.11, Python 3.12, and `sdd-validation`.
- Configure `main` to require pull requests, required checks, up-to-date branches, and no direct push bypass.
- Verify the configuration through GitHub API output and a controlled PR state.

Risks:
- Repository permissions or GitHub plan limits may prevent automation; record the exact blocker rather than weakening local enforcement.

### S14-S15 – Security ownership and dogfood

Objectives:
- Close or explicitly evidence external security actions.
- Run Step13 through ready, implementation, preview, review, and done states.

Implementation:
- Confirm credential rotation with the owner without recording secret values.
- Record the history-remediation decision and evidence in Step13 RESULT.
- Obtain human Gate B and Gate C approvals, update manifest and traceability, run complete validation, and verify `validate_step --phase done`.

Risks:
- Step13 cannot honestly be DONE while credential rotation, human preview, or review evidence is missing.

## Validation strategy

- Focused unit tests for `dev/sdd/tools/` and `new_step.py`.
- `python -m ruff check .`
- `python -m pytest -m "not e2e"`
- `python dev/sdd/tools/validate_step.py --phase ready --step dev/step13`
- `python dev/sdd/tools/validate_step.py --phase done --step dev/step13`
- `python dev/sdd/tools/validate_repo.py`
- canonical full validation with mock preview and mock Playwright.
- A real human preview is required for Gate B and is not replaced by automation.
