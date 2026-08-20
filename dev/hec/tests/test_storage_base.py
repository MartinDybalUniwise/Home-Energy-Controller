"""Testy atomic_write_json – zejména odolnost proti přechodnému WinError 5."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from hec.storage.base import atomic_write_json, read_json


def test_atomic_write_survives_a_transient_permission_error(tmp_path):
    """Antivirus/indexer na Windows umí soubor na pár milisekund zamknout –
    os.replace() na to spadne s PermissionError, ale zápis nesmí selhat."""
    path = tmp_path / "weather.json"
    real_replace = os.replace
    calls = {"count": 0}

    def flaky_replace(src, dst):
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError("[WinError 5] Access is denied")
        return real_replace(src, dst)

    with patch("hec.storage.base.time.sleep"), patch("hec.storage.base.os.replace", flaky_replace):
        atomic_write_json(path, {"temp_c": 17.9})

    assert calls["count"] == 3
    assert read_json(path)["temp_c"] == 17.9


def test_atomic_write_gives_up_after_persistent_permission_error(tmp_path):
    """Skutečně zamčený soubor (ne jen přechodně) musí selhat viditelně, ne
    donekonečna čekat nebo tiše ztratit data."""
    path = tmp_path / "weather.json"

    def always_locked(src, dst):
        raise PermissionError("[WinError 5] Access is denied")

    with patch("hec.storage.base.time.sleep"), patch("hec.storage.base.os.replace", always_locked):
        with pytest.raises(PermissionError):
            atomic_write_json(path, {"temp_c": 17.9})
