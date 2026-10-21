# Result

Implementation complete; validation/review in progress. Human Gate remains pending.
No production deployment, physical setting change, history rewrite or meter sign correction.

## Confirmed validation

- Complete unit/integration suite: 393 PASS, 56 browser tests deselected as intended (744.58s).
- Affected/controller/predictor/SDD regressions: 81 PASS (199.31s).
- Ruff, repo hygiene, all 18 manifest-bearing steps structural and Step29 ready: PASS.
- Runtime safe flags: controller enabled=false, write_enabled=false; TNG writer=false and GoodWe=false.

## Browser provenance

Earlier browser runs served current frontend files from an old preview backend
PID15420 (started2026-10-20 19:38, runtime0.1.1). They are diagnostic only,
not final E2E evidence. The preview helper healthcheck had accepted the occupied
port8181 while its newly started child exited. Production8080 was unaffected.
Final full browser validation uses the independently launched preview8183,
runtime0.1.2, project root C:/TepelneCerpadlo/step26-git,
config C:/TepelneCerpadlo/step29-isolated-preview/preview.json,
with separate mock data/history/log/archive paths and all physical I/O disabled.
Observed backend PID8508. Final browser result pending.

The first complete run against this verified backend passed 55/56 cases,
including all 9 Step29 cases, all mobile/desktop layout checks and 200% text zoom.
Only the pre-existing slow-status latency fixture failed. Its synchronous Python
sleep blocked dispatch of unrelated browser requests. Replacing it with a browser
Promise correctly isolates status latency, but a targeted repeat exposed remaining
loopback variability in the other live endpoints (one pass, one fail). An exact
request-timing diagnostic then rendered successfully without a JavaScript error;
that successful run does not by itself prove the intermittent failure's cause.

The final two latency regressions therefore use deterministic responses for their
current/weather/prices/prediction dependencies and delay only status by 2 seconds,
preserving its JSON, HTTP status and original 5-second visibility assertion.
Other E2E scenarios still exercise the real isolated backend. Final full-suite
evidence must be from this corrected fixture; no earlier failures are reported as PASS.

## Review and practical limits

Independent reviewer found three IMPORTANT issues in the first implementation:
Forecast undefined variable, Today unknown/balanced grid label, and stale values
after all Shelly reads fail. All three were corrected and regressions added.
Final exact-commit review remains pending complete valid browser evidence.
Physical phase/CT wiring remains unverified; UI reports invalid readings explicitly.
Native battery charging reason is an explicitly labelled hypothesis, not a command.

## Evidence

E-029-001: truthfulness unit/browser regressions and owner-shaped midnight fixture.
E-029-002: real Chromium360/390/430/1280 screenshots and text zoom checks.
E-029-003: quality/interval/nullable metrics regressions and API contract notes.
E-029-004: zero/negative-price quarter/midnight cache and snapshot preservation tests.
E-029-005: full test logs, safety/provenance and independent review (pending final result).
Local artifacts: C:/TepelneCerpadlo/step29-evidence and step29-*.log alongside it.
