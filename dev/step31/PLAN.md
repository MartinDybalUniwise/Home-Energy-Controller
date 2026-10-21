# Mobile layout and flow correction

## Goal

Fix all three screenshot-reported UI defects without compromising measurement truthfulness.

Classification: LARGE. Gate A PENDING; no application source edit before owner approval of this concrete plan.

| Step | Work | Status |
| --- | --- | --- |
| S01 | Inspect screenshots and reproduce Today/Flow layout and touch navigation | IN_PROGRESS |
| S02 | Correct card/grid sizing, typography, wrapping, margins and missing-state presentation | PLANNED |
| S03 | Restore a readable compact mobile flow diagram, correct arrows, direct values and reduced-motion behavior | PLANNED |
| S04 | Remove global swipe route changes; preserve inner scrolling and explicit navigation | PLANNED |
| S05 | Real browser geometry, touch/zoom/data-quality regressions, affected checks and independent review | PLANNED |
| S06 | Owner Human Gate and separately authorized incremental-backup deployment | PLANNED |

Diagram: fit the mobile viewport with readable HTML labels and SVG/CSS connectors, rather than shrinking a desktop canvas or replacing all connections with cards. Reuse the entity palette, directional arrows and animation preferences from dev/step01/UI_DESIGN.md, sections 4.3 and 6. Arrow thickness may encode magnitude within the established 2-8 px range. Do not imply independently measured allocation between sources where only net powers are known. Missing or invalid meter values remain explicit; no invented heating/DHW output or measured-zero fallback.

Scope includes both Today and Flow, complete unavailable recommendation text, aligned appliance labels/values/status and adequate spacing. Fix root layout rules instead of masking overflow with a document-wide clip. Touch regressions must use actual browser touch events, assert the route stays fixed while content moves and verify normal vertical scrolling and explicit menu navigation.

Risks: conflicting legacy CSS and narrow/zoomed layouts; validate bounding boxes of text and children, not only document width. Preserve backend, raw history, controller/native device settings and TNG change gate. No new history scan, backfill or baseline copy. Future approved release uses Step30 incremental backups and excludes frozen logs before entry.

Rollback: return application code to the verified 0.1.3 revision, preserving runtime data and tracking markers; no schema migration or hardware action.
