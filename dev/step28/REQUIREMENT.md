# Requirements

## Objective

Prevent proven impossible historical TNG temperatures from corrupting charts/aggregates, preserve raw evidence and current control inputs, and make the same chart readable on mobile.

- REQ-028-001: Historical TNG temperatures below absolute zero/nonfinite are unknown before aggregation. Do not infer vendor flag encoding, fabricate a corrected temperature or overwrite original history/current snapshots.
- REQ-028-002: Missing table/tooltip values remain unknown, never zero. TNG mobile axis text and chart are readable; multi-day dates distinguish time. Other chart families retain their behavior.
- REQ-028-003: Regression tests cover the actual outlier failure and 24h/7d/30d/mobile/desktop, gaps, valid negatives and zero; all mandatory validation and independent review before Human Gate/deployment. Controllers, writers, scheduler, config and device switches remain unchanged.
