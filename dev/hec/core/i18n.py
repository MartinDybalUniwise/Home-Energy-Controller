"""Jazykové mutace.

Zásada: v kódu nikdy nestojí text pro uživatele, jen klíč. Katalogy jsou
JSON soubory v `locales/`. Referenční jazyk je čeština – proti ní se v testu
porovnává úplnost ostatních jazyků.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
REFERENCE = "cs"
FALLBACK = "en"
PARAM = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def available(directory: Path | None = None) -> list[str]:
    directory = directory or LOCALES_DIR
    return sorted(path.stem for path in directory.glob("*.json"))


def load(lang: str, directory: Path | None = None) -> dict:
    directory = directory or LOCALES_DIR
    path = directory / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_all(directory: Path | None = None) -> dict[str, dict]:
    return {lang: load(lang, directory) for lang in available(directory)}


def flatten(catalog: dict, prefix: str = "") -> dict[str, str]:
    """Vnořený katalog na plochý slovník `sekce.klíč`."""
    out: dict[str, str] = {}
    for key, value in catalog.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = value
    return out


def lookup(catalog: dict, key: str):
    node = catalog
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def translate(key: str, lang: str = REFERENCE, params: dict | None = None,
              catalogs: dict[str, dict] | None = None) -> str:
    """Přeloží klíč. Chybí-li překlad, zkusí se záložní jazyk, pak samotný klíč."""
    catalogs = catalogs if catalogs is not None else load_all()
    text = lookup(catalogs.get(lang, {}), key)
    if text is None:
        text = lookup(catalogs.get(FALLBACK, {}), key)
    if text is None:
        return key
    if params:
        text = PARAM.sub(lambda m: str(params.get(m.group(1), m.group(0))), text)
    return text


def missing_keys(reference: dict, other: dict) -> tuple[set[str], set[str]]:
    """Vrací (chybějící v `other`, navíc v `other`) proti referenčnímu katalogu."""
    ref, oth = set(flatten(reference)), set(flatten(other))
    return ref - oth, oth - ref
