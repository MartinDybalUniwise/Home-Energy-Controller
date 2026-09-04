# PR workflow and evidence

Before asking for a PR, the developer/reviewer must:

1. compare the diff with the approved requirement and `Sxx` plan;
2. run the relevant ruff, pytest, runtime smoke, and Playwright commands;
3. review generated files for credentials, production data, logs, and browser
   artifacts;
4. record exact results, deviations, safety flags, human-test status, and
   limitations in `RESULT.md` and the PR template;
5. wait for explicit Gate C (`CREATE PR` or `FINISH PR`).

The PR template distinguishes `PASS`, `FAIL`, and `NOT RUN`; it must never
claim human testing from automation. CI remains the existing ruff/pytest
workflow. Playwright is deliberately local-only because this bootstrap must
support a home LAN and must not receive secrets.

## Feedback loop

Classify feedback before editing:

- **SMALL:** implement the minimum, rerun relevant tests (and Playwright for
  UI), update evidence.
- **LARGE:** stop, update requirement/plan/acceptance criteria with new `Sxx`,
  obtain approval, then implement.

Do not push to `main`, create a PR, or change frozen root prototypes as part of
the local workflow.
