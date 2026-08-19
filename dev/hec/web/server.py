"""Webový server postavený na standardní knihovně.

Bez frameworku záměrně: na Raspberry Pi u zákazníka je každá závislost něco,
co se musí instalovat a aktualizovat. `ThreadingHTTPServer` obslouží desítky
požadavků z prohlížeče bez problémů.
"""

from __future__ import annotations

import json
import mimetypes
import secrets as pysecrets
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ..core.logging_setup import get_logger
from . import api

FRONTEND = Path(__file__).resolve().parent / "frontend"
SESSION_HOURS = 24 * 30
MAX_BODY = 2 * 1024 * 1024


class SessionStore:
    """Přihlášení tokenem v cookie. Prázdné heslo = rozhraní bez přihlášení."""

    def __init__(self, password: str):
        password = (password or "").strip()
        # Nevyplněná proměnná prostředí zůstane v konfiguraci jako ${HEC_WEB_PASSWORD}.
        # Brát ji jako heslo by znamenalo rozhraní, do kterého se nikdo nedostane.
        if password.startswith("${") and password.endswith("}"):
            password = ""
        self.password = password
        self.tokens: dict[str, datetime] = {}

    @property
    def required(self) -> bool:
        return bool(self.password)

    def login(self, password: str) -> str | None:
        if not pysecrets.compare_digest(password or "", self.password):
            return None
        token = pysecrets.token_urlsafe(32)
        self.tokens[token] = datetime.now() + timedelta(hours=SESSION_HOURS)
        return token

    def valid(self, token: str | None) -> bool:
        if not self.required:
            return True
        expires = self.tokens.get(token or "")
        if expires is None:
            return False
        if expires < datetime.now():
            self.tokens.pop(token, None)
            return False
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "HomeEnergyController"
    app = None
    sessions: SessionStore = None
    log = get_logger("web")

    # --- pomocné -----------------------------------------------------------
    def _send(self, status: int, payload, content_type="application/json; charset=utf-8",
              headers: dict | None = None):
        # Hotové bajty se posílají tak, jak jsou – i když mají typ application/json
        # (statický manifest.json). Serializovat by se měly jen datové struktury.
        if isinstance(payload, bytes):
            body = payload
        elif content_type.startswith("application/json"):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            body = str(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _cookie(self, name: str) -> str | None:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return unquote(value)
        return None

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _authorised(self) -> bool:
        return self.sessions.valid(self._cookie("hec_session"))

    def log_message(self, fmt, *args):        # noqa: A003 – potlačení výpisu na stderr
        self.log.debug("http | %s", fmt % args)

    # --- statické soubory ---------------------------------------------------
    def _serve_static(self, path: str):
        relative = path.lstrip("/") or "index.html"
        target = (FRONTEND / relative).resolve()
        try:
            target.relative_to(FRONTEND.resolve())
        except ValueError:
            return self._send(403, {"error": "forbidden"})
        if not target.is_file():
            target = FRONTEND / "index.html"          # jednostránková aplikace
            if not target.is_file():
                return self._send(404, {"error": "not_found"})
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        cache = "no-cache" if target.name in ("index.html", "sw.js") else "max-age=3600"
        self._send(200, target.read_bytes(), content_type=mime, headers={"Cache-Control": cache})

    # --- směrování ----------------------------------------------------------
    def do_GET(self):                                  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if not route.startswith("/api/"):
            return self._serve_static(route)

        if route == "/api/session":
            return self._send(200, {"required": self.sessions.required,
                                    "authorised": self._authorised()})
        if route.startswith("/api/i18n/"):
            return self._send(*api.translations(route.rsplit("/", 1)[-1]))

        if not self._authorised():
            return self._send(401, {"error": "unauthorised"})

        routes = {
            "/api/current": lambda: api.current(self.app),
            "/api/status": lambda: api.status(self.app),
            "/api/history": lambda: api.history(self.app, params),
            "/api/sources": lambda: api.sources(self.app),
            "/api/prices": lambda: api.prices(self.app),
            "/api/weather": lambda: api.weather(self.app),
            "/api/prediction": lambda: api.prediction(self.app),
            "/api/summaries": lambda: api.summaries(self.app, params),
            "/api/appliances": lambda: api.appliance_cycles(self.app, params),
            "/api/phases": lambda: api.phases(self.app, params),
            "/api/decisions": lambda: api.decisions(self.app, params),
            "/api/metrics": lambda: api.metrics(self.app, params),
            "/api/heatpump": lambda: api.heatpump(self.app, params),
            "/api/config": lambda: api.config_get(self.app),
            "/api/config/schema": lambda: api.config_schema(self.app),
        }
        handler = routes.get(route)
        if handler is None:
            return self._send(404, {"error": "not_found"})
        try:
            return self._send(*handler())
        except Exception as exc:                       # noqa: BLE001
            self.log.error("api_failed | route=%s error=%s: %s", route, type(exc).__name__, exc)
            return self._send(500, {"error": "internal_error"})

    def do_POST(self):                                 # noqa: N802
        route = urlparse(self.path).path
        if route == "/api/login":
            token = self.sessions.login(str(self._body().get("password", "")))
            if token is None:
                return self._send(401, {"error": "invalid_password"})
            cookie = f"hec_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_HOURS * 3600}"
            return self._send(200, {"authorised": True}, headers={"Set-Cookie": cookie})
        if not self._authorised():
            return self._send(401, {"error": "unauthorised"})
        return self._send(404, {"error": "not_found"})

    def do_PUT(self):                                  # noqa: N802
        route = urlparse(self.path).path
        if not self._authorised():
            return self._send(401, {"error": "unauthorised"})
        if route == "/api/config":
            return self._send(*api.config_put(self.app, self._body()))
        return self._send(404, {"error": "not_found"})

    def do_HEAD(self):                                 # noqa: N802
        self.do_GET()


def build_server(app, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {
        "app": app,
        "sessions": SessionStore(str(app.config.get("web.password", "") or "")),
    })
    host = host if host is not None else str(app.config.get("web.host", "0.0.0.0"))
    port = int(port if port is not None else app.config.get("web.port", 8080))
    return ThreadingHTTPServer((host, port), handler)


def serve(app) -> int:
    server = build_server(app)
    host, port = server.server_address[0], server.server_address[1]
    get_logger("web").info("web_started | host=%s port=%s", host, port)
    print(f"Home Energy Controller – http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        app.stop()
    return 0
