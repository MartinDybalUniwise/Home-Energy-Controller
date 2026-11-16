# Validation before production activation

- Prechange verified incremental snapshot:c69a5bbc4bc84d168599c0006876771d.
  First attempt refused an incompletely released Windows process handle; service
  was restored, then stopped/verified with a short exit wait. Successful routine
  capture copied415538141bytes; initial_audit=false, dirty history files229.
  No unchanged full-history traversal or frozen-directory access.
- Full non-browser suite:678 passed,116 deselected. Final affected/i18n suite
  after the last DHW-window correction:127 passed.
- Nov15 shadow replay:1437 samples. Original code:99 coast samples,60 after13h.
  Final code:0 coast samples,0 after13h. Nov10 final replay:1437 samples,0 coast.
  Both use actual measured history and acknowledgement reconstruction. Initial
  settings are assumed42/21.5; this is explicitly not a physical simulation.
- Replay exposed a possible extra catch-up before an ordinary DHW window. Added
  a90min scheduled-window exclusion and regression; final13h plan is heating.
- Insufficient confirmed heating response is diagnosed; missing DHW remains
  explicit when comfort prevents catch-up. No claim of guaranteed warm rooms or
  counterfactual energy savings from shadow replay.
- Mobile390px overview/control warnings:PASS, screenshots inspected, no horizontal
  overflow or browser errors. Dashboard uses the actual controller catch-up plan.
- Changed Python lint, compile, JSON/i18n, whitespace, repository hygiene and
  README status validation:PASS. Whole-repository Ruff has34 PRE-EXISTING findings
  in test_mcp_setup and historical step46/47/48 activation scripts; baseline
  comparison proves identical code/location/messages. They are not new failures.
- Generated example-only test output was restored to its pre-task content;
  schema and private production configuration are unchanged. No telemetry is
  committed. Pump flag preserved.

Private evidence lives under the owner's monitoring-evidence directory: before/
after replay JSON, full/targeted test output, baseline lint comparison and mobile
screenshots. Existing two-hour reviews read the expanded hec-status skill and
report faults/debt into this chat; no new timer or direct chat transport exists.

Production0.1.20 started from the existing HomeEnergyController service, actual
writerPID3484. New42/21.5 request sent09:33:30 and both native false->true->false
cycles completed09:35:33 on Nov16. Room21.7C, boiler25.6C; recovery evidence is
initially insufficient and coast correctly vetoed. A resolved plan alone was
not counted as acknowledgement. No extra command was used for testing.

An additional pre-restart capture correctly refused the dirty tree after an
initial commit failed for missing Git identity. The finally clause restored the
service using the validated code, protected by the original prechange snapshot.
Commit194295d then succeeded under explicit Codex identity. A clean follow-up
snapshot/restart and subsequent readbacks are recorded in private live evidence.

Final clean routine snapshot:91e3dfb18bb34217a0cff3ef03555283, revision9724389,
copied33277303bytes,15 dirty history files, initial_audit=false. The existing
service restarted successfully with writerPID10412 in the correct root. At09:38
version0.1.20, both gates clear, actual heating42C, room21.7C, boiler25.6C.
Both last_post_at values remained09:33:30: restart sent no duplicate commands.
Current/prediction/config GETs succeeded; TNG reader has no current error.
Live evidence:comfort-deployment-2026-11-16.json in private monitoring evidence.
The final documentation-only commit does not alter the verified runtime code.
