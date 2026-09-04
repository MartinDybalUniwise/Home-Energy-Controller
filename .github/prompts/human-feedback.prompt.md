---
name: HEC feedback triage
description: Classify and safely process HEC human feedback.
agent: planner
argument-hint: Human feedback and affected step
output: Classification and approved-scope update
stop-conditions: Stop for approval before LARGE implementation.
---

# HEC human feedback prompt

Classify the feedback as **SMALL** or **LARGE** before editing. A small fix is
not immediate authorization to implement. Default behavior is:
`analyze → short plan → WAIT FOR APPROVAL → implement`.

For SMALL feedback (text, layout, validation, contained bug): analyze the
relevant files, classify as SMALL, produce a short change plan, wait for
explicit approval, then implement the minimum fix, run relevant tests and
Playwright for UI, and update result evidence.

For LARGE feedback (new module/data flow, API/storage contract, controller or
write behavior, security, architecture, or major UI): stop, re-plan,
re-approve, and implement only after explicit human approval and the normal
large-change gate (`REQUIREMENT.md`, `PLAN.md`, `ACCEPTANCE_CRITERIA.md`,
Gate A).

Never infer a human PASS from automated checks.
