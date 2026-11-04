# Daily-review optimisation - owner approved2026-11-04

Evidence: daily reviews Nov1/2, calendar Nov3 review, Nov4 two-hour reviews,
calendar summary/command files Nov1-4 and live snapshot Nov4 19:06 Prague.
Prechange incremental backup:6a8448425cd7402a9b0045e3f8de55ab.

One Application.controller, existing TNG/GoodWe writers, unchanged900s/ack gates,
exclusive modes,42C water,24C temporary room and60%/20% battery charge limits.
No extra scheduler, LAN probing, manual plan rewriting or retrospective commands.

- Battery: reserve configured-capacity/current-house-load estimated energy for a
  sustained later one-hour peak materially dearer by>=0.60CZK and>=8%. Release
  surplus/current peak demand naturally via General. Preserve comfort/refill
  exception, hold expiry, BMS/clock/manual-mode limits and no forced export.
- Floor: evaluate hourly; warm store>=38C with room>=21.5, safe price coast or
  prior timeout defer a new pulse to at most120min idle. Room<=21.3 or qualified
  AKU<35 prevents postponement. Preserve bounded45min reheat; coast may restore
  after15min when no below35 observation exists and present AKU is not cold.
- Confirmation: update transport gates before resolving the plan. A clear,
  matching thermostat readback prevents reopening the gate after restart. Fresh
  direct settings readback can complete restoration even when room telemetry is
  stale; never infer confirmation from a POST. Publish restoration wait/delay.
- Comfort: slow fresh cooling near21.2C activates recovery before another15min
  below21. Sudden ventilation delay, stale-data rules and explicitoff retained.
- DHW: only second ordinary bounded boiler window with target<=50C can skip
  switching when fresh boiler probe>=target; resume at target-2C. Preserve first
  window, hygienic/higher targets and dated owner overrides. Probe is not proof
  of usable hot-water volume. Readiness storage failure retains ordinary plan.
- Forecast: recent matching-day median (>=3 recent examples), bounded empirical
  whole-house weather response where data supports it, or measured heating
  decomposition where valid. House totals include heating once. Today uses
  fresh same-day GoodWe load counter plus explicitly estimated remainder; stale
  counters never become zero or yesterday's consumption. Invalid Shelly gives
  no COP/heat-meter claim. Configured capacity/future demand remain estimates.

Validation must include guarded TNG transitions, forecast no-double-counting,
price peak retention/comfort override, floor deferral limits and DHW hysteresis.
Do not erase runtime/purchase/cycle/confirmation state during deployment.

Final validation:214 regressions passed across optimisation scenarios, battery
economics/comfort coordination, floor state, cloud adapter900s/ack gates, price
planning, predictive comfort, forecasts, config and API. Ruff, Python compilation,
JSON and diff checks passed. Real-data read-only replay protects noon SOC45 for
the sustained16h peak. Corrected today's forecast~55kWh includes measured~49.6.

Thermostat idempotency requires matching full-template SHA256 recorded with the
original POST plus clear native gate and matching readback. A changed night/profile
template still goes through the normal writer. Legacy gates without a fingerprint
retain the normal guarded POST behaviour; no fabricated confirmation/migration.
Historical signed/unqualified HP energy cannot teach a heat slope; measured heat
decomposition requires explicit valid-sample quality. Reject empirical weather
fits with negative baseline; fall back to recent whole-house median.
