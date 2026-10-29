from types import SimpleNamespace

import pytest

from hec.web import mcp_setup


@pytest.mark.parametrize("origin,host,allowed", [
    ("https://energy.example", "energy.example", True),
    ("https://energy.example:444", "energy.example:444", True),
    ("http://localhost:8080", "localhost:8080", True),
    ("http://127.0.0.1:8080", "127.0.0.1:8080", True),
    ("http://192.168.2.115:8080", "192.168.2.115:8080", True),
    ("http://192.168.2.115:80", "192.168.2.115:80", False),
    ("http://192.168.2.116:8080", "192.168.2.116:8080", False),
    ("http://192.168.2.115.evil.example:8080", "192.168.2.115.evil.example:8080", False),
    ("https://evil.example", "energy.example", False),
    ("null", "energy.example", False),
    ("", "energy.example", False),
    ("https://user:pass@energy.example", "energy.example", False),
])
def test_transport_and_csrf(origin, host, allowed):
    assert mcp_setup.trusted_origin(origin, host) is allowed


@pytest.fixture
def intake(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_setup, "PRIVATE", tmp_path)
    monkeypatch.setattr(mcp_setup, "_available", lambda app: True)
    protected = []
    def protect(target):
        assert target.stat().st_size == 0  # ACL is set before any secret bytes.
        protected.append(target)
    monkeypatch.setattr(mcp_setup, "_protect_empty_file", protect)
    return tmp_path, protected


def save(body, **kwargs):
    return mcp_setup.save(None, body, origin=kwargs.get("origin", "https://energy.example"),
                          host="energy.example", content_type=kwargs.get("content_type", "application/json"))


def test_key_is_private_write_once_never_read_back(intake):
    root, protected = intake
    key = "sk-" + "fake_test_only_" * 4
    code, result = save({"api_key": key})
    assert code == 201 and result == {"configured": True, "connection_verified": False}
    assert (root / mcp_setup.KEY_NAME).read_text() == key
    assert len(protected) == 1
    assert mcp_setup.status(None) == (200, {"available": True, "configured": True})
    assert key not in str(result) + str(mcp_setup.status(None))
    assert save({"api_key": "sk-" + "another_fake_key_" * 4})[0] == 409
    assert (root / mcp_setup.KEY_NAME).read_text() == key


@pytest.mark.parametrize("body", [{}, {"api_key": "bad"}, {"api_key": "sk-" + "x" * 25, "path": "other"},
    {"api_key": "sk-" + "x" * 25 + "\n"}, {"api_key": 123}])
def test_invalid_body_never_creates_file(intake, body):
    assert save(body)[0] == 422
    assert not (intake[0] / mcp_setup.KEY_NAME).exists()


def test_acl_failure_does_not_store_credential(intake, monkeypatch):
    def fail(target):
        raise OSError("fake failure")
    monkeypatch.setattr(mcp_setup, "_protect_empty_file", fail)
    assert save({"api_key": "sk-" + "fake_test_" * 4}) == (503, {"error": "private_key_storage_unavailable"})
    assert not (intake[0] / mcp_setup.KEY_NAME).exists()


def test_bad_origin_and_content_type_are_blocked(intake):
    body = {"api_key": "sk-" + "fake_test_" * 4}
    assert save(body, origin="https://evil.example")[0] == 403
    assert save(body, content_type="text/plain")[0] == 403
    assert not (intake[0] / mcp_setup.KEY_NAME).exists()


def test_preview_is_disabled_by_default(tmp_path):
    app = SimpleNamespace(config=SimpleNamespace(root=tmp_path))
    assert mcp_setup.status(app) == (200, {"available": False, "configured": False})


def test_nonproduction_post_never_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_setup, "PRIVATE", tmp_path)
    monkeypatch.setattr(mcp_setup, "_available", lambda app: False)
    assert save({"api_key": "sk-" + "fake_test_" * 4})[0] == 503
    assert not list(tmp_path.iterdir())
