# Step 22 Plan - Stable SDG runtime scheduling

## Status vocabulary

`PLANNED`, `IN_PROGRESS`, `DONE`, `BLOCKED`.

## Goal

Prevent slow SDG history polls from driving an immediate repeat loop, preserve
reader isolation, and provide enough safe evidence to explain whether the HEC
runtime is stopped, misconfigured, or actively importing SDG history.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Reproduce and classify the slow-poll/runtime lifecycle behavior | DONE |
| S02 | Define scheduler timing and lifecycle diagnostics contract | DONE |
| S03 | Implement the smallest scheduler/diagnostic correction | DONE |
| S04 | Add focused regression and safety tests | DONE |
| S05 | Perform read-only external/runtime validation | PLANNED |
| S06 | Run repository validation and prepare Reviewer handoff | IN_PROGRESS |

## Detailed implementation strategy

### S01 – Reproduce and classify the runtime behavior

Objectives:
- Confirm the current scheduler semantics for a poll longer than its interval.
- Correlate `reader_started`, `poll_success`, poll duration, and process exit
	evidence without starting or changing the external runtime.
- Establish whether the missing process is a normal manual stop, a crash, or a
	service/task lifecycle issue; do not infer this from a stale log alone.

Implementation:
- Use deterministic fake readers and existing log/status APIs in local tests.
- Inspect `T:\Home-Energy-Controller` and the Promotic share read-only only.
- Record checkout path, configuration source, latest SDG log timestamp, and
	process presence without collecting secrets.

Risks:
- A historical successful import cannot prove the current process is alive.
- External runtime evidence may be stale or belong to another launch method.

### S02 – Define scheduler and diagnostics contracts

Objectives:
- Specify whether next polling is measured from poll completion, scheduled
	start, or a bounded hybrid policy, including behavior after slow/error polls.
- Specify stop/join behavior and the minimum status fields needed to diagnose
	an inactive runtime.

Implementation:
- Preserve existing `ReaderStatus`, backoff, and `sdg_history` contracts where
	possible.
- Keep diagnostics secret-free and compatible with existing API/status output.

Risks:
- Changing timing semantics can affect all readers; the contract must cover
	both fast readers and long-running network readers.

### S03 – Implement the smallest correction

Objectives:
- Apply only the approved scheduler/lifecycle change after Gate A.
- Keep SDG reading strictly read-only and avoid parser/storage redesign.

Implementation:
- Prefer a local change in scheduler timing/lifecycle ownership over a broad
	controller refactor.
- Do not add an automatic restart, service installation, or external command.

Risks:
- A timing correction that relies on wall-clock time could be non-portable;
	use the existing monotonic scheduling model.

### S04 – Add focused regression and safety tests

Objectives:
- Verify no immediate catch-up loop after a slow poll.
- Verify a slow SDG reader does not block a healthy reader.
- Verify stop behavior, error isolation, backoff, and unchanged write gates.

Implementation:
- Extend scheduler/app tests with deterministic fake readers and bounded
	monotonic/event control; keep SDG DBF tests from Step 21 unchanged except
	where a direct contract requires an assertion.
- Add evidence that the runtime status distinguishes stopped/no-process from
	reader failure where the existing interface supports it.

Risks:
- Timing tests can be flaky if they depend on real sleeps; avoid sleeps or use
	controlled clocks/events.

### S05 – Read-only external/runtime validation

Objectives:
- Validate the configured SDG path, checkpoint continuity, recent history
	writes, and log sequence against the external checkout if available.
- Confirm no external file, service, device, or configuration writes occur.

Implementation:
- Use read-only PowerShell inspection and safe local preview only.
- Do not start, stop, restart, install, or reconfigure the external runtime.

Risks:
- Runtime validation may remain open if no authorized operator supplies a live
	process/service window; mark it open rather than claiming success.

### S06 – Validation and handoff

Objectives:
- Run focused pytest, Ruff, relevant non-E2E tests, safe preview/browser
	checks if UI/status changes are included, and Step 22 validation.
- Record exact results, unrelated failures, and remaining runtime evidence.

Implementation:
- Keep Step 22 `IN_PROGRESS` until Reviewer and Human Gate evidence exists.
- Do not mark Gate B/C or DONE from automated output alone.

Risks:
- Existing unrelated failures must be classified using the SDD severity model
	and must not be hidden or fixed opportunistically.
