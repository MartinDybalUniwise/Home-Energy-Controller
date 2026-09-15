"""Datová vrstva webového API.

Funkce vracejí (http_status, payload). Server je jen obálka – díky tomu se dá
celé API testovat bez otevírání soketu.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ..core import config as config_mod
from ..core import i18n
from ..core import schema as schema_mod
from ..core.goodwe_hardware_authorization import authorize as authorize_goodwe_hardware
from ..core.goodwe_hardware_authorization import load as load_goodwe_authorization
from ..core.timeutil import now_local, parse_iso, to_iso
from ..finance.service import FinanceService
from ..forecast.household_consumption_forecast import forecast_household_consumption
from ..forecast.pv_forecast import forecast_pv
from ..readers.goodwe_manager import GoodWeManager
from ..readers.sdg_history_reader import SDGHistoryReader
from ..storage.base import read_json
from ..storage.series import downsample, series_fields

RELATIVE = re.compile(r"^-(\d+)([hdm])$")
BUCKET_FOR_SPAN = ((6 * 3600, 60), (48 * 3600, 300), (8 * 86400, 900), (None, 3600))


def parse_moment(value: str | None, default: datetime) -> datetime:
    """Přijímá ISO čas, `-24h`, `-7d`, `-30m` nebo `today`."""
    if not value:
        return default
    if value == "today":
        return now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "now":
        return now_local()
    match = RELATIVE.match(value)
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        delta = {"h": timedelta(hours=amount), "d": timedelta(days=amount),
                 "m": timedelta(minutes=amount)}[unit]
        return now_local() - delta
    return parse_iso(value) or default


def auto_bucket(span_seconds: float) -> int:
    """Zhuštění podle délky rozsahu – mobil nesmí stahovat statisíce řádků."""
    for limit, bucket in BUCKET_FOR_SPAN:
        if limit is None or span_seconds <= limit:
            return bucket
    return 3600


def current(app, params: dict | None = None) -> tuple[int, dict]:
    fast = (params or {}).get("fast") == "1"
    try:
        return 200, app.current(include_status=not fast)
    except TypeError:
        # Keep lightweight test doubles compatible with the optional fast mode.
        payload = app.current()
        if fast:
            payload.pop("status", None)
        return 200, payload


def status(app) -> tuple[int, dict]:
    return 200, app.status()


def history(app, params: dict) -> tuple[int, dict]:
    source = params.get("source")
    if not source:
        return 400, {"error": "missing_source"}

    to = parse_moment(params.get("to"), now_local())
    frm = parse_moment(params.get("from"), to - timedelta(hours=24))
    if frm > to:
        frm, to = to, frm

    records = app.storage.query(source, frm, to)
    fields = [f for f in (params.get("fields") or "").split(",") if f] or series_fields(records)

    bucket = params.get("bucket")
    bucket = int(bucket) if bucket and bucket.isdigit() else auto_bucket((to - frm).total_seconds())
    rows = downsample(records, fields, bucket)

    return 200, {
        "source": source,
        "from": to_iso(frm),
        "to": to_iso(to),
        "bucket_seconds": bucket,
        "fields": fields,
        "count": len(rows),
        "raw_count": len(records),
        "rows": rows,
    }


def sources(app) -> tuple[int, dict]:
    return 200, {"sources": app.storage.sources()}


def log_days(app, params: dict) -> tuple[int, dict]:
    source = params.get("source")
    if not source:
        return 400, {"error": "missing_source"}
    return 200, {"source": source, "days": app.storage.days(source)}


def logs(app, params: dict) -> tuple[int, dict]:
    """Syrová JSONL historie jednoho zdroje – bez zhuštění, pro ruční kontrolu.

    Bez `day` vrací posledních `tail` záznamů (výchozí a maximum jsou omezené,
    aby jeden požadavek nikdy nevytáhl celou historii do prohlížeče). S `day`
    vrací celý daný den – tam si o rozsah řekl uživatel sám.
    """
    source = params.get("source")
    if not source:
        return 400, {"error": "missing_source"}

    day = params.get("day")
    if day:
        frm = parse_moment(day, now_local())
        rows = app.storage.query(source, frm, frm + timedelta(days=1), end_exclusive=True)
    else:
        tail = max(1, min(int(params.get("tail", 200) or 200), 2000))
        rows = app.storage.last(source, tail)

    return 200, {"source": source, "day": day, "count": len(rows), "rows": rows}


def prices(app) -> tuple[int, dict]:
    """Ceny na dnešek a zítřek pro graf a plánování."""
    today = now_local().date()
    out = {}
    for label, day in (("today", today), ("tomorrow", today + timedelta(days=1))):
        payload = read_json(app.config.data_dir / f"ote-{day.isoformat()}.json")
        out[label] = payload
    return 200, out


def weather(app) -> tuple[int, dict]:
    return 200, read_json(app.config.data_dir / "weather.json", {}) or {}


def prediction(app) -> tuple[int, dict]:
    predictor = getattr(app, "predictor", None)
    if predictor is None:
        return 200, {"available": False, "reason_key": "prediction.not_enough_data"}
    forecast = predictor.forecast()
    # dev/step09 fáze B: nový sjednocený tvar (value/range/confidence/...)
    # vedle starých plochých polí – frontend na Predikci se nemění, jde jen
    # o přípravu na sdílení a další zdroje predikcí (fáze D+).
    generated_at = forecast.get("generated_at")
    for day in forecast.get("days", []):
        day["forecast_pv"] = forecast_pv(day, generated_at).to_dict()
        day["forecast_consumption"] = forecast_household_consumption(day, generated_at).to_dict()
    return 200, forecast


def summaries(app, params: dict) -> tuple[int, dict]:
    days = int(params.get("days", 30))
    analyser = getattr(app, "summaries", None)
    if analyser is None:
        return 200, {"days": []}
    return 200, {"days": analyser.recent(days)}


def appliance_cycles(app, params: dict) -> tuple[int, dict]:
    detector = getattr(app, "appliances", None)
    if detector is None:
        return 200, {"cycles": []}
    return 200, {"cycles": detector.recent(int(params.get("days", 7)))}


def phases(app, params: dict) -> tuple[int, dict]:
    analyser = getattr(app, "phases", None)
    if analyser is None:
        return 200, {"available": False}
    return 200, analyser.analyse(int(params.get("days", 7)))


def heatpump(app, params: dict) -> tuple[int, dict]:
    analyser = getattr(app, "heatpump", None)
    if analyser is None:
        return 200, {"measured": False}
    return 200, analyser.analyse_day()


def decisions(app, params: dict) -> tuple[int, dict]:
    controller = getattr(app, "controller", None)
    if controller is None:
        return 200, {"decisions": []}
    return 200, {"decisions": controller.recent(int(params.get("days", 7))),
                 "state": controller.state()}


def metrics(app, params: dict) -> tuple[int, dict]:
    reporter = getattr(app, "metrics", None)
    if reporter is None:
        return 200, {"days": 0}
    return 200, reporter.report(int(params.get("days", 30)))


def _finance_service(app) -> FinanceService:
    service = getattr(app, "finance", None)
    return service if service is not None else FinanceService(app)


def finance_dashboard(app, params: dict) -> tuple[int, dict]:
    return 200, _finance_service(app).dashboard(params)


def finance_manual(app, params: dict) -> tuple[int, dict]:
    return 200, _finance_service(app).manual_items(params)


def config_get(app) -> tuple[int, dict]:
    return 200, {"config": app.config.to_public_dict(), "errors": app.config.errors}


def config_schema(app) -> tuple[int, dict]:
    return 200, {"fields": schema_mod.describe()}


def _goodwe_host(app) -> str:
    return str(app.config.get("goodwe.host", "") or "").strip()


def _goodwe_manager(app) -> GoodWeManager:
    injected = getattr(app, "goodwe_verifier", None)
    if injected is not None:
        return injected
    reader_lookup = getattr(app, "reader", None)
    reader = reader_lookup("goodwe") if callable(reader_lookup) else None
    manager = getattr(reader, "manager", None)
    if manager is not None:
        return manager
    return GoodWeManager(app.config)


def _goodwe_authorization_payload(app) -> dict:
    return {
        "authorization": load_goodwe_authorization(app.config),
        "verification": getattr(app, "goodwe_authorization_evidence", None),
    }


def goodwe_authorization_status(app) -> tuple[int, dict]:
    return 200, _goodwe_authorization_payload(app)


def goodwe_authorization_verify(app) -> tuple[int, dict]:
    host = _goodwe_host(app)
    if not host:
        result = {"status": "FAILED", "verified": False, "host": host,
                  "error": "goodwe_host_not_configured", "message_key": "settings.goodwe_verify_not_configured",
                  "verified_at": to_iso(now_local())}
        app.goodwe_authorization_evidence = result
        return 400, result
    try:
        manager = _goodwe_manager(app)
        manager.read_runtime()
        snapshot = manager.status_snapshot()
        result = {
            "status": "SUCCESS",
            "verified": True,
            "host": host,
            "model": snapshot.get("model"),
            "firmware": snapshot.get("firmware"),
            "evidence_id": str(uuid4()),
            "verified_at": to_iso(now_local()),
            "message_key": "settings.goodwe_verify_ok",
        }
        app.goodwe_authorization_evidence = result
        return 200, result
    except Exception as exc:  # noqa: BLE001
        result = {"status": "FAILED", "verified": False, "host": host,
                  "error": f"{type(exc).__name__}: {exc}",
                  "message_key": "settings.goodwe_verify_failed",
                  "verified_at": to_iso(now_local())}
        app.goodwe_authorization_evidence = result
        return 502, result


def goodwe_authorization_approve(app, body: dict) -> tuple[int, dict]:
    evidence = getattr(app, "goodwe_authorization_evidence", None) or {}
    host = _goodwe_host(app)
    if not evidence.get("verified") or evidence.get("status") != "SUCCESS":
        return 409, {"error": "goodwe_verification_required",
                     "message_key": "settings.goodwe_approve_verification_required",
                     **_goodwe_authorization_payload(app)}
    if evidence.get("host") != host:
        return 409, {"error": "goodwe_verification_host_mismatch",
                     "message_key": "settings.goodwe_approve_host_mismatch",
                     **_goodwe_authorization_payload(app)}
    approved_by = str((body or {}).get("approved_by") or "local-admin")
    artifact = authorize_goodwe_hardware(
        app.config,
        device_host=host,
        evidence_id=str(evidence["evidence_id"]),
        approved_by=approved_by,
        verification=lambda: evidence.get("verified") is True and evidence.get("host") == host,
    )
    return 200, {"authorization": artifact, "verification": evidence}


def config_verify(app, target: str) -> tuple[int, dict]:
    """Read-only checks for configured local paths; never probes device writes."""
    targets = {
        "storage.data": "storage.data_path",
        "storage.logs": "storage.logs_path",
        "storage.history": "storage.history_path",
        "storage.archive": "storage.archive_path",
        "sdg": "goodwe.sdg.log_root_path",
    }
    path_key = targets.get(target)
    if path_key is None:
        return 400, {"error": "unsupported_verify_target"}

    raw_path = str(app.config.get(path_key, "") or "")
    if not raw_path:
        return 200, {"target": target, "configured": False, "available": False,
                     "path": "", "message_key": "settings.verify_not_configured"}
    path = Path(raw_path).expanduser()
    if not path.is_absolute() and not raw_path.startswith("\\\\"):
        path = app.config.root / path

    result = {"target": target, "configured": True, "available": path.is_dir(),
              "path": str(path), "message_key": "settings.verify_unavailable"}
    if target == "sdg":
        files = [file for directory in SDGHistoryReader.candidate_directories(path)
                 if directory.is_dir() for file in directory.rglob("*")
                 if file.is_file() and file.suffix.lower() == ".dbf"]
        files.sort(key=lambda file: file.stat().st_mtime_ns, reverse=True)
        result.update({"file_count": len(files),
                       "latest_file": str(files[0]) if files else None,
                       "available": path.is_dir() and bool(files),
                       "message_key": "settings.verify_ok" if files else "settings.verify_no_files"})
    elif path.is_dir():
        result["message_key"] = "settings.verify_ok"
    return 200, result


def config_put(app, body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        return 400, {"error": "invalid_body"}
    incoming = body.get("config", body)
    goodwe_incoming = incoming.get("goodwe", {}) if isinstance(incoming, dict) else {}
    if isinstance(goodwe_incoming, dict) and any(
            key in goodwe_incoming for key in ("hardware_verified", "hardware_authorization")):
        return 400, {"error": "hardware_authorization_read_only"}
    # Zamaskované hodnoty z UI se nikdy nezapisují zpět – tajemství se mění jen v .env.
    before = deepcopy(app.config.data)
    merged = _merge_preserving_secrets(app.config.data, incoming)
    errors = config_mod.save(app.config, merged)
    if errors:
        return 400, {"errors": errors}
    # Porovnává se stav před uložením – save() konfiguraci v paměti už přepsal.
    return 200, {"saved": True, "restart_required": _restart_required(before, app.config.data)}


def _merge_preserving_secrets(existing: dict, incoming: dict) -> dict:
    from ..core.secrets import is_secret_key
    out = dict(existing)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            out[key] = _merge_preserving_secrets(existing[key], value)
        elif is_secret_key(key) and isinstance(value, str) and "***" in value:
            out[key] = existing.get(key)
        else:
            out[key] = value
    return out


def _restart_required(old: dict, new: dict) -> list[str]:
    changed = []
    for field in schema_mod.describe():
        if not field["restart"]:
            continue
        path = field["path"].split(".")
        old_value, new_value = old, new
        for part in path:
            old_value = (old_value or {}).get(part) if isinstance(old_value, dict) else None
            new_value = (new_value or {}).get(part) if isinstance(new_value, dict) else None
        if old_value != new_value:
            changed.append(field["path"])
    return changed


def translations(lang: str) -> tuple[int, dict]:
    catalog = i18n.load(lang)
    if not catalog:
        return 404, {"error": "unknown_language", "available": i18n.available()}
    return 200, {"lang": lang, "available": i18n.available(), "catalog": catalog}
