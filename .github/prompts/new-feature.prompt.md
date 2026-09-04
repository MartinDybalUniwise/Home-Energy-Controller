---
name: HEC new feature
description: Plan a traceable HEC feature without implementation.
agent: planner
argument-hint: Requested feature or outcome
output: Requirement, plan, acceptance criteria, and traceability
stop-conditions: Stop at the human approval gate.
---

# HEC new feature prompt

Treat this as a LARGE change unless analysis proves it is SMALL. Read
`CLAUDE.md`, relevant HEC docs, and Step11 workflow. Analyze the requirement,
identify affected modules, safety/i18n/portability risks, and tests. Create or
update `REQUIREMENT.md`, `PLAN.md`, and `ACCEPTANCE_CRITERIA.md` with traceable
`S01...SNN` steps. **Stop for human approval. Do not implement code before
approval.**
