#!/usr/bin/env python3
"""Spouštěč Home Energy Controller nezávislý na aktuálním adresáři.

    python3 dev/run.py --once      # jedno kolo čtení
    python3 dev/run.py             # trvalý běh se sběrem dat a webem
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hec.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
