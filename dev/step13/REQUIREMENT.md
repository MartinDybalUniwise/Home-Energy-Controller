# Step 13 requirement

## Objective

Complete the HEC SDD enforcement workflow so that readiness and completion are machine-checkable, traceability is evidence-backed, active tooling uses canonical `dev/sdd/` paths, and merge protection requires the resulting validation checks.

## Scope

### In scope

- REQ-013-001: Define and validate one canonical `STEP.json` schema used by Step13 and future steps.
- REQ-013-002: Implement explicit ready and done validation phases with fail-closed gate and evidence rules.
- REQ-013-003: Add regression tests for historical incomplete evidence and for `new_step.py` generation behavior.
- REQ-013-004: Make `new_step.py` create the canonical manifest and insert the next step after the last existing step row without hardcoded step numbers.
- REQ-013-005: Move active validation, preview, VS Code, Copilot, prompt, and path-specific instruction references to canonical `dev/sdd/` locations.
- REQ-013-006: Enforce role boundaries through explicit agent tools and human-approved handoffs where the host supports them.
- REQ-013-007: Include mock Playwright in canonical full validation and produce machine-readable validation evidence from the actual run.
- REQ-013-008: Render a PR body as a projection of manifest, traceability, result, and validation evidence.
- REQ-013-009: Configure and verify `main` merge protection for required test and SDD checks without requiring an additional reviewer.
- REQ-013-010: Record security owner actions for credential rotation and history-remediation decision without handling secrets in repository files.
- REQ-013-011: Dogfood Step13 through the complete ready, implementation, validation, human preview, review, and done workflow.

### Out of scope

- REQ-013-OUT-001: LAN read-only preview implementation.
- REQ-013-OUT-002: Product logic, controller logic, storage contracts, or device write behavior.
- REQ-013-OUT-003: Git history rewrite without explicit owner approval after credential rotation.

## Non-functional requirements

- NFR-013-001: Validation is deterministic, fail-closed, and portable on Windows and Linux/Python 3.11-3.12 as currently supported by CI.
- NFR-013-002: Existing Step12 evidence remains historically accurate and is not rewritten to appear complete.
- NFR-013-003: Validation output is auditable through stable IDs, commands, timestamps, and status values.
- NFR-013-004: Changes remain limited to SDD tooling, development metadata, CI/repository configuration, and focused tests.

## Safety requirements

- TNG write gate remains disabled.
- `controller.enabled=false` remains required in preview/local validation.
- No physical-device writes.
- Safety-sensitive path-specific instructions must be automatically discoverable under `.github/instructions/**/*.instructions.md`.
- Full validation must clean up runtime and browser artifacts without tracking them.

## Risks

- R-013-001: A stricter done validator may expose historical steps that were merged before enforcement; this is expected and must be covered by regression tests.
- R-013-002: Branch protection configuration can accidentally lock out maintainers or require a check name that CI does not publish; verify through the GitHub API and a controlled PR.
- R-013-003: Prompt and agent tool metadata may vary by VS Code version; keep runtime-critical rules in repository instructions and validator checks.
- R-013-004: Security owner actions cannot be completed by code alone; record the external dependency and do not claim it is done without evidence.
