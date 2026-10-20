"""Read-only HEC PROD evidence and bounded operational answers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..core.secrets import redact
from ..core.timeutil import now_local, parse_iso, to_iso

_JSON_FILES = (
    "config.json",
    "config/config.json",
    "config/config.prod.json",
    "data/runtime_state.json",
)
_CURRENT_PREFIX = "data/current_"
_LOG_FILES = (
    "logs/hec.log",
    "logs/errors.log",
    "logs/errors.txt",
    "logs/actions.txt",
)
_TIMESTAMP_KEYS = ("timestamp", "collected_at", "updated_at", "ts", "time")
_QUESTION_TERMS = {
    "status": ("status", "stav", "current", "aktuální", "aktualni"),
    "config": ("config", "konfig", "nastavení", "nastaveni"),
    "errors": ("error", "chyby", "chyba", "log", "incident"),
    "history": ("history", "histor", "včera", "vcera", "recent", "poslední", "posledni"),
    "safe_mode": ("safe mode", "bezpečný režim", "bezpecny rezim", "safe"),
    "write_gates": ("write", "zápis", "zapis", "tng", "goodwe writer"),
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    return parse_iso(value)


def _find_timestamp(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in _TIMESTAMP_KEYS:
            if key in value and isinstance(value[key], str):
                return value[key]
        for child in value.values():
            found = _find_timestamp(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_timestamp(child)
            if found:
                return found
    return None


class ProdEvidenceReader:
    """Reads a bounded, immutable view of one HEC installation."""

    def __init__(self, root: str | Path, *, now: datetime | None = None,
                 stale_after: timedelta = timedelta(minutes=30)):
        self.root = Path(root).expanduser().resolve()
        self.now = now or now_local()
        self.stale_after = stale_after

    def _path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"Artifact is outside PROD root: {relative}") from exc
        return candidate

    def _read_json(self, relative: str) -> tuple[Any | None, dict[str, Any]]:
        path = self._path(relative)
        source = {"path": relative, "exists": path.exists(), "readable": False}
        if not path.exists():
            return None, source
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            source["error"] = type(exc).__name__
            return None, source
        source["readable"] = True
        return value, source

    def _first_json(self, relatives: tuple[str, ...]) -> tuple[Any | None, dict[str, Any]]:
        last_source: dict[str, Any] = {"path": relatives[0], "exists": False, "readable": False}
        for relative in relatives:
            value, source = self._read_json(relative)
            if source["exists"]:
                return value, source
            last_source = source
        return None, last_source

    def _config(self) -> tuple[dict[str, Any], dict[str, Any]]:
        value, source = self._first_json(("config.json", "config/config.json", "config/config.prod.json"))
        return (value if isinstance(value, dict) else {}), source

    def _current_sources(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        data_dir = self._path("data")
        if not data_dir.is_dir():
            return {}, [{"path": "data", "exists": False, "readable": False}]
        sources: dict[str, Any] = {}
        evidence: list[dict[str, Any]] = []
        for path in sorted(data_dir.glob("current_*.json")):
            relative = path.relative_to(self.root).as_posix()
            value, source = self._read_json(relative)
            source["source"] = path.name.removeprefix("current_").removesuffix(".json")
            timestamp = _find_timestamp(value)
            source["timestamp"] = timestamp
            parsed = _timestamp(timestamp)
            source["stale"] = bool(parsed and self.now - parsed > self.stale_after)
            if value is None:
                source["error"] = source.get("error", "invalid_payload")
            else:
                sources[source["source"]] = value
            evidence.append(source)
        return sources, evidence

    def _logs(self, limit: int = 20) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        entries: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        for relative in _LOG_FILES:
            path = self._path(relative)
            if not path.exists():
                continue
            source = {"path": relative, "exists": True, "readable": False}
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as exc:
                source["error"] = type(exc).__name__
            else:
                source["readable"] = True
                for line in lines[-limit:]:
                    if line.strip():
                        entries.append({"source": relative, "line": line})
            evidence.append(source)
        return entries[-limit:], evidence

    def snapshot(self) -> dict[str, Any]:
        config, config_source = self._config()
        runtime, runtime_source = self._read_json("data/runtime_state.json")
        sources, source_evidence = self._current_sources()
        logs, log_evidence = self._logs()
        stale = [item["source"] for item in source_evidence if item.get("stale")]
        artifacts = [config_source, runtime_source, *source_evidence, *log_evidence]
        missing = [item["path"] for item in artifacts if not item.get("exists")]
        unreadable = [item["path"] for item in artifacts
                      if item.get("exists") and not item.get("readable")]
        errors = [entry for entry in logs if re.search(r"\b(error|exception|failed|timeout)\b", entry["line"], re.I)]
        return {
            "observed_at": to_iso(self.now),
            "root": str(self.root),
            "config": redact(_jsonable(config)),
            "runtime": _jsonable(runtime) if isinstance(runtime, dict) else None,
            "sources": _jsonable(sources),
            "source_evidence": source_evidence,
            "recent_errors": errors,
            "log_evidence": log_evidence,
            "config_evidence": config_source,
            "runtime_evidence": runtime_source,
            "stale_sources": stale,
            "unreadable_artifacts": unreadable,
            "missing_artifacts": missing,
        }


class OperationsAgent:
    """Generates read-only reports and answers a bounded question set."""

    def __init__(self, reader: ProdEvidenceReader):
        self.reader = reader

    @staticmethod
    def _gates(config: dict[str, Any]) -> dict[str, bool]:
        return {
            "controller_enabled": bool(config.get("controller", {}).get("enabled", False)),
            "tng_write_enabled": bool(config.get("tng", {}).get("write_enabled", False)),
            "goodwe_writer_enabled": bool(config.get("goodwe", {}).get("writer_enabled", False)),
        }

    def report(self) -> dict[str, Any]:
        evidence = self.reader.snapshot()
        gates = self._gates(evidence["config"])
        attention: list[str] = []
        if evidence["unreadable_artifacts"] or evidence["missing_artifacts"]:
            attention.append("Some PROD artifacts are missing, unreadable, or malformed.")
        if evidence["stale_sources"]:
            attention.append("Some source data is stale.")
        if evidence["recent_errors"]:
            attention.append("Recent error-level log entries were found.")
        if not attention:
            attention.append("No attention item was detected in the inspected evidence.")
        overall = "DEGRADED" if evidence["missing_artifacts"] or evidence["unreadable_artifacts"] \
            or evidence["stale_sources"] or evidence["recent_errors"] else "OK"
        return {
            "kind": "status_report",
            "observed_at": evidence["observed_at"],
            "overall_status": overall,
            "attention": attention,
            "gates": gates,
            "stale_sources": evidence["stale_sources"],
            "source_count": len(evidence["sources"]),
            "recent_error_count": len(evidence["recent_errors"]),
            "evidence": evidence,
        }

    def greeting(self) -> dict[str, Any]:
        report = self.report()
        return {
            "kind": "greeting",
            "agent": "HEC PROD Operations Agent",
            "observed_at": report["observed_at"],
            "message": f"HEC PROD status: {report['overall_status']}. {report['attention'][0]}",
            "report": report,
        }

    def answer(self, question: str) -> dict[str, Any]:
        report = self.report()
        normalized = question.casefold()
        matched = [topic for topic, terms in _QUESTION_TERMS.items()
                   if any(term.casefold() in normalized for term in terms)]
        if not matched:
            return {
                "kind": "answer",
                "question": question,
                "status": "unsupported",
                "answer": "Question is outside the Step 31 evidence scope.",
                "supported_topics": sorted(_QUESTION_TERMS),
                "observed_at": report["observed_at"],
            }
        if "config" in matched:
            answer = {"configuration": report["evidence"]["config"]}
        elif "errors" in matched or "history" in matched:
            answer = {
                "recent_errors": report["evidence"]["recent_errors"],
                "log_evidence": report["evidence"]["log_evidence"],
            }
        elif "safe_mode" in matched:
            answer = {
                "safe_mode": report["evidence"]["runtime"].get("safe_mode")
                if isinstance(report["evidence"]["runtime"], dict) else None,
                "stale_sources": report["stale_sources"],
            }
        elif "write_gates" in matched:
            answer = {"gates": report["gates"]}
        else:
            answer = {
                "overall_status": report["overall_status"],
                "attention": report["attention"],
                "stale_sources": report["stale_sources"],
            }
        return {
            "kind": "answer",
            "question": question,
            "status": "answered",
            "answer": answer,
            "observed_at": report["observed_at"],
            "sources": report["evidence"]["source_evidence"] + report["evidence"]["log_evidence"],
        }
