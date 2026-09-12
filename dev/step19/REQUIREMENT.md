# Step 19 Requirement

## Objective

Replace the card-heavy Step 18 Today composition with a coherent daily energy
cockpit that fits 1920x1080 without vertical scrolling while preserving the HEC
appearance, readability, touch ergonomics, data bindings, localization, and
safety behavior.

## Scope

### In scope

- Today (`#/overview`) information architecture and visual density.
- Shared desktop sidebar width, branding density, navigation spacing, and
  compact health presentation.
- Existing Today header, recommendation, KPI, rhythm, appliance, and chart
  content where retained below.
- Browser regression coverage for geometry, overflow, interaction,
  localization, and missing-data fallbacks.

### Out of scope

- Backend, API, storage, database, reader, writer, controller, scheduler, or
  data-model changes.
- Content changes on other pages beyond effects of the shared sidebar.
- New optimization or appliance scheduling logic.
- Physical-device writes or safety-gate changes.

## Functional requirements

- REQ-019-001: At 1920x1080, the complete Today cockpit shall fit inside the
  viewport without vertical page scroll, clipped text, overlap, or hidden
  sections.
- REQ-019-002: The desktop sidebar shall be 190-210 px wide, preserve all
  destinations, retain 52-58 px touch-friendly navigation rows, reduce branding
  prominence, and show health as a compact status rather than a large card.
- REQ-019-003: The Today header shall be approximately 100-120 px high and show
  greeting, date/time, one concise summary, temperature, condition,
  precipitation, wind, and sunrise/sunset without duplicate PV suitability.
- REQ-019-004: One approximately 90-110 px horizontal recommendation panel shall
  contain the dominant best window and concise Now, Avoid, and PV-peak statuses;
  separate supporting cards shall be removed.
- REQ-019-005: The six live telemetry values shall remain data-bound and
  readable in one approximately 90-105 px strip with semantic status colors.
- REQ-019-006: Daily Energy Rhythm shall remain dominant, retain the 00:00-24:00
  timeline, suitability zones, current-time marker, weather, temperature,
  rating, and price, and occupy approximately 260-290 px.
- REQ-019-007: The standalone daily-production card shall be removed; its
  estimate and peak shall appear once in the rhythm section header.
- REQ-019-008: The lower workspace shall contain only appliance recommendations
  and the existing production/load/price chart, using approximately 35-40% and
  60-65% of available width.
- REQ-019-009: Appliance recommendations shall use compact 52-60 px rows with
  icon, name, recommended time, and status. A Plan-all action shall remain only
  if its existing implementation performs a real user-visible function.
- REQ-019-010: The chart shall preserve PV production, consumption, price, and
  Day / 2 days / 7 days controls without loss of legibility.
- REQ-019-011: The next-window donut and repeated copies of the same daily
  recommendation, PV outlook, or suitability message shall be removed.
- REQ-019-012: Existing API bindings and missing-data fallbacks shall be reused;
  the frontend shall not invent values or new scheduling behavior.
- REQ-019-013: Changed user-facing text shall use the existing Czech/English
  i18n mechanism, and controls shall retain keyboard, focus, and touch access.

## Non-functional requirements

- NFR-019-001: Preserve dark navy surfaces, blue panels, green/blue/orange
  semantics, current typography, restrained rounded corners, and HEC character.
- NFR-019-002: Prevent uncontrolled stretching above Full HD with bounded
  dimensions and responsive grid constraints.
- NFR-019-003: Keep primary values readable at wall-display distance and retain
  practical touch targets while reducing decorative padding.
- NFR-019-004: Verify no-scroll behavior from rendered browser geometry.

## Safety requirements

- `controller.enabled=false` and `tng.write_enabled=false` remain mandatory.
- No physical-device write or TNG confirmation-cycle change is permitted.
- Frozen root prototypes remain unchanged.

## Risks

- Fixed height targets can clip localized or missing-data content.
- Sidebar compaction can reduce touchability or affect every page.
- Removing duplicate panels can remove the only path to an existing feature.
- Dense Full-HD composition can regress at 1440x900 or 1280x800.
- Layered Step 18 CSS overrides can reintroduce unexpected dimensions.