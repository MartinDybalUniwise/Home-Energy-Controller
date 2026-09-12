# Step 18 Request – SDG Log Reader

## Summary

Add the first SDG integration step as a read-only log reader. The source is the
verified UNC directory `\\192.168.2.115\Promotic\Apps\SDGeco\Data`. Existing
FTE/GoodWe telemetry readers remain available and provide the fallback path when
SDG data is unavailable, unreadable, or too stale.

This request covers log reading and source selection only. It does not add
GoodWe control, writer behavior, SDG writes, or changes to the existing FTE
reader implementation.

## Scope

### In scope

- Read-only discovery and parsing of SDG DBF logs.
- SDG trend and event log source contract.
- Normalization into the existing `goodwe` telemetry history contract.
- Freshness and validity checks for SDG samples.
- Fallback to the unchanged existing `GoodWeReader`.
- Source provenance and diagnostics for `sdg`, `fte_backup`, and unavailable data.
- Focused unit and mock tests for parsing, freshness, deduplication, and fallback.

### Out of scope

- Any GoodWe writer, controller, optimizer, or inverter command.
- Any SDG or GoodWe physical-device write.
- Refactoring or replacement of the existing FTE/GoodWe reader.
- SDG configuration UI, deployment changes, or production activation.
- Changes to frozen root prototypes.
- New API or storage contracts unless required to preserve the existing
  `goodwe` history contract and provenance can be added compatibly.

## Safety constraints

- `controller.enabled=false`.
- `tng.write_enabled=false`.
- `goodwe.enabled=false` in local and preview validation unless separately
  approved for a read-only test.
- No physical-device writes.
- SDG access is read-only and limited to the configured log root.
- Stale, malformed, or ambiguous data must fail closed; values must never be
  guessed.
- No secrets, production data, logs, caches, or browser artifacts are committed.

## Acceptance signal

A future implementation can identify whether a current `goodwe` sample came
from fresh SDG logs or from the unchanged FTE backup, preserves the existing
consumer contract, and fails closed when neither source supplies valid fresh
data. The plan is not implementation approval; Gate A remains pending.
