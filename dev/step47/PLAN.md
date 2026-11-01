# Coordinated comfort and battery planning - owner approved2026-11-01

Repair the measured06:44 failure without duplicate controllers, writers or UI policy.
Application.controller shares its fresh resolved thermal plan and TNG sample with
its existing battery planner. Keep exclusive DHW, TNG900s/confirmation guards,
42C water and21.7C room caps, PV vetoes, battery60%/20%/7kW limits and20% reserve.

1. Native grid charge windows may contain NT only. At a VT edge, immediately stop
owned charging through the existing audited writer; never restart it in VT.
All charge economics still require90% efficiency,0.30 wear and0.50 margin. The
purchase basis is a conservative planned ceiling, not measured cost or savings.

2. A fresh heating plan, fresh room<21.5, actual heating-enabled state and a local
VT price peak can release a held battery to20% General self-consumption. This
requires a still-profitable cheaper NT refill window within6h, with estimated
refill energy at the currently permitted charge power >=110% of current house
power extrapolated to the VT end. No capacity/heat/PV forecast is invented.
This is an explicit priority choice: cover present comfort before holding the
entire battery for a later peak, not a claim of globally optimal financial return.
Persist release to the current VT end to prevent re-locking/chattering on warming
or restart. Never force discharge/export. BMS/temperature/clock/data gates remain.
Lowering the reserve for a valid comfort release bypasses the command cooldown.
Without valid prices or battery safety, do not change General discharge reserves.

3. Record distinct room samples under confirmed21.7 thermostat requests and
exclusive heating. At a completed preheat, >=1h continuous observations and>=6
samples can conservatively extend subsequent lead time from2h up to4h when room
readiness21.5 was not reached. Measured rise estimates time to21.6 plus15min;
no rise uses4h, never a claim of measured heat inventory or compressor/COP data.
Discard unconfirmed, interrupted, stale/gapped and owner-edited plan evidence.
Learned lead expires after7days. Fit the longest feasible2-4h NT/exclusive cheaper
block; keep the ordinary comfort veto. Model does not guarantee readiness.

Replan only owned dates and remaining time; never rewrite missed night as executed.
Seed response from today's audited04:15 thermostat acknowledgement and measured
room samples; preserve TNG confirmation/telemetry/comfort state and purchase basis.
Two-hour reviews must check adaptation, release eligibility and physical response.
Prechange incremental snapshot:5f0087bae5674edcaa2579b860c6a8bb.

Current-day published lead is frozen; newly learned response updates future dates
without moving completed windows into the past. The repair cutoff prevents today's
missed preheat from appearing executed. Real-data offline replay at06:44 selects
20% reserve (not a hardware action), estimated remaining VT demand0.849kWh and
refill3.6kWh; charge window03:15-06:00 instead of03:15-06:15. The counterfactual
four-hour preheat would start02:00, not proof that it happened or would reach target.

Validation:201 broad regressions passed;80 thermal/coordination cases passed after
adding the published-day freeze check. Ruff and isolated real-day replay passed.
