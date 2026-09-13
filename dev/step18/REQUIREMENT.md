# Step 18 Requirement

## Objective

Define the functional and visual requirements for the UI/UX redesign of the Today
(`Dnes`) and Energy Flow (`Tok energie`) pages based on the authoritative visual
references. The design focuses on an 11" Full HD (1920x1080) landscape wall
touchscreen, eliminating wasted space, maximizing readability from 1–2 meters,
enforcing touch targets of at least 64x64 px, and structuring information into a
clear decision hierarchy without altering backend contracts or hardware safety.

## Context

The Home Energy Controller frontend was previously desktop/mobile agnostic with
larger empty padding areas. The new requirements establish a touch-first,
information-dense wall display paradigm where all key real-time metrics, solar
production forecasts, appliance recommendations, and daily energy rhythm are
visible on a single 1080p screen without vertical scrolling.

## Requirements

- REQ-018-001: The system shall provide an 11" Full HD (1920x1080 landscape)
  optimized layout with zero waste space, dense card spacing (12–16 px gaps,
  16 px padding), and zero vertical scroll requirement on 1080p.
- REQ-018-002: The system shall display a compact top header containing a
  personalized greeting, date, time, weather overview (temperature, condition
  icon, wind speed, precipitation probability, sunrise/sunset, and PV
  suitability badge).
- REQ-018-003: The system shall provide a dominant Hero Recommendation section
  displaying the best appliance operating window, a "Proč právě teď?"
  modal/tooltip action, and 3 supporting status cards ("Teď je", "Vyhněte se",
  "Očekává se").
- REQ-018-004: The system shall display a 6-card live telemetry KPI strip (PV
  production, house load, battery SoC with charging/discharging power, grid
  import/export, spot electricity price, heat pump / DHW status) with high
  contrast and trend indicators.
- REQ-018-005: The system shall display a 24-hour Daily Energy Rhythm timeline
  with color-coded suitability blocks (Best, OK, Avoid), weather icons,
  temperatures, precipitation, text ratings, spot prices below each block, a
  vertical 'now' indicator, and a daily PV estimation box.
- REQ-018-006: The system shall provide a lower workspace containing:
  - An appliance recommendation list (Washing machine, Dishwasher, Dryer, Heat
    pump) with timeline mini-bars, savings estimates, and priority indicators.
  - A circular countdown donut gauge showing the time remaining to the next
    suitable window, expected benefits, and the next 2 upcoming windows.
  - A high-contrast multi-curve chart (PV production, consumption, price) with
    horizon toggles (Day / 2 days / 7 days).
- REQ-018-007: The system shall provide a bottom action bar with rotating
  energy tips/opportunities, expected daily savings, and quick action buttons.
- REQ-018-008: The system shall provide a dedicated left sidebar navigation with
  primary links (Dnes, Výhled, Tok energie, Historie) and a collapsible
  "Servisní menu" containing secondary/technical pages (Nastavení, Stav, Data,
  Finance).
- REQ-018-009: The system shall preserve all existing backend APIs, storage
  readers, mock preview capabilities, and graceful fallbacks for missing
  weather or OTE price data.
- REQ-018-010: The system shall support full CZ and EN localization catalogs
  without hardcoded user-facing strings and provide Playwright E2E test coverage
  across 1920x1080, 1440x900, 1280x800, 1024x768, and 390x844 viewports.

## Constraints

- No modifications to frozen root prototypes (`tng_controller.py`, `goodwe-read.py`, etc.).
- No change to backend REST API contracts or JSON schema.
- Safe mode and hardware safety invariants remain untouched (`controller.enabled=false`, `tng.write_enabled=false`).
- All user-facing text must use i18n translation keys.
