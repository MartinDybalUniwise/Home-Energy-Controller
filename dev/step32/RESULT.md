# Deployment result - 0.1.5

Owner final Human Gate APPROVED in chat. Candidate 4ea6752c6dd87ba93358b2b39c25d1c3ef26b59a verified at 2026-10-22T11:56:16.473489+02:00.
Final production revision 704feee638daf75c014f9cecb050678a5a98bb19, PID 17376; final metadata reload verified at 2026-10-22T12:01:30.830574+02:00.
All six sources fresh, controller remains disabled, native TNG write gate preserved, private configuration hashes unchanged. History tracker valid and actual writer PID matches.
Real production current API confirms energy_counter_semantics=ac-grid-separated-v1, unsupported daily GRID counters null, explicit AC daily and cumulative GRID counters numeric. Actual API query over pre-fix22October07:58 history returns GRIDdaily null and preserves AC energy under explicit names; no raw rewrite.
Actual read-only Chromium smoke PASS at390/1280px: GoodWe source, daily GRID dashes, load visible, no page overflow or page errors. Existing mobile flow connectors visible. No mocked production responses or API writes. Actual release dialog timestamp matches the verified release time.
Routine backup snapshot 79c2f332239a4d24b37680fb90328ad5, initial_audit=false, newly copied 57811055 bytes/39 files. Changed history source reads 21 files/69467330 bytes; unchanged history not traversed. Logical restore references 1514752357 bytes, not newly copied volume. No bootstrap or frozen-log access. Metadata-only final reload copied0 backup bytes.
Evidence: C:/TepelneCerpadlo/step32-release-evidence/{backup.json,deployed.json,deployed-final.json,final-status.json,browser-smoke.json,legacy-history-proof.json,final-release-browser.json} and production-energy-390.png.
No algorithm tuning, instantaneous sign changes, new device settings, imports or backfill. Daily GRID stays unknown until a trustworthy daily source/baseline exists; lifetime totals are never relabelled as day totals.

## Historical implementation and pre-deployment record

# Result

Implementation complete; Gate B APPROVED by independent /root/release_review for exact code2c56811294ae8219b37f0605814fff9f91edf602, no unresolved BLOCKER/IMPORTANT. Owner final Human Gate and deployment remain pending; Step32 IN_PROGRESS. Production0.1.4 unchanged.

## Confirmed cause and correction

E-032-001 PASS: Installed GoodWe0.4.10 reports ET e_day_exp register35199/e_day_imp35202 as Kind.AC, whereas meter_e_total_exp36015/meter_e_total_imp36017 are Kind.GRID. Bounded actual read at22October08:59:45 on GW10K-ET/04029-09-S11 gave ACexport7.9=load7.9kWh and GRID cumulative export5668.75/import22359.87kWh. No daily GRID sensor was exposed. Evidence C:/TepelneCerpadlo/step32-evidence/readonly-device-counters.json. Only device discovery/runtime reads, no settings or physical writes.

Both adapters now share explicit AC/grid counter mapping. Additive inverter_ac_*_day_kwh preserves the AC values, grid_*_total_kwh carries valid cumulative meter values. Existing e_import_day_kwh/e_export_day_kwh stay present but null; no fictional midnight baseline or daily replacement. Missing/invalid/disconnected meter values stay unknown and measured zero remains zero. Instantaneous power signs unchanged.

E-032-002 PASS: Current projects a copy, without modifying the controller snapshot. History masks legacy daily AC aliases before aggregation, retaining actual AC energy under explicit names; flat, nested and mixed forms covered. Raw bytes unchanged. UI no longer treats raw SDG e_day_imp/exp or unmarked old normalized daily fields as GRID energy. It chooses current GoodWe when SDG has no daily energy, labels the source, and renders unavailable GRID as a dash. Independent historical power-based summaries remain available and small GRID values show two decimals. CZ/EN history labels distinguish inverter AC and cumulative grid totals. Asset/cache versions updated.

## Final validation

E-032-003 automated/review PASS, Human Gate pending:
- 67 unit/adapter/current/summary/i18n PASS, C:/TepelneCerpadlo/step32-unit.log.
- 33 storage/history/API/TNG regressions PASS,23 unrelated tests deselected, C:/TepelneCerpadlo/step32-history.log.
- 12 actual Chromium E2E PASS (CZ/EN across legacyGoodWe, correctedGoodWe, rawSDG, legacySDG, historical summary and explicit-zero scenarios), C:/TepelneCerpadlo/step32-browser.log. First browser command deselected all12 due default marker filter and is not counted; final run explicitly used -m e2e. Screenshot fixtures are test data, not contemporaneous production readings.
- Earlier wider82PASS run predates the final mixed-shape edge fix; final67unit and33history cover that final backend. No claim that all prior77browser tests were rerun for this bounded repair.
- Ruff and git whitespace PASS. Repository hygiene and Step32 ready validation recorded separately after final evidence update.

Fresh final preview PID8984 on8185, workingroot C:/TepelneCerpadlo/step26-git, config C:/TepelneCerpadlo/step32-isolated-preview/preview.json. No readers, controller/writes disabled, all storage isolated. Actual unmocked API history over flat+mixed test fixtures returned GRIDdaily null and AC7.9/8.0; fixture bytes unchanged. Proof C:/TepelneCerpadlo/step32-evidence/final-preview-proof.json. Application revision in proof is exact reviewed2c568112; later evidence-only docs commits do not change application code.

## Limits and safety

No production restart, code/configuration change, backup, import/backfill or raw history rewrite. Frozen odlozene-logy never entered. Root prototypes, physical controls and TNG change gate untouched. The repair does not manufacture SDG screenshot values0.04/0.07 as HEC daily counters. A trustworthy day total derived from cumulative GRID counters requires a separate verified baseline design; the current repair correctly reports unsupported daily values as unknown. Future approved deployment uses existing incremental backups only.


## GitHub promotion and portable test fixtures

Owner requested PR and merge. PR43 promotes the deployed release plus earlier approved reconciliation from the integration branch into main: https://github.com/MartinDybalUniwise/Home-Energy-Controller/pull/43. Initial Linux CI exposed two test-fixture issues: the frozen-folder guard passed a POSIX directory descriptor to Path during temporary cleanup, and the energy summary fixture used Prague midnight while the CI host uses UTC day bounds. Only tests were corrected: integer descriptors delegate to real scandir, forbidden Path/string forms are explicitly asserted to fail before entry, and summary timestamps use the same host-local day as the analyser. Energy assertions, safety checks and workflow coverage are retained. No application or production change and no redeployment. Final CI results are recorded on PR43.
