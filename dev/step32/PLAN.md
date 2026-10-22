# Grid energy counter correction

## Goal

Small bounded correction of a confirmed semantic mapping bug. Owner explicitly approved investigation and correction in chat; no additional plan approval is needed for this scope.

| Step | Work | Status |
| --- | --- | --- |
| S01 | Confirm actual library sensor kind/register and bounded read-only hardware evidence | PASS |
| S02 | Share explicit AC/grid mapping across adapters; mask legacy counters on read and remove UI AC fallbacks | PASS |
| S03 | Unit and real browser regressions, targeted affected checks, independent review | PASS |
| S04 | Owner Human Gate and separately authorized incremental deployment | PASS |

Evidence: library0.4.10 on GW10K-ET, e_day_exp at35199 and e_day_imp35202 have kind AC; meter_e_total_exp36015 / meter_e_total_imp36017 have kind GRID. Raw read08:59:45: e_day_exp7.9=e_load_day7.9; grid totals5668.75/22359.87kWh. No GRID daily sensor is exposed. Therefore daily grid counters must become null, not an assumed numeric replacement; add cumulative meter fields for future independently planned day-baseline handling. Existing power-based summary remains independently calculated.

Risk: old stored telemetry and SDG aliases may restore bad values. Mask only read projections; no file rewrite or backfill. Keep physical I/O, instantaneous signs and TNG gate untouched. Preview disables all external readers and writes. Rollback is source-only to verified0.1.4, retaining tracked history. Routine future backup only, frozen logs excluded before entry.
