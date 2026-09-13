# Step 19 Request

## Objective

Redesign Home / Today as one compact daily energy cockpit for the primary
11-inch 1920x1080 wall touchscreen. Preserve the HEC visual language and live
data bindings while removing repeated information, excessive card height, and
unnecessary sidebar width.

The complete Today page must fit a 1920x1080 viewport without vertical
scrolling. It must answer, in order: what is happening now, the best consumption
window, what to avoid, the current house state, the daily energy rhythm,
appliance recommendations, and the near-term production/load/price outlook.

## Requested composition

- Compact 190-210 px sidebar with all existing destinations and compact health.
- 100-120 px greeting/weather header without repeated PV-suitability copy.
- 90-110 px horizontal recommendation panel with one dominant best window and
  three concise supporting statuses.
- 90-105 px six-item current-state strip.
- 260-290 px Daily Energy Rhythm using the full content width, with production
  estimate moved into its section header.
- 300-330 px lower workspace containing compact appliance rows and the existing
  chart in an approximate 35-40% / 60-65% split.
- Removal of the standalone next-window donut and duplicated messages.

## Constraints

- Frontend-only implementation.
- No backend, API, database, reader, writer, controller, scheduler, or data-model
  changes.
- No fabricated business logic or values; retain existing API bindings and
  missing-data fallbacks.
- Preserve Czech/English localization, accessibility, and touch operation.
- Planning only until explicit Gate A approval.