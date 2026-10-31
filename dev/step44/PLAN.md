# Economic battery control — owner approved 2026-10-31

One production controller resolves thermal targets and economic battery actions.
Economic mode excludes the old independent GoodWe rules (including export limits
and forced discharge). TNG transport and its persisted gates remain unchanged.

Decisions: at most20% rated inverter power (GW10K-ET =2kW nominal), up to60% SOC
from grid, leave40% for solar. Actual BMS allowance and a conservative7kW import
budget reduce/stop extra charging. These are operational budgets, not electrical
breaker protection. Existing device protections remain authoritative.

Require complete published96-quarter total-price curves and a sustained later
one-hour peak within12h. Purchase only if later price minus purchase/0.90 minus
0.30 wear >=0.50 CZK/kWh. All economics are model assumptions. Native charging
windows last1–3h; do not infer battery capacity or future house load from the
unverified10kWh setting or low-confidence PV forecast. Prefer measured solar
surplus and retain headroom. No guaranteed savings or claimed measured efficiency.

Use SDK-encoded eco group1 with bounded hours and current weekday; disable other
eco groups and verify power, SOC, hours, weekday, group switches and work_mode.
Check device clock within120s. GENERAL holds bought energy through a minimum-SOC
reserve and releases to20% for profitable self-consumption. Never force discharge
or change export limits. Journal ownership/basis before hardware writes so a crash
after acceptance is recoverable; retain this state through service restarts.

Limitations: the inverter schedule is recurring by weekday, not an absolute date;
the controller removes its active charge mode outside the window. If HEC stays
offline for a full week, the native weekday program can recur. Native hours and
60% SOC still bound it. Disabling the master switch freezes automatic writes; stop
an active charge through the normal writer before disabling control when needed.
PV forecast is not a trigger to buy energy; reserve40% and measured PV veto provide
conservative solar dependence until forecast/load confidence improves. No paid
energy ledger is claimed; retained maximum charge basis is conservative.

Reviews: the existing ACTIVE two-hour Codex task already reads skills/hec-status
at every run. Extend that mandatory skill and AGENTS/rules instead of introducing
a second schedule. The automation update tool is unavailable in this session;
the existing recurrence is preserved. Evaluate plans, commands, acknowledgements,
and physical measurements separately; include comfort and total-price economics.

Deployment: supported stopped-writer incremental backups before changes/deploy,
isolated fake-device tests, SDK encoding replay, raw-config activation preserving
private references and byte-identical TNG runtime state, service/readback checks.

Validation before activation:127 targeted tests passed (battery safety/economics,
exclusive unified controller, write result reporting, GoodWe transport, thermal
and morning-price regressions). Ruff and production Python3.13 compilation passed.
Offline replay with the installed SDK verified the complete bounded-program
readback, including Saturday mask64, -20% charge,60% SOC and inactive groups2–4.
Actual published2026-10-31 curve yields remaining charge window12:30–15:30;
its execution remains conditional on fresh live PV/load/SOC/BMS/clock inputs.
