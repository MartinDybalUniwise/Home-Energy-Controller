# Step 12 requirement

## Objective

Harden the Home Energy Controller SDD workflow so that repository hygiene, approval gates, traceability, preview safety, and CI enforcement are machine-verifiable and not merely described in documentation.

## Scope

### In scope

- Security cleanup for tracked credentials, runtime artefacts, and Git hygiene.
- Moving reusable development tools from `dev/step11/` to a canonical `dev/sdd/` platform.
- Standardizing SDD templates and workflow documents.
- Machine-readable step manifests and traceability.
- Automated step validation and repo hygiene validation.
- Explicit Copilot / agent role and tool hardening.
- Prompt metadata and path-specific safety instructions.
- Split preview modes: mock vs. LAN read-only.
- Python compatibility and CI gate alignment.
- Definition of Ready / Done and PR evidence generation.
- GitHub merge protection and ADR support.

### Out of scope

- Product feature refactors in `dev/hec/`.
- Controller logic redesign or optimization changes.
- Forecast/finance/business algorithm changes.
- New device-write logic or TNG bypasses.
- Broad repo-wide architecture rewrite unrelated to SDD hygiene.
- Any automatic physical-device writes.

## Functional requirements

- REQ-SDD-001: The repository must contain a reusable SDD platform under `dev/sdd/` and Step 11 must remain historical evidence only.
- REQ-SDD-002: Every LARGE step must have a canonical request, requirement, plan, acceptance criteria, traceability model, and step manifest.
- REQ-SDD-003: Validation must enforce missing gates, incomplete Sxx statuses, unresolved blockers, and missing acceptance evidence.
- REQ-SDD-004: Repo hygiene checks must reject forbidden tracked paths and common secret patterns.
- REQ-SDD-005: The system must distinguish mock preview and LAN read-only preview, with fail-closed safety validation before launch.
- REQ-SDD-006: Local preview testing and CI preview testing must both be supported, but CI must use deterministic mock-mode only unless a future explicit LAN-safe contract is approved.
- REQ-SDD-007: The TNG and GoodWe write-capable paths must remain disabled by default in local development and preview; other device writes are out of scope for this step.
- REQ-SDD-008: The workflow must preserve the Step11 human gate concept but make it machine-verifiable and evidence-backed.
- REQ-SDD-009: Git history cleanup must be included as part of the security remediation after credential rotation, not instead of it.
- REQ-SDD-010: Step 12 itself must be dogfooded under the workflow it introduces.

## Non-functional requirements

- NFR-SAFE-001: No credentials or secrets may be committed to the repo.
- NFR-SAFE-002: Production data, logs, runtime state, and browser artifacts must remain untracked.
- NFR-SAFE-003: Local preview must never enable write operations.
- NFR-SAFE-004: Workflow output must be deterministic and auditable.
- NFR-SAFE-005: Validation must fail fast and emit actionable blocks.
- NFR-SAFE-006: The solution must work on the existing Windows/Linux developer environments used by HEC.

## Safety requirements

- TNG write gates remain invariant: the confirmation cycle and 900-second minimum interval remain mandatory; no bypasses are allowed in this step.
- `controller.enabled=false` and `tng.write_enabled=false` remain required in local and preview modes.
- GoodWe write behavior stays disabled unless a future approved feature explicitly introduces controlled write capability.
- LAN read-only mode may ingest data from local home network sources, but all writes remain blocked.

## Data requirements

- Runtime data, logs, and history must not be tracked in the repo.
- Test fixtures must reside under a dedicated fixtures path and remain anonymized and deterministic.
- Validation output may be generated under ignored runtime folders only.

## Dependencies

- Existing Step11 workflow and safety profile.
- HEC docs and deployment boundaries in `dev/hec/docs/`.
- GitHub Actions / branch protection capability.

## Risks

- Credential exposure already happened in a public repo and must be treated as compromised until rotated.
- History cleanup is sensitive and must follow the security fix-first order.
- Local LAN preview can be non-deterministic if used without a strict read-only contract.
- Python compatibility can create false-negative CI failures if support matrix and tests are not aligned.

## Open questions

- Whether Git history rewrite is approved by the repo owner after credential rotation.
- Whether a mock Playwright job in CI is accepted as the default PR gate or only as a local check until stable.
- Whether future LAN preview will ever be enabled in CI or remain local-only.
