"""Safety contract for the isolated Step11 preview profile."""

from __future__ import annotations

from pathlib import Path

from hec.core import config as config_mod

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PREVIEW_CONFIG = PROJECT_ROOT / "dev" / "step11" / "config.preview.json"


def test_preview_profile_is_read_only_and_isolated():
    config = config_mod.load(PREVIEW_CONFIG, root=PROJECT_ROOT)

    assert config.get("web.host") == "127.0.0.1"
    assert config.get("web.port") == 8181
    assert config.get("controller.enabled") is False
    assert config.get("tng.write_enabled") is False
    assert config.get("goodwe.enabled") is False
    assert config.data_dir == PROJECT_ROOT / "dev" / "step11" / ".runtime" / "data"
    assert config.logs_dir == PROJECT_ROOT / "dev" / "step11" / ".runtime" / "logs"
    assert config.get("web.password") == ""
