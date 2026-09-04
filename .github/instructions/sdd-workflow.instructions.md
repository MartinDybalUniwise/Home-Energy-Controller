---
applyTo: "dev/sdd/**/*.py,dev/sdd/**/*.json,dev/step*/**/*.md,.vscode/**/*.json"
---

Use `dev/sdd/` as the canonical SDD tooling location. Validate the relevant
step with `validate_step.py --phase ready` or `--phase done`; do not represent
open gates, unchecked acceptance criteria, missing evidence, or blockers as
complete. Keep runtime output, browser artifacts, credentials, and production
data out of Git.