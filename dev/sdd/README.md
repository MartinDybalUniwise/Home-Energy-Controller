# SDD platform

This directory holds the reusable process and safety tools for Home Energy Controller development.

The purpose is to make step creation, validation, and evidence generation consistent across the repository without changing `dev/hec/` product code.

## Safety invariants

- `controller.enabled=false` in local and preview development
- `tng.write_enabled=false` in local and preview development
- `goodwe.enabled` remains disabled in preview unless a future explicit feature is approved
- no physical write path is enabled by default
- CI validation must be deterministic and fail-closed

## Threat model

HEC is a private, single-owner home system operated by one trusted
administrator. Trusted actors are: the local HEC administrator, anyone with
filesystem/repo access, anyone able to run Python/PowerShell on the HEC host,
and the owner deliberately editing config or running a service command.
Deliberate bypass of application-level protection by a trusted administrator
is out of scope and must not be treated as a defect.

Typical failure impact is a suboptimal electricity purchase/sale (low
thousands of CZK at most), a poorly heated hot-water tank, a temporarily too
warm/cold house, or the need for a manual fix. These impacts alone are never
grounds for an enterprise/security BLOCKER.

## Severity model

- **BLOCKER** - realistic risk of device damage, uncontrolled/repeated
  physical writes, a write to the wrong device, major loss/corruption of
  production data or config, secret leakage, inability to start the
  application, a major regression of a core function, or an irreversible
  operation without a conscious human step. Every BLOCKER must state a
  concrete, realistic failure scenario and its impact.
- **IMPORTANT** - a real functional defect that meaningfully degrades normal
  operation but can be safely fixed manually or by disabling the feature.
- **MINOR** - robustness, edge cases, UX, observability, docs, traceability,
  naming, extra tests.
- **FUTURE HARDENING** - defense-in-depth or security hardening against a
  trusted administrator, cryptographic signing, immutable evidence, extreme
  edge cases. Requires full local admin/code-execution access to exploit.

MINOR and FUTURE HARDENING findings must never block S06/S07/Human Gate/DONE.
A finding that only matters if a trusted local admin deliberately bypasses the
system must be classified as FUTURE HARDENING at most.

## Included tooling

- `new_step.py` creates the next numbered step from templates
- `validate_step.py` checks that a step is structurally complete and traceable
- `validate_repo.py` checks repo hygiene and secret exposure risks
- `preview.py` handles mock and LAN read-only preview startup/safety validation
- `full_validation.py` runs the repository validation workflow

## Workflow

1. Choose the next step number.
2. Analyze and classify the request as SMALL or LARGE.
3. For SMALL requests:
   - prepare a chat plan,
   - wait for explicit human approval,
   - only then implement.
4. For LARGE requests:
   - create the step package BEFORE Gate A using:
     `python dev/sdd/tools/new_step.py`
   - complete REQUEST, REQUIREMENT, PLAN, ACCEPTANCE_CRITERIA,
     TRACEABILITY, STEP.json and RESULT,
   - run structural and ready validation,
   - leave Gate A as PENDING,
   - STOP and request human approval.
5. Gate A is approval of the completed planning package.
6. Only after explicit human approval:
   - set gate_a.status = APPROVED,
   - implementation may begin.
7. Developer implements only the approved scope.
8. Developer runs automated validation and stops before Human Gate.
9. Reviewer verifies implementation against requirements,
   acceptance criteria, traceability and safety.
10. Human Gate is required before DONE.
11. Only after all required gates and evidence pass may the step be marked DONE.

Changed-step CI validation follows the manifest lifecycle: planned or
in-progress steps must pass the `ready` phase, while steps marked `DONE` must
pass the stricter `done` phase.

## Definition of ready

A new request never implies implementation. Before any application code edit,
a human must approve the plan. SMALL changes require a short chat plan and
explicit approval; LARGE steps require their request, requirement, plan,
acceptance criteria, traceability matrix, and `STEP.json` manifest. The plan
must identify substeps, risks, validation, and an explicit approval gate.

## Definition of done

A completed step has passing repository and step validation, evidence for each
mandatory acceptance criterion, a filled `RESULT.md`, and no unresolved
blockers. Automated checks never substitute for a human hardware test.

A BLOCKER raised during review must name a concrete realistic failure
scenario within the defined threat model; findings outside that model do not
block DONE.

## UI validation rule

For UI steps, automated validation is valid only when real browser E2E tests
actually execute against the running preview.

A skipped E2E suite is NOT PASS.

A UI step cannot proceed to Reviewer or Human Gate when:
- the page remains in a loading state,
- browser console contains application JavaScript errors,
- required controls are not interactable,
- Playwright reports failures or the suite is skipped.