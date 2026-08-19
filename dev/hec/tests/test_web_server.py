"""Testy HTTP serveru – směrování, přihlášení, statické soubory."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest
from hec.core import config as config_mod
from hec.core import schema
from hec.storage.jsonl import JsonlStorage
from hec.web.server import build_server


class MiniApp:
    def __init__(self, tmp_path, password=""):
        data = schema.defaults()
        data["web"]["password"] = password
        data["web"]["port"] = 0                      # volný port přidělí systém
        self.config = config_mod.Config(data, path=tmp_path / "c.json", root=tmp_path)
        self.config.ensure_dirs()
        self.storage = JsonlStorage(self.config.data_dir, self.config.history_dir)

    def current(self):
        return {"sources": {"goodwe": {"pv_w": 4210}}, "status": self.status()}

    def status(self):
        return {"readers": {}, "stale_sources": [], "site_name": "Test"}

    def stop(self):
        pass


@pytest.fixture
def server(tmp_path, request):
    password = getattr(request, "param", "")
    httpd = build_server(MiniApp(tmp_path, password), host="127.0.0.1", port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def get(url, cookie=None):
    request = urllib.request.Request(url)
    if cookie:
        request.add_header("Cookie", cookie)
    with urllib.request.urlopen(request, timeout=5) as response:      # noqa: S310
        return response.status, json.loads(response.read().decode("utf-8")), response.headers


def test_api_returns_current_state(server):
    status, payload, _ = get(f"{server}/api/current")
    assert status == 200 and payload["sources"]["goodwe"]["pv_w"] == 4210


def test_unknown_api_route_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as error:
        get(f"{server}/api/nonsense")
    assert error.value.code == 404


def test_frontend_is_served_and_spa_routes_fall_back_to_index(server):
    with urllib.request.urlopen(f"{server}/", timeout=5) as response:  # noqa: S310
        assert b"Home Energy Controller" in response.read()
    with urllib.request.urlopen(f"{server}/history", timeout=5) as response:  # noqa: S310
        assert response.status == 200


def test_path_traversal_is_refused(server):
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(f"{server}/../../../etc/passwd", timeout=5)  # noqa: S310
    assert error.value.code in (403, 404)


def test_translations_are_public(server):
    status, payload, _ = get(f"{server}/api/i18n/en")
    assert status == 200 and payload["catalog"]["nav"]["overview"] == "Overview"


@pytest.mark.parametrize("server", ["tajne"], indirect=True)
def test_password_protects_data_but_not_login(server):
    status, payload, _ = get(f"{server}/api/session")
    assert payload == {"required": True, "authorised": False}

    with pytest.raises(urllib.error.HTTPError) as error:
        get(f"{server}/api/current")
    assert error.value.code == 401

    request = urllib.request.Request(f"{server}/api/login", method="POST",
                                     data=json.dumps({"password": "tajne"}).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:      # noqa: S310
        cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie

    status, payload, _ = get(f"{server}/api/current", cookie=cookie.split(";")[0])
    assert status == 200


@pytest.mark.parametrize("server", ["tajne"], indirect=True)
def test_wrong_password_is_rejected(server):
    request = urllib.request.Request(f"{server}/api/login", method="POST",
                                     data=json.dumps({"password": "spatne"}).encode(),
                                     headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=5)                    # noqa: S310
    assert error.value.code == 401
