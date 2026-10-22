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

Implementation and automated validation complete. Independent Gate B approved
code revision 135b70c3f4cbc1bd5ccd0f672a40d555f2d077b6. Owner Human Gate remains
pending; Step29 stays IN_PROGRESS. No production deployment or physical setting
change, meter sign correction or historical data rewrite was performed.

## Confirmed validation

- Full unit/integration suite: 393 PASS (744.58s); browser tests deliberately excluded from this command.
- Affected/controller/predictor/SDD regressions: 81 PASS (199.31s).
- Full real Chromium suite: 56 PASS (488.34s), no skips, against isolated preview at8183.
- Includes mobile 360/390/430px, desktop 1280px, 200% text zoom, factual zero/unknown/offline/error states and stale sources.
- Ruff, repository hygiene, all 18 manifest-bearing steps structural and Step29 ready: PASS.
- Runtime smoke after E2E: PASS. All five external readers (GoodWe/TNG/Shelly/OTE/weather), controller and TNG writes disabled.

Logs: C:/TepelneCerpadlo/step29-unit-final.log,
step29-final-targeted.log, step29-e2e-approved.log and step29-runtime-final.log.
The final two status-latency regressions isolate all other API dependencies,
using the real Czech catalog. Only status is delayed 2s; original 5s assertions
remain. The geometry test waits for page readiness before unchanged dimensional
assertions. These fixtures do not claim real-backend startup timing.

## Provenance and safety

Final E2E used PID8508 on127.0.0.1:8183, runtime 0.1.2, project root
C:/TepelneCerpadlo/step26-git and config
C:/TepelneCerpadlo/step29-isolated-preview/preview.json, with separate
data/history/log/archive paths. Post-test TCP ownership still confirmed PID8508.
Proof: step29-evidence/isolated-runtime.json and final-runtime.json.
Earlier runs on8181 used an old 0.1.1 backend and are diagnostic only. Their
results were not used as final evidence. Other failed/intermediate logs remain
diagnostic. Production8080/HEAD98e9fa5 remained unchanged.

## Independent review and practical limits

The reviewer found three IMPORTANT issues in the first candidate: Forecast
undefined variable, Today unknown/balanced grid label and stale Shelly readings
after read failures. All were fixed and covered by regressions. Final review
found no remaining BLOCKER/IMPORTANT after 56 PASS and complete runtime proof.
Physical CT/phase wiring remains unverified; signed raw readings are preserved
and errors explicit. Native battery reserve charging is labelled a possible
explanation, not a confirmed cause. No physical control algorithm was changed.

## Traceable evidence

- E-029-001: truthfulness unit/browser regressions and owner-shaped midnight fixture.
- E-029-002: real Chromium screenshots flow-360/390/430/1280.png and 200% text zoom checks in C:/TepelneCerpadlo/step29-evidence.
- E-029-003: quality/adjacent-interval/nullable metrics regressions and API.md contract.
- E-029-004: current-quarter/midnight/zero/negative-price cache and snapshot preservation tests.
- E-029-005: complete test logs, post-test runtime proof and independent review recorded in STEP.json.

AC-029-001 through AC-029-004 PASS. Automated checks/review for AC-029-005 PASS;
its owner Human Gate remains pending before DONE and deployment.
