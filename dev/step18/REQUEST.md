# Step 18 Request

## Objective

Redesign the UI/UX for the Today (Dnes) and Energy Flow (Tok energie) screens
according to authoritative visual references and the approved touchscreen design.
The goal is to eliminate wasted screen space, significantly increase typography
and icon sizing, optimize touch interactions for an 11" Full HD (1920x1080) wall
touchscreen, and provide clear decision hierarchy while preserving all existing
backend and product functionality.

This phase is strictly limited to planning and documentation. No application
code, Python scripts, HTML/CSS/JS assets, or hardware configurations shall be
modified until explicit human Gate A approval is granted.

## Visual reference authority

The attached mockup designs and wireframes are the authoritative visual
references:
1. Touchscreen 11" (1920x1080 landscape, high readability from 1-2m, min 64x64px touch targets).
2. Zero waste space: dense, compact, high information density with no empty gaps.
3. Top Header: Weather overview with temperature, condition icon, wind, rain, sun times, PV suitability.
4. Hero Recommendation: Dominant card for best appliance window (11:30–14:30), explanation action ("Proč právě teď?"), and 3 supporting status cards (Teď je, Vyhněte se, Očekává se).
5. KPI Strip: 6 live telemetry cards (PV, House load, Battery SoC/power, Grid import/export, Electricity price, Heat pump / DHW).
6. Daily Energy Rhythm: 24h timeline with color-coded suitability blocks, weather icons, temperatures, rain %, text ratings, and hourly spot prices directly under each block, plus vertical 'now' indicator and daily PV estimation box.
7. Lower Workspace:
   - Appliance recommendations (Washing machine, Dishwasher, Dryer, Heat pump) with timeline mini-bars, savings estimate, and priority indicators.
   - Next suitable window donut gauge with countdown timer and next 2 windows.
   - High-contrast multi-curve forecast chart (PV, Load, Price) with Day / 2-days / 7-days horizon switcher.
8. Bottom Action Bar: Rotating tips/opportunities, daily expected savings summary, and action CTAs.
9. Navigation: Left sidebar with main pages and collapsible Service menu for technical pages (Settings, Status, Logs).

## Explicit non-goals in this planning phase

- No edits to `dev/hec/web/frontend/*` (CSS, JS, HTML).
- No edits to backend API, storage, controller, or readers.
- No modifications to frozen root prototypes (`tng_controller.py`, `goodwe-read.py`, etc.).
- No execution of hardware writes or changes to `controller.enabled` / `tng.write_enabled`.
