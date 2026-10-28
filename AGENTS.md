# HEC — standing owner authorization

For HEC status reports and scheduled reviews, read and apply skills/hec-status/SKILL.md.

The repository owner explicitly approved autonomous project work on 2026-10-28.
No repeated human approval is needed for ordinary implementation, tests, commits,
pushes, PRs, conflict resolution, merging after required checks pass, incremental
backups, deployment, service restart or configuration/day-plan changes within the
owner's requested scope. Keep plans and validation evidence; standing approval
satisfies project-specific human gates for that scope.

Keep brief progress updates. Ask only for indispensable missing information.
Platform restrictions and Windows access controls still apply. Report actual
blocks accurately; never claim an unperformed action succeeded.

Production is C:/TepelneCerpadlo/Home-Energy-Controller. Use only its existing
HomeEnergyController service. The owner account has service START/STOP and Modify
access to C:/TepelneCerpadlo/hec-release-backups for unattended work. Follow the
supported incremental backup procedure before deployments, without full-history
copies/scans. Preserve private configuration, telemetry, runtime state and the TNG
confirmation cycle and 900-second write guard. Never commit secrets or telemetry.

C:/TepelneCerpadlo/odlozene-logy is frozen: exclude it before entry. Do not read,
scan, modify or back up its contents. Skip diagnostic log contents older than 7 days.

Owner preferences: avoid overheating an already comfortable house; prioritize
heating-water comfort and solar hot-water storage for evening showers. Use dated
overrides for daily plans. Take absolute power for the Shelly heat-pump meter and
retain signed raw readings; preserve other meters and unrelated fault detection.
Put routine UI explanations behind clickable info. Retain timestamps and clear
measurement/estimate labels. Refresh overview values without whole-page flashing.

Two-hour reviews may adjust the current-day plan from fresh data and must always
send a concise graphical mobile-friendly report to the chat.

If a real approval is unavoidable, post a prominent graphical mobile-friendly notice in this chat stating the blocked action, exact approval needed, reason and next user action. Do not bury it in routine status text.
Status requests: lead with a concise mobile graphical report showing current actual state, measured evolution, and the plan for today by default (tomorrow/day after only when explicitly requested). Always retain current state. Below the visualization place two short side-by-side columns: verbal assessment and recommendation. No long prose.

Operational rules are maintained in dev/hec/web/frontend/hec-rules.json and shown at /#/rules. Read this registry before changing HEC plans. Never enable heating and DHW simultaneously: use tng.operation exclusive heating/boiler windows with bounded DHW duration. Keep this registry and its change log updated when the owner adds a rule. Use compact, colourful graphical status and plan views.

Sensor invariant: water_output_temperature is the TNG heat-pump outlet (tw), not floor-loop water, buffer storage or floor surface. No separate floor-loop sensor is currently provided. Never infer floor temperature/comfort or stored heat from that field alone; heating_set_temperature is a requested setpoint.
