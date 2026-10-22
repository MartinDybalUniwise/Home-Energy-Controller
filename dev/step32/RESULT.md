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
