---
applyTo: "dev/hec/**/*.py,dev/hec/**/*.js,dev/hec/**/*.json"
---

Preserve the HEC safety contract: keep `controller.enabled=false` and
`tng.write_enabled=false` in local and preview development. Never perform a
physical-device write or bypass the TNG confirmation cycle and 900-second
minimum interval. Preserve i18n keys, atomic writes, ISO timestamps, and
Windows/Linux/Raspberry Pi portability.