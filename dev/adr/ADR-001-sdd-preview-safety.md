# ADR-001: SDD preview safety modes

## Status

Accepted

## Context

HEC development needs a deterministic preview for CI and may also need a local
LAN preview to exercise read-only integration paths. Neither workflow may
enable a physical-device write.

## Decision

CI uses the `dev/sdd/config/preview.mock.json` profile. It binds only to
loopback, uses isolated ignored runtime storage, disables all readers, keeps
`controller.enabled=false`, and keeps `tng.write_enabled=false`.

LAN read-only validation remains an explicit local-only follow-up. It must use
a separately reviewed profile and preserve the same controller and TNG write
invariants before it can be enabled.

## Consequences

The mock mode is stable and network-independent for CI. A LAN profile cannot
be casually introduced into CI or used to bypass the write safeguards.