# Deployment result - 0.1.4

Owner Human Gate APPROVED: Schvaluji nasazení. Candidate d5e89a210645ad307ee70e206013c75e32a2943c verified at 2026-10-21T14:48:18.701059+02:00.
Final production revision f744bec700a97c20887586ede1b60ec3a5301501, PID 8000; release metadata reloaded and verified at 2026-10-21T14:55:32.888874+02:00.
All six sources fresh, controller disabled, native TNG gate preserved, private configuration hashes unchanged. Backend product code unchanged.
Real production API (no mocked data), Chromium 360/390/430/1280px PASS: diagram visible on mobile, no horizontal page overflow, recommendation text fits, no page errors. Actual touch scrolling at390px preserves route, horizontal/vertical scrolling and explicit menu navigation work. Real release dialog shows the actual verified timestamp.
Routine backups only, initial_audit=false: first attempt 34511902 B; retry 18949173 B; cumulative new payload 53461075 B. Final snapshot 6bb3c8b1cd644bdd98cdbf310418d877, logical restore references 1491332212 B. Each capture read11 marked changed history files; no unchanged history traversal, no bootstrap, frozen logs untouched. Final metadata reload copied0 backup bytes.
First attempt deliberately rolled back to tracked0.1.3 after short startup wait expired; SDG subsequently recovered on original version. Original verification failure retained in attempt1-failure.json. Operator waiting budget increased, all six fresh-source requirements retained; no product workaround or configuration change. Initial production browser attempt during rollback and a second attempt with a five-second menu-render wait were non-green and are not counted as passing evidence. The final run used consistent operational waits for real network data; all layout, touch and no-error assertions retained. Cumulative backup cap includes both attempts.
Evidence directory C:/TepelneCerpadlo/step31-release-evidence: attempt1-backup.json, attempt1-failure.json, backup.json, deployed.json, deployed-final.json, final-status.json, browser-smoke.json, final-release-browser.json, production-flow-390.png and production-overview-390.png.

## Historical implementation and pre-deployment record

# Result

Implementation and automated validation complete. Independent Gate B APPROVED for code 09b75c0684dfa535fad41b332b28d6b02522e1e1 by /root/release_review; no unresolved BLOCKER or IMPORTANT. Owner Human Gate and production deployment remain pending; production remains unchanged at 0.1.3.

## Final validation

- Exact candidate 09b75c0684dfa535fad41b332b28d6b02522e1e1: all 77 real Chromium E2E PASS, no skips. C:/TepelneCerpadlo/step31-e2e-safe-local.log.
- Browser coverage includes all prior navigation/settings/history/control-plan/Today/Flow/Forecast checks and 21 new Step31 cases: 360/390/430/1280px, Czech/English, 200% text zoom, child geometry, real CDP touch scrollLeft/scrollY and explicit menu navigation, zero/missing/negative flows, both arrow polarities, full/reduced/off motion and actual animated dash offsets in two time positions.
- A reviewer found one IMPORTANT issue: negative net flows reversed arrow markers but animated dashes still moved forward. Fixed via direction-specific animation; both dedicated tests PASS, C:/TepelneCerpadlo/step31-direction-final.log. Marker and animation now agree.
- Three targeted desktop cockpit geometry tests PASS after compact layout correction; C:/TepelneCerpadlo/step31-desktop-fix.log. Existing geometry requirements were not weakened.
- Ruff, git whitespace, all 20 manifest packages structural validation and repository hygiene PASS.

## Provenance and limits

Final tests used only port 8184, working source C:/TepelneCerpadlo/step26-git, explicit isolated config C:/TepelneCerpadlo/step31-isolated-preview/preview.json and separate data/history/logs/archive paths. All external reader polling, controller and physical writes are disabled. Manual SDG verification also targets a local empty fixture. Exact final runtime, process and config proof: C:/TepelneCerpadlo/step31-evidence/final-runtime.json.

Earlier diagnostic runs are not final green evidence: 13/15 before the English weather zoom fix, 18/19 before the mobile animation CSS selector fix, 21 PASS before the desktop panel size fix, an intentionally interrupted run for independent review, and 14 PASS before an existing English reload assertion failed. The unchanged English test passed alone (1 PASS, C:/TepelneCerpadlo/step31-language-recheck.log); final canonical full run above passed without changing its five-second assertions. No claim is made that the earlier language failure was caused by product changes or was fixed by code. Test preview was separately tightened to use a local SDG fixture for the manual verification test.

No production restart/deployment/configuration edit, raw history rewrite, backup, import/backfill or physical setting change. Frozen logs were not entered. Production source remained 5bf1d35e06e720ae4afa1252b58212be9f26f699 with listener PID13656 at the read-only check. No backend Python application code changed; the relevant automated validation is real frontend browser coverage, not a new backend unit-suite claim.

## Traceable evidence

- E-031-001: geometry and long unavailable-state text, 200% text zoom and Czech/English regressions.
- E-031-002: measured-direction markers, actual animated dash direction, zero/missing/invalid paths and readable HTML labels with SVG connectors.
- E-031-003: actual browser-generated touch gestures preserve the route and horizontal/vertical scrolling; explicit menu navigation still works.
- E-031-004: complete 77 PASS log, final isolated runtime proof and review/owner gate recorded separately. Human Gate required before DONE and deployment.

Screenshots in C:/TepelneCerpadlo/step31-evidence are explicit test-fixture images, not production telemetry. Original non-green diagnostic logs remain outside the repository.
