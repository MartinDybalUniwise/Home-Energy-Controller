# Step 15 requirement

## Title

Production deployment readiness for the HEC production host

## Problem

The repository documents installation and restart flow, but it does not yet define a production deployment workflow for the live host at 192.168.2.115.

## Objective

Define a safe and repeatable deployment workflow that can update the production HEC service, verify it, and roll back if needed while keeping secrets out of git and preserving preview safety.

## Requirements

- **REQ-015-001 – Production inventory:** document the target host
	`192.168.2.115`, URL `http://192.168.2.115:8080`, service `hec.service`,
	installation root `/opt/home-energy-controller`, runtime paths, service
	user, and approved maintenance access model. Unverified host facts remain
	explicit pre-deployment blockers.
- **REQ-015-002 – Controlled update:** define an idempotent update procedure
	that selects an approved revision, records the current revision and service
	state, validates before restart, preserves runtime data and secrets, and
	records non-secret evidence.
- **REQ-015-003 – Recovery:** define a release-preserving rollback procedure
	covering service stop/start, restoration of the previous revision and
	configuration backup, health verification, and escalation on failure.
- **REQ-015-004 – Security and safety:** keep credentials host-local, use
	least-privilege SSH access where possible, prohibit secrets and production
	data in Git, and preserve local preview invariants including
	`controller.enabled=false` and `tng.write_enabled=false`.

## Scope

- document the target host, service, and runtime paths
- define a controlled update flow with explicit validation gates
- define rollback and emergency recovery
- define secret handling and access control
- enforce local preview safety and no physical-device write rules
