# AI-first development workflow

The standard path for future HEC changes is:

```text
Requirement
→ Plan
→ Human approval
→ Development
→ Static/unit/integration tests
→ Local safe preview
→ Playwright (for UI changes)
→ Human test
→ Feedback
→ SMALL fix or LARGE re-plan
→ Retest
→ Result
→ PR
```

## Change classification

**SMALL** means a contained text, CSS, validation, test, or local bug fix with
no architectural, API, storage, controller, or safety impact. Analyze,
implement the minimum, test, and report.

**LARGE** means a new module/data source, contract/storage/API change,
controller/write/security behavior, architectural change, or substantial UI
redesign. Create or update `REQUIREMENT.md`, `PLAN.md`, and
`ACCEPTANCE_CRITERIA.md`, split work into `Sxx`, and stop at Gate A.

## Roles and gates

The planner produces scope and stops for approval. The developer implements
only the approved plan and never performs hardware writes. The reviewer checks
requirement/plan/diff, safety, i18n, tests, and evidence; it does not perform
unrelated cleanup.

Automated validation may say `PASS`, but only a person can pass Gate B. A PR
requires Gate C and an explicit user request.

## Safe operating rules

Read `CLAUDE.md` first. Preserve root prototypes, the TNG confirmation cycle
and 900-second minimum, i18n, secret handling, and Windows/Linux/Pi
portability. Use fixtures or disabled readers when hardware is unavailable.
Never infer a successful human test from browser automation.
