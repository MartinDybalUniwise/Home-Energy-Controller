"""Testy provozních nástrojů: první spuštění a diagnostický export."""

from __future__ import annotations

import json
import zipfile

from hec.core import config as config_mod
from hec.core import schema
from hec.storage.jsonl import JsonlStorage
from hec.tools.diagnostics import collect, export
from hec.tools.init_install import initialise


class MiniApp:
    def __init__(self, tmp_path):
        data = schema.defaults()
        data["web"]["password"] = "tajne-heslo-do-uzivatele"
        self.config = config_mod.Config(data, path=tmp_path / "config.json", root=tmp_path)
        self.config.ensure_dirs()
        self.storage = JsonlStorage(self.config.data_dir, self.config.history_dir)

    def status(self):
        return {"readers": {}, "stale_sources": []}


def test_initialise_creates_config_and_env(tmp_path):
    (tmp_path / ".env.example").write_text("HEC_TNG_PASSWORD=\n", encoding="utf-8")

    result = initialise(root=tmp_path, config_path=tmp_path / "config.json")

    assert (tmp_path / "config.json").exists()
    assert (tmp_path / ".env").exists()
    assert len(result["created"]) == 2
    for directory in ("data", "logs", "history"):
        assert (tmp_path / directory).is_dir()


def test_initialise_never_overwrites_existing_files(tmp_path):
    (tmp_path / "config.json").write_text('{"web": {"port": 9999}}', encoding="utf-8")
    (tmp_path / ".env.example").write_text("X=1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("HEC_TNG_PASSWORD=puvodni\n", encoding="utf-8")

    initialise(root=tmp_path, config_path=tmp_path / "config.json")

    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["web"]["port"] == 9999
    assert "puvodni" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_diagnostics_summary_hides_secrets(tmp_path):
    app = MiniApp(tmp_path)
    summary = json.dumps(collect(app), ensure_ascii=False)

    assert "tajne-heslo-do-uzivatele" not in summary
    assert "version" in summary and "status" in summary


def test_diagnostics_zip_scrubs_logs_too(tmp_path):
    app = MiniApp(tmp_path)
    (app.config.logs_dir / "hec.log").write_text(
        "login with tajne-heslo-do-uzivatele\nnormální řádek\n", encoding="utf-8")
    (app.config.root / "connect.json").write_text(
        json.dumps({"tng": {"password": "heslo-z-connect-json"}}), encoding="utf-8")
    (app.config.logs_dir / "errors.log").write_text("chyba: heslo-z-connect-json\n", encoding="utf-8")

    archive_path = export(app)

    with zipfile.ZipFile(archive_path) as archive:
        content = "".join(archive.read(name).decode("utf-8") for name in archive.namelist())
    assert "tajne-heslo-do-uzivatele" not in content
    assert "heslo-z-connect-json" not in content
    assert "normální řádek" in content and "***" in content


def test_diagnostics_can_be_written_anywhere(tmp_path):
    app = MiniApp(tmp_path)
    target = tmp_path / "export" / "diag.zip"

    assert export(app, target) == target
    assert zipfile.is_zipfile(target)
