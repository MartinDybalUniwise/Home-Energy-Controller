# Approved incremental backup plan

## Goal

Reuse immutable historical backup payloads and capture only new or changed files without losing late corrections.

Classification: LARGE. Owner approved the concrete proposal in chat (Udelej to).
Implementation choices below make that approved scope reliable, without seeking duplicate consent.

| Step | Work | Status |
| --- | --- | --- |
| S01 | Register approved scope and review backup/write paths | PASS |
| S02 | Add persistent write-ahead dirty paths to all history mutation paths | PASS |
| S03 | Baseline registration, immutable payloads and atomic incremental reference snapshots | PASS |
| S04 | Explicit staging restore and release/rollback documentation | PASS |
| S05 | Meaningful tests, lint, SDD validation and independent review | PENDING |
| S06 | Owner Human Gate and separately approved production activation | PENDING |

The first transition requires one explicitly reported, stopped-writer audit of current
history against the existing verified baseline: only differences are copied. Thereafter
no historical glob or old-file stat/hash occurs during routine captures; only dirty paths
are visited. Persistent markers precede writes and survive process termination, so
Application.stop timeout is never treated as proof that writers stopped.
Untracked rollback/manual tools require explicit tracking invalidation and a new audit;
no automatic full-scan fallback is permitted. Configured external archive is unsupported
and rejected. The existing full backup and all referenced payloads remain in place.
No existing-history move, rewrite, compression, device command or production restart.
Rollback of tooling does not remove backup objects; rollback to untracked writers invalidates coverage.
