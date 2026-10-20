# Step26 - production deployment completed

## Release and approvals

- Version: **0.1.1**, tag **v0.1.1**.
- Deployed, fully validated commit: `0b36d3e3c69007f231ed87b102d6c09dd0a3e299`.
- Fixed release time: **2026-10-20 18:29:45 Europe/Prague**, taken from the
  first successful actual production deployment verification.
- PR41 merged into PR40's branch; PR40 merged into
  `claude/reconcile-production-20261020`. Main synchronization remains separate.
  Existing production control changes relative to main are not attributed to this step.
- Independent review approved both steps after fixing audit starvation in `79ac8f2`.
  Reviewer evidence: `../step27/REVIEW.md`. The reviewer also approved the planned
  metadata reload procedure. Owner explicitly approved deployment in chat.

## Production execution

Production root: `C:/TepelneCerpadlo/Home-Energy-Controller`.
Existing Python and `dev/run.py` startup command were preserved.

| Event | Europe/Prague time | Process |
| --- | --- | --- |
| Original 0.1.0 stopped after identity/config checks | 2026-10-20 18:04:37 | 14532 |
| Verified complete backup | 2026-10-20 18:10:17 | stopped writers |
| Offline SDG replay completed | 2026-10-20 18:26:13 | service tool only |
| First 0.1.1 start | 2026-10-20 18:29:44 | 9980 |
| Actual deployment verified / fixed release time | 2026-10-20 18:29:45 | 9980 |
| Planned final metadata reload | 2026-10-20 18:32:30 | **4132** |
| Final live checks | 2026-10-20 18:35:07 | **4132** |

The second start was planned solely to load metadata recorded from the actual
successful deployment. Current data, runtime state and checkpoints were preserved
between starts. There were no uncontrolled retry restarts.

Final verification: one listener on `[::]:8080`, PID4132, correct project root,
exact tag/commit, all six readers successful with zero reader errors, and no new
ERROR/CRITICAL/Traceback events in either startup log. Production browser confirmed
v0.1.1, the fixed Prague release time, dialog close/focus and zero JavaScript errors.

All four original configuration/secret-file SHA256 hashes match the preflight.
All enable/write switches are unchanged; main `controller.enabled=false` remains
false. TNG persisted last-post times survived the metadata reload. Controller,
writer, GoodWe manager, scheduler and TNG write-protection code remain unchanged
against deployed baseline3f0d9c2. No physical test writes were requested/performed.

## Actual production history

Counts below are from a frozen stopped-writer snapshot after offline work.

| Source | Before | After repair | After authoritative SDG replay |
| --- | ---: | ---: | ---: |
| TNG | 88,963 | 82,602 | 82,602 |
| SDG history | 1,331,922 | 1,296,380 | 1,296,662 |
| Existing daily summaries | 58 | 58 | 58 |

Repair: 88,963 TNG input timestamps corrected and historical settings cleared;
6,361 TNG duplicates removed. SDG: 1,295,961 input timestamps corrected,
6,536 exact duplicates and 29,006 import-status rows removed. Nine existing
temperature summaries changed; unrelated energy fields were preserved.
412 files changed. Repeated repair: **zero changed files**, zero unknown input rows.

All 369 available DBFs were replayed through the existing reader: 693,459 valid
source rows processed, zero corrupt files. Migration/adoption changes are not
reported as newly recovered measurements. The net SDG increase after replay is
282 rows. Repeat: imported0 and checkpoint_writes0. 123 source rows lacked a
normalizable timestamp and were not inserted; no zero/estimated values were used.

Live collection resumed successfully: a later snapshot contained 82,635 TNG and
1,296,782 SDG rows. TNG's new measurement timestamps through18:32:20 exactly match
their UTC sample_time; SDG measurements through18:34 and GoodWe through18:35
were verified. Older TNG gaps that returned empty First responses remain unknown;
SDG availability is not presented as proof of complete independent GoodWe history.

Detailed CSV by source/day, including corrected inputs, duplicate removals,
status removals and net source backfill:
`C:/TepelneCerpadlo/step27-evidence/production-history-by-period.csv`.

## Performance and validation

- Actual one-time production SDG migration: **507.89 seconds**. Initial legacy
  checkpoint loading and report generation are outside this measured interval.
- Checkpoint: **94,147,898 bytes before -> 243,168 bytes after**; 369 files tracked.
- Live unchanged poll observed: source_bytes427, imported0, checkpoint_writes0.
  Audits/real source changes can require additional bounded I/O.
- Observed working set after restart: approximately64-88 MB at recorded samples.
  Different uptime/cache conditions do not establish a comparable long-term RSS gain.
- Controlled same-input benchmark remains in PERFORMANCE.md: unchanged median
  0.2420 -> 0.000264 seconds; initial migration memory increased80.18 ->108.85 MB.
  This one-time tradeoff is retained, not described as a memory improvement.
- Exact final release commit `0b36d3e`: **355 unit PASS, 41 real browser E2E PASS**,
  zero skipped E2E, Ruff/SDD/repo/runtime smoke PASS. PR checks on the reviewed
  combined source passed Python3.11/3.12 and full SDD/browser validation before merge.
  The timestamp-only post-merge commit was fully validated locally.

## Backup and rollback

Verified complete backup:
`C:/TepelneCerpadlo/hec-backup-20261020-180437`.
It contains 1,156 verified files /1,481,598,253 bytes, 3,490,261 validated JSONL rows,
the original code archive, repository bundle, local planning documents,
configuration, secrets, logs, history, checkpoints and runtime state.
`manifest.json` and `verified.json` provide the verification evidence.

Additional affected-file repair backup:
`C:/TepelneCerpadlo/hec-backup-20261020-180437-repair`.
Both are outside Git. Rollback restores baseline3f0d9c2 plus the complete consistent
data/config/checkpoint set while the verified production process is stopped;
new files are preserved outside the active directories. Rollback was prepared,
not executed or claimed as tested on hardware.

Raw deployment/repair/UI/validation evidence is outside Git at
`C:/TepelneCerpadlo/step27-evidence`. No production data, logs, backups or credentials
were committed. No new user feature beyond version/changelog was introduced;
Step27 fixes existing settings persistence under separately approved scope.
