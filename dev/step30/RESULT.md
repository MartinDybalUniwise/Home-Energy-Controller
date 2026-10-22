# Deployment result - 0.1.3

Owner Human Gate APPROVED in chat. Combined Step29 + Step30 candidate verified at 2026-10-21T11:38:34.484968+02:00.
Candidate revision: 3b721e12cd10afb476a802e720809e6192d1c04e. Final production revision: 5bf1d35e06e720ae4afa1252b58212be9f26f699; PID: 13656.
Final metadata reload verified at 2026-10-21T11:43:36.869626+02:00; real browser confirms the actual release timestamp in the release dialog.
All six readers fresh, controller remains disabled, native TNG gate unchanged, private configuration hashes unchanged.
Real read-only production browser smoke PASS at 390 and 1280 CSS px, no page errors, no horizontal overflow and labels at least 16 px.
History tracker is valid and active with durable dirty markers and the production writer PID.
New backup payload: 52694727 bytes, 49 files. Logical restore references 1487560984 bytes.
Initial stopped-writer audit source reads: 1494333581 bytes; this is not new copied backup volume. The existing baseline is reused and frozen logs untouched.
Snapshot: 8e409525c9704a9ea087418474c68cf9. Final metadata reload copied zero backup bytes and performed no second bootstrap/capture.
Evidence: C:/TepelneCerpadlo/step30-release-evidence/backup.json, deployed.json, deployed-final.json, final-status.json, browser-smoke.json, final-release-browser.json and production-flow-390.png / production-flow-1280.png.
Physical meter wiring remains unverified. This release labels bad measurements; no control algorithm tuning was performed.

## Earlier validation and pre-deployment record (historical)

# Result

Implementation and independent review are complete. Gate B APPROVED for 048ce35f1a13a0f8fa19890216514d54dfefe899 by /root/release_review, with no unresolved BLOCKER or IMPORTANT. Human Gate remains pending.

## Validation

- Candidate d614580: 418 unit/integration tests passed, 56 E2E tests deselected, 751.39 seconds. Evidence: C:/TepelneCerpadlo/step30-unit-final.log. Step30 changes no frontend; this is not a claim of a new E2E run.
- Final accounting-only change counts the second source read performed when copying changed history. Both targeted tests passed (2 passed, 23 deselected, 70.51 seconds): C:/TepelneCerpadlo/step30-accounting-final.log. They verify no unchanged-history reads/enumeration, changed old-day capture and full staging restore.
- Earlier focused validation: 63 storage/history/backup tests passed and 25 backup/recovery tests passed. Logs: C:/TepelneCerpadlo/step30-targeted-final.log and C:/TepelneCerpadlo/step30-backup-final.log.
- Final checks PASS: Ruff on changed Python files, git diff --check, structural validation of all 19 step packages, Step30 ready validation and repository hygiene validation. Production HEAD remains 98e9fa5b5454bc1fd44bcdc07e86f6396c4f38bb and API listener PID remains 16584.

## Requirement evidence

- E-030-001: Existing verified baseline registered as snapshot 787def35548f4745aec8b6d3a45db2be, 1043 history references, zero copied payload bytes and zero history bytes read. Report: C:/TepelneCerpadlo/step30-register-baseline.json. Manifest metadata was written; these counters do not mean zero total disk writes.
- E-030-002: Persistent dirty paths precede append, merge, repair and deletion. Regression tests cover failure before write, late corrections, tracking gaps, unsafe archive configuration and crash/retry cases.
- E-030-003: Immutable payloads and complete reference manifests publish HEAD before marker acknowledgement. Routine captures visit only dirty history paths and recent diagnostic logs; unchanged code archives/Git bundles are reused. Source-read accounting includes hashing and copying changed files.
- E-030-004: Real Git bundle/code/data restore is tested into empty staging, including corrupt or missing dependencies and staging relocation/rebinding. Referenced baseline and immutable objects must be retained.
- E-030-005: Frozen logs are rejected lexically and pruned before traversal, covered by a scanner guard test. No frozen payload was accessed. Actual live production PID was refused before capture; evidence: C:/TepelneCerpadlo/step30-live-refusal.log. No production restart or configuration/control change occurred.
- E-030-006: Full suite and two final targeted tests passed. Independent final review passed; owner Human Gate remains pending, both recorded separately in STEP.json; no deployment success is claimed here.

## Activation and limits

Production remains on its original version. Only metadata registration has run against the existing full backup; no production bootstrap or staging restore has run. The new writer tracking must be deployed before incremental coverage exists. During the separately approved deployment, stop and verify all writers, then perform one explicit bootstrap audit against the baseline to capture changes since that backup. Subsequent routine captures must not enumerate unchanged history. Untracked tooling/rollback requires explicit invalidation and another approved audit; no automatic full-scan fallback exists.

The existing full baseline and all referenced objects remain required restore dependencies. Old historical helpers are not the new release procedure. See dev/hec/docs/RELEASE_BACKUPS.md and C:/TepelneCerpadlo/HEC_RELEASE_BACKUP_POLICY.txt. Human Gate remains pending; Step30 must not be marked DONE or represented as active in production.

## Deployment guard correction

The first approved deployment attempt stopped safely before capture (0 copied bytes), then restored the original 0.1.2 service. Windows took over two seconds to report a refused loopback connection; the two-second probe was inconclusive. The probe now waits up to eight seconds and still rejects timeouts and every ambiguous connection error. Independent reviewer approved this minimal correction, conditional on targeted success: 5 PASS, 23 deselected, 63.00 seconds; C:/TepelneCerpadlo/step30-offline-guard-tests.log. Ruff and whitespace checks PASS. The deployment helper enforces a cumulative new-payload copy limit strictly below 900,000,000 bytes before every copy; no new 1 GB backup is permitted.
