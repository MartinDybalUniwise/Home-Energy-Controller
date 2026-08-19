"""Testy jazykových mutací. Chybějící klíč v jednom jazyce je chyba, ne detail."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from hec.core import i18n

FRONTEND = Path(i18n.LOCALES_DIR).parent / "web" / "frontend"
KEY_IN_CODE = re.compile(r"""\bt\(\s*['"]([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)['"]""", re.I)
DATA_I18N = re.compile(r'data-i18n(?:-label)?="([^"]+)"')


def test_reference_language_exists():
    assert i18n.REFERENCE in i18n.available()
    assert "en" in i18n.available()


@pytest.mark.parametrize("lang", [lang for lang in i18n.available() if lang != i18n.REFERENCE])
def test_every_language_has_the_same_keys_as_the_reference(lang):
    missing, extra = i18n.missing_keys(i18n.load(i18n.REFERENCE), i18n.load(lang))
    assert not missing, f"{lang}: chybí klíče {sorted(missing)}"
    assert not extra, f"{lang}: klíče navíc {sorted(extra)}"


@pytest.mark.parametrize("lang", i18n.available())
def test_no_empty_translations(lang):
    empty = [key for key, value in i18n.flatten(i18n.load(lang)).items() if not str(value).strip()]
    assert not empty


@pytest.mark.parametrize("lang", [lang for lang in i18n.available() if lang != i18n.REFERENCE])
def test_placeholders_match_between_languages(lang):
    """Přeložená věta musí mít stejné parametry – jinak by v UI zůstalo {price}."""
    reference = i18n.flatten(i18n.load(i18n.REFERENCE))
    other = i18n.flatten(i18n.load(lang))
    for key, text in reference.items():
        assert set(i18n.PARAM.findall(text)) == set(i18n.PARAM.findall(other[key])), key


def test_translate_falls_back_without_crashing():
    assert i18n.translate("nav.overview", "cs") == "Přehled"
    assert i18n.translate("nav.overview", "xx") == "Overview"        # fallback na en
    assert i18n.translate("neexistuje.klic", "cs") == "neexistuje.klic"


def test_parameters_are_substituted():
    text = i18n.translate("status.stale_source", "cs", {"source": "goodwe", "age": "90 s"})
    assert "goodwe" in text and "90 s" in text


def test_frontend_uses_only_existing_keys():
    """Každý klíč použitý v UI musí být v katalogu – jinak uživatel uvidí klíč."""
    catalog = i18n.flatten(i18n.load(i18n.REFERENCE))
    used: set[str] = set()
    for path in list(FRONTEND.rglob("*.js")) + list(FRONTEND.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        used |= set(KEY_IN_CODE.findall(text)) | set(DATA_I18N.findall(text))

    unknown = {key for key in used if key not in catalog and not key.startswith("prediction.confidence_")}
    assert not unknown, f"klíče chybějící v katalogu: {sorted(unknown)}"


def test_catalogs_are_valid_json_without_trailing_content():
    for lang in i18n.available():
        raw = (i18n.LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8")
        assert isinstance(json.loads(raw), dict)
