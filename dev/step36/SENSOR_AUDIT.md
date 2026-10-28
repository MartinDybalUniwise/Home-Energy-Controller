# Temperature semantics audit — 2026-10-28

Owner reported that the overview label "Topná voda" presented the heat-pump
outlet as though it were a separate floor-loop measurement.

## Verified mapping

| Upstream TNG field | HEC measurement | Meaning |
| --- | --- | --- |
| t | outside_temperature | Outdoor temperature |
| tw | water_output_temperature | Water at heat-pump outlet |
| tb | boiler_temperature | DHW tank sensor |
| tt | room_temperature | Room sensor |
| HeatTemp_Const | heating_set_temperature | Requested constant heating setting, not a sensor |

No separate floor-loop, return-water, buffer-storage or floor-surface sensor is
provided by the current reader. No outlet-to-floor conversion is justified.

## Uses inspected

- Reader current and overlap history use the same tw mapping; series processing,
  history repair and history API preserve water_output_temperature. No remapping
  or rewriting historical observations is needed.
- Overview label and history legend now explicitly say heat-pump outlet. The
  requested heating setting is labelled separately from its measured outlet.
- TNG scheduled writes and one-off controller requests use requested setpoints,
  not a fabricated floor temperature. Existing confirmation and 900-second guard
  remain. One-off requests now also respect exclusive operation windows.
- Optimisation uses outdoor temperature, requested heating setting, boiler
  temperature, energy and price. It does not use outlet temperature as a measured
  floor state. Its generic DHW price explanation incorrectly mentioned floor
  inertia; the explanation now describes DHW reheating instead.
- Forecast heat demand uses outdoor/weather degree days and historical energy;
  no floor temperature is derived from tw. Energy summaries and heat-pump analysis
  use outdoor and boiler sensors, not tw as floor temperature.
- Flow receives the explicit outlet field without renaming it to floor water.
- Monitoring instructions, project skill and rule SENSOR-001 now prohibit
  inferring floor-loop temperature, floor comfort or stored heat from tw alone.

## Validation

92 targeted offline tests passed for reader mapping, exclusive modes, history and
controllers. Browser checks cover integrated temperatures, one timestamp,
day-plan median, rules, mobile/desktop widths and preserved DOM on refresh.
API field names remain compatible; historical records are unchanged.
