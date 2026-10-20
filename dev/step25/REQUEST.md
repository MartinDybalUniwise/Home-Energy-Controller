# Request

## Summary

Review and plan the separation of device data collection, telemetry storage,
analytics, decision-making, device writers, and the HEC dashboard. The current
implementation runs enabled readers as daemon threads inside one HEC process and
lets them write directly to the shared JSONL store. This makes collection
lifecycle dependent on HEC startup, scheduler health, and process survival.

The target is a telemetry-centered architecture: readers measure, a durable
store retains the source of truth, analytics observe, controllers decide and
writers perform explicitly gated writes, while HEC consumes the store.

## Scope

- In scope:
	- repository-verified current-state inventory and coupling analysis;
	- contracts for telemetry, technical logs, timestamps, quality and retention;
	- a staged migration plan from the current single process;
	- service/process, supervision, communication, and dashboard boundaries;
	- future WeatherStation, multi-device Shelly, Energy Reader, AI Observer,
		AI Analyst, and Financial Controller interfaces;
	- preserving current behavior during each migration stage.
- Out of scope:
	- implementing or enabling the new architecture in this step;
	- changing device protocols, production data, configuration, or runtime;
	- physical writes to TNG, GoodWe, or any other device;
	- replacing JSONL with a database before a separate approved step;
	- automatic AI-driven development, controller writes, or enterprise trust
		controls outside the defined private single-owner threat model.

## Safety constraints

- `controller.enabled=false`
- `tng.write_enabled=false`
- `goodwe.writer_enabled=false` and no hardware authorization changes
- No physical-device writes or production service changes
- No changes to frozen root prototypes
- TNG `LastSettingsNotConfirmed` cycle and 900-second minimum interval remain
	mandatory for every future writer migration
- Read-only analysis must not expose secrets or modify production state

## Acceptance signal

Step25 is ready when the repository contains an approval-quality planning
package that records the implementation-backed current architecture, target
boundaries, risks, traceability, and independently testable migration steps.
Gate A approval is required before any application-code or runtime change.
