# One controller and visible PV/battery plan — owner approved2026-10-31

Display the same status.controller.battery_plan on Control & Plan and as a battery
lane on the overview's existing day timeline. No additional planner, command API,
device writer, timer or economic calculation in the browser. All caps/window prices
come from the backend plan; backend adds only date and configured-power metadata.

Distinguish conditional intent from actual power, SOC and command confirmation.
Show remaining windows only, never label missed early-morning windows executed.
Reject stale/wrong-date plans and disabled controls; protection vetoes and failed
writes must not appear as active charging. Existing ten-second UI refresh and
minute overview chart refresh are reused. Preserve thermal rows and keyboard detail.

Enforce economic ownership at Controller.apply as well as run_once. Hide unused
legacy battery targets in Settings while economic mode is active, keeping one
authoritative configuration and the existing master permission. No device settings
or TNG gates are changed by this display work. Update the operational registry.

Validate renderer state/freshness against disabled, stale, failed and elapsed
plans, shared-controller rejection of old rules, real desktop/mobile rendering
and absence of UI write requests. Back up before edits/deployment; preserve all
runtime state and the original production service.

Fast current responses include only the cached controller state in addition to
their existing measurements. Do not fetch full diagnostics for the overview or
instantiate a second planner to obtain these windows.

Before deployment:123 targeted regression tests passed, including retired-rule
rejection and the fast read-only API contract. The Node projection test passed
for enabled/current, elapsed, stale, disabled, failed and protected plans. Ruff,
production Python compilation and Czech/English/registry JSON validation passed.
The configuration endpoint recursively merges partial UI saves, preserving the
hidden economic-mode flag and inactive legacy fields without reactivating them.
