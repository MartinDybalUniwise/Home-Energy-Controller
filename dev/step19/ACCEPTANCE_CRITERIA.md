# Step 19 Acceptance Criteria

All criteria remain unchecked until implementation evidence exists. Automated
checks do not replace the human 1920x1080 review.

- [x] AC-019-001: At 1920x1080, Today has no vertical or horizontal page
  overflow and every required section is fully visible without clipping or
  overlap.
- [x] AC-019-002: The desktop sidebar is 190-210 px, preserves every route,
  provides 52-58 px navigation rows, exposes compact health, and remains
  keyboard- and touch-operable.
- [x] AC-019-003: The header is 100-120 px and includes required concise
  greeting/weather information without duplicate PV messaging.
- [x] AC-019-004: One 90-110 px recommendation panel shows the best window plus
  concise Now, Avoid, and PV-peak statuses; separate supporting cards do not
  render and Why-now remains accessible.
- [x] AC-019-005: All six telemetry items remain visible, data-bound,
  semantically colored, and readable in a 90-105 px strip.
- [x] AC-019-006: Daily Energy Rhythm is 260-290 px, uses expanded width, retains
  required timeline details, and shows production estimate/peak once in its
  header.
- [x] AC-019-007: The lower workspace is 300-330 px and contains exactly the
  compact appliance panel and chart at approximately 35-40% / 60-65%; the
  standalone next-window donut does not render.
- [x] AC-019-008: Appliance rows are 52-60 px and retain icon, name, time, and
  status. No non-functional action is presented as operative.
- [x] AC-019-009: The chart retains PV, consumption, price, and all three horizon
  controls with legible rendering.
- [x] AC-019-010: Czech/English render without unknown keys, missing-data states
  use existing fallbacks, and no fake business logic is added.
- [x] AC-019-011: Non-Today routes and shared sidebar behavior pass smoke checks
  across 1920x1080, 1440x900, 1280x800, 1024x768, and 390x844.
- [x] AC-019-012: Ruff, non-E2E pytest, Playwright, Step validation, hygiene, and
  full validation pass with exact commands/results recorded.
- [x] AC-019-013: Safety settings remain disabled, no physical write occurs, and
  no backend/API/storage/controller contract changes are present.
- [ ] AC-019-014: A human confirms at 1920x1080 that there is no scroll,
  clipping, overlap, repetition, unreadable text, undersized touch control, or
  loss of Daily Energy Rhythm hierarchy.
- [x] AC-019-015: At 1920, 1440, 1280, and 1024 px widths, removed panels leave
  no empty grid column; rhythm and the two-panel lower workspace consume the
  available content width.

## Definition of ready

Step 19 is ready only after this package is consistent, ready-phase validation
passes, and Gate A is explicitly approved and recorded.