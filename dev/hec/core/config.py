"""Načtení, validace a bezpečný zápis konfigurace."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from . import schema as schema_mod
from . import secrets as secrets_mod
from .timeutil import now_local

# Kořen instalace = adresář, ve kterém leží data/, logs/, history/ a connect.json.
# Odvozuje se od umístění balíku, ne od aktuálního pracovního adresáře, aby
# systém fungoval stejně při spuštění ze služby i z příkazové řádky.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent      # dev/hec
PROJECT_ROOT = PACKAGE_ROOT.parent.parent                  # kořen repozitáře
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "config" / "config.json"
EXAMPLE_CONFIG_PATH = PACKAGE_ROOT / "config" / "config.example.json"
MAX_BACKUPS = 10


class Config:
    """Konfigurace s přístupem přes tečkovou cestu a s odvozenými cestami."""

    def __init__(self, data: dict, path: Path | None = None, root: Path | None = None,
                 errors: list[str] | None = None):
        self.data = data
        self.path = Path(path) if path else DEFAULT_CONFIG_PATH
        self.root = Path(root) if root else PROJECT_ROOT
        self.errors = errors or []

    # --- čtení -------------------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, name: str) -> dict:
        value = self.get(name, {})
        return value if isinstance(value, dict) else {}

    def __getitem__(self, dotted: str) -> Any:
        return self.get(dotted)

    # --- cesty -------------------------------------------------------------
    def path_for(self, key: str) -> Path:
        """Cesta ze sekce storage. Relativní cesta se váže ke kořeni instalace."""
        raw = str(self.get(f"storage.{key}", "") or "")
        if not raw:
            return Path()
        if os.name == "nt" and raw.startswith("/"):
            return PurePosixPath(raw)
        path = Path(raw).expanduser()
        return path if path.is_absolute() or raw.startswith("\\\\") else (self.root / path)

    @property
    def data_dir(self) -> Path:
        return self.path_for("data_path")

    @property
    def logs_dir(self) -> Path:
        return self.path_for("logs_path")

    @property
    def history_dir(self) -> Path:
        return self.path_for("history_path")

    @property
    def archive_dir(self) -> Path | None:
        path = self.path_for("archive_path")
        return path if str(path) not in ("", ".") else None

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.logs_dir, self.history_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # --- zápis -------------------------------------------------------------
    def to_public_dict(self) -> dict:
        """Konfigurace pro UI a diagnostiku – bez tajemství."""
        return secrets_mod.redact(self.data)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: neplatný JSON ({exc})") from exc


def load(path: str | Path | None = None, *, root: Path | None = None,
         env_file: str | Path | None = None) -> Config:
    """Načte konfiguraci: .env → soubor → dosazení ${VAR} → validace → doplnění výchozích."""
    root = Path(root) if root else PROJECT_ROOT
    secrets_mod.load_env(env_file or (root / ".env"))
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = _read_json(path)
    expanded = secrets_mod.expand_tree(raw)
    data, errors = schema_mod.validate(expanded)
    return Config(data, path=path, root=root, errors=errors)


def save(config: Config, new_data: dict, *, keep_backups: int = MAX_BACKUPS) -> list[str]:
    """Ověří, zazálohuje předchozí verzi a atomicky zapíše. Vrací seznam chyb.

    Při chybě se nezapisuje nic – konfigurace nesmí skončit v polovičním stavu.
    """
    validated, errors = schema_mod.validate(new_data)
    if errors:
        return errors

    path = config.path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = now_local().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.stem}.backup-{stamp}{path.suffix}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        backups = sorted(path.parent.glob(f"{path.stem}.backup-*{path.suffix}"))
        for old in backups[:-keep_backups]:
            old.unlink(missing_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    config.data = validated
    return []


def write_example(path: Path | None = None) -> Path:
    """Vygeneruje config.example.json z výchozích hodnot schématu."""
    path = Path(path) if path else EXAMPLE_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema_mod.defaults(), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path
