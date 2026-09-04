---
name: HEC finish PR
description: Produce an evidence-backed HEC pull-request summary.
agent: reviewer
argument-hint: Approved step directory
output: RESULT.md and PR body
stop-conditions: Do not create or submit a PR.
---

# HEC finish PR prompt

Review the actual diff against the approved requirement and plan. Run the
documented final validation where possible. Prepare `RESULT.md` and a PR body
containing source/step, planned and implemented work, deviations, exact
ruff/pytest/runtime/Playwright results, human-test status, controller/TNG/
GoodWe safety status, secrets/production-data status, limitations, and
follow-up. Use `NOT RUN` when a command was not run. Do not claim human testing,
push, or create a PR without explicit user instruction.
