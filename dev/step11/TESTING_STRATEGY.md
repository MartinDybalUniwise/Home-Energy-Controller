# Testing strategy

HEC uses a local test pyramid. Automated layers never replace the human gate.

| Layer | Scope | Command/evidence |
|---|---|---|
| T0 Static | Ruff and import/syntax checks | `python -m ruff check .` |
| T1 Unit | Pure config, model, forecast, controller behavior | `python -m pytest` |
| T2 Integration | Storage, mocked readers, API, safe controller behavior | Existing pytest suite |
| T3 Runtime smoke | Safe process, HTTP homepage/API, disabled writes and isolated paths | `full_validation.py` |
| T4 Playwright | Browser shell, dashboard, navigation, Settings, languages, responsive viewports | `dev/hec/tests/e2e/` |
| T5 Human | A person uses the preview and records feedback | Explicit `NOT PERFORMED`/approval |

The default pytest command excludes the `e2e` marker so the baseline suite is
independent of browser binaries. The Playwright task and full validation
explicitly select it. Browser installation is local because the app's real
read-only data path can involve a home LAN; CI continues to run only the
existing ruff and pytest checks.

## Failure handling

`full_validation.py` is fail-fast: lint or tests stop before preview; runtime
failure stops before Playwright; the `finally` block attempts to stop the
preview. The process exits non-zero on a failed command. Missing browser
dependencies are a real validation failure, not a PASS.
