# Step 17 Acceptance Criteria

## Objective

These criteria define when the Step17 planning package is complete enough to be
considered ready. Step17 remains `PLANNED`; therefore the checklist stays
unchecked and does not represent DONE status.

## Canonical criteria

- [ ] AC-017-001: `REQUEST.md` and `REQUIREMENT.md` define the Step17
  repository/SDD review scope, safety boundaries, and planning-only non-goals.
- [ ] AC-017-002: `PLAN.md`, `TRACEABILITY.md`, `STEP.json`, and `RESULT.md`
  are mutually consistent and use `REQ-017-*`, `AC-017-*`, `E-017-*`, and
  `S01...` identifiers coherently.
- [ ] AC-017-003: `STEP.json` records `classification=LARGE`,
  `status=PLANNED`, `readiness=YES`, and Gate A `APPROVED`, without claiming
  DONE or feature implementation.
- [ ] AC-017-004: `dev/README.md` contains a Step17 row aligned with the
  manifest and marked as a planning-only step.
- [ ] AC-017-005: `python3 dev/sdd/tools/validate_step.py --phase structural
  --step dev/step17` passes.
- [ ] AC-017-006: `python3 dev/sdd/tools/validate_step.py --phase ready --step
  dev/step17` passes.
- [ ] AC-017-007: `RESULT.md` records the planning-only boundary, exact files
  changed, and the fact that no application code, root prototype, or device
  write behavior was modified.

## Definition of ready

Step17 is ready when the planning files exist, the manifest and traceability are
coherent, Gate A is approved, and both validator phases pass. Ready does **not**
mean done.
