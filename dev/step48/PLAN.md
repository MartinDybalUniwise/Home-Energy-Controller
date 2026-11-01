# Hourly floor-circulation check - owner approved2026-11-01

Owner explicitly instructs: assume the circulation pump runs only while heating,
and enable the proposed check after an idle hour. This is an owner assumption,
not verified pump/relay/compressor telemetry. Keep one Application.controller.
No external scheduled job, second device writer, UI planner, LAN probing or new
hardware control route. Existing two-hour reviews remain separate observation.

The unified thermal resolver runs the persisted floor state machine on the existing
TNG poll. Infer assumed activity only from fresh room<=actual room target, reported
heating enabled, boiler disabled and cleared confirmation gates. Never use the
phase-fault Shelly meter or unresolved passive bits to infer confirmed activity.
After60min without assumed heating, first require valid fresh observations and
exclusive heating/basic confirmation, then request a bounded heat pulse through
the existing thermostat path. Water target42C; temporary room request=room+0.5C,
ceiling24C, locked per cycle. This is a service request, NOT a permanent comfort
change. It can start the compressor; a pump-only command remains unverified.
The ordinary21.7C price-preheat cap remains; this separately authorised bounded
floor service has a temporary request up to24C and never raises water above42C.

Observe at2/5/10/15min from the audited POST, marking missed/invalid samples rather
than assigning later data to an earlier instant. Only fresh<=180s, photo-range
AKU34.2-41.5C with room/outlet/outside agreement to independent cloud within0.8C
can support AKU decisions. Owner photos2026-11-01 confirm41.2/41.5C; only this
upper evidence boundary is extended. Packet CRC/high branches/global control
eligibility remain unverified/false. Owner-approved use is narrow, bounded and
must not enable other passive fields or general actuator logic. This supersedes
the old blanket passive-control prohibition ONLY for the floor check qualifier.

If a qualified AKU sample<35C occurs, latch reheating. Never treat unknown/stale
AKU or out-of-range low candidates as0C. During a started request keep the already
bounded42C request until valid recovery or timeout; no invented temperature.
Earliest restoration request after15min, cleared acknowledgement, AKU>=38C and
three distinct samples over>=100s with spread<=0.3C. Restore no later than45min
by requesting the CURRENT common plan; never restore obsolete saved schedules.
900s write/confirmation gates still apply, so delivered restoration may be delayed.
Software timeout depends on HEC/cloud availability; no native pump timer is claimed.
Abort to ordinary plan on stale room, disabled controls, explicitoff/DHW, or24C
room ceiling. An unacknowledged request times out; sent!=acknowledged!=pump run.
Persist active/restore state across restart; no new cycle until restore confirmed.
After completion wait an idle hour again; ongoing ordinary heating resets that
idle clock. First activation starts the clock now, without inventing past activity.

Active phases use60s polling in the existing TNG reader; inactive cadence remains
unchanged. Its existing boundary scheduler also wakes near the hourly due time.
Audit transitions and milestone observations as tng_commands.floor_check and expose
thermal_plan.floor_check. Preserve cloud ExternalCirculationPump flag on existing
basic-setting writes; never toggle it as a supposed pump-on command. The same
battery controller recognises an active floor request for its conditional VT
comfort supply, without altering charging economics or inverter configuration.

Prechange backup:1bed73853c744de889c94cd9e482fbad. Preserve TNG runtime and battery
purchase state. No daily schedule rewrites are needed for this feature.

Validation before activation:239 targeted regressions passed, including real TNG
adapter simulation of request/confirmation/restoration with>=900s between writes,
restart, timeout, invalid samples, exclusive DHW/off, crosschecks, preserved pump
flag, battery coordination, cloud API and price planning. Ruff, production Python
compilation, translations and registry JSON passed. No real test pulse has yet run.

Owner update2026-11-01: expand floor-check operational AKU range to30.0-41.5C.
Below34.2C use owner_extended_provisional / owner_extended_range_cloud_crosschecked;
this is owner-authorised operational acceptance, NOT additional photo validation.
Keep original decoder photo-reference range34.2-41.5C and CRC/global control_eligible
unverified. Freshness/cloud crosschecks, exclusive modes,42C/24C caps and900s gates
remain unchanged. Below35C valid expanded samples latch the existing reheat phase.

Range-extension validation:52 tests passed (floor state machine, passive wire
quality boundary cases and unified controller); Ruff and git diff --check passed.
Prechange incremental snapshot:9fb4e3bd0b374521be5dc4f4a5ebc65f.

Completion repair2026-11-01: live cloud returns DayTemperature as an object with
FloatValue21.5 and ByteArray, rather than the scalar used by initial fixtures.
This prevented acknowledgement/restoration matching despite native gate clearance.
Parse the explicit numeric finite FloatValue for Day/NightTemperature, preserve
legacy scalar support, never infer readback from POST. Complete persisted restore
only with fresh room, pendingFalse, clear gate and CURRENT plan target match.
No additional heating request or bypass of900s gates is required.
Prechange incremental snapshot:c06398fe1faa4f97956303cc8695feef.

Completion-fix verification:61 reader/floor/unified-controller regressions passed;
Ruff and git diff --check passed. Live native DayTemperature21.5 was read directly
from cloud before repair; device requests/persisted confirmation gates untouched.
