# Step39 — conservative price and FTE heating shift

Owner approved implementation and deployment on 2026-10-30, including FTE/PV dependence.
No UI implementation. Register the operating rule in the existing rules registry.

## Strategy

- Keep exclusive heating/DHW operation, existing comfort guard and cloud TNG gates/900 s.
- Publish heating and thermostat dated overrides for today and tomorrow. Preserve ordinary
  schedules, all DHW configuration, raw secrets/environment references, and owner-edited dates.
- Validate complete 96-period price curves for the exact Prague date. Missing/incomplete prices
  and DST-transition days use the safe 42 C /21.5 C fallback, without price shifting.
- Identify contiguous expensive periods >=45 minutes at least 1 CZK/kWh above daily median.
  Coast over their most expensive up-to-90 minutes. Require a preceding continuous two-hour
  heating window within six hours and a price gap >=1 CZK/kWh. Exclude DHW/off windows.
- Preheat water request <=42 C; room target21.7 C with a per-window ceiling latch.
  Coast water request35 C/room21.2 C only with fresh cloud room >=21.5 C on entry.
  Restore42 C/21.5 C at21.3 C and latch for the remainder. No direct compressor command,
  no guaranteed stored heat, floor temperature or monetary savings.
- FTE/GoodWe actual export >=3 kW plus PV-minus-house >=3 kW for10 minutes can preheat
  even at high spot prices. Require battery >=20%, discharge <=100 W, import <=200 W,
  room <21.7 C. When running, use measured PV coverage of the house (including HP),
  not the original export threshold. End on loss of coverage, ceiling, or two hours from
  the first solar activation of the day. Persist timers and latches across restart.
- Require GoodWe online data <=120 s and cloud room <=900 s, finite valid fields.
  Faulty HP Shelly, passive candidate fields and underestimating consumption forecasts
  are not control inputs. PV forecasts cannot authorise extra heating; actual surplus is required.
- Log saved plans and effective runtime phases separately from sent/confirmed commands.
  Existing display shows saved dated plans; runtime comfort/solar veto is in sources.tng.price_shift.

## Delivery and validation

- Existing production backup before edits: snapshot c639341294e8410bb52ed08d8a57172c.
- Feature opt-in: tng.price_shift.enabled. Default absent means disabled.
- On first authorised installation only, replace today's existing heating/thermostat overrides
  with planner-owned overrides; retain previous days, ordinary schedules and DHW.
- Test curve validation, most-expensive block selection, next-day publication, manual edits,
  comfort/stale-data veto, solar start/stop/battery/ceiling/time bound, restart state and TNG gates.
- Deploy via existing HomeEnergyController service only; verify fresh telemetry and actual
  effective phase. Do not force a write to bypass an outstanding TNG confirmation.
