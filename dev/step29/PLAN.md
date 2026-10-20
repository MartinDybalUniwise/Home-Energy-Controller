# Approved correction plan

## Goal

Implement the owner's approved midnight diagnostic and mobile readability corrections.

Classification: LARGE, multiple presentation/analysis defects, no new physical control.
Owner approved the concrete diagnostic plan and mobile proposal before code edits.

| Step | Work | Status |
| --- | --- | --- |
| S01 | Preserve diagnostic evidence and record approved scope | PASS |
| S02 | Add observational meter quality; correct energy and running reports | PASS |
| S03 | Replace shrinking appliance diagram with readable HTML rows; factual statuses | PASS |
| S04 | Remove Today mock data and project cached price for current quarter | PASS |
| S05 | Unit, full real-browser, lint, repository/step checks and independent review | IN_PROGRESS |
| S06 | Owner Human Gate and separately authorized deployment | PENDING |

Risks: physical meter orientation is not proven; never apply abs() or change wiring remotely.
Incomplete data must not become measured zero or a full-day claim. Preserve existing
field names and raw telemetry. Annotation fields are additive. No hardware control,
TNG change-gate, native inverter mode, SOC settings, production files or history rewrite.
No automatic bulk recalculation. Empty summary UI must explain missing reports.
Validate isolated mock preview with writes disabled; use production-shaped fixtures.
Rollback: revert code changes; no data migration or physical setting rollback needed.
