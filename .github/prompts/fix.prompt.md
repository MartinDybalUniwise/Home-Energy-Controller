---
name: HEC small fix
description: Implement a validated small HEC correction.
agent: developer
argument-hint: Fault description or failing test
output: Minimal fix and validation evidence
stop-conditions: Return to planning if the change is LARGE.
---

# HEC small fix prompt

Read `CLAUDE.md` and inspect the affected code and tests. Analyze before
editing. Treat every new request as `PLAN FIRST` by default.

Confirm this is a SMALL change with no architecture, API/storage, controller,
write, or security impact. Produce a short plan in chat: the intended change,
likely affected files, tests to run, and risk; then wait for explicit approval.
Only after approval may the agent implement the minimum safe change, preserve
i18n and portability, and run ruff and relevant pytest tests. Run Playwright
when the UI is affected. If the user explicitly says `Implement this directly`
or `No planning needed`, the planning gate may be skipped by explicit override;
otherwise default to `WAIT FOR APPROVAL`.

Report the exact commands, results, and limitations.
