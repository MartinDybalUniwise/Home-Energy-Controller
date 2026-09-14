# Step 21 Request - Reliable SDG history import

## Summary

The SDG reader reports successful polling, but the application can still show
no history because the importer may discover the wrong directory layout, fail
to recognize SDG timestamps such as `pm_time`, or checkpoint a file after
skipping all of its records. The operator then sees an apparently healthy
reader with no usable SDG data.

The fix is needed now because the production Promotic share contains real SDG
DBF files under `Apps/SDGeco/Data`, while the current runtime evidence showed
successful polls with zero usable imported records.

## Scope

- In scope: SDG DBF path discovery, timestamp normalization, checkpoint and
	retry semantics, source naming, import diagnostics, history visibility, and
	regression tests.
- Out of scope: GoodWe/TNG writes, controller rules, production configuration
	rollout, schema redesign, and changes to frozen root prototypes.

## Safety constraints

- `controller.enabled=false`
- `tng.write_enabled=false`
- No physical-device writes
- No changes to frozen root prototypes
- Production/UNC SDG paths are read-only validation targets; no file is created,
  changed, deleted, renamed, or moved there.

## Acceptance signal

Success is demonstrated when a fixture using the real SDGeco directory layout
and `pm_time` imports records into `sdg_history`, remains visible through the
History API/UI, and a file with zero valid records is retried rather than
permanently checkpointed as complete. Production validation may confirm counts
and timestamps read-only, but is not required as a write or deployment step.
