---
name: HEC small fix
description: Implement a validated small HEC correction.
agent: developer
argument-hint: Fault description or failing test
output: Minimal fix and validation evidence
stop-conditions: Return to planning if the change is LARGE.
---

# HEC small fix prompt

Read `CLAUDE.md` and inspect the affected code and tests. Confirm this is a
SMALL change with no architecture, API/storage, controller, write, or security
impact. Find the root cause, implement the minimum safe change, preserve i18n
and portability, then run ruff and relevant pytest tests. Run Playwright when
the UI is affected. Report the exact commands, results, and limitations.
