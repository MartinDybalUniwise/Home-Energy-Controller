# Live control page — 0.1.17

The previous page displayed a placeholder planner state and described enabled
writers as disabled. It watched general controller decisions, omitting the
independent TNG schedule/price-shift loop and its real command audit.

The replacement reads status.controller.thermal_plan as the authoritative resolved
plan of the unified controller. It consumes current fast snapshots, reader/controller status,
current saved configuration, today's TNG command history, decisions and forecast.
It shows separate TNG transport, price/solar/comfort, controller and inverter states;
effective targets alongside observed settings; confirmation phases and remaining
guard time; remaining saved windows (including thermostat boundaries); and actual
sent/confirmed/failed events. Saved windows do not claim executed commands.

The existing 10-second refresh patches the current DOM and preserves open details.
Missing endpoints, stale cloud measurements, disabled writers and unknown states
are shown explicitly. Source timestamps remain visible. All day boundaries use
Europe/Prague. Device control, schedules, write gates and private config are unchanged.

Validation: 18 deterministic browser model assertions (runtime comfort veto,
thermostat targets/boundaries, disabled writes, stale samples/missing reader, authoritative unified plan,
master-disable handling and stale unified plans,
confirmation states and 900-second guard, command grouping/local day, failed
endpoints, malformed dates and HTML escaping). Browser integration also verifies
the legacy independent TNG vs disabled controller, audit rendering, 10-second
refresh preserving node identity/open details, mobile widths 360/390, desktop
1440 and visible connection failure. Screenshots and evidence are retained under
C:/TepelneCerpadlo/step42-evidence.

Run verify.cjs with Playwright installed and HEC_BASE_URL pointing to an isolated
frontend server, not production. Optional PLAYWRIGHT_MODULE and CHROMIUM_PATH
select a bundled runtime. These model checks use only fixture control data.

Deployment: offline incremental ReleaseBackups capture, replace only listed UI,
locale and release files, restart existing HomeEnergyController, verify 0.1.17,
all readers and production browser. Roll back listed files on failure.

Concurrent controller unification was detected before deployment. Its source and
configuration changes are preserved; this UI supports the new runtime contract.
Resolved plans are never labeled as failed or sent based on Decision.applied.
