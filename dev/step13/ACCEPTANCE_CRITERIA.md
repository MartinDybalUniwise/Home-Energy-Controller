# Step 13 acceptance criteria

- [x] AC-013-001: `dev/sdd/schema/step.schema.json` exists and `STEP.json` for Step13 validates against the canonical schema.
- [x] AC-013-002: `validate_step.py --phase ready` requires Gate A, complete planning artifacts, IDs, and requirement-to-AC-to-Sxx mappings.
- [x] AC-013-003: `validate_step.py --phase done` rejects open AC/Sxx/gates, missing evidence, incomplete traceability, and blockers.
- [x] AC-013-004: Historical Step12 evidence fails the done phase for the expected incomplete-state reasons.
- [x] AC-013-005: `new_step.py` generates the canonical manifest, selects the next number, preserves existing steps, inserts the README row correctly, and fails safely on an existing target.
- [x] AC-013-006: Active VS Code, Copilot, prompt, and validation references use `dev/sdd/`; Step11 remains historical only.
- [x] AC-013-007: Path-specific safety instructions are discoverable under `.github/instructions/**/*.instructions.md` and retain controller/TNG safety rules.
- [x] AC-013-008: Planner, Developer, and Reviewer role metadata and handoffs preserve human approval and limit reviewer write scope.
- [x] AC-013-009: Canonical full validation runs mock Playwright, cleans up runtime artifacts, and records actual results in `dev/sdd/.runtime/validation.json`.
- [x] AC-013-010: `render_pr.py` generates `dev/sdd/.runtime/pr_body.md` solely from manifest, requirements, traceability, result, and validation evidence.
- [ ] AC-013-011: CI passes Python 3.11, Python 3.12, repository hygiene, and `sdd-validation`; `main` requires the corresponding checks and pull requests.
- [ ] AC-013-012: Credential rotation and history-remediation decision are explicitly evidenced without secret values; unresolved owner actions block DONE.
- [ ] AC-013-013: Step13 receives human Gate B and Gate C approval and passes `validate_step.py --phase done` as its own dogfood evidence.
- [ ] AC-013-014: Safety invariants remain true: controller disabled, TNG writes disabled, no physical-device writes, and no new tracked runtime/secrets.
