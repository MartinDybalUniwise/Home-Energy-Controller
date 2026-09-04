# Local development

## Prepare

Open the repository root in VS Code. Create or activate a Python 3.11+
environment, then install development dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

On Linux/Pi use `python3` and `.venv/bin/python`. The VS Code tasks use the
`python` command from the selected environment.

## Tests and preview

```powershell
python -m ruff check .
python -m pytest
python dev/step11/preview.py start
# open http://127.0.0.1:8181
python dev/step11/preview.py stop
```

The preview uses `config.preview.json` through the existing `Config` loader.
It writes only under `dev/step11/.runtime/`, binds to loopback, disables all
physical readers, keeps the controller and TNG writes disabled, and uses no
production `data/`, `logs/`, or `history/`. It is safe to use without devices.

For a local network read-only check, use a separately reviewed config copy with
all write flags still disabled. Never point the preview at real credentials or
production paths without a human safety review.

## Playwright

With the safe preview running:

```powershell
$env:HEC_RUN_E2E = "1"
$env:HEC_BASE_URL = "http://127.0.0.1:8181"
python -m pytest dev/hec/tests/e2e -o addopts= -m e2e `
  --screenshot only-on-failure --tracing retain-on-failure `
  --output dev/step11/.runtime/playwright
```

The suite checks dashboard shell/navigation, Settings, both language catalogs,
and 1280×800, 1920×1080 wall/full-HD, and 390×844 mobile viewports. Artifacts
are local-only and ignored by Git.

## Debugging and one-command validation

Use `HEC: Debug Dev Preview` in VS Code for breakpoints. It launches
`dev/run.py` with the same safe config. `HEC: Full Validation` runs ruff,
pytest, preview health/safety checks, Playwright, and cleanup in that order.
It returns non-zero on a failed stage and never reports an unrun stage as
passing.
