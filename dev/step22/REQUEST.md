# Step 22 Request - Stable SDG runtime scheduling

## Summary

The read-only SDG history reader is enabled and has successfully imported
historical records from 334 DBF files. Runtime evidence shows individual SDG
polls taking approximately 90–98 seconds while the configured reader interval
is 10 seconds. The scheduler currently calculates the next run from the poll
start time, so a slow poll can make the next run immediately due. The latest
runtime check also found no running HEC Python process after the last recorded
successful import.

The result is misleading operational state: SDG history may have been read
successfully, while the runtime is no longer running or repeatedly performs
long network scans. The repair is needed to make the read-only history reader
predictable and diagnosable without changing device-control behavior.

## Scope

- In scope:
	- scheduler timing semantics for slow readers;
	- SDG reader runtime status and lifecycle diagnostics;
	- regression tests for slow-poll scheduling, graceful stop, and SDG status;
	- read-only validation against the external checkout and Promotic share;
	- deployment/runbook evidence needed to distinguish stopped runtime from
		failed reader initialization.
- Out of scope:
	- changing DBF parsing or the SDG data contract from Step 21;
	- enabling controller, TNG, GoodWe writer, or any physical-device write;
	- modifying the external checkout `T:\Home-Energy-Controller`;
	- installing, restarting, reconfiguring, or writing to production services;
	- changing frozen root prototype scripts.

## Safety constraints

- `controller.enabled=false`
- `tng.write_enabled=false`
- `goodwe.writer_enabled=false`
- No physical-device writes
- External paths and production checkouts are read-only inspection targets
- No changes to frozen root prototypes

## Acceptance signal

Focused scheduler tests demonstrate that a poll which takes longer than its
nominal interval does not cause an immediate catch-up loop, and that stopping
the application leaves no new reader activity. Runtime evidence identifies
whether HEC is running, which checkout/configuration it uses, and whether
`sdg_history` has a recent successful import, without any external write.
