# Requirements

## Objective

Separate inverter AC energy from grid-meter energy.

- REQ-032-001: Neither GoodWe adapter labels AC daily import/export as grid import/export. Preserve AC counters under explicit additive names and valid grid-meter cumulative counters. Unsupported daily grid values stay unknown.
- REQ-032-002: Legacy current/history and UI SDG fallback cannot reintroduce the wrong grid daily values. Preserve raw files and true measured zero; do not fabricate a midnight baseline or change instantaneous signs.
- REQ-032-003: Meaningful regressions, targeted browser validation, independent review and owner Human Gate precede DONE/deployment. No device/config/control changes or history rewrite.
