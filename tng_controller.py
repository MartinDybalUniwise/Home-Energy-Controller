import argparse, copy, json, logging, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent

def load_json(name):
    with open(ROOT / name, encoding="utf-8") as f: return json.load(f)

def setup_logger(path, name):
    p=ROOT/path; p.parent.mkdir(parents=True, exist_ok=True)
    lg=logging.getLogger(name); lg.setLevel(logging.INFO); lg.handlers.clear()
    h=logging.FileHandler(p, encoding="utf-8"); h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    lg.addHandler(h); return lg

class DailyJsonlHandler(logging.Handler):
    def __init__(self, path):
        super().__init__()
        self.path=ROOT/path
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def emit(self, record):
        try:
            day=datetime.now().astimezone().strftime("%Y-%m-%d")
            daily=self.path.with_name(f"{self.path.stem}-{day}{self.path.suffix}")
            with open(daily,"a",encoding="utf-8") as f:
                f.write(str(record.getMessage()).strip()+"\n")
        except Exception:
            self.handleError(record)

def setup_state_logger(path, name):
    lg=logging.getLogger(name); lg.setLevel(logging.INFO); lg.handlers.clear()
    lg.addHandler(DailyJsonlHandler(path)); return lg

def in_window(now, start, end):
    t=now.strftime("%H:%M")
    return start <= t < end if start <= end else (t >= start or t < end)

def scheduled_value(section, now):
    value=section["default_temperature"]
    for w in section.get("schedule", []):
        if in_window(now,w["from"],w["to"]): value=w["temperature"]
    return value

class TNG:
    def __init__(self, conn, cfg, action, state, error):
        self.c=conn["tng"]; self.cfg=cfg; self.action=action; self.state=state; self.error=error
        self.s=requests.Session(); self.s.headers.update({"User-Agent":self.c["user_agent"]})
        self.pending_sent={}
        self.runtime_state_path=ROOT / self.cfg["runtime"].get("state_file", "data/runtime_state.json")
        self.runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
        # Safety state for outbound configuration changes.
        # A change must be confirmed by the heat pump before another change is allowed.
        self.change_gate={
            "basic": {"last_post_at": None, "awaiting_confirmation": False, "seen_pending": False, "last_requested": None},
            "thermostat": {"last_post_at": None, "awaiting_confirmation": False, "seen_pending": False, "last_requested": None},
        }
        self.telemetry_state={"last_sample_time": None}
        self._load_runtime_state()
        if not self.runtime_state_path.exists(): self._save_runtime_state()
    def _load_runtime_state(self):
        if not self.runtime_state_path.exists():
            return
        try:
            saved=json.loads(self.runtime_state_path.read_text(encoding="utf-8"))
            for kind in ("basic","thermostat"):
                if isinstance(saved.get(kind),dict):
                    for key in ("last_post_at","awaiting_confirmation","seen_pending","last_requested"):
                        if key in saved[kind]: self.change_gate[kind][key]=saved[kind][key]
            if isinstance(saved.get("telemetry"),dict):
                self.telemetry_state["last_sample_time"]=saved["telemetry"].get("last_sample_time")
            self.action.info("RUNTIME_STATE LOADED | %s", json.dumps(saved,ensure_ascii=False,separators=(",",":")))
        except Exception as e:
            self.error.exception("RUNTIME_STATE LOAD ERROR | %s",e)

    def _save_runtime_state(self):
        try:
            tmp=self.runtime_state_path.with_suffix(self.runtime_state_path.suffix+".tmp")
            payload={
                "basic": self.change_gate["basic"],
                "thermostat": self.change_gate["thermostat"],
                "telemetry": self.telemetry_state
            }
            tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
            tmp.replace(self.runtime_state_path)
        except Exception as e:
            self.error.exception("RUNTIME_STATE SAVE ERROR | %s",e)

    def _seconds_since_last_post(self, kind):
        value=self.change_gate[kind].get("last_post_at")
        if not value: return None
        try:
            dt=datetime.fromisoformat(value)
            if dt.tzinfo is None: dt=dt.astimezone()
            return max(0.0,(datetime.now().astimezone()-dt).total_seconds())
        except Exception:
            return 0.0

    def url(self,key):
        e=self.c["endpoints"][key]
        e=e.format(thermostat_key=self.c["thermostat_key"],basic_key=self.c["basic_key"],thermostat_id=self.c["thermostat_id"], heatpump_hash=self.c.get("heatpump_hash", ""), from_ms="{from_ms}", to_ms="{to_ms}")
        return urljoin(self.c["base_url"],e)
    def login(self):
        r=self.s.get(self.c["login_url"],timeout=self.cfg["runtime"]["request_timeout_seconds"]); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        def val(n):
            x=soup.find("input",{"name":n}); return x.get("value","") if x else ""
        body={"__EVENTTARGET":"","__EVENTARGUMENT":"","__VIEWSTATE":val("__VIEWSTATE"),"__VIEWSTATEGENERATOR":val("__VIEWSTATEGENERATOR"),
              "ctl00$MainContent$UserName":self.c["username"],"ctl00$MainContent$Password":self.c["password"],"ctl00$MainContent$ctl01":"Log In"}
        r=self.s.post(self.c["login_url"],data=body,headers={"Content-Type":"application/x-www-form-urlencoded"},timeout=self.cfg["runtime"]["request_timeout_seconds"]); r.raise_for_status()
        if ".AspNet.ApplicationCookie" not in self.s.cookies: raise RuntimeError("TNG login failed: authentication cookie missing")
        self.s.cookies.set(self.c["timezone_cookie_name"],self.c["timezone_cookie_value"],domain="tngsmart.cz",path="/")
        self.s.cookies.set("acceptCookies","true" if self.c["accept_cookies"] else "false",domain="tngsmart.cz",path="/")
        self.action.info("LOGIN OK")
    def ensure_login(self):
        if ".AspNet.ApplicationCookie" not in self.s.cookies: self.login()
    def post_json(self, endpoint, payload, kind):
        self.ensure_login(); headers=copy.deepcopy(self.c["headers"]); headers["Content-Type"]="application/json; charset=UTF-8"
        if self.cfg["runtime"].get("dry_run"):
            self.action.info("DRY_RUN | %s | %s",kind,json.dumps(payload,ensure_ascii=False,separators=(",",":"))); return 204
        r=self.s.post(self.url(endpoint),headers=headers,json=payload,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        if r.status_code in (401,403): self.s.cookies.clear(); self.login(); r=self.s.post(self.url(endpoint),headers=headers,json=payload,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        self.action.info("POST | %s | HTTP=%s | payload=%s",kind,r.status_code,json.dumps(payload,ensure_ascii=False,separators=(",",":")))
        if r.status_code != 204: raise RuntimeError(f"{kind}: expected HTTP 204, got {r.status_code}: {r.text[:500]}")
        return r.status_code
    def read_state(self):
        self.ensure_login()
        headers=copy.deepcopy(self.c["headers"])
        r=self.s.get(self.url("thermostat_page"), headers=headers, timeout=self.cfg["runtime"]["request_timeout_seconds"])
        if "Please Sign In" in r.text:
            self.s.cookies.clear(); self.login()
            r=self.s.get(self.url("thermostat_page"), headers=headers, timeout=self.cfg["runtime"]["request_timeout_seconds"])
        r.raise_for_status()

        out={"timestamp":datetime.now().astimezone().isoformat(),"http":r.status_code,"url":str(r.url)}
        scalar_re = re.compile(r'["\']?([A-Za-z_][A-Za-z0-9_]*)["\']?\s*:\s*(true|false|null|-?\d+(?:\.\d+)?|["\'][^"\']*["\'])', re.I)
        raw={}
        wanted_words=("temp","heat","boiler","thermostat","outside","outdoor","room","water","sensor","boost","pool","regulation","curve","confirmed","available","incoming","changed")
        for m in scalar_re.finditer(r.text):
            key=m.group(1); value=m.group(2)
            if not any(w in key.lower() for w in wanted_words): continue
            if value.lower()=="true": value=True
            elif value.lower()=="false": value=False
            elif value.lower()=="null": value=None
            elif value[:1] in ("\'", '"'): value=value[1:-1]
            else:
                try: value=float(value) if "." in value else int(value)
                except ValueError: pass
            raw[key]=value
        for k in ["LastSettingsNotConfirmed","IsConfirmed","DayTemperature","NightTemperature","SettingsAvailable","DataAvailable","ChangedTime","IncomingTime"]:
            if k in raw: out[k]=raw[k]
        out["tng"]=raw

        # Current configured heat-pump/boiler state from MyInstallations.
        installations_ep=self.c["endpoints"].get("installations_page", "/Pages/Account/MyInstallations?HeatPumpHash={heatpump_hash}")
        installations_url=urljoin(self.c["base_url"],installations_ep.format(heatpump_hash=self.c["heatpump_hash"]))
        ih=copy.deepcopy(self.c["headers"]); ih["Accept"]="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ir=self.s.get(installations_url,headers=ih,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        if ir.status_code in (401,403) or "Please Sign In" in ir.text:
            self.s.cookies.clear(); self.login(); ir=self.s.get(installations_url,headers=ih,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        ir.raise_for_status()
        hm=re.search(r'HeatPump\s*=\s*(\{.*?\});\s*CurrentHeatPumpHash',ir.text,re.S)
        if hm:
            hp=json.loads(hm.group(1))
            settings=hp.get("Settings") or {}
            boiler_set=settings.get("BoilerSet") or {}
            boiler_temp=settings.get("BoilerTemp") or {}
            heat_set=settings.get("HeatSet") or {}
            heat_temp=settings.get("HeatTemp_Const") or {}
            out["settings"]={
                "boiler_on":boiler_set.get("Boiler"),
                "boiler_set_temperature":boiler_temp.get("FloatValue",boiler_temp.get("ShortValue")),
                "boiler_sensor":boiler_set.get("Sensor"),
                "boiler_boost":boiler_set.get("Boost"),
                "heating_on":heat_set.get("Heat"),
                "heating_set_temperature":heat_temp.get("FloatValue",heat_temp.get("ShortValue")),
                "heating_mode":heat_set.get("HeatingMode"),
                "equit_curve":settings.get("EquitCurve"),
                "last_settings_not_confirmed":hp.get("LastSettingsNotConfirmed"),
                "advanced_settings_not_confirmed":hp.get("AdvancedSettingsNotConfirmed")
            }
            out["settings_http"]=ir.status_code
        else:
            out["settings"]={}
            out["settings_http"]=ir.status_code
            out["settings_warning"]="HeatPump object not found on MyInstallations"

        # Real heat-pump telemetry used by the TNG graph.
        # First run: bootstrap a larger history window. Next runs: continue from
        # the last persisted sample with a small overlap to tolerate timing gaps.
        now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
        bootstrap_seconds=int(self.cfg["runtime"].get("telemetry_bootstrap_seconds", self.cfg["runtime"].get("telemetry_history_seconds",3600)))
        overlap_seconds=int(self.cfg["runtime"].get("telemetry_overlap_seconds",120))
        cursor=self.telemetry_state.get("last_sample_time")
        from_ms=now_ms-bootstrap_seconds*1000
        if cursor:
            try:
                cursor_dt=datetime.fromisoformat(cursor.replace("Z","+00:00"))
                from_ms=max(0,int(cursor_dt.timestamp()*1000)-overlap_seconds*1000)
            except Exception:
                pass
        ep=self.c["endpoints"]["heatpump_data"].format(heatpump_hash=self.c["heatpump_hash"],from_ms=from_ms,to_ms=now_ms)
        telemetry_url=urljoin(self.c["base_url"],ep)
        th=copy.deepcopy(self.c["headers"]); th["Accept"]="*/*"; th["Content-Type"]="application/json; charset=utf-8"
        tr=self.s.get(telemetry_url,headers=th,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        if tr.status_code in (401,403):
            self.s.cookies.clear(); self.login(); tr=self.s.get(telemetry_url,headers=th,timeout=self.cfg["runtime"]["request_timeout_seconds"])
        tr.raise_for_status()
        data=tr.json()
        samples=data.get("First") or []
        if samples:
            last=samples[-1]
            def c10_sample(sample,k):
                v=sample.get(k); return None if v is None else v/10.0
            out["heatpump"]={
                "sample_time":last.get("time"),
                "outside_temperature":c10_sample(last,"t"),
                "water_output_temperature":c10_sample(last,"tw"),
                "boiler_temperature":c10_sample(last,"tb"),
                "room_temperature":c10_sample(last,"tt")
            }
            out["telemetry_http"]=tr.status_code
        else:
            out["heatpump"]={"sample_time":None,"outside_temperature":None,"water_output_temperature":None,"boiler_temperature":None,"room_temperature":None}
            out["telemetry_http"]=tr.status_code
            out["telemetry_warning"]="HeatPumpData returned no samples"

        # Compact state log for later graphing. One valid JSON object per line.
        settings=out.get("settings") or {}
        hp=out.get("heatpump") or {}
        # Persist a telemetry cursor. The API request intentionally overlaps the
        # previous window, but only samples newer than the cursor are written.
        compact=None
        cursor_time=self.telemetry_state.get("last_sample_time")
        cursor_dt=None
        if cursor_time:
            try: cursor_dt=datetime.fromisoformat(cursor_time.replace("Z","+00:00"))
            except Exception: cursor_dt=None
        newest_time=cursor_time
        newest_dt=cursor_dt
        for sample in samples:
            sample_time=sample.get("time")
            if not sample_time:
                continue
            try: sample_dt=datetime.fromisoformat(sample_time.replace("Z","+00:00"))
            except Exception: continue
            if cursor_dt is not None and sample_dt <= cursor_dt:
                continue
            compact={
                "timestamp":datetime.now().astimezone().isoformat(),
                "sample_time":sample_time,
                "outside_temperature":c10_sample(sample,"t"),
                "water_output_temperature":c10_sample(sample,"tw"),
                "boiler_temperature":c10_sample(sample,"tb"),
                "room_temperature":c10_sample(sample,"tt"),
                "boiler_on":settings.get("boiler_on"),
                "boiler_set_temperature":settings.get("boiler_set_temperature"),
                "boiler_sensor":settings.get("boiler_sensor"),
                "boiler_boost":settings.get("boiler_boost"),
                "heating_on":settings.get("heating_on"),
                "heating_set_temperature":settings.get("heating_set_temperature"),
                "heating_mode":settings.get("heating_mode"),
                "equit_curve":settings.get("equit_curve")
            }
            self.state.info(json.dumps(compact,ensure_ascii=False,separators=(",",":")))
            if newest_dt is None or sample_dt > newest_dt:
                newest_dt=sample_dt
                newest_time=sample_time
        if newest_time and newest_time != cursor_time:
            self.telemetry_state["last_sample_time"]=newest_time
            self._save_runtime_state()
        out["log_state"]=compact
        return out

    def _gate_update(self, kind, pending_flag):
        """Track the TNG confirmation cycle for a posted change.

        Expected sequence after POST: pending False -> True -> False.
        We intentionally require seeing True at least once before considering
        the command confirmed. This prevents us from flooding TNG while a
        previous configuration is still waiting for the heat pump.
        """
        g=self.change_gate[kind]
        if not g["awaiting_confirmation"]:
            return
        if pending_flag is True:
            if not g["seen_pending"]:
                g["seen_pending"]=True
                self._save_runtime_state()
            return
        if pending_flag is False and g["seen_pending"]:
            g["awaiting_confirmation"]=False
            g["seen_pending"]=False
            self._save_runtime_state()
            self.action.info("CONFIRMED | %s | TNG pending flag returned TRUE -> FALSE", kind.upper())
        elif pending_flag is False and g["awaiting_confirmation"]:
            # If the process was restarted and missed the TRUE phase, retain the
            # 15-minute guard. After it expires, FALSE is sufficient to recover.
            elapsed=self._seconds_since_last_post(kind)
            min_interval=int(self.cfg["runtime"].get("minimum_change_interval_seconds",900))
            if elapsed is not None and elapsed >= min_interval:
                g["awaiting_confirmation"]=False
                self._save_runtime_state()
                self.action.info("CONFIRMED_RECOVERY | %s | pending=false after %.0fs",kind.upper(),elapsed)

    def _can_post(self, kind, pending_flag):
        """Return (allowed, reason) for a new settings POST."""
        self._gate_update(kind, pending_flag)
        g=self.change_gate[kind]

        # Never send while TNG itself says a previous change is waiting.
        if pending_flag is True:
            return False, "TNG reports LastSettingsNotConfirmed=true"

        # After our own POST, wait for the explicit TRUE -> FALSE confirmation cycle.
        if g["awaiting_confirmation"]:
            return False, "waiting for TNG confirmation cycle TRUE -> FALSE"

        min_interval=int(self.cfg["runtime"].get("minimum_change_interval_seconds",900))
        elapsed=self._seconds_since_last_post(kind)
        if elapsed is not None and elapsed < min_interval:
            return False, f"minimum change interval not reached ({int(elapsed)}s/{min_interval}s)"

        return True, "ok"

    def _mark_posted(self, kind, requested=None):
        g=self.change_gate[kind]
        g["last_post_at"]=datetime.now().astimezone().isoformat()
        g["awaiting_confirmation"]=True
        g["seen_pending"]=False
        g["last_requested"]=requested
        self._save_runtime_state()

    def _last_action_status(self):
        candidates=[]
        for kind in ("basic","thermostat"):
            g=self.change_gate.get(kind,{})
            ts=g.get("last_post_at")
            if ts:
                candidates.append((ts,kind,g.get("last_requested") or {}))
        if not candidates:
            return "last action: none"
        ts,kind,req=max(candidates,key=lambda x:x[0])
        if kind == "basic":
            if req.get("boiler_temperature") is not None:
                return f"last action: SET boiler temp {req['boiler_temperature']} C"
            if req.get("heating_temperature") is not None:
                return f"last action: SET heating temp {req['heating_temperature']} C"
        if kind == "thermostat" and req.get("day_temperature") is not None:
            return f"last action: SET thermostat temp {req['day_temperature']} C"
        return f"last action: {kind}"

    def _check_status(self, current_state):
        hp=(current_state or {}).get("heatpump") or {}
        st=(current_state or {}).get("settings") or {}
        def fmt(v):
            return "-" if v is None else f"{v:g}"
        return (
            f"boiler {fmt(hp.get('boiler_temperature'))}/{fmt(st.get('boiler_set_temperature'))} C | "
            f"water {fmt(hp.get('water_output_temperature'))} C | "
            f"outside {fmt(hp.get('outside_temperature'))} C | "
            f"room {fmt(hp.get('room_temperature'))} C | "
            f"{self._last_action_status()}"
        )

    def apply(self, current_state=None):
        now=datetime.now()
        current_state=current_state or {}
        settings=current_state.get("settings") or {}

        # BASIC_SETTINGS: send only when the value currently stored in TNG differs
        # from the value required by the schedule. After a POST, do not repeat the
        # same request while TNG is still confirming/propagating that change.
        if self.cfg["boiler"]["enabled"] or self.cfg["heating"]["enabled"]:
            p=copy.deepcopy(self.cfg["basic_settings_template"])
            basic_matches=True

            if self.cfg["boiler"]["enabled"]:
                desired_boiler=scheduled_value(self.cfg["boiler"],now)
                p["BoilerTemp"]=desired_boiler
                if settings.get("boiler_set_temperature") != desired_boiler:
                    basic_matches=False

            if self.cfg["heating"]["enabled"]:
                desired_heat=scheduled_value(self.cfg["heating"],now)
                p["HeatTemp_Const"]=desired_heat
                if settings.get("heating_set_temperature") != desired_heat:
                    basic_matches=False

            sig=json.dumps(p,sort_keys=True)
            basic_pending=settings.get("last_settings_not_confirmed")
            self._gate_update("basic", basic_pending)
            if basic_matches:
                self.pending_sent.pop("basic",None)
            elif self.pending_sent.get("basic") == sig and self.change_gate["basic"]["awaiting_confirmation"]:
                self.action.info("SKIP | BASIC_SETTINGS | waiting for confirmation of already sent payload")
            else:
                allowed,reason=self._can_post("basic",basic_pending)
                if allowed:
                    self.post_json("basic_settings",p,"BASIC_SETTINGS")
                    self.pending_sent["basic"]=sig
                    self._mark_posted("basic", {"boiler_temperature": p.get("BoilerTemp"), "heating_temperature": p.get("HeatTemp_Const")})
                else:
                    self.action.info("SKIP | BASIC_SETTINGS | %s",reason)

        # Thermostat target is not reliably exposed by the current status page,
        # so retain duplicate suppression for identical requested thermostat data.
        if self.cfg["thermostat"]["enabled"]:
            p=copy.deepcopy(self.cfg["thermostat_settings_template"])
            p["DayTemperature"]=scheduled_value(self.cfg["thermostat"],now)
            sig=json.dumps(p,sort_keys=True)
            thermostat_pending=current_state.get("LastSettingsNotConfirmed")
            self._gate_update("thermostat", thermostat_pending)
            if self.pending_sent.get("thermostat") == sig and self.change_gate["thermostat"]["awaiting_confirmation"]:
                self.action.info("SKIP | THERMOSTAT_SETTINGS | waiting for confirmation of already sent payload")
            elif self.pending_sent.get("thermostat") != sig:
                allowed,reason=self._can_post("thermostat",thermostat_pending)
                if allowed:
                    self.post_json("thermostat_settings",p,"THERMOSTAT_SETTINGS")
                    self.pending_sent["thermostat"]=sig
                    self._mark_posted("thermostat", {"day_temperature": p.get("DayTemperature"), "night_temperature": p.get("NightTemperature")})
                else:
                    self.action.info("SKIP | THERMOSTAT_SETTINGS | %s",reason)

def schedule_signature(cfg, now):
    values=[]
    for name in ("boiler","heating","thermostat"):
        section=cfg.get(name,{})
        if section.get("enabled"):
            values.append((name,scheduled_value(section,now)))
    return tuple(values)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--once",action="store_true"); ap.add_argument("--status",action="store_true"); ap.add_argument("--dry-run",action="store_true"); a=ap.parse_args()
    conn=load_json("connect.json"); cfg=load_json("config.json"); cfg["runtime"]["dry_run"] = cfg["runtime"].get("dry_run",False) or a.dry_run
    action=setup_logger(cfg["logging"]["action_log"],"actions"); state=setup_state_logger(cfg["logging"]["state_log"],"state"); error=setup_logger(cfg["logging"]["error_log"],"errors")
    t=TNG(conn,cfg,action,state,error)
    try:
        t.login()
        if a.status: print(json.dumps(t.read_state(),ensure_ascii=False,indent=2)); return
        check_interval=max(1,int(cfg["runtime"]["check_interval_seconds"]))
        next_check=0.0
        last_schedule_sig=None
        while True:
            now=datetime.now()
            sig=schedule_signature(cfg,now)
            schedule_changed=(last_schedule_sig is not None and sig != last_schedule_sig)
            due=(time.monotonic() >= next_check) or schedule_changed or last_schedule_sig is None
            if due:
                try:
                    s=t.read_state()
                    t.apply(s)
                    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "OK |", t._check_status(s), flush=True)
                except Exception as e:
                    error.exception("LOOP ERROR | %s",e)
                    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR - see error log", file=sys.stderr, flush=True)
                next_check=time.monotonic()+check_interval
                last_schedule_sig=sig
                if a.once: break
            time.sleep(1)
    except Exception as e: error.exception("FATAL | %s",e); raise
if __name__=="__main__": main()
