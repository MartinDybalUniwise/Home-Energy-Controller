# Home Energy Controller – plán vývoje

Dokument vychází z `HOME_ENERGY_CONTROLLER_DEVELOPMENT_PROMPT.md` a z inventury
současného repozitáře (stav: commit `b024cd3`, srpen 2026).

Řídící pravidlo celého plánu (kap. 30 a 35 zadání): **stávající funkční kód se
nepřepisuje, ale postupně zapouzdřuje.** Každá fáze musí skončit stavem, kdy
systém běží a sbírá data.

---

## 1. Inventura repozitáře

| Soubor | Stav | Hodnocení |
|---|---|---|
| `tng_controller.py` (464 ř.) | **funkční, produkčně používaný** | Nejcennější část repa. Login na tngsmart.cz, čtení stavu, telemetrie, zápis nastavení včetně potvrzovacího protokolu. Chránit testy před jakýmkoli zásahem. |
| `ote_reader.py` (170 ř.) | **funkční** | Scrape 15min day-ahead cen z OTE, atomický zápis `data/ote-YYYY-MM-DD.json`. Chybí přepočet na CZK/kWh a JSONL historie. |
| `goodwe-read.py` (60 ř.) | **prototyp** | Jednorázový výpis přes knihovnu `goodwe` (rodina ET, IP 192.168.2.116). Není smyčka, není ukládání, IP je natvrdo, knihovna chybí v `requirements.txt`. |
| `connect.json` | **funkční, ale bezpečnostní problém** | Obsahuje heslo, thermostat_key, basic_key, heatpump_hash v plaintextu **a je verzovaný v gitu**. |
| `config.json` | funkční | Runtime, logging, rozvrhy bojleru/topení/termostatu, šablony TNG payloadů. Zatím jen TNG doména. |
| `data/weather.json` | **data bez zdrojáku** | Open-Meteo, Ostrava, `current` + `forecast_hourly` (temp, cloud, precip, wind, GHI/direct/diffuse, sunshine). Skript, který to vygeneroval, v repu **není**. |
| `logs/state-2026-08-18.jsonl` | funkční | Denní JSONL telemetrie TČ – přesně formát, který zadání chce. |
| `logs/actions.txt`, `logs/errors.txt` | funkční | Bez rotace, rostou neomezeně. |
| `data/runtime_state.json` | funkční | Perzistence change-gate a kurzoru telemetrie. |
| `start.cmd`, `test.cmd`, `ote-test.cmd` | funkční | Pouze Windows (`py`). Linux ekvivalent chybí. |
| `README.md` | zastaralý | Popisuje jen TNG controller, tvrdí interval 60 s (config má 300 s). |
| chybí | – | `.gitignore`, `.env.example`, testy, Shelly reader, weather reader, web UI, API, archivace, `history/`. |

### Co z prompt-zadání už reálně existuje

Kap. 31, fáze 1 je hotová zhruba z 35 %: TNG a OTE čtou spolehlivě, weather
částečně (chybí kód), GoodWe jen prototyp, Shelly vůbec, dashboard vůbec.

---

## 2. Zdokumentovaná zjištěná rozhraní

Tyto formáty jsou závazné pro zpětnou kompatibilitu (kap. 30 bod 7).

### TNG (tngsmart.cz)

* Login: POST formuláře ASP.NET WebForms na `/Pages/Login`
  (`__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `ctl00$MainContent$UserName/Password`).
  Úspěch = přítomnost cookie `.AspNet.ApplicationCookie`.
* Nutné doplnit cookies: `TimeZone-<hash>` = `7200000`, `acceptCookies`.
* Čtení stavu: HTML scrape `/Pages/Account/MyThermostat?ThermostatId=` +
  regex nad `HeatPump = {...}` v `/Pages/Account/MyInstallations?HeatPumpHash=`.
* Telemetrie: `GET /api/HeatPumpData/{hash}-{from_ms}-{to_ms}-0`, pole `First[]`,
  klíče `time`, `t` (venkovní), `tw` (výstupní voda), `tb` (bojler), `tt` (pokoj);
  **hodnoty jsou v desetinách °C** (dělí se 10).
* Zápis: `POST /api/HeatPumpInsertBasicSettings_v3/{basic_key}` a
  `POST /api/HeatPumpInsertThermostatSettings/{thermostat_key}`, očekává se
  **HTTP 204**; jiný kód = chyba.
* Potvrzovací protokol: po POSTu musí `LastSettingsNotConfirmed` projít cyklem
  `false → true → false`, teprve pak smí jít další zápis. Guard 900 s.
  **Tuto logiku nepředělávat, jen přenést.**

### OTE

`data/ote-YYYY-MM-DD.json`: `date`, `market`, `resolution` (`PT15M`), `currency`
(`EUR/MWh`), `source`, `fetched_at`, `period_count` (96, mimo přechod na letní čas),
`min/max/avg_price_eur_mwh`, `periods[] = {period, start, end, price_eur_mwh}`.

### Weather (Open-Meteo)

`data/weather.json`: `source`, `location`, `latitude`, `longitude`, `fetched_at`,
`current{time,temp_c,cloud_pct,precip_mm,wind_kmh,ghi_wm2,direct_wm2,diffuse_wm2}`,
`forecast_hourly[]` (totéž + `sunshine_sec`).

### GoodWe (knihovna `goodwe`, rodina ET)

Ověřené klíče: `ppv`, `ppv1`, `ppv2`, `house_consumption`, `active_power`,
`pbattery1`, `battery_soc`, `battery_soh`, `vbattery1`, `ibattery1`,
`battery_temperature`, `battery_charge_limit`, `battery_discharge_limit`,
`work_mode_label`, `grid_in_out_label`, `e_day`, `e_load_day`, `e_day_imp`, `e_day_exp`.
**Fázové hodnoty L1/L2/L3 zadání vyžaduje, ale prototyp je nevypisuje – nutno
ověřit na reálném měniči** (u ET bývají `vgrid/igrid/pgrid`, `vgrid2…`, `vgrid3…`).

### JSONL telemetrie TČ

Jeden JSON objekt na řádek: `timestamp` (lokální ISO 8601 s offsetem),
`sample_time` (UTC z TNG), teploty, `boiler_on/set/sensor/boost`,
`heating_on/set/mode`, `equit_curve`.

---

## 3. Kritické nálezy k okamžitému řešení

1. **Přihlašovací údaje v gitu.** `connect.json` obsahuje heslo k tngsmart.cz
   a všechny klíče a je součástí historie. Odstranění souboru z HEAD problém
   neřeší – hodnoty zůstanou v commitu `b024cd3`.
   → **Heslo je nutné změnit na tngsmart.cz**, teprve pak má smysl přechod na
   `.env`. Pokud je repozitář veřejný, je to blokující úkol před čímkoli dalším.
2. Chybí `.gitignore` – hrozí commit dalších tajemství a dat.
3. Logy bez rotace (kap. 21 vyžaduje rotaci).
4. Všechny cesty jsou relativní k `ROOT` skriptu; konfigurovatelné
   `data/logs/history/archive` cesty (kap. 4–5) neexistují.
5. Nula testů okolo funkční TNG logiky, přitom kap. 30 bod 6 je vyžaduje před
   jakýmkoli refaktorem.
6. Historie končí v `logs/`, ne v `history/`; archivace po 30 dnech neexistuje.

---

## 4. Cílová architektura

```text
home-energy-controller/
├── hec/
│   ├── core/
│   │   ├── config.py          # načtení + validace + backup + hot-reload
│   │   ├── secrets.py         # .env / env proměnné
│   │   ├── logging_setup.py   # strukturované logy + rotace
│   │   ├── model.py           # Sample, Reading, Status, Decision
│   │   └── scheduler.py       # asynchronní smyčka, per-reader interval
│   ├── storage/
│   │   ├── base.py            # StorageBackend (append/query/latest)
│   │   ├── jsonl.py           # JsonlStorage (výchozí)
│   │   └── archiver.py        # 30denní archivace + gzip + retry
│   ├── readers/
│   │   ├── base.py            # BaseReader: poll(), backoff, stale flag
│   │   ├── goodwe.py
│   │   ├── tng.py             # přenesená logika z tng_controller.py
│   │   ├── ote.py             # přenesený ote_reader.py
│   │   ├── weather.py
│   │   ├── shelly.py          # Plus/Gen2 + Pro 3EM
│   │   └── mqtt.py            # (fáze 5) LoRaWAN/meteostanice
│   ├── controller/
│   │   ├── controller.py      # orchestrace, safe mode
│   │   ├── rules.py           # deklarativní pravidla + reason
│   │   ├── predictor.py
│   │   └── optimizer.py
│   ├── analysis/
│   │   ├── appliances.py      # detekce cyklů spotřebičů
│   │   ├── phases.py          # L1/L2/L3 analýza
│   │   └── summaries.py       # denní bilance
│   └── web/
│       ├── api.py             # FastAPI: /api/current|history|prediction|config|status
│       └── frontend/          # PWA (Overview/History/Prediction/Settings)
├── config/  config.json, schema.json
├── data/  logs/  history/
├── tests/
├── docs/
└── tng_controller.py          # ponechán jako wrapper, dokud fáze 1 neskončí
```

### Klíčové kontrakty

```python
# readers/base.py
class BaseReader(Protocol):
    name: str                  # "goodwe" | "tng" | ...
    interval_seconds: int
    def poll(self) -> Sample:  # vyhodí výjimku, smyčku neshodí
        ...
    @property
    def last_success(self) -> datetime | None: ...
    @property
    def is_stale(self) -> bool: ...
```

```python
# storage/base.py
class StorageBackend(Protocol):
    def append(self, source: str, sample: dict) -> None: ...
    def latest(self, source: str) -> dict | None: ...
    def query(self, source: str, frm: datetime, to: datetime) -> Iterable[dict]: ...
```

Controller ani readery nesmí vědět, jestli za `StorageBackend` je JSONL nebo SQL
(kap. 28). Readery nesmí volat controller – komunikace jde přes storage + in-memory
snapshot.

### Rozhodnutí o technologiích

* **Backend:** Python 3.11+, FastAPI + Uvicorn. Důvod: běží na Pi, automatická
  OpenAPI pro `/api/*`, async se hodí ke knihovně `goodwe` (už je async).
* **Frontend:** čistý HTML/CSS/JS + Chart.js, bez build kroku. Na Pi i Androidu
  funguje okamžitě, žádný Node toolchain. PWA přes `manifest.json` + service worker.
* **Úložiště:** JSONL, gzip archiv. Žádné SQL (kap. 5).
* **Konfigurace:** `config/config.json` + `config/schema.json` (jsonschema),
  tajemství výhradně v `.env`.

---

## 5. Fáze a milníky

Odhady jsou v člověkodnech soustředěné práce, ne v kalendáři.

### Fáze 0 – Základ a bezpečnost (2–3 dny) → milník **M0**

Nutný předpoklad všeho ostatního.

- [ ] Změnit heslo k tngsmart.cz; zvážit rotaci thermostat/basic klíčů.
- [ ] `.gitignore` (`.env`, `connect.json`, `data/`, `logs/`, `history/`, `__pycache__`).
- [ ] `.env.example` + `hec/core/secrets.py`; `connect.json` se načítá s tím, že
      hodnoty `${VAR}` se dosazují z prostředí (zpětně kompatibilní).
- [ ] `requirements.txt` doplnit: `goodwe`, `fastapi`, `uvicorn`, `jsonschema`,
      `python-dotenv`, `pytest`, `aiohttp`.
- [ ] **Testy okolo funkčního TNG chování před refaktorem** (kap. 30 bod 6):
      `in_window` přes půlnoc, `scheduled_value`, celý change-gate
      (`_can_post`/`_gate_update`/`_mark_posted`) na fake odpovědích,
      parsování `HeatPump = {...}`, dělení telemetrie deseti, parsování OTE
      tabulky z uloženého HTML fixture.
- [ ] `pytest` běží zeleně; GitHub Action `python -m pytest`.

**Akceptace M0:** `pytest` zelený, v repu žádné tajemství, `tng_controller.py`
běží beze změny chování (`--once --dry-run` dá stejný výstup jako dnes).

---

### Fáze 1 – Spolehlivý sběr dat (5–8 dnů) → milník **M1**

Cíl kap. 31/fáze 1: všechny readery, JSONL historie, žádná nová automatika.

- [ ] `hec/core/config.py`: sloučená konfigurace se sekcemi `system`, `storage`,
      `polling`, `goodwe`, `tng`, `ote`, `weather`, `shelly`, `controller`;
      validace proti `schema.json`, záloha předchozí verze při zápisu.
- [ ] `hec/core/logging_setup.py`: strukturovaný formát
      `ts | level | module | event | key=value`, `RotatingFileHandler`,
      samostatný log na modul.
- [ ] `hec/storage/jsonl.py`: `history/<source>/YYYY-MM-DD.jsonl` + atomický zápis
      `data/current_<source>.json`. Stávající `logs/state-*.jsonl` se ponechá do
      doby, než ověříme migraci; migrační skript `tools/migrate_state_log.py`.
- [ ] `readers/base.py`: retry s exponenciálním backoffem, `last_success`,
      `is_stale`, izolace výjimek (kap. 22).
- [ ] `readers/tng.py`: přenést třídu `TNG` beze změny sémantiky zápisu.
      `tng_controller.py` zůstane jako tenký wrapper (kap. 30 bod 8).
- [ ] `readers/goodwe.py`: smyčka à 10 s, IP z configu, **ověřit dostupnost
      fázových veličin L1/L2/L3 na reálném měniči** a zapsat je do inventury.
- [ ] `readers/ote.py`: přenést + doplnit `price_czk_kwh` (kurz EUR/CZK z configu
      nebo z ČNB), refresh při startu, při chybějícím dni a periodicky.
- [ ] `readers/weather.py`: **napsat znovu** tak, aby produkoval dnešní formát
      `data/weather.json` 1:1; interval 15 min.
- [ ] `readers/shelly.py`: Gen2 RPC (`/rpc/Shelly.GetStatus`), podpora
      `Switch.GetStatus` (spotřebiče) i `EM.GetStatus` (Pro 3EM pro TČ),
      seznam zařízení v configu, interval 10 s. **Pouze čtení, žádné spínání.**
- [ ] `hec/core/scheduler.py`: jeden proces, per-reader interval, graceful shutdown.
- [ ] `run.py` – jednotný vstupní bod pro Windows i Linux; `start.sh` vedle `start.cmd`.

**Akceptace M1:** proces běží 48 h bez pádu, v `history/` denní JSONL od všech
pěti zdrojů, výpadek sítě u jednoho readeru neovlivní ostatní, `data/current_*.json`
odpovídá realitě, log se rotuje.

---

### Fáze 2 – API a dashboard (4–6 dnů) → milník **M2**

- [ ] `GET /api/current` – agregovaný snapshot včetně stáří dat u každého zdroje.
- [ ] `GET /api/history?source=&from=&to=&resolution=` – downsampling na serveru,
      aby mobil nestahoval 96k řádků.
- [ ] `GET /api/status` – stav readerů, poslední úspěch, safe mode, verze.
- [ ] `GET/PUT /api/config` – čtení a bezpečný zápis s validací a zálohou.
- [ ] Frontend skeleton: navigace Overview / History / Prediction / Settings,
      swipe na mobilu **i** menu (kap. 13), překladové klíče `cs` jako výchozí.
- [ ] **Overview**: schéma toku energie FVE → dům → baterie/síť/TČ s animovanými
      šipkami, živé hodnoty PV, spotřeba, TČ, SOC, síť, spot, počasí, TUV.
- [ ] Dynamické pozadí podle počasí a denní doby + přepínač animací
      `full/reduced/off` a respekt `prefers-reduced-motion` (kap. 17).
- [ ] **History**: rozsahy dnes / 24 h / 7 dnů / 30 dnů / vlastní, výběr sérií.
- [ ] **Settings**: sekce dle kap. 18, indikace „vyžaduje restart“.
- [ ] PWA manifest + service worker (offline shell).

**Akceptace M2:** na mobilu se Overview načte do 2 s a hodnoty odpovídají
`data/current_*.json`; změna intervalu v UI se projeví bez editace souborů.

---

### Fáze 3 – Analýza a archivace (4–5 dnů) → milník **M3**

- [ ] `storage/archiver.py`: po `archive_after_days` přesun do `archive_path`,
      gzip, **lokální soubor se maže až po ověření kopie**, tolerance nedostupného
      NAS, retry, log chyb (kap. 5). Windows UNC i POSIX cesty přes `pathlib`.
- [ ] `analysis/summaries.py`: denní bilance (výroba, spotřeba, import, export,
      self-consumption, náklad v CZK) do `history/summary/YYYY-MM.jsonl`.
- [ ] `analysis/appliances.py`: detekce start/stop cyklu z výkonového profilu
      Shelly (práh + hystereze + minimální délka), profil = doba, kWh, špička.
- [ ] `analysis/phases.py`: zatížení L1/L2/L3, nesymetrie, špičky,
      **textová doporučení, žádný automatický zásah** (kap. 10).
- [ ] Analýza TČ: korelace Shelly Pro 3EM (CT kleště) × stav TNG × venkovní
      teplota → odhad reálného příkonu a topného faktoru.
- [ ] Rozšíření History page o spotřebiče, fáze a denní souhrny.

**Akceptace M3:** archiv na NAS vzniká a při odpojeném NAS se nic lokálně nemaže;
detekce cyklu myčky/pračky souhlasí s ručně ověřeným záznamem.

---

### Fáze 4 – Predikce (4–6 dnů) → milník **M4**

Jednoduché a vysvětlitelné modely, žádné ML (kap. 11 a 29).

- [ ] PV: z `ghi_wm2`/`direct_wm2` předpovědi × kalibrační koeficient učený
      regresí z vlastní historie (posledních 30 dnů).
- [ ] Spotřeba: typický denní profil podle dne v týdnu, medián posledních N dnů.
- [ ] Potřeba tepla: závislost energie TČ na denním průměru venkovní teploty
      (lineární fit z vlastních dat).
- [ ] SOC baterie: simulace 24 h dopředu z PV, spotřeby a kapacity.
- [ ] Cena dne: predikovaný import/export × spotové ceny.
- [ ] Doporučená okna pro spotřebiče a TUV (nejlevnější / nejvíce přebytku).
- [ ] **Vždy s intervalem a mírou jistoty** („18–22 kWh, jistota střední“);
      žádná falešná přesnost.
- [ ] Prediction page dle kap. 16 + zpětné vyhodnocení přesnosti predikce.

**Akceptace M4:** po 14 dnech provozu je MAPE denní PV predikce < 25 % a stránka
zobrazuje rozptyl, ne jedno číslo.

---

### Fáze 5 – Řízená optimalizace (5–7 dnů) → milník **M5**

- [ ] `controller/rules.py`: pravidlo = `{enabled, priority, condition, action,
      reason, limits, manual_override}` (kap. 31/fáze 4), deklarativně v configu.
- [ ] Priorita toků z kap. 7 konfigurovatelná, žádné natvrdo zadané ekonomické
      předpoklady.
- [ ] Startovní sada pravidel:
      * přebytek PV + vysoký SOC + nízký spot → zvýšit cíl TUV v mezích;
      * drahá elektřina → snížit TUV/topení v mezích komfortu;
      * levné okno + předpověď zhoršení → mírné předtopení podlahy.
- [ ] Komfortní limity (min/max pokoj, min/max TUV, max předtopení, tichý režim)
      mají **absolutní přednost** před optimalizací.
- [ ] Zápisy do TNG výhradně přes stávající change-gate; ani jedno pravidlo
      neobchází guard 900 s a potvrzovací cyklus.
- [ ] **Safe mode** (kap. 22–23): stáří kritických dat > práh → optimalizace se
      zastaví, poslední bezpečné nastavení zůstane, příkazy se neopakují,
      v UI je varování, sběr dat pokračuje.
- [ ] Každé rozhodnutí se loguje do `history/controller/YYYY-MM-DD.jsonl`
      s lidsky čitelným zdůvodněním a v UI se zobrazuje (kap. 33).
- [ ] Metriky přínosu (kap. 34): ušetřený nákup, zvýšená self-consumption,
      posunuté spotřeby, úspora v Kč – s porovnáním proti „bez optimalizace“.

**Akceptace M5:** týden provozu bez zásahu, každé rozhodnutí má v UI vysvětlení,
žádné oscilace, komfortní meze nikdy překročeny.

---

### Následně (bez odhadu)

Automatické spínání spotřebičů, nabíjení EV, V2H, MQTT/LoRaWAN meteostanice,
Home Assistant, migrace na SQLite/Timescale, Docker.

---

## 6. Testovací strategie

* **Regresní testy před refaktorem** (fáze 0) – bez nich se do `tng_controller.py`
  nesahá.
* Unit testy: parsery (OTE HTML fixture, TNG `HeatPump` objekt, Shelly JSON),
  časová okna, change-gate, archivace na fake FS, pravidla controlleru.
* Integrační: fake HTTP server místo tngsmart.cz/OTE/Shelly; test, že výpadek
  jednoho readeru neshodí smyčku a že safe mode nastane při stale datech.
* Manuální checklist na reálném HW před každým milníkem (`--dry-run` nejdřív).
* CI: GitHub Actions, `pytest` + `ruff` na Pythonu 3.11 a 3.12.

## 7. Nasazení

* Vývoj Windows (`start.cmd`, `run.py`), produkce Raspberry Pi
  (`systemd` unit `hec.service`, `Restart=always`).
* Všechny cesty přes `pathlib.Path`, žádné natvrdo psané oddělovače.
* Dokumentace startu v `docs/DEPLOYMENT.md` (vzniká ve fázi 1).

## 8. Rizika

| Riziko | Dopad | Mitigace |
|---|---|---|
| TNG změní HTML/API | ztráta čtení i zápisu | parsery izolované, fixture testy, hlasitá chyba místo tichého selhání |
| Únik hesla z gitu | cizí přístup k TČ | změna hesla ve fázi 0, `.env` |
| GoodWe nedává fázové hodnoty | část kap. 10 nesplnitelná | ověřit hned ve fázi 1, případně doplnit druhým Shelly 3EM |
| Příliš časté zápisy do TNG | zablokování/opotřebení | zachovat change-gate a interval 900 s beze změny |
| OTE změní layout stránky | výpadek cen | fixture test + fallback na poslední známý den + upozornění v UI |
| Rozsah projektu | nedokončení | striktní pořadí fází, každý milník použitelný sám o sobě |

## 9. Otázky k rozhodnutí

1. Je repozitář veřejný? (určuje naléhavost změny hesla)
2. Kam přesně archivovat po 30 dnech – UNC cesta na NAS, nebo `/mnt/...`?
3. Jaké Shelly modely a kolik jich je (Gen1 vs Gen2 mají jiné API)?
4. Kurz EUR/CZK: pevný z configu, nebo stahovat z ČNB?
5. Distribuční tarif a poplatky – mají vstupovat do ceny za kWh, nebo stačí
   holý spot?
6. Přesný typ měniče GoodWe a zda je dostupný fázový detail L1/L2/L3.
