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
- Test-generated config.example output restored to its pre-task content. No
  private configuration or telemetry is committed. Physical pump flag preserved.

Private evidence lives under the owner's monitoring-evidence directory: before/
after replay JSON, full/targeted test output, baseline lint comparison and mobile
screenshots. Existing two-hour reviews read the expanded hec-status skill and
report faults/debt into this chat; no new timer or direct chat transport exists.

Production activation and live confirmation are recorded below after observation.
