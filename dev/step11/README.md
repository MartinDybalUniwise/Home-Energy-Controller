# Step 11 – AI-first development bootstrap

Step 11 adds a repeatable local, Spec-Driven Development workflow for HEC. It
is development infrastructure, not an energy, forecast, finance, or device
control feature. It keeps the existing `dev/hec/` application and frozen root
prototypes intact.

The bootstrap contains repository instructions, planner/developer/reviewer
roles, reusable prompts, an isolated read-only preview on port 8181, VS Code
tasks, Python Playwright smoke tests, fail-fast validation, and PR evidence
templates.

**Status:** implemented; automated validation is recorded in `RESULT.md`.
Human preview testing remains an explicit gate and is not claimed here.

Start with [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md), then use
[`AI_DEVELOPMENT_WORKFLOW.md`](AI_DEVELOPMENT_WORKFLOW.md) for future changes.
