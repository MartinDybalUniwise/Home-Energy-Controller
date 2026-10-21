# Requirements

## Objective

Stop repeated copying and traversal of unchanged historical data during releases while preserving recoverable snapshots.

- REQ-030-001: Reuse the existing verified full backup once; routine releases never enumerate, read or hash unchanged history files.
- REQ-030-002: Persist dirty history paths before append, importer replacement and offline repair, including corrections of old days; reject tracking gaps and unsupported archive mode.
- REQ-030-003: Copy only new/changed payloads into an immutable store; atomically publish a complete reference manifest before acknowledging dirty markers. Require stopped writers.
- REQ-030-004: Restore a selected snapshot into an empty staging directory, verify all payloads and reject missing/corrupt dependencies or unsafe paths. Preserve all referenced baselines.
- REQ-030-005: Exclude frozen logs before traversal, include at most seven days of diagnostic logs, preserve live history/query availability and all physical control settings.
- REQ-030-006: Prove zero unchanged-history reads/copies on repeat backup, old-day corrections, interrupted/retried capture and complete restore; independent review and Human Gate before deployment.
