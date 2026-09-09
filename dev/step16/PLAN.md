# Step 16 plan

## Goal

Define a safe, testable GoodWe integration refactor without implementing or
enabling inverter control. Step 16 remains `PLANNED` until implementation,
automated evidence, human review, and hardware verification are complete.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Confirm GoodWe library API and communication ownership | PLANNED |
| S02 | Design the shared manager and read-only reader boundary | PLANNED |
| S03 | Specify writer commands, confirmation gates, and audit records | PLANNED |
| S04 | Specify SDG history import and path configuration | PLANNED |
| S05 | Define configuration, diagnostics, i18n, and test contracts | PLANNED |
| S06 | Implement and test the approved design in a later development phase | PLANNED |
| S07 | Perform guarded human and hardware verification before completion | PLANNED |

## Safety boundaries

- `controller.enabled=false` and `tng.write_enabled=false` remain unchanged.
- No GoodWe write path, physical-device access, or controller enablement is part
  of this planning step.
- The TNG confirmation cycle and 900-second minimum interval remain mandatory.
- Unsupported device values must be represented explicitly, never guessed.

## Validation plan

Implementation will require focused unit tests, Ruff, repository hygiene, safe
mock preview, Playwright smoke, and a separately recorded human hardware test.
Automated checks will not be used as hardware evidence.