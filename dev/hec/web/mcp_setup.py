"""Narrow one-time credential intake for the independent MCP gateway.

No HEC configuration, reader, controller or schedule is changed. Never read back
the key. Only the existing Windows production installation may use this writer.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

PRODUCTION = Path("C:/TepelneCerpadlo/Home-Energy-Controller")
PRIVATE = Path("C:/TepelneCerpadlo/hec-ai-gateway/private")
KEY_NAME = "openai-runtime-key.txt"


def _available(app) -> bool:
    return os.name == "nt" and app.config.root.resolve() == PRODUCTION.resolve() and PRIVATE.is_dir()


def status(app):
    available = _available(app)
    configured = available and (PRIVATE / KEY_NAME).is_file() and (PRIVATE / KEY_NAME).stat().st_size > 0
    return 200, {"available": available, "configured": bool(configured)}


def trusted_origin(origin: str, host: str) -> bool:
    try:
        parsed = urlsplit(origin)
        if parsed.netloc.lower() != host.lower() or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return False
        if parsed.username or parsed.password:
            return False
        return parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"})
    except ValueError:
        return False


def _protect_empty_file(target: Path) -> None:
    owner = (PRIVATE / "owner-sid.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"S-1-5-21-(?:\d+-){2}\d+-\d+", owner):
        raise OSError("invalid owner identity")
    result = subprocess.run(
        ["icacls.exe", str(target), "/inheritance:r", "/grant:r",
         f"*{owner}:(F)", "*S-1-5-18:(F)", "*S-1-5-32-544:(F)"],
        check=False, timeout=8, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise OSError("private ACL unavailable")


def save(app, body, *, origin: str, host: str, content_type: str):
    if not _available(app):
        return 503, {"error": "mcp_setup_unavailable"}
    if content_type.split(";", 1)[0].strip().lower() != "application/json" or not trusted_origin(origin, host):
        return 403, {"error": "secure_same_origin_required"}
    if not isinstance(body, dict) or set(body) != {"api_key"}:
        return 422, {"error": "invalid_mcp_key"}
    key = body.get("api_key")
    if not isinstance(key, str) or not re.fullmatch(r"sk-[A-Za-z0-9_-]{20,2048}", key):
        return 422, {"error": "invalid_mcp_key"}
    target = PRIVATE / KEY_NAME
    created = False
    try:
        # No overwrite. Set ACL on an empty file before any credential bytes exist.
        with target.open("x", encoding="utf-8"):
            pass
        created = True
        _protect_empty_file(target)
        with target.open("w", encoding="utf-8") as stream:
            stream.write(key)
            stream.flush()
            os.fsync(stream.fileno())
        return 201, {"configured": True, "connection_verified": False}
    except FileExistsError:
        return 409, {"error": "mcp_key_already_configured"}
    except (OSError, subprocess.SubprocessError):
        if created:
            try:
                target.unlink()
            except OSError:
                pass
        return 503, {"error": "private_key_storage_unavailable"}
