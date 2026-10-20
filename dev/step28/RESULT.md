# Step28 result

Implementation and independent review PASS; owner Human Gate and production deployment PENDING. Candidate 0.1.2 has no release timestamp. Production remains the deployed 0.1.1 at 0b36d3e; this step has made no production writes.

## E-028-001 - Historical measurement quality

Historical `query` and `last` normalize only the four TNG temperature fields. Values below -273.15 C, non-finite values and non-numeric inputs become unknown before downsampling. Valid negatives, zero and null remain valid/unknown as appropriate; no vendor flag decoding or replacement temperatures are invented. JSONL source bytes, current snapshots, `latest`, reader/writer/configuration/control code are unchanged. `/api/history` and `/api/logs` expose the normalized historical view; original evidence remains in JSONL files.

22 unit cases PASS, including flat/nested values, raw/current byte preservation, the actual -3255.1/-3254.7 defect, NaN/Inf, real negative/zero values, mixed hourly mean, entirely missing buckets and temperature columns, and unaffected other sources.

## E-028-002 - Mobile chart, touch and table

TNG history uses dimensions matching the available width and a 260px mobile plot, retaining 11px axis text. Other chart renderers keep their dimensions. Multi-day labels show dates; tooltips show date and time, with touch mapping matching the actual viewBox. Null/absent measurements appear as gaps and table dashes rather than zero. A real zero still displays 0.00.

Six real Chromium regressions PASS across 390x844 and 1280x800 and 24h/7d/30d. Browser test fixture explicitly selects Europe/Prague, independently of CI host timezone.

Read-only replay of actual production history: 38,757 measurements -> 649 hourly points; valid room range 19.3-22.892 C; no page errors. The affected 2026-10-02 raw file SHA256 remained `fda7a36108a136c9d4fae900aa9f601107e16da36c9cf6cc21b893bb7cc5caed`. Both mobile and desktop screenshots were visually inspected; the independent reviewer also inspected mobile.

Local artifacts: `C:/TepelneCerpadlo/step28-evidence/tng-30d-mobile.png`, `tng-30d-desktop.png`, `replay.json`.

## E-028-003 - Validation and review

- Local full validation: 377 unit PASS, 47 real browser E2E PASS, Ruff PASS, 17 step packages PASS, repo hygiene PASS, safe runtime smoke PASS. No E2E skips.
- Exact code/test head: `e784f6ba94acf2f7ee9a20d38874d81470652e70`; product code is identical to reviewed `c9998ffdd1a4637d5b18b8e128a80bc4ea18ebca`. The final six-line test-only change sets its timezone precondition.
- [Exact-head CI](https://github.com/MartinDybalUniwise/Home-Energy-Controller/actions/runs/39470342540): Python 3.11, Python 3.12 and full SDD validation all PASS. Duplicate push workflow 39470336399 alsoPASS.
- Local validation metadata reports a dirty tree because E2E settings forms persist default expansion in the mock config. That generated mock-only diff was inspected and restored after testing. It is not part of the PR.
- Independent `release_review`: no BLOCKER or IMPORTANT; 22 unit cases independently PASS; product scope, normalization, raw/current preservation, chart/mobile/touch and test timezone fixture reviewed. Gate B approved for the exact code/test head above.
- Source logs and metadata: `C:/TepelneCerpadlo/step28-evidence/validation.log` and `validation.json`.

[Draft PR #42](https://github.com/MartinDybalUniwise/Home-Energy-Controller/pull/42) targets the actual production integration branch. Its base includes only the already-completed Step26 documentation after 0.1.1; unrelated main divergence is excluded. Remaining step: owner Human Gate before merge/deployment/DONE. Release time must describe a real successful deployment, never preparation time.
