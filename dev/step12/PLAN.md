# Step 12 plan

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Introduce a reusable, enforceable, and auditable SDD workflow for HEC without changing core product behavior. The step focuses on repository hygiene, process enforcement, preview safety, traceability, and automation. It must be implementable in a way that can be validated by CI and by local preview workflows.

## Decision log

### Decision 1 – history cleanup is in scope

Yes, we include history cleanup as part of Step 12.

Reasoning:
- The repository already contains committed secrets and production data in public history; this is a real security issue.
- Rotating secrets without cleaning Git history would leave the published secret material in the past history and reduce the protection value.
- Git history rewrite must happen only after credential rotation and is a controlled follow-up action, not a replacement for it.

Scope treatment:
- Step 12 handles the security cleanup and repo hygiene path together.
- The task includes a review of whether rewrite is necessary and approved, with the security fix-first order preserved.

### Decision 2 – CI + local preview validation

Yes, both are included, but with a strict split:
- CI uses deterministic mock preview and repo/SDD validation.
- Local preview may use LAN read-only validation with explicit safety enforcement.
- LAN-mode should not be promoted into CI unless it is explicitly fail-closed, deterministic, and safe for the environment.

Reasoning:
- A mock preview is the correct CI-safe validation path because it is deterministic and has no external dependencies or secret-bearing environment.
- A LAN read-only preview is valuable locally because it validates the application with real home-network sources without writes.
- A public CI runner should not depend on a local network or device topology unless the safety contract is formally approved and isolated.

### Decision 3 – TNG and GoodWe write gate

We explicitly preserve the write-disabled rule for TNG and GoodWe in local development and preview.

For this step:
- `tng.write_enabled=false` remains a hard invariant.
- `controller.enabled=false` remains required in local/preview validation.
- GoodWe write capability remains disabled by default and is not expanded in Step 12.
- No broader device-write scope is introduced in this step.

This matches the repository safety policy and avoids drifting into controller behavior changes.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Security cleanup and repo hygiene | PLANNED |
| S02 | Extract reusable `dev/sdd/` platform | PLANNED |
| S03 | Standard SDD templates | PLANNED |
| S04 | `STEP.json` manifest | PLANNED |
| S05 | Traceability model | PLANNED |
| S06 | `new_step.py` | PLANNED |
| S07 | `validate_step.py` | PLANNED |
| S08 | `validate_repo.py` | PLANNED |
| S09 | Copilot agent hardening | PLANNED |
| S10 | Prompt frontmatter and binding | PLANNED |
| S11 | Path-specific safety instructions | PLANNED |
| S12 | Preview mode split and safety validation | PLANNED |
| S13 | Python compatibility and CI alignment | PLANNED |
| S14 | CI SDD gate | PLANNED |
| S15 | GitHub main protection | PLANNED |
| S16 | Definition of Ready / Done | PLANNED |
| S17 | ADR support | PLANNED |
| S18 | PR renderer from evidence | PLANNED |
| S19 | Runtime validation evidence | PLANNED |
| S20 | Dogfood Step 12 itself | PLANNED |

## Detailed implementation strategy

### S01 – Security cleanup and repo hygiene

Objectives:
- Remove tracked credentials and production runtime artefacts.
- Harden `.gitignore` and repo hygiene conventions.
- Ensure local developer data remains local, but repository state is clean.

Implementation:
- Remove `connect.json` from the tracked repository state.
- Add `connect.json` and `.env` to `.gitignore` if not already covered.
- Remove tracked `data/`, `logs/`, `history/`, `archive/` files from Git tracking and preserve them locally.
- Move test fixtures to a dedicated fixture path if they are needed.
- Add repo hygiene checks and secret-pattern scanning.

Risks:
- If secret rotation is not done in parallel, the repo remains insecure despite removing files from Git.
- History rewrite requires owner approval and must be treated separately from the immediate secret rotation.

### S02 – Extract reusable SDD platform

Objectives:
- Move `preview.py`, `full_validation.py`, runtime paths, and config fixtures out of `dev/step11/` into a stable `dev/sdd/` platform.
- Keep Step11 as historical evidence only.

Implementation:
- Create `dev/sdd/` with `README.md`, templates, tools, config, runtime, and validation scripts.
- Move and refactor `dev/step11/preview.py` to `dev/sdd/tools/preview.py`.
- Move and refactor `dev/step11/full_validation.py` to `dev/sdd/tools/full_validation.py`.
- Update task definitions and developer docs to reference the new path.

Risks:
- Hidden dependencies on `dev/step11` may be missed if the migration is done too quickly.

### S03 – Standard templates

Objectives:
- Create consistent, reusable SDD artifacts.
- Make request, requirement, plan, and acceptance output structurally consistent.

Files:
- `dev/sdd/templates/REQUEST.md`
- `dev/sdd/templates/REQUIREMENT.md`
- `dev/sdd/templates/PLAN.md`
- `dev/sdd/templates/ACCEPTANCE_CRITERIA.md`
- `dev/sdd/templates/TRACEABILITY.md`
- `dev/sdd/templates/RESULT.md`

### S04 – Machine-readable manifest

Objectives:
- Add `STEP.json` to each LARGE step.
- Avoid markdown-only state.

Implementation:
- Define JSON structure with `step`, `classification`, `status`, gate states, and readiness.
- Keep `STEP.json` and markdown documentation in sync.

### S05 – Traceability model

Objectives:
- Treat requirement-to-evidence mapping as a first-class artifact.

Implementation:
- Add requirement IDs, AC IDs, step IDs, evidence IDs, and test IDs.
- Update `TRACEABILITY.md` with explicit mappings and blocked statuses.

### S06 – `new_step.py`

Objectives:
- Ensure every future step starts from a reusable template.

Implementation:
- Detect the last step directory.
- Create the next numbered step directory.
- Copy templates and populate `STEP.json`.
- Append a row to `dev/README.md`.
- Never hand-create a global structure by memory.

### S07 – `validate_step.py`

Objectives:
- Enforce workflow gates before a step is considered ready.

Checks:
- Required files are present.
- Gate A is approved before implementation.
- Plan contains substeps and required sections.
- Acceptance criteria exist.
- Traceability is complete.
- No mandatory Sxx remains `PLANNED`/`IN_PROGRESS` at completion.
- No unresolved blocker remains.
- README or manifest readiness is consistent with actual evidence.

### S08 – `validate_repo.py`

Objectives:
- Enforce repository hygiene as a technical gate.

Checks:
- Forbidden tracked files and folders.
- Secret patterns.
- Runtime output directories.
- Large or unexpected binary blobs.

### S09 – Copilot agent hardening

Objectives:
- Make role boundaries explicit for Planner / Developer / Reviewer.

Implementation:
- Define the tools and edit permissions per role.
- Require controlled handoff after approval.
- Prevent a reviewer from silently rewriting product code during review.

### S10 – Prompt metadata and binding

Objectives:
- Turn prompt files into explicit workflow components, not just text prompts.

Implementation:
- Add frontmatter with `name`, `description`, `agent`, `argument-hint`, `output`, and stop conditions.
- Bind each prompt to the relevant role.

### S11 – Path-specific safety instructions

Objectives:
- Add targeted safety guardrails for risky modules.

Implementation:
- Add instructions for `dev/hec/controller/**`, the TNG write path, and config/secret paths.
- Require any change in these areas to be treated as `LARGE` and to include regression tests.

### S12 – Preview mode split and fail-closed safety validation

Objectives:
- Separate mock preview from LAN read-only preview.

Implementation:
- `preview.mock`: deterministic, no local network, no physical device access.
- `preview.lan`: real read-only data sources only, strict no-write contract.
- Before app startup, run a fail-closed safety validation.
- Refuse startup if `tng.write_enabled=true` or if a dangerous combination is detected.

Risks:
- Over-broad “enabled=true” logic may incorrectly classify read-only sources as dangerous.
- The safety validator must distinguish read capability from write capability and must be intentionally strict.

### S13 – Python compatibility and CI alignment

Objectives:
- Resolve the mismatch between documented support and actual CI/test behavior.

Implementation:
- Align the support matrix to the actual supported Python range.
- Fix platform-neutral test assumptions that fail on Windows.
- Keep the local developer standard working on default Windows Python versions.

### S14 – CI SDD gate

Objectives:
- Move enforcement into repository automation.

Implementation:
- Add a dedicated `SDD Validation` job in CI.
- Include:
  - repo hygiene checks
  - secret scan/pattern checks
  - SDD validation
  - traceability validation
  - mock preview run if stable
- Keep LAN read-only validation as a local-only or explicit opt-in job, unless a safe contract is approved.

### S15 – GitHub main protection

Objectives:
- Ensure the repo cannot bypass the process via direct merge.

Implementation:
- Verify and configure branch protection for `main`.
- Require PRs, required checks, and SDD validation pass before merge.

### S16 – Definition of Ready / Done

Objectives:
- Make the acceptance criteria explicit and canonical.

Implementation:
- Publish the ready/done conditions in `dev/sdd/README.md`.
- Make them machine-checkable where practical.

### S17 – ADR support

Objectives:
- Preserve key architectural decisions outside ephemeral chat history.

Implementation:
- Create `dev/adr/` and add entries for important long-lived decisions.

### S18 – PR renderer

Objectives:
- Generate PR content from real evidence instead of hand-crafted narrative.

Implementation:
- Build a script that projects from `STEP.json`, `PLAN.md`, `RESULT.md`, and `TRACEABILITY.md` into a generated PR body.

### S19 – Machine-readable validation evidence

Objectives:
- Avoid “PASS” claims without actual execution evidence.

Implementation:
- Put validation output under ignored runtime paths with a machine-readable schema.
- Use it to build `RESULT.md` and PR evidence.

### S20 – Dogfood Step 12 itself

Objectives:
- Prove Step12 works on itself.

Implementation:
- Execute the Step12 process from request through traceability into validation and evidence.
- Only mark the step ready after the complete workflow is executed.

## Final readiness rule

A step is ready only when:
- all required checkpoints are passed,
- all mandatory acceptance criteria have evidence,
- no gate remains open or undocumented,
- repo hygiene and secret checks pass,
- preview safety checks pass,
- and the result is supported by machine-readable evidence.

## Verification approach

For every major implementation phase:
- run `ruff check .` for Python changes,
- run relevant `pytest` targets,
- run the mock preview or relevant smoke checks,
- run the SDD validator,
- run repo hygiene validation,
- confirm no write gates are enabled in preview or local dev.

## Risk management

- The primary risk is security exposure from committed credentials and history.
- The second risk is workflow drift: step documentation becoming aspirational without enforcement.
- The third risk is preview confusion: conflating mock preview, LAN read-only mode, and write-enabled hardware behavior.

This step addresses all three explicitly and intentionally.
