# Approved SMALL plan

## Goal

Correct the reported historical TNG chart defect. Owner explicitly approved this chat plan before application edits.

| Step | Work | Status |
| --- | --- | --- |
| S01 | Diagnose raw/API/chart and preserve production state | PASS |
| S02 | Historical read quality and missing-value table semantics | PASS |
| S03 | TNG-only responsive chart and meaningful date labels | PASS |
| S04 | Regressions, full validation and independent review PASS; owner Human Gate pending | IN_PROGRESS |

Known evidence: 86 impossible room values: two on2026-09-18 and84 on2026-10-02; values-3254.7/-3255.1. Thirty-day hourly average reaches-3255.1 and controls the chart axis. Do not guess a bitmask correction. Apply quality rules only to history reads, keeping stored rows and current snapshots intact. Original mobile SVG960-wide shrinks11px text to about4px. Limit responsive changes to TNG history, preserving single temperature axis and legend. Verify on safe mock using production-shaped fixtures and a read-only production-data replay. No production mutation while developing.
