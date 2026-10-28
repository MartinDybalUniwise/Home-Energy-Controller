# Step35 — today PV forecast and one-day schedules

Owner approved implementation, deployment, current-day plan and two-hour follow-up controls on 2026-10-28.

Today PV is the fresh GoodWe daily PV counter plus remaining Open-Meteo irradiation, accounting for preceding-hour means and the measurement timestamp. Interval coverage, stale/missing counters and weather, zero, midnight and sunset are treated explicitly. Remaining uncertainty never replaces missing measurements with zero. Today has a separate model label and measured/remaining detail. Background forecast runs every 15 minutes; heavy maintenance retains its original schedule. Physical control algorithms and TNG confirmation/900s protections remain unchanged.

Date-keyed section overrides allow a current-day plan to expire without replacing the ordinary schedules. Additional checks use the existing config API, not direct hardware commands.

Validation: original TNG/predictor baseline passed; new partial-hour/missing/stale/zero/duplicate/sunset/date-expiry regressions passed. Browser preview passed on 390/1280 px with the measured/remaining breakdown and no JS errors. The full offline suite exposed three metadata-only failures because the initial export lacked .git; these are rerun after binding local Git metadata.
