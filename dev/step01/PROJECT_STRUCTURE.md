# Struktura projektu a stav dokončení

Stav k `be72d1f` (srpen 2026). Procenta vyjadřují **podíl hotové funkčnosti vůči
cílovému produktu**, ne rozpracovanost souboru. Funkční prototyp, který ale
nemá konfiguraci, retry a ukládání do historie, není 100 %.

## Legenda

| Značka | Rozsah | Význam |
|---|---|---|
| ✅ | 100 % | hotovo a ověřeno v provozu |
| 🟢 | 70–99 % | funkční, chybí detaily nebo zapouzdření |
| 🟡 | 30–69 % | funguje částečně, chybí podstatné části |
| 🟠 | 1–29 % | prototyp nebo náčrt |
| ⬜ | 0 % | neexistuje |

---

## 1. Kořen repozitáře – funkční prototypy (zmrazené)

Tyto soubory běží v provozu. **Nemění se**, dokud jejich funkce není přenesena
do `dev/hec/`, pokryta testy a ověřena na reálném hardwaru.

```text
Home-Energy-Controller/
├── tng_controller.py ................................... 🟢 70 %
├── ote_reader.py ....................................... 🟢 70 %
├── weather_reader.py ................................... 🟡 55 %
├── goodwe-read.py ...................................... 🟠 15 %
├── config.json ......................................... 🟡 30 %
├── connect.json ........................................ 🟠 20 %  ⚠ tajemství v gitu
├── requirements.txt .................................... 🟠 25 %
├── start.cmd / test.cmd / ote-test.cmd ................. 🟡 40 %  jen Windows
├── README.md ........................................... 🟠 10 %  zastaralý
├── HOME_ENERGY_CONTROLLER_DEVELOPMENT_PROMPT.md ........ ✅ 100 % zadání
├── data/ ............................................... 🟡 50 %
│   ├── ote-YYYY-MM-DD.json ............................. ✅ 100 %
│   ├── weather.json .................................... 🟢 80 %
│   └── runtime_state.json .............................. ✅ 100 %
└── logs/ ............................................... 🟡 40 %
    ├── state-YYYY-MM-DD.jsonl .......................... 🟢 80 %  patří do history/
    ├── actions.txt ..................................... 🟡 60 %  bez rotace
    └── errors.txt ...................................... 🟡 60 %  bez rotace
```

### Detail

| Soubor | % | Co funguje | Co chybí do cíle |
|---|---|---|---|
| `tng_controller.py` | 70 | login, čtení stavu z HTML, telemetrie, zápis basic/thermostat settings, change-gate s potvrzovacím cyklem, rozvrhy, denní JSONL | konfigurace cest, tajemství z `.env`, retry/backoff, stale-detekce, i18n hlášek, napojení na společný storage a API, testy |
| `ote_reader.py` | 70 | scrape 15min cen, atomický zápis, CLI `--date/--watch`, tolerance chybějícího D+1 | CZK/kWh, distribuční složka, historie v JSONL, backoff, sdílený logger, testy |
| `weather_reader.py` | 55 | Open-Meteo, aktuální stav + hodinová předpověď 3 dny, `status: ok/error`, jen stdlib | souřadnice z configu, východ/západ slunce, kód počasí pro ikonu a pozadí, horizont 72 h, retry, historie, testy |
| `goodwe-read.py` | 15 | jednorázové připojení k měniči ET, výpis známých veličin | smyčka, IP z configu, ukládání, fáze L1/L2/L3, reconnect, testy; knihovna `goodwe` chybí v `requirements.txt` |
| `config.json` | 30 | runtime, logging, rozvrhy, šablony TNG payloadů | sekce ostatních zdrojů, `storage`, `ui`, `controller`, JSON schéma, verzování a migrace |
| `connect.json` | 20 | funkční přístupové údaje k TNG | **přesun tajemství do `.env`**, podpora více instalací |
| `start.cmd`/`test.cmd` | 40 | spuštění na Windows | ekvivalent pro Linux, systemd unit |
| `README.md` | 10 | základní příkazy TNG controlleru | popis produktu, instalace, konfigurace, EN verze |

---

## 2. Vývojový adresář `dev/` – plány

```text
dev/
├── README.md ........................................... ✅ 100 %  index kroků
└── step01/ ............................................. ✅ 100 %
    ├── DEVELOPMENT_PLAN.md ............................. ✅ 100 %
    ├── PROJECT_STRUCTURE.md ............................ ✅ 100 %  (tento soubor)
    ├── UI_DESIGN.md .................................... ✅ 100 %
    └── I18N.md ......................................... ✅ 100 %
```

---

## 3. Cílový produkt `dev/hec/` – co teprve vznikne

Vzniká od kroku 02. Procenta ukazují, kolik z dané části už existuje v prototypech
kořene (a dá se přenést), ne kolik je napsáno tady.

```text
dev/hec/
├── run.py .............................................. ⬜ 0 %   jednotný vstupní bod
├── core/
│   ├── config.py ....................................... ⬜ 0 %   načtení, validace, záloha, hot-reload
│   ├── schema.py ....................................... ⬜ 0 %   JSON schéma konfigurace
│   ├── secrets.py ...................................... ⬜ 0 %   .env / proměnné prostředí
│   ├── logging_setup.py ................................ 🟠 25 %  logger existuje, chybí rotace a struktura
│   ├── model.py ........................................ ⬜ 0 %   Sample, Reading, Status, Decision
│   ├── scheduler.py .................................... 🟠 15 %  smyčka existuje jen uvnitř TNG controlleru
│   └── i18n.py ......................................... ⬜ 0 %   překladové klíče pro backend
├── storage/
│   ├── base.py ......................................... ⬜ 0 %   StorageBackend
│   ├── jsonl.py ........................................ 🟠 25 %  denní JSONL handler existuje
│   └── archiver.py ..................................... ⬜ 0 %   30 dnů, gzip, NAS, retry
├── readers/
│   ├── base.py ......................................... ⬜ 0 %   retry, backoff, stale
│   ├── tng.py .......................................... 🟢 70 %  přenos z tng_controller.py
│   ├── ote.py .......................................... 🟢 70 %  přenos z ote_reader.py
│   ├── weather.py ...................................... 🟡 55 %  přenos z weather_reader.py
│   ├── goodwe.py ....................................... 🟠 15 %  přenos z goodwe-read.py
│   ├── shelly.py ....................................... ⬜ 0 %   Gen2 RPC, spotřebiče + Pro 3EM
│   └── mqtt.py ......................................... ⬜ 0 %   LoRaWAN / meteostanice (později)
├── controller/
│   ├── controller.py ................................... 🟠 20 %  rozvrhová logika existuje pro TNG
│   ├── rules.py ........................................ ⬜ 0 %   deklarativní pravidla s reason_key
│   ├── safe_mode.py .................................... ⬜ 0 %
│   ├── predictor.py .................................... ⬜ 0 %
│   └── optimizer.py .................................... ⬜ 0 %
├── analysis/
│   ├── appliances.py ................................... ⬜ 0 %   detekce cyklů spotřebičů
│   ├── phases.py ....................................... ⬜ 0 %   L1/L2/L3, nesymetrie
│   ├── heatpump.py ..................................... ⬜ 0 %   příkon vs. stav TNG vs. počasí
│   └── summaries.py .................................... ⬜ 0 %   denní bilance
├── web/
│   ├── api.py .......................................... ⬜ 0 %   /api/current|history|prediction|config|status|i18n
│   └── frontend/
│       ├── index.html .................................. ⬜ 0 %
│       ├── css/tokens.css .............................. ⬜ 0 %   design tokeny (UI_DESIGN.md)
│       ├── js/pages/overview.js ........................ ⬜ 0 %   tok energie
│       ├── js/pages/history.js ......................... ⬜ 0 %   grafy
│       ├── js/pages/prediction.js ...................... ⬜ 0 %
│       ├── js/pages/settings.js ........................ ⬜ 0 %
│       ├── js/background.js ............................ ⬜ 0 %   dynamické pozadí podle počasí
│       ├── js/i18n.js .................................. ⬜ 0 %
│       ├── manifest.json ............................... ⬜ 0 %   PWA
│       └── sw.js ....................................... ⬜ 0 %   service worker
├── locales/
│   ├── cs.json ......................................... ⬜ 0 %
│   └── en.json ......................................... ⬜ 0 %
├── config/
│   ├── config.example.json ............................. ⬜ 0 %
│   └── schema.json ..................................... ⬜ 0 %
├── tools/
│   └── migrate_state_log.py ............................ ⬜ 0 %   logs/state-*.jsonl → history/
├── tests/ .............................................. ⬜ 0 %   regresní testy TNG, parsery, pravidla
└── docs/
    ├── DEPLOYMENT.md ................................... ⬜ 0 %
    ├── API.md .......................................... ⬜ 0 %
    └── CHANGELOG.md .................................... ⬜ 0 %
```

Mimo balík:

```text
.gitignore .............................................. ⬜ 0 %   ⚠ chybí
.env.example ............................................ ⬜ 0 %
CLAUDE.md ............................................... ✅ 100 %  pravidla pro práci v repu
.github/workflows/ci.yml ................................ ⬜ 0 %
install.sh / install.ps1 ................................ ⬜ 0 %
```

---

## 4. Celkové dokončení

Váha = odhadovaný podíl na celkové práci. Dokončení = vážený průměr.

| Oblast | Váha | Dokončeno | Příspěvek |
|---|---:|---:|---:|
| Reader TNG | 8 % | 70 % | 5,6 |
| Reader GoodWe | 6 % | 15 % | 0,9 |
| Reader OTE | 4 % | 65 % | 2,6 |
| Reader Weather | 4 % | 55 % | 2,2 |
| Reader Shelly | 6 % | 0 % | 0,0 |
| Jádro (config, secrets, logging, scheduler, i18n) | 10 % | 12 % | 1,2 |
| Úložiště a archivace | 7 % | 20 % | 1,4 |
| Controller a pravidla | 10 % | 15 % | 1,5 |
| Analýza | 8 % | 0 % | 0,0 |
| Predikce | 8 % | 0 % | 0,0 |
| Web API | 6 % | 0 % | 0,0 |
| Frontend, PWA, jazykové mutace | 15 % | 0 % | 0,0 |
| Testy a CI | 4 % | 0 % | 0,0 |
| Produktizace a dokumentace | 4 % | 15 % | 0,6 |
| **Celkem** | **100 %** | | **≈ 16 %** |

### Podle fází plánu

| Fáze | Milník | Dokončeno |
|---|---|---:|
| 0 – Základ a bezpečnost | M0 | 0 % |
| 1 – Spolehlivý sběr dat | M1 | 40 % |
| 2 – API, dashboard, jazyky | M2 | 0 % |
| 3 – Analýza a archivace | M3 | 0 % |
| 4 – Predikce | M4 | 0 % |
| 5 – Řízená optimalizace | M5 | 5 % |
| 6 – Produktizace | M6 | 5 % |

---

## 5. Kritické mezery

| # | Mezera | Dopad | Řeší |
|---|---|---|---|
| 1 | Heslo a klíče k TNG v git historii | bezpečnost, blokuje nabídku zákazníkovi | fáze 0 |
| 2 | Chybí `.gitignore` | další úniky, commit provozních dat | fáze 0 |
| 3 | Nula testů okolo funkční TNG logiky | refaktor je hazard | fáze 0 |
| 4 | Chybí Shelly reader | bez něj není měření spotřebičů ani TČ | fáze 1 |
| 5 | GoodWe jen prototyp | bez něj není FVE, baterie ani fáze | fáze 1 |
| 6 | Žádné UI ani API | systém není použitelný pro uživatele | fáze 2 |
| 7 | Texty natvrdo česky | blokuje EN mutaci a prodej mimo ČR | fáze 2 |
| 8 | Logy bez rotace, historie mimo `history/` | provozní riziko na Pi (zaplnění SD karty) | fáze 1 a 3 |
