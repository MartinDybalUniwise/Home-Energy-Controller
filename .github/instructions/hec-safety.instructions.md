---
applyTo: "dev/hec/**/*.py,dev/hec/**/*.js,dev/hec/**/*.json"
---

Preserve the HEC safety contract: keep `controller.enabled=false` and
`tng.write_enabled=false` in local and preview development. Never perform a
physical-device write or bypass the TNG confirmation cycle and 900-second
minimum interval. Preserve i18n keys, atomic writes, ISO timestamps, and
Windows/Linux/Raspberry Pi portability.

Physical write safety baseline:

1. physical writes default OFF,
2. an explicit operational enable/write switch exists,
3. writes go through a single central writer boundary,
4. values are validated against reasonable limits,
5. a read-back follows the write where technically available,
6. a communication error must not cause infinite/repeated uncontrolled writes,
7. the system can safely stop automatic control and fall back to manual/default.

HEC's threat model treats the local administrator as trusted; do not add
protections against a deliberate local bypass.