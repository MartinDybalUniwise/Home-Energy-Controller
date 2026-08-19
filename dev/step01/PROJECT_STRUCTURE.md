# Struktura projektu a stav dokončení

Aktualizováno po kroku 08. Procenta vyjadřují **podíl hotové funkčnosti vůči
cílovému produktu**, ne rozpracovanost souboru. Kód, který je napsaný a pokrytý
testy, ale nikdy neběžel proti reálnému zařízení, není 100 %.

## Legenda

| Značka | Rozsah | Význam |
|---|---|---|
| ✅ | 100 % | hotovo a ověřeno v provozu |
| 🟢 | 70–99 % | funkční a otestované, chybí ověření na reálném hardwaru nebo detail |
| 🟡 | 30–69 % | funguje částečně, chybí podstatné části |
| 🟠 | 1–29 % | prototyp nebo náčrt |
| ⬜ | 0 % | neexistuje |

---

## 1. Kořen repozitáře

```text
Home-Energy-Controller/
├── tng_controller.py ................................... 🟢 70 %  prototyp v provozu, ZMRAZENÝ
├── ote_reader.py ....................................... 🟢 70 %  prototyp v provozu, ZMRAZENÝ
├── weather_reader.py ................................... 🟡 55 %  prototyp v provozu, ZMRAZENÝ
├── goodwe-read.py ...................................... 🟠 15 %  prototyp, ZMRAZENÝ
├── config.json / connect.json .......................... 🟡 30 %  vstup pro prototypy
├── connect.example.json ................................ ✅ 100 % vzor s ${PROMENNE}
├── .env.example ........................................ ✅ 100 %
├── .gitignore .......................................... ✅ 100 %
├── requirements.txt / requirements-dev.txt ............. ✅ 100 %
├── pyproject.toml ...................................... ✅ 100 % pytest + ruff
├── CLAUDE.md ........................................... ✅ 100 %
├── README.md ........................................... ✅ 100 %
├── CHANGELOG.md ........................................ ✅ 100 %
├── .github/workflows/ci.yml ............................ 🟢 90 %  ruff + pytest, 3.11 a 3.12
└── HOME_ENERGY_CONTROLLER_DEVELOPMENT_PROMPT.md ........ ✅ 100 % zadání
```

Funkce prototypů je přenesena do `dev/hec/` a pokryta testy. **Odstranit je lze
teprve po ověření nové verze na reálném hardwaru** (pravidlo 1 v `CLAUDE.md`).

---

## 2. Plány vývoje

```text
dev/
├── README.md ........................................... ✅ 100 %  index kroků
├── step01/  analýza, plán, struktura, UI, i18n ......... ✅ 100 %
├── step02/  bezpečnostní základ a jádro (M0) ........... ✅ 100 %
├── step03/  úložiště, readery, plánovač (M1) ........... ✅ 100 %
├── step04/  API, rozhraní, jazyky (M2) ................. ✅ 100 %
├── step05/  analýza a archivace (M3) ................... ✅ 100 %
├── step06/  predikce (M4) .............................. ✅ 100 %
├── step07/  řízená optimalizace (M5) ................... ✅ 100 %
└── step08/  produktizace (M6) .......................... ✅ 100 %
```

---

## 3. Produkt `dev/hec/`

```text
dev/
├── run.py .............................................. ✅ 100 %  spouštěč
└── hec/
    ├── __main__.py ..................................... ✅ 100 %  --once --status --init --diagnostics
    ├── core/
    │   ├── config.py ................................... 🟢 95 %  validace, záloha, atomický zápis
    │   ├── schema.py ................................... 🟢 95 %  83 polí s typem a rozsahem
    │   ├── secrets.py .................................. ✅ 100 % .env, ${VAR}, maskování
    │   ├── logging_setup.py ............................ ✅ 100 % rotace + filtr tajemství
    │   ├── model.py .................................... ✅ 100 % Sample, ReaderStatus, Decision
    │   ├── timeutil.py ................................. ✅ 100 %
    │   ├── i18n.py ..................................... ✅ 100 %
    │   ├── scheduler.py ................................ 🟢 95 %  vlákno na reader
    │   ├── maintenance.py .............................. 🟢 90 %  bilance, cykly, predikce, archiv
    │   └── app.py ...................................... 🟢 95 %  propojení a snapshot
    ├── storage/
    │   ├── base.py ..................................... ✅ 100 % StorageBackend, atomický zápis
    │   ├── jsonl.py .................................... 🟢 95 %  denní soubory, dotazy
    │   ├── series.py ................................... 🟢 95 %  podvzorkování, kWh z výkonu
    │   └── archiver.py ................................. 🟢 90 %  gzip, ověření kopie, retry
    ├── readers/
    │   ├── base.py ..................................... ✅ 100 % backoff, stav, izolace chyb
    │   ├── tng.py ...................................... 🟢 85 %  přeneseno včetně change-gate
    │   ├── ote.py ...................................... 🟢 90 %  + CZK, kurz ČNB
    │   ├── weather.py .................................. 🟢 90 %  + slunce, kód počasí
    │   ├── goodwe.py ................................... 🟡 55 %  neověřeno na reálném měniči
    │   ├── shelly.py ................................... 🟡 60 %  neověřeno na reálném zařízení
    │   ├── registry.py ................................. ✅ 100 %
    │   └── mqtt.py ..................................... ⬜ 0 %   LoRaWAN / meteostanice (později)
    ├── controller/
    │   ├── rules.py .................................... 🟢 80 %  tři pravidla, limity, klíče důvodů
    │   ├── controller.py ............................... 🟢 80 %  safe mode, zápis přes gate
    │   ├── predictor.py ................................ 🟢 85 %  výroba, spotřeba, teplo, cena, okna
    │   └── metrics.py .................................. 🟢 75 %  doložitelné ukazatele
    ├── analysis/
    │   ├── summaries.py ................................ 🟢 90 %  denní bilance včetně ceny
    │   ├── appliances.py ............................... 🟢 85 %  cykly a typický profil
    │   ├── phases.py ................................... 🟢 85 %  nesymetrie a doporučení
    │   └── heatpump.py ................................. 🟢 80 %  spotřeba na denostupeň
    ├── web/
    │   ├── api.py ...................................... 🟢 90 %  18 endpointů
    │   ├── server.py ................................... 🟢 90 %  stdlib, přihlášení, statika
    │   └── frontend/
    │       ├── index.html .............................. ✅ 100 %
    │       ├── css/tokens.css .......................... ✅ 100 % design tokeny obou motivů
    │       ├── css/app.css ............................. 🟢 90 %  stripe, karty, pozadí
    │       ├── js/app.js ............................... 🟢 90 %  směrování, gesta, obnova
    │       ├── js/pages.js ............................. 🟢 85 %  čtyři stránky
    │       ├── js/chart.js ............................. 🟢 85 %  SVG graf, zaměřovač, tabulka
    │       ├── js/flow.js .............................. 🟢 85 %  schéma toku energie
    │       ├── js/background.js ........................ 🟢 85 %  scény podle počasí
    │       ├── js/i18n.js, api.js, icons.js ............ ✅ 100 %
    │       ├── manifest.json, sw.js, icon.svg .......... 🟢 90 %  PWA a offline shell
    ├── locales/cs.json, en.json ........................ 🟢 95 %  170 klíčů, shodná sada
    ├── config/config.example.json ...................... ✅ 100 % generováno ze schématu
    ├── deploy/install.sh, install.ps1, hec.service ..... 🟢 80 %  neověřeno na čistém Pi
    ├── docs/DEPLOYMENT.md, API.md ...................... ✅ 100 %
    ├── tools/diagnostics.py, init_install.py ........... 🟢 90 %
    └── tests/ .......................................... 🟢 85 %  181 testů
```

---

## 4. Celkové dokončení

| Oblast | Váha | Dokončeno | Příspěvek |
|---|---:|---:|---:|
| Reader TNG | 8 % | 85 % | 6,8 |
| Reader GoodWe | 6 % | 55 % | 3,3 |
| Reader OTE | 4 % | 90 % | 3,6 |
| Reader Weather | 4 % | 90 % | 3,6 |
| Reader Shelly | 6 % | 60 % | 3,6 |
| Jádro | 10 % | 95 % | 9,5 |
| Úložiště a archivace | 7 % | 90 % | 6,3 |
| Controller a pravidla | 10 % | 80 % | 8,0 |
| Analýza | 8 % | 85 % | 6,8 |
| Predikce | 8 % | 85 % | 6,8 |
| Web API | 6 % | 90 % | 5,4 |
| Frontend, PWA, jazyky | 15 % | 85 % | 12,8 |
| Testy a CI | 4 % | 85 % | 3,4 |
| Produktizace a dokumentace | 4 % | 80 % | 3,2 |
| **Celkem** | **100 %** | | **≈ 79 %** |

### Podle fází plánu

| Fáze | Milník | Dokončeno | Co zbývá |
|---|---|---:|---|
| 0 – Základ a bezpečnost | M0 | 90 % | změna hesla a odstranění `connect.json` z indexu |
| 1 – Spolehlivý sběr dat | M1 | 80 % | ověření GoodWe a Shelly na reálné instalaci |
| 2 – API, dashboard, jazyky | M2 | 90 % | ověření na mobilu a tabletu |
| 3 – Analýza a archivace | M3 | 85 % | porovnání detekce cyklů se skutečností |
| 4 – Predikce | M4 | 85 % | měření přesnosti po 14 dnech provozu |
| 5 – Řízená optimalizace | M5 | 75 % | týden provozu, zápis topné křivky |
| 6 – Produktizace | M6 | 80 % | licence, průvodce prvním spuštěním, test čisté instalace |

---

## 5. Co zbývá a proč

| # | Položka | Kdo to odblokuje |
|---|---|---|
| 1 | Změna hesla k tngsmart.cz a `git rm --cached connect.json` | zadavatel (heslo se zatím měnit nemá) |
| 2 | Ověření readeru GoodWe včetně fázových veličin L1/L2/L3 | přístup k reálnému měniči |
| 3 | Ověření readeru Shelly (gen1 vs gen2, Pro 3EM na TČ) | fyzická zařízení |
| 4 | Zapnutí zápisu topné křivky do TNG | ověření na hardwaru s `--dry-run` |
| 5 | Přesnost predikce (cíl MAPE < 25 %) | 14 dní provozu |
| 6 | Licence projektu a přehled licencí závislostí | rozhodnutí o způsobu prodeje |
| 7 | Průvodce prvním spuštěním v UI | navazuje na rozhodnutí č. 6 |
| 8 | MQTT / LoRaWAN meteostanice | až bude hardware |
