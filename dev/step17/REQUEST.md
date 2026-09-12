# Step 17 Request

## Objective

Complete the canonical Step17 planning package for a repository/SDD review step.
This request authorizes documentation work only: create the mandatory standard
files, align `dev/README.md`, and validate Step17 readiness. It does **not**
authorize application-code changes, root-prototype changes, runtime-config
changes, or any physical-device write path.

## Requested outcome

1. Create `REQUEST.md`, `REQUIREMENT.md`, `PLAN.md`,
   `ACCEPTANCE_CRITERIA.md`, `TRACEABILITY.md`, `STEP.json`, and `RESULT.md`
   under `dev/step17/`.
2. Use coherent Step17 identifiers:
   - requirements: `REQ-017-xxx`
   - acceptance criteria: `AC-017-xxx`
   - evidence: `E-017-xxx`
   - plan steps: `S01...`
3. Keep Step17 as a planning-only step: `PLANNED`, `readiness=YES`, Gate A
   approved, and no DONE claim.
4. Record that the repository sources of truth remain `CLAUDE.md`,
   `.github/copilot-instructions.md`, `dev/README.md`, `dev/sdd/README.md`,
   and the SDD validator/tooling under `dev/sdd/`.

## Explicit non-goals

- No `dev/hec/` application implementation
- No root prototype edits
- No secrets, runtime logs, or device data in Git
- No controller/TNG/GoodWe write enablement
