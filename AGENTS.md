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

The owner confirmed the desired heating-store reading is AKU/buffer temperature. The physical panel has a distinct buffer sensor (owner photo 40.2 C); current cloud history exposes only t/tw/tb/tt. Do not claim the hardware lacks an AKU sensor. Live AKU now comes from the independent receive-only tng_wire mirror (fresh <=180 s, valid field quality). Never substitute outlet or a photo. Cloud tng control remains unchanged; unverified passive fields are not control inputs. See dev/hec/docs/TNG_WIRE.md.

Owner clarification 2026-10-28: Direct LAN TNG access is READ-ONLY. Existing cloud API control remains authorised and enabled. Local investigation is explicitly paused until the owner supplies further information/credentials; do not probe the LAN controller while paused.

Owner-approved 2026-10-30: tng.price_shift.enabled activates conservative price/FTE
planning (dev/step39/PLAN.md). Preserve planner-owned dated heating/thermostat
overrides during routine reviews; do not flatten them to constant42 merely to
restore a schedule. Check sources.tng.price_shift for the effective comfort/solar
veto, distinct from the saved plan. A deliberate edit of either dated schedule
opts that date out of automatic rewriting. DHW and ordinary schedules are separate.

Owner-approved unification2026-10-30: Application.controller is the sole production
planning authority (dev/step40/PLAN.md). TNG is its transport with unchanged gates;
controller.enabled is the master switch. Retired individual thermal rules must
never issue additional commands. GoodWe actuation remains separately disabled to
preserve existing battery/grid operation. Review status.controller.thermal_plan
and the saved dated schedules; a resolved plan is not a sent/confirmed command.

Repair2026-10-31 (dev/step43/PLAN.md) supersedes the original daily-median/90-minute
price policy: local preceding-six-hour comparison, gap>=0.60 CZK/kWh and8%, later
nearly-cheap two-hour preheat, coast<=3 h with the same21.3 C comfort veto. Preserve
revised_at cutoffs: never turn a counterfactual missed night into an executed plan.

Mobile report correction 2026-10-28: the owner phone displays local visualize directives as raw text. Use native mobile Markdown with status emoji, compact state/trend/plan blocks and a short Assessment | Recommendation table for scheduled and mobile reports. Never send local HTML paths or visualize directives in these reports. The full report must be readable in chat without opening files.

Owner-approved2026-10-31 battery control supersedes the disabled-GoodWe statement
above. The same Application.controller now exclusively selects economic battery
planning (dev/step44/PLAN.md); never activate legacy battery/export rules alongside
it. Grid charge ceiling60%, power<=20%, model efficiency90%, wear0.30 CZK/kWh and
net margin>=0.50 CZK/kWh. Leave PV headroom, hold bought energy for dear periods,
release via General self-consumption, never forced grid export. Preserve TNG gates.
Existing two-hour reviews MUST follow the expanded checks in skills/hec-status:
prices, comfort, measured PV/SOC/power, native charge schedule/readback, TNG actual
acknowledgement and behaviour. Every review sends its own dated mobile report.

Owner clarification2026-10-31: one inverter configuration, one unified controller.
Plan views are read-only projections of status.controller.battery_plan; never add
UI price optimisation, another writer/controller or an independent battery timer.
Hide inactive legacy battery configuration in economic mode. Reject retired-rule
actuation while economic mode owns GoodWe. See dev/step45/PLAN.md.

Owner-approved2026-10-31 EVV1/D57d distribution-aware pricing (dev/step46/PLAN.md).
Use core.electricity_price.load_priced_day for all plans/API consumers; do not use
cached total prices without projecting current configuration. One NT/VT config,
no SDG duplicate controls. Check distribution_pricing.valid and validity dates.
Reviews must verify exported EVV1 times against distributor changes; preserve
owned schedules and comfort gates. Configured fees are not verified supplier fees.
