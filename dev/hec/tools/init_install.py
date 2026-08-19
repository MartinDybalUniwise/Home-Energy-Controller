"""První spuštění: vytvoření konfigurace a souboru s tajemstvími."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..core import config as config_mod
from ..core import schema


def initialise(root: Path | None = None, config_path: Path | None = None) -> dict:
    """Vytvoří chybějící `config.json` a `.env`. Existující soubory nepřepisuje."""
    root = Path(root) if root else config_mod.PROJECT_ROOT
    config_path = Path(config_path) if config_path else config_mod.DEFAULT_CONFIG_PATH
    created: list[str] = []

    config_mod.write_example()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(schema.defaults(), ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        created.append(str(config_path))

    env = root / ".env"
    example = root / ".env.example"
    if not env.exists() and example.exists():
        shutil.copyfile(example, env)
        created.append(str(env))

    for directory in ("data", "logs", "history"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    return {"created": created, "config": str(config_path), "root": str(root)}
