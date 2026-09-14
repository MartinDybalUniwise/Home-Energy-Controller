# Step 22 Result

## Summary

Step 22 implementation is complete for scheduler timing, bounded stop, safe
runtime context, and focused regression coverage. No external checkout, share,
service, or device was changed.

## Planned vs implemented

- Planned: Stabilize slow SDG scheduling and runtime diagnostics after Gate A.
- Implemented: Scheduler schedules after poll completion, stop uses one total
	timeout budget, status exposes non-secret process/configuration context, and
	SDG nested `values` are flattened for History API series discovery,
	aggregation, and raw rows. The History frontend accepts SDG numeric fields,
	so the UI renders values instead of timestamps only. Control & Plan now uses
	the latest daily summary when current counters are unavailable. Tests cover
	timing, isolation, stop, SDG regression, storage, API output, and browser
	rendering.

## Validation

- Command: `python -m pytest dev/hec/tests/test_scheduler_app.py -q`
- Result: PASS, 10 passed.
- Command: `$env:HEC_RUN_E2E='1'; $env:HEC_BASE_URL='http://127.0.0.1:8181'; python -m pytest dev/hec/tests/e2e -o addopts= -m e2e -x -q`
- Result: PASS, 27 passed with safe preview running.
- Command: `python -m pytest dev/hec/tests/test_step16_goodwe_implementation.py -k 'sdg' -q`
- Result: PASS, 5 passed.
- Command: `python -m pytest dev/hec/tests/test_web_api.py -k 'sdg_history' -q`
- Result: PASS, 1 passed.
- Command: `python -m ruff check .`
- Result: PASS.
- Command: `python -m pytest dev/hec/tests/test_scheduler_app.py dev/hec/tests/test_storage_jsonl.py dev/hec/tests/test_web_api.py dev/hec/tests/test_step16_goodwe_implementation.py -k 'sdg or history or series or scheduler or storage' -q`
- Result: PASS, 31 passed; includes nested SDG `values` flattening and API
	regressions.
- Command: `python dev/sdd/tools/preview.py start` and read-only `/api/status` check
- Result: PASS; preview started, runtime context present, controller/write gates false.
- Command: `python dev/sdd/tools/validate_step.py --phase ready --step dev/step22`
- Result: PASS.
- Command: `python -m pytest -m "not e2e"`
- Result: PASS, 298 passed, 27 deselected; the Step 16 GoodWe audit regression
	test was corrected to locate the audit file by the actual recorded timestamp.
- Command: `python dev/sdd/tools/full_validation.py` with safe preview running
- Result: Previously failed on the audit test; the corrected test passes in the
	non-E2E suite. Full Validation is rerun by CI for this PR.

## Safety status

- Controller enabled: false
- TNG write enabled: false
- GoodWe writer enabled: false
- Physical writes: blocked
- External checkout/share: read-only inspection only

## Open items

- AC-022-006 remains open until the external runtime/process state is validated
	in an authorized read-only observation window.
- Gate B and Gate C remain `NOT_REQUESTED`; the Step must not be marked DONE.
