"""Tajemství: načtení z .env a dosazení ${PROMENNA} do konfigurace.

Hesla, klíče ani tokeny nikdy nepatří do konfiguračních souborů v gitu.
Konfigurace obsahuje jen odkaz `${HEC_TNG_PASSWORD}`, hodnota přijde z prostředí.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

# Názvy polí, jejichž hodnota se nikdy nesmí objevit v logu ani v exportu.
SECRET_KEYS = frozenset({
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "thermostat_key", "basic_key", "heatpump_hash", "timezone_cookie_name",
})


def load_env(path: str | Path = ".env", *, override: bool = False) -> dict[str, str]:
    """Načte .env do os.environ. Existující proměnné prostředí mají přednost."""
    path = Path(path)
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


def expand(value: str, env: dict[str, str] | None = None) -> str:
    """Dosadí ${VAR} nebo ${VAR:-výchozí}. Neznámá proměnná zůstane prázdná."""
    source = env if env is not None else os.environ

    def repl(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return source.get(name) or (default if default is not None else "")

    return PLACEHOLDER.sub(repl, value)


def expand_tree(node, env: dict[str, str] | None = None):
    """Rekurzivně dosadí placeholdery v celé konfiguraci."""
    if isinstance(node, str):
        return expand(node, env)
    if isinstance(node, dict):
        return {k: expand_tree(v, env) for k, v in node.items()}
    if isinstance(node, list):
        return [expand_tree(v, env) for v in node]
    return node


def is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SECRET_KEYS)


def mask(value) -> str:
    """Zamaskuje hodnotu pro výpis: ponechá délku, ne obsah."""
    text = str(value)
    if not text:
        return ""
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]} ({len(text)})"


def redact(node):
    """Kopie struktury s zamaskovanými tajemstvími – pro logy a diagnostický export."""
    if isinstance(node, dict):
        return {k: (mask(v) if is_secret_key(k) and isinstance(v, (str, int)) else redact(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    return node


def collect_secret_values(node) -> set[str]:
    """Posbírá konkrétní tajné hodnoty, aby je logger mohl z textu odstranit."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if is_secret_key(key) and isinstance(value, str) and len(value) >= 6:
                found.add(value)
            else:
                found |= collect_secret_values(value)
    elif isinstance(node, list):
        for value in node:
            found |= collect_secret_values(value)
    return found
