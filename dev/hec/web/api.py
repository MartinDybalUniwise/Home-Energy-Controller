"""Datová vrstva webového API.

Funkce vracejí (http_status, payload). Server je jen obálka – díky tomu se dá
celé API testovat bez otevírání soketu.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta

from ..core import config as config_mod
from ..core import i18n
from ..core import schema as schema_mod
from ..core.timeutil import now_local, parse_iso, to_iso
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


def current(app) -> tuple[int, dict]:
    return 200, app.current()


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
    rows = downsample(records, fields, bucket) if bucket else records

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
    return 200, predictor.forecast()


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


def config_get(app) -> tuple[int, dict]:
    return 200, {"config": app.config.to_public_dict(), "errors": app.config.errors}


def config_schema(app) -> tuple[int, dict]:
    return 200, {"fields": schema_mod.describe()}


def config_put(app, body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        return 400, {"error": "invalid_body"}
    incoming = body.get("config", body)
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
