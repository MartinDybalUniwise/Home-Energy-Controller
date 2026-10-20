from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from hec.agent.operations import OperationsAgent, ProdEvidenceReader


def _write_fixture(root, *, timestamp: str, include_runtime: bool = True) -> None:
    (root / "data").mkdir()
    (root / "logs").mkdir()
    (root / "config").mkdir()
    (root / "config.json").write_text(json.dumps({
        "controller": {"enabled": False},
        "tng": {"write_enabled": False},
        "goodwe": {"writer_enabled": False, "password": "super-secret"},
    }), encoding="utf-8")
    (root / "data" / "current_goodwe.json").write_text(json.dumps({
        "timestamp": timestamp,
        "values": {"pv_w": 1000},
    }), encoding="utf-8")
    if include_runtime:
        (root / "data" / "runtime_state.json").write_text(json.dumps({
            "safe_mode": False,
        }), encoding="utf-8")
    (root / "logs" / "hec.log").write_text(
        "2026-09-19T10:00:00+02:00 | INFO | hec.test | sample | source=goodwe\n",
        encoding="utf-8",
    )


def _agent(root, now: datetime) -> OperationsAgent:
    return OperationsAgent(ProdEvidenceReader(root, now=now))


def test_report_and_greeting_are_read_only_and_mask_secrets(tmp_path):
    now = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    _write_fixture(tmp_path, timestamp="2026-09-19T11:55:00+00:00")

    result = _agent(tmp_path, now).greeting()
    serialized = json.dumps(result, ensure_ascii=False)

    assert result["kind"] == "greeting"
    assert result["report"]["overall_status"] == "OK"
    assert result["report"]["gates"] == {
        "controller_enabled": False,
        "tng_write_enabled": False,
        "goodwe_writer_enabled": False,
    }
    assert "super-secret" not in serialized
    assert result["report"]["evidence"]["config"]["goodwe"]["password"] != "super-secret"
    assert not (tmp_path / "config.json.tmp").exists()


def test_stale_and_missing_evidence_are_degraded(tmp_path):
    now = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    _write_fixture(tmp_path, timestamp="2026-09-19T10:00:00+00:00", include_runtime=False)
    (tmp_path / "logs" / "errors.log").write_text(
        "2026-09-19T11:59:00+00:00 | ERROR | hec.test | timeout | source=weather\n",
        encoding="utf-8",
    )

    report = _agent(tmp_path, now).report()

    assert report["overall_status"] == "DEGRADED"
    assert report["stale_sources"] == ["goodwe"]
    assert report["recent_error_count"] == 1
    assert report["evidence"]["runtime"] is None


def test_malformed_json_is_explicitly_unreadable(tmp_path):
    now = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    _write_fixture(tmp_path, timestamp="2026-09-19T11:55:00+00:00")
    (tmp_path / "data" / "current_weather.json").write_text("{broken", encoding="utf-8")

    report = _agent(tmp_path, now).report()

    assert "data/current_weather.json" in report["evidence"]["unreadable_artifacts"]
    assert report["overall_status"] == "DEGRADED"


def test_bounded_questions_and_unsupported_question(tmp_path):
    now = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    _write_fixture(tmp_path, timestamp="2026-09-19T11:55:00+00:00")
    agent = _agent(tmp_path, now)

    assert agent.answer("Je povolen zapis do TNG?")["status"] == "answered"
    unsupported = agent.answer("Kolik bude cena za tri dny?")
    assert unsupported["status"] == "unsupported"
    assert "config" in unsupported["supported_topics"]


def test_artifact_path_cannot_escape_root(tmp_path):
    reader = ProdEvidenceReader(tmp_path)

    with pytest.raises(ValueError, match="outside PROD root"):
        reader._path("../secret.json")


def test_missing_source_directory_is_explicit(tmp_path):
    now = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    report = _agent(tmp_path, now).report()

    assert report["evidence"]["source_evidence"] == [{
        "path": "data",
        "exists": False,
        "readable": False,
    }]
    assert report["overall_status"] == "DEGRADED"
    assert any(path.startswith("config") for path in report["evidence"]["missing_artifacts"])
