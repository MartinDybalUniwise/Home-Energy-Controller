# Step40 — one production planning authority

Owner authorised implementation/deployment and routine requirement decisions on2026-10-30.

## Decisions

- Application has exactly one Controller. It owns the thermal resolver, dated price
  plan, exclusive heating/DHW policy, comfort guard and measured FTE surplus veto.
- TngReader only reads the cloud, persists existing runtime state and executes the
  resolved target through the existing basic/thermostat gates and900 s guard.
  Application binds its planner to the same Controller before starting any threads.
- Retire default dhw_pv_surplus, dhw_price_high and heating_preheat_cheap rules.
  Their old single-action dispatch is rejected even if injected or called directly.
  Compatibility imports and standalone unit adapters use the same resolver implementation,
  not a second policy. Bound production adapters reject one-off target requests.
- One master controller.enabled switch stops automatic TNG planning/writes. Disabling
  automation does not physically turn off the heating; the device retains its settings.
- Preserve the currently accepted price/FTE plan and all bounded DHW windows. Do not
  redesign DHW demand or claim known heat inventory during an architectural migration.
- Keep the inverter in its prior operating mode. The previously disabled generic controller
  had latent GoodWe commands enabled, including export limit0 W. Migration explicitly
  disables controller.optimization.goodwe_control.enabled before enabling the master.
  No new battery/grid actuation is authorised by the act of enabling the common planner.
- Thermal data validity is checked in the thermal resolver, independently from optional
  inverter rule prerequisites. Missing price/PV data cancels economic modulation while
  retaining the accepted comfort fallback. Never use passive uncertain sensors or partial
  Shelly power as control inputs. Cloud failure retains the last device settings until recovery.
- Keep legacy JSON formats, environment references and tng_runtime_state.json gates,
  comfort timing and solar latches. No reset to bypass confirmations.
- Controller history stores plan_tng as a resolved target with applied=false. Sent,
  device-acknowledged commands remain separate in tng_commands. Do not equate them.
- Repair only the misleading control status cards and display resolved plan values as
  human-readable values, not [object Object]. No layout redesign or new UI workflow.

## Verification and release

- Prechange incremental snapshot: b91d7d336df7461e9f808402a43ad659.
- Test single basic write, competing-path rejection, master disable, comfort over DHW,
  explicit off, stale-data fallback, GoodWe opt-in and Application singleton binding.
- Run backend regressions, i18n/schema/API checks and existing TNG gate/price/comfort tests.
- Compile changed modules with production Python3.13; verify JS syntax and actual status page.
- Commit exact code before supported incremental release backup. Stop the existing service,
  capture latest runtime data, enable unified control with inverter actuation off, restart the
  same service and verify new controller owner/status, unchanged daily plan and fresh telemetry.
- Rollback: restore the saved prechange code/configuration and preserve the latest device
  acknowledgement state; never clear gate fields or restore a stale gate while the device runs.
