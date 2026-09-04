# Step 13 request

## Summary

Step12 created the reusable `dev/sdd/` platform, but its validators currently check mostly file structure. A step can therefore appear valid while its gates, acceptance criteria, traceability, implementation status, and evidence are still open. Step13 completes the machine-enforced SDD workflow and uses the workflow on itself.

The outcome is a fail-closed ready/done process: incomplete evidence cannot be presented as done and the repository cannot merge the implementation without the required checks.

## Scope

- In scope:
  - one canonical `STEP.json` schema and schema validation;
  - `validate_step.py --phase ready|done` with gate, status, traceability, evidence, and blocker enforcement;
  - regression coverage proving historical Step12 is not falsely DONE;
  - robust `new_step.py` generation and focused tests;
  - migration of active VS Code, Copilot, prompt, and path-specific instruction references from Step11 to `dev/sdd/`;
  - explicit agent tools and handoffs where supported;
  - Playwright in canonical full validation;
  - machine-readable validation evidence and evidence-based PR rendering;
  - documentation and CI/branch-protection requirements for the merge gate;
  - security owner actions recorded and verified without exposing credentials.
- Out of scope:
  - LAN read-only preview implementation, planned for a separate safety-sensitive step;
  - changes to `dev/hec/` product behavior or device integrations;
  - physical-device writes, TNG controller behavior, or bypassing the 900-second write interval;
  - rewriting Git history unless credentials are rotated and the repository owner explicitly approves it.

## Safety constraints

- `controller.enabled=false` in local and preview development.
- `tng.write_enabled=false` in local and preview development.
- No physical-device writes or network write-capable integrations.
- No secrets, tokens, credentials, runtime data, logs, or Playwright artifacts in Git.
- Root production prototypes remain unchanged.
- Branch protection changes are configuration work and must be verified without weakening the merge gate.

## Acceptance signal

The Step13 implementation is ready for human approval when `validate_step.py --phase ready` passes for Step13. It is done only when `validate_step.py --phase done`, repository hygiene, Ruff, unit tests, mock preview, runtime smoke, and Playwright mock validation all pass; machine-readable evidence and the PR body are generated from those results; required checks are configured; and Gate C is approved. The historical Step12 manifest must continue to fail the done phase.
