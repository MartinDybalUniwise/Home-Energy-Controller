---
name: HEC new feature
description: Plan a traceable HEC feature without implementation.
agent: planner
argument-hint: Requested feature or outcome
---

# HEC new feature prompt

A new user development request is never implicit authorization to implement.
Treat this as a LARGE change unless analysis proves it is SMALL. Read
`CLAUDE.md`, relevant HEC docs, and the canonical `dev/sdd/` workflow. Analyze the requirement,
identify affected modules, safety/i18n/portability risks, and tests. For SMALL
work, produce a short plan and wait for explicit approval; for LARGE work,
create or update `REQUIREMENT.md`, `PLAN.md`, and `ACCEPTANCE_CRITERIA.md`
with traceable `S01...SNN` steps. **Stop for human approval. Do not implement
code before approval.**
