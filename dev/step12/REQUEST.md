# Step 12 request

## Source

- Audit and requirement input: `HEC_STEP12_SDD_HARDENING.md`
- Repository context: `CLAUDE.md`, `dev/README.md`, `dev/step11/*`
- Scope boundary: HEC local development workflow, repository hygiene, and SDD enforcement.

## Requested by

- Repository owner / maintainer via project decision record.

## Original request

Implement Step 12 as the hardening pass for the HEC Spec-Driven Development workflow. The goal is to turn the Step 11 bootstrap from documented practice into an enforced, reusable, secure, and auditable workflow, without drifting into a product refactor.

## Business goal

Make the local HEC development process safe, repeatable, and enforceable before merge or PR completion.

## Decision summary

1. History cleanup is included in the scope and is treated as a security and hygiene task.
2. CI validation must cover deterministic mock preview and SDD validation; LAN preview remains local-only unless explicitly approved.
3. The write gate for physical devices is treated as a strict invariant for TNG and GoodWe; no broader device-write expansion is included in this step.

## Relevant constraints

- Do not refactor unrelated product code.
- Preserve `dev/hec/` architecture.
- Keep all write-capable devices disabled during local development.
- Never commit secrets, credentials, runtime data, logs, or browser artifacts.
- Keep Step 11 as historical evidence; Step 12 creates the reusable `dev/sdd/` platform.

## Supporting references

- `dev/step11/PLAN.md`
- `dev/step11/REQUIREMENT.md`
- `dev/step11/RESULT.md`
- `dev/hec/docs/API.md`
- `dev/hec/docs/DEPLOYMENT.md`
