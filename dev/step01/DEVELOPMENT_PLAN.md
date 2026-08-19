# Krok 01 – plán vývoje Home Energy Controller

Dokument vychází z `HOME_ENERGY_CONTROLLER_DEVELOPMENT_PROMPT.md` a z inventury
repozitáře (stav: `be72d1f`, srpen 2026).

**Produktový cíl:** profesionální, nabídkyschopné řešení – ne jen skript pro jednu
domácnost. Z toho plynou tři požadavky nad rámec původního zadání:

1. **Jazykové mutace CZ + EN** od začátku, architektura připravená na další jazyky
   (viz [`I18N.md`](I18N.md)) – žádné natvrdo psané texty, ani v hláškách controlleru.
2. **Rozšiřitelnost** – nová zařízení a zdroje se přidávají jako plugin (reader),
   bez zásahu do controlleru; konfigurace bez editace kódu.
3. **Nasaditelnost u zákazníka** – instalace bez ručního skládání souborů,
   oddělená konfigurace instalace od kódu, white-label vzhled, licenční čistota
   všech použitých fontů, ikon a knihoven.

**Řídící pravidlo (kap. 30 a 35 zadání):** stávající funkční kód se nepřepisuje,
ale postupně zapouzdřuje. Každá fáze končí stavem, kdy systém běží a sbírá data.

---

## 1. Inventura repozitáře

| Soubor | Stav | Hodnocení |
|---|---|---|
| `tng_controller.py` (464 ř.) | **funkční, produkčně používaný** | Nejcennější část repa. Login na tngsmart.cz, čtení stavu, telemetrie, zápis nastavení včetně potvrzovacího protokolu. Chránit testy před jakýmkoli zásahem. |
| `ote_reader.py` (170 ř.) | **funkční** | Scrape 15min day-ahead cen z OTE, atomický zápis `data/ote-YYYY-MM-DD.json`. Chybí přepočet na CZK/kWh a JSONL historie. |
| `weather_reader.py` (119 ř.) | **funkční** | Open-Meteo, jen standardní knihovna, `status: ok/error` v výstupu. Pevné souřadnice, 3 dny, bez historie a bez retry. |
| `goodwe-read.py` (60 ř.) | **prototyp** | Jednorázový výpis přes knihovnu `goodwe` (rodina ET, IP 192.168.2.116). Není smyčka, není ukládání, IP natvrdo, knihovna chybí v `requirements.txt`. |
| `connect.json` | **funkční, ale bezpečnostní problém** | Heslo, thermostat_key, basic_key, heatpump_hash v plaintextu **a verzované v gitu**. |
| `config.json` | funkční | Runtime, logging, rozvrhy bojleru/topení/termostatu, šablony TNG payloadů. Zatím jen TNG doména. |
| `data/weather.json` | funkční | Výstup `weather_reader.py`: `current` + `forecast_hourly` (temp, cloud, precip, wind, GHI/direct/diffuse, sunshine). |
| `logs/state-2026-08-18.jsonl` | funkční | Denní JSONL telemetrie TČ – přesně formát, který zadání chce. |
| `logs/actions.txt`, `logs/errors.txt` | funkční | Bez rotace, rostou neomezeně. |
| `data/runtime_state.json` | funkční | Perzistence change-gate a kurzoru telemetrie. |
| `start.cmd`, `test.cmd`, `ote-test.cmd` | funkční | Pouze Windows (`py`). Linux ekvivalent chybí. |
| `README.md` | zastaralý | Popisuje jen TNG controller, tvrdí interval 60 s (config má 300 s). |
| chybí | – | `.gitignore`, `.env.example`, testy, Shelly reader, web UI, API, i18n, archivace, `history/`. |

Podrobný rozpad se stavem dokončení každého souboru: [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md).

**Souhrn:** fáze 1 zadání (monitoring) je hotová zhruba ze 40 % – TNG, OTE a
weather čtou spolehlivě, GoodWe je prototyp, Shelly a dashboard neexistují.

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
`status`, `current{time,temp_c,cloud_pct,precip_mm,wind_kmh,ghi_wm2,direct_wm2,diffuse_wm2}`,
`forecast_hourly[]` (totéž + `sunshine_sec`).
Chybí pro potřeby produktu: východ/západ slunce, denní agregace, delší horizont
(pro predikci je potřeba alespoň 48–72 h), kód počasí pro volbu ikony a pozadí.

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
   `.env`. U komerčního produktu je to navíc blokující bod jakéhokoli auditu.
2. Chybí `.gitignore` – hrozí commit dalších tajemství a provozních dat.
3. Logy bez rotace (kap. 21 vyžaduje rotaci).
4. Všechny cesty jsou relativní k `ROOT` skriptu; konfigurovatelné
   `data/logs/history/archive` cesty (kap. 4–5) neexistují.
5. Nula testů okolo funkční TNG logiky, přitom kap. 30 bod 6 je vyžaduje před
   jakýmkoli refaktorem.
6. Historie končí v `logs/`, ne v `history/`; archivace po 30 dnech neexistuje.
7. Texty jsou natvrdo česky v kódu i v logu – blokuje anglickou mutaci.

---

## 4. Cílová architektura

Kompletní strom se stavem dokončení je v [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md);
zde jen princip.

```text
dev/
├── stepNN/          # plány a rozhodnutí jednotlivých etap
└── hec/             # samotný produkt (vzniká v kroku 02)
    ├── core/        # config, secrets, logging, model, scheduler, i18n
    ├── storage/     # StorageBackend → JsonlStorage, archiver
    ├── readers/     # goodwe, tng, ote, weather, shelly, mqtt
    ├── controller/  # controller, rules, predictor, optimizer
    ├── analysis/    # appliances, phases, summaries
    └── web/         # FastAPI + PWA frontend
```

### Klíčové kontrakty

```python
# readers/base.py
class BaseReader(Protocol):
    name: str                  # "goodwe" | "tng" | ...
    interval_seconds: int
    def poll(self) -> Sample:  # smí vyhodit výjimku, smyčku neshodí
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
(kap. 28). Readery nesmí volat controller – komunikace jde přes storage
a in-memory snapshot. Nový reader = nový soubor + záznam v configu, **nic víc**.

### Rozhodnutí o technologiích

| Oblast | Volba | Důvod |
|---|---|---|
| Backend | Python 3.11+, FastAPI + Uvicorn | běží na Pi, automatická OpenAPI pro `/api/*`, async sedí ke knihovně `goodwe` |
| Frontend | HTML/CSS/JS bez build kroku + Chart.js | na Pi i Androidu funguje okamžitě, žádný Node toolchain u zákazníka |
| PWA | `manifest.json` + service worker | instalovatelné na Androidu bez obchodu |
| Úložiště | JSONL + gzip archiv | kap. 5, migrace na SQL zůstává otevřená |
| Konfigurace | `config/config.json` + `schema.json` (jsonschema) | validace před zápisem, editovatelné z UI |
| Tajemství | výhradně `.env` / proměnné prostředí | kap. 20 |
| i18n | JSON katalogy `cs`/`en`, klíčované texty | viz [`I18N.md`](I18N.md) |
| Licence | vlastní kód + knihovny MIT/BSD/Apache, fonty OFL | nutné pro komerční nabídku |

---

## 5. Fáze a milníky

Odhady jsou v člověkodnech soustředěné práce, ne v kalendáři.
Každé fázi bude odpovídat jeden krok v `dev/stepNN/`.

### Fáze 0 – Základ a bezpečnost (2–3 dny) → milník **M0** → `step02`

- [ ] Změnit heslo k tngsmart.cz; zvážit rotaci thermostat/basic klíčů.
- [ ] `.gitignore` (`.env`, `connect.json`, `data/`, `logs/`, `history/`, `__pycache__`).
- [ ] `.env.example` + `hec/core/secrets.py`; `connect.json` se načítá s dosazením
      `${VAR}` z prostředí (zpětně kompatibilní se stávajícím souborem).
- [ ] `requirements.txt`: `goodwe`, `fastapi`, `uvicorn`, `jsonschema`,
      `python-dotenv`, `pytest`, `httpx`.
- [ ] **Regresní testy funkčního chování před refaktorem** (kap. 30 bod 6):
      `in_window` přes půlnoc, `scheduled_value`, celý change-gate
      (`_can_post`/`_gate_update`/`_mark_posted`), parsování `HeatPump = {...}`,
      dělení telemetrie deseti, parsování OTE tabulky z uloženého HTML fixture,
      mapování Open-Meteo odpovědi na `weather.json`.
- [ ] GitHub Action: `pytest` + `ruff` na Pythonu 3.11 a 3.12.
- [ ] Skeleton balíku `hec/` (prázdné moduly + `__init__.py`).

**Akceptace M0:** `pytest` zelený, v repu žádné tajemství, `tng_controller.py`
běží beze změny chování (`--once --dry-run` dá stejný výstup jako dnes).

---

### Fáze 1 – Spolehlivý sběr dat (5–8 dnů) → milník **M1** → `step03`

- [ ] `core/config.py`: sekce `system`, `storage`, `polling`, `goodwe`, `tng`,
      `ote`, `weather`, `shelly`, `controller`, `ui`; validace proti `schema.json`,
      záloha předchozí verze při zápisu.
- [ ] `core/logging_setup.py`: formát `ts | level | module | event | key=value`,
      `RotatingFileHandler`, samostatný log na modul, **žádné tajemství v logu**.
- [ ] `storage/jsonl.py`: `history/<source>/YYYY-MM-DD.jsonl` + atomický zápis
      `data/current_<source>.json`; migrační skript `tools/migrate_state_log.py`.
- [ ] `readers/base.py`: retry s exponenciálním backoffem, `last_success`,
      `is_stale`, izolace výjimek (kap. 22).
- [ ] `readers/tng.py`: přenést třídu `TNG` beze změny sémantiky zápisu;
      `tng_controller.py` zůstane jako tenký wrapper (kap. 30 bod 8).
- [ ] `readers/goodwe.py`: smyčka à 10 s, IP z configu, **ověřit dostupnost
      fázových veličin L1/L2/L3 na reálném měniči** a zapsat do inventury.
- [ ] `readers/ote.py`: přenést + `price_czk_kwh` (kurz z configu nebo z ČNB),
      refresh při startu, při chybějícím dni a periodicky.
- [ ] `readers/weather.py`: přenést, doplnit konfigurovatelné souřadnice,
      východ/západ slunce, kód počasí (pro ikonu a pozadí), horizont 72 h,
      retry, zápis do historie.
- [ ] `readers/shelly.py`: Gen2 RPC (`/rpc/Shelly.GetStatus`), `Switch.GetStatus`
      (spotřebiče) i `EM.GetStatus` (Pro 3EM pro TČ), seznam zařízení v configu,
      interval 10 s. **Pouze čtení, žádné spínání.**
- [ ] `core/scheduler.py`: jeden proces, per-reader interval, graceful shutdown.
- [ ] `run.py` – jednotný vstupní bod pro Windows i Linux; `start.sh` vedle `start.cmd`.

**Akceptace M1:** proces běží 48 h bez pádu, v `history/` denní JSONL od všech
pěti zdrojů, výpadek jednoho readeru neovlivní ostatní, `data/current_*.json`
odpovídá realitě, log se rotuje.

---

### Fáze 2 – API, dashboard a jazykové mutace (6–8 dnů) → milník **M2** → `step04`

- [ ] `GET /api/current` – snapshot včetně stáří dat u každého zdroje.
- [ ] `GET /api/history?source=&from=&to=&resolution=` – downsampling na serveru.
- [ ] `GET /api/status` – stav readerů, poslední úspěch, safe mode, verze.
- [ ] `GET/PUT /api/config` – čtení a bezpečný zápis s validací a zálohou.
- [ ] `GET /api/i18n/{lang}` – katalog textů; `Accept-Language` fallback.
- [ ] Frontend podle [`UI_DESIGN.md`](UI_DESIGN.md): navigace Overview / History /
      Prediction / Settings, swipe na mobilu **i** menu (kap. 13).
- [ ] **Overview**: schéma toku energie FVE → dům → baterie/síť/TČ s animovanými
      šipkami, živé hodnoty PV, spotřeba, TČ, SOC, síť, spot, počasí, TUV.
- [ ] Dynamické pozadí podle počasí a denní doby + přepínač animací
      `full/reduced/off` a respekt `prefers-reduced-motion` (kap. 17).
- [ ] **History**: rozsahy dnes / 24 h / 7 dnů / 30 dnů / vlastní, výběr sérií.
- [ ] **Settings**: sekce dle kap. 18, indikace „vyžaduje restart“, přepínač jazyka.
- [ ] Kompletní katalogy `cs.json` a `en.json`, **nula natvrdo psaných textů**.
- [ ] PWA manifest + service worker (offline shell).

**Akceptace M2:** na mobilu se Overview načte do 2 s a hodnoty odpovídají
`data/current_*.json`; přepnutí CZ↔EN přeloží celé UI včetně jednotek a formátů
data; změna intervalu v UI se projeví bez editace souborů.

---

### Fáze 3 – Analýza a archivace (4–5 dnů) → milník **M3** → `step05`

- [ ] `storage/archiver.py`: po `archive_after_days` přesun do `archive_path`,
      gzip, **lokální soubor se maže až po ověření kopie**, tolerance nedostupného
      NAS, retry, log chyb (kap. 5). Windows UNC i POSIX cesty přes `pathlib`.
- [ ] `analysis/summaries.py`: denní bilance (výroba, spotřeba, import, export,
      self-consumption, náklad) do `history/summary/YYYY-MM.jsonl`.
- [ ] `analysis/appliances.py`: detekce start/stop cyklu z výkonového profilu
      Shelly (práh + hystereze + minimální délka), profil = doba, kWh, špička.
- [ ] `analysis/phases.py`: zatížení L1/L2/L3, nesymetrie, špičky,
      **textová doporučení, žádný automatický zásah** (kap. 10).
- [ ] Analýza TČ: korelace Shelly Pro 3EM (CT kleště) × stav TNG × venkovní
      teplota → odhad reálného příkonu a topného faktoru.
- [ ] Rozšíření History o spotřebiče, fáze a denní souhrny.

**Akceptace M3:** archiv na NAS vzniká a při odpojeném NAS se nic lokálně nemaže;
detekce cyklu myčky/pračky souhlasí s ručně ověřeným záznamem.

---

### Fáze 4 – Predikce (4–6 dnů) → milník **M4** → `step06`

Jednoduché a vysvětlitelné modely, žádné ML (kap. 11 a 29).

- [ ] PV: z `ghi_wm2`/`direct_wm2` × kalibrační koeficient učený regresí z vlastní
      historie (30 dnů).
- [ ] Spotřeba: typický denní profil podle dne v týdnu, medián posledních N dnů.
- [ ] Potřeba tepla: závislost energie TČ na denním průměru venkovní teploty.
- [ ] SOC baterie: simulace 24 h dopředu z PV, spotřeby a kapacity.
- [ ] Cena dne: predikovaný import/export × spotové ceny.
- [ ] Doporučená okna pro spotřebiče a TUV (nejlevnější / největší přebytek).
- [ ] **Vždy s intervalem a mírou jistoty** („18–22 kWh, jistota střední“).
- [ ] Prediction page dle kap. 16 + zpětné vyhodnocení přesnosti predikce.

**Akceptace M4:** po 14 dnech provozu je MAPE denní PV predikce < 25 % a stránka
zobrazuje rozptyl, ne jedno číslo.

---

### Fáze 5 – Řízená optimalizace (5–7 dnů) → milník **M5** → `step07`

- [ ] `controller/rules.py`: pravidlo = `{enabled, priority, condition, action,
      reason_key, limits, manual_override}` (kap. 31/fáze 4), deklarativně v configu.
      `reason_key` je **překladový klíč**, ne hotová věta – kvůli EN mutaci.
- [ ] Priorita toků z kap. 7 konfigurovatelná, žádné natvrdo zadané ekonomické
      předpoklady.
- [ ] Startovní sada pravidel:
      * přebytek PV + vysoký SOC + nízký spot → zvýšit cíl TUV v mezích;
      * drahá elektřina → snížit TUV/topení v mezích komfortu;
      * levné okno + předpověď zhoršení → mírné předtopení podlahy.
- [ ] Komfortní limity (min/max pokoj, min/max TUV, max předtopení, tichý režim)
      mají **absolutní přednost** před optimalizací.
- [ ] Zápisy do TNG výhradně přes stávající change-gate; žádné pravidlo neobchází
      guard 900 s ani potvrzovací cyklus.
- [ ] **Safe mode** (kap. 22–23): stáří kritických dat > práh → optimalizace se
      zastaví, poslední bezpečné nastavení zůstane, příkazy se neopakují,
      v UI je varování, sběr dat pokračuje.
- [ ] Každé rozhodnutí do `history/controller/YYYY-MM-DD.jsonl` s vysvětlením
      a zobrazení v UI (kap. 33).
- [ ] Metriky přínosu (kap. 34): ušetřený nákup, self-consumption, posunuté
      spotřeby, úspora v Kč – proti scénáři „bez optimalizace“.

**Akceptace M5:** týden provozu bez zásahu, každé rozhodnutí má v UI vysvětlení,
žádné oscilace, komfortní meze nikdy překročeny.

---

### Fáze 6 – Produktizace (4–6 dnů) → milník **M6** → `step08`

Fáze navíc oproti původnímu zadání; plyne z cíle „nabízet jako řešení“.

- [ ] Instalátor: `install.sh` (systemd unit, uživatel, práva) a `install.ps1`.
- [ ] Průvodce prvním spuštěním v UI – zadání lokality, zařízení, jednotek, jazyka.
- [ ] Oddělení kódu od instalace: veškerá konfigurace mimo balík, upgrade bez
      ztráty nastavení; verzování schématu configu a migrace.
- [ ] White-label: název, logo a barevný akcent z konfigurace (viz `UI_DESIGN.md`).
- [ ] Ochrana přístupu: přihlášení do UI, HTTPS/reverse proxy, doporučené
      síťové zapojení (systém nikdy nevystavovat přímo do internetu).
- [ ] Diagnostický export pro podporu (logy + config **bez tajemství**).
- [ ] Uživatelská dokumentace CZ + EN, `CHANGELOG.md`, licenční přehled závislostí.

**Akceptace M6:** čistá instalace na Raspberry Pi z nuly podle dokumentace do
30 minut bez zásahu do kódu.

---

### Následně (bez odhadu)

Automatické spínání spotřebičů, nabíjení EV, V2H, MQTT/LoRaWAN meteostanice,
Home Assistant, migrace na SQLite/Timescale, více instalací pod jednou správou,
Docker.

---

## 6. Testovací strategie

* **Regresní testy před refaktorem** (fáze 0) – bez nich se do `tng_controller.py`
  nesahá.
* Unit testy: parsery (OTE HTML fixture, TNG `HeatPump` objekt, Open-Meteo,
  Shelly JSON), časová okna, change-gate, archivace na fake FS, pravidla controlleru.
* Integrační: fake HTTP server místo tngsmart.cz/OTE/Shelly; test, že výpadek
  jednoho readeru neshodí smyčku a že safe mode nastane při stale datech.
* i18n test: každý klíč použitý v kódu existuje v `cs.json` i `en.json` a naopak.
* Manuální checklist na reálném HW před každým milníkem (`--dry-run` nejdřív).

## 7. Nasazení

* Vývoj Windows (`start.cmd`, `run.py`), produkce Raspberry Pi
  (`systemd` unit `hec.service`, `Restart=always`).
* Všechny cesty přes `pathlib.Path`, žádné natvrdo psané oddělovače.
* Dokumentace startu v `dev/hec/docs/DEPLOYMENT.md` (vzniká ve fázi 1).

## 8. Rizika

| Riziko | Dopad | Mitigace |
|---|---|---|
| TNG změní HTML/API | ztráta čtení i zápisu | parsery izolované, fixture testy, hlasitá chyba místo tichého selhání |
| Únik hesla z gitu | cizí přístup k TČ | změna hesla ve fázi 0, `.env` |
| GoodWe nedává fázové hodnoty | část kap. 10 nesplnitelná | ověřit hned ve fázi 1, případně druhý Shelly 3EM |
| Příliš časté zápisy do TNG | zablokování/opotřebení | zachovat change-gate a interval 900 s beze změny |
| OTE změní layout stránky | výpadek cen | fixture test + fallback na poslední známý den + upozornění v UI |
| Nedokumentovaný zásah do TNG u zákazníka | odpovědnost za škodu | výchozí stav = jen čtení, zápis se zapíná vědomě, vše logováno |
| Rozsah projektu | nedokončení | striktní pořadí fází, každý milník použitelný sám o sobě |

## 9. Otázky k rozhodnutí

1. Je repozitář veřejný? (určuje naléhavost změny hesla)
2. Kam přesně archivovat po 30 dnech – UNC cesta na NAS, nebo `/mnt/...`?
3. Jaké Shelly modely a kolik jich je (Gen1 vs Gen2 mají jiné API)?
4. Kurz EUR/CZK: pevný z configu, nebo stahovat z ČNB?
5. Distribuční tarif a poplatky – mají vstupovat do ceny za kWh, nebo stačí spot?
6. Přesný typ měniče GoodWe a zda je dostupný fázový detail L1/L2/L3.
7. Produkt: nabízí se jako **hotové zařízení s instalací**, nebo jako software
   k vlastnímu nasazení? (ovlivní fázi 6 – instalátor, aktualizace, podpora)
