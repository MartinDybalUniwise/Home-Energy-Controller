# Step 14 requirements

## Title

SDD Operational Closure

## Problem

Step13 introduced the canonical SDD tooling, but the repository can still accept
an incomplete workflow in several ways: CI does not enforce the DONE phase for
changed steps, the PR renderer can project incomplete evidence, the generated
manifest is not guaranteed to match the canonical schema, and the merge gate is
not protected by repository settings. A deterministic locale test is also
currently red in CI.

## Objective

Ensure that every changed active step is either genuinely complete or is
blocked before merge, with deterministic tests, current evidence, explicit
human-gate semantics, and protected GitHub checks.

## Outcome

Close the remaining operational gaps without redesigning the SDD platform. A
changed LARGE step must be complete, validated, and backed by current evidence
before its PR can be merged. The workflow must remain honest: Step13 stays
historical and incomplete where its evidence is incomplete, while Step14
proves the corrected process on itself.

## Scope

### In scope

- deterministic Czech and English Playwright navigation tests;
- phase-aware acceptance validation, including a valid completed synthetic step;
- schema-compatible manifests from `new_step.py`;
- changed-step DONE validation in CI;
- GitHub `main` branch protection and required checks, verified through the
  repository configuration and a controlled PR workflow;
- explicit Gate A, Gate B, and Gate C lifecycle semantics;
- a justified `NOT_REQUIRED` state for human gates where applicable;
- real VS Code agent handoffs and reviewer tool-contract alignment;
- generic, guarded, and current-commit-aware PR rendering;
- validation evidence bound to the current Git commit;
- README status generated or checked against `STEP.json`;
- non-secret evidence for security-owner actions from Step13;
- Step14 dogfooding through the complete validation and done workflow.

### Out of scope

- LAN read-only preview or any new physical-device integration;
- changes to `dev/hec/` product behavior;
- physical-device writes, TNG writes, controller writes, or bypassing the
  900-second TNG interval;
- rewriting Git history without an explicit repository-owner decision after
  credential rotation;
- broad SDD redesign after the operational gaps in this requirement are closed.

## Safety constraints

- Keep `controller.enabled=false` and `tng.write_enabled=false` in all local,
  preview, and CI validation environments.
- Do not call write-capable device APIs.
- Do not store credentials, tokens, production data, logs, browser artifacts,
  or runtime caches in Git.
- Record only security-action facts such as confirmation, actor, and timestamp;
  never record secret values.
- Do not alter frozen root prototypes.
- Preserve atomic writes, ISO 8601 timestamps with timezone, i18n behavior,
  and Windows/Linux/Raspberry Pi portability.

## Lifecycle decisions

- Gate A means plan approval before implementation.
- Gate B means human preview or explicit `NOT_REQUIRED` with a reason when no
  user-visible or runtime behavior is affected.
- Gate C means owner approval to create the final PR. GitHub required checks
  and branch protection control merge eligibility after the PR exists.
- A gate with `NOT_REQUIRED` must include a non-empty reason and must not be
  used to bypass a required safety or human validation step.
- Step13 remains historical evidence and is not rewritten to claim DONE.

## Dependencies

- Step13 canonical schema and validator remain available.
- GitHub repository administration access is available for branch protection.
- The repository owner can confirm security actions without sharing secrets.
- CI can run Python 3.11, Python 3.12, mock preview, and mock Playwright.

## Requirement IDs

- REQ-014-001: CI locale validation is deterministic and green.
- REQ-014-002: DONE validation accepts a genuinely complete step and rejects incomplete steps.
- REQ-014-003: New steps are generated with schema-compatible canonical manifests.
- REQ-014-004: CI validates only changed active steps at the DONE phase before merge.
- REQ-014-005: `main` requires pull requests and all required checks.
- REQ-014-006: Gate lifecycle and `NOT_REQUIRED` semantics are explicit and enforceable.
- REQ-014-007: Agent handoffs and reviewer capabilities match their contracts.
- REQ-014-008: PR rendering refuses incomplete or stale validation evidence.
- REQ-014-009: Validation evidence identifies the commit and cannot be reused stale.
- REQ-014-010: Repository workflow status has one source of truth.
- REQ-014-011: Step13 security-owner actions are evidenced without secrets.
- REQ-014-012: Step14 completes its own ready, validation, review, and done gates.

## Completion boundary

Step14 is complete only when all mandatory acceptance criteria pass, the final
validation evidence matches `HEAD`, the required GitHub checks are green, the
repository merge gate is verified, and Step14 itself has status `DONE` with
Gate A approved, Gate B approved or justified `NOT_REQUIRED`, and Gate C
approved. LAN read-only preview remains a later independent step.
