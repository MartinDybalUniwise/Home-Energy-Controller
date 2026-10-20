# Step28 deployment result - PASS

Owner explicitly approved the reviewed PR and production deployment before any stop or source replacement. PR #42 merged as 8c57a0e; its complete tree equals the fully tested f27b5a1. Version 0.1.2 is now deployed at `98e9fa5b5454bc1fd44bcdc07e86f6396c4f38bb`, tagged `v0.1.2`.

The impossible room temperatures no longer contaminate averages. They appear as missing measurements; genuine negative values and zero remain. Production API 24h/7d/30d and actual mobile/desktop chart/table checks PASS with no JavaScript errors. Thirty-day room range: 19.3-22.892 C.

## Verified backup and preserved state

- Full stopped-writer backup: `C:\TepelneCerpadlo\hec-backup-20261020-201411`.
- 1,163 files, 1,481,571,188 bytes, 3,452,393 JSONL rows validated, hashes match original files.
- All four configuration/secret-file hashes unchanged. Device/control switches unchanged, main controller remains disabled as configured.
- Original affected September 18 and October 2 JSONL files remain byte-identical to the backup. No data repair or history rewrite was run for Step28.
- TNG basic/thermostat last-post state survived both starts and did not move backwards. Existing scheduled writer behavior and 900s gate remain unchanged.
- Six readers healthy at final verification. GoodWe had one transient response error on the first start and recovered without configuration changes.

## Actual release event and verification

- First API start: 2026-10-20T20:26:34.0208+02:00, process 7668.
- Completed production API/browser verification and authoritative release timestamp: `2026-10-20T20:37:10.993092+02:00`.
- The follow-up commit changes only that `released_at` field. Independent reviewer accepted its provenance.
- Exact release commit CI: Python 3.11/3.12 and full SDD workflow PASS, including 377 unit and 47 real browser E2E tests. [Release workflow](https://github.com/MartinDybalUniwise/Home-Energy-Controller/actions/runs/39476479474).
- Metadata reload verified: process 16584, version 0.1.2, Prague release time displayed correctly even in a UTC browser, dialog close PASS, no page errors.
- Final production HEAD equals the tag commit. Completion documentation is a separate subsequent commit; no restart is needed for it.

## Evidence

Local evidence directory: `C:/TepelneCerpadlo/step28-evidence`.
`production-backup.json`, `production-candidate-verified.json`, `production-candidate-ui.json`, `actual-release-time.json`, `production-release-verified.json`, `production-release-ui.json`, and `push-ci-98e9fa5b5454bc1fd44bcdc07e86f6396c4f38bb.json`.
Screenshots: `production-candidate-tng-mobile.png`, `production-candidate-tng-desktop.png`, `production-release-dialog.png`.

Gate A approved before implementation; Gate B independently approved product and release metadata; Gate C explicitly approved by the owner. Step28 DONE.

## Rollback prepared, not needed

Previous code is tag `v0.1.1` / commit `0b36d3e3c69007f231ed87b102d6c09dd0a3e299`. If rollback becomes necessary, stop the verified single instance, check out that code and restart with the same production Python and configuration. Preserve current data and gate state; no historical data restoration is needed for this read-only history correction. The full verified backup is available if recovery beyond a code rollback is ever required.
