# Step 16 – GoodWe Integration Refactor

## Žádost

Přepracovat stávající integraci GoodWe tak, aby HEC byl jediný aktivní 
controller/writer FVE. SDG zůstane jen reader/logger. Společná komunikační 
vrstva bez kolizí.

Vychází z dokumentu `HEC_FTE_READER_WRITER_UPRAVA.md`.

## Cíl

- Nový centrální `GoodWeManager` (lock, retry, read-back, fallback Modbus)
- Reader čte primárně přes knihovnu GoodWe, fallback na raw Modbus jen pro nepodporované funkce
- Writer idempotentní, všechny příkazy přes knihovnu, fallback jen jako poslední zrada
- SDG zůstane pouze čtení + logging, bez aktivního řízení FVE
- Plně konfigurovatelná cesta k SDG logům (nový parametr `goodwe.sdg.log_root_path`)
- Testy a audit pro všechny operace

## Architektura

```text
HEC Controller
    ↓
GoodWeManager (thread-safe lock, retry, read-back)
    ├── Reader (library GoodWe)
    ├── Writer (library GoodWe + fallback Modbus)
    ├── Lock / mutex
    └── Logging
    ↓
GoodWe Python library
    └── [fallback: raw Modbus jen pro nepodporované]
    ↓
GoodWe inverter

SDG
    ├── Reader (logs only)
    ├── Logger
    ├── Historická data
    └── Diagnostika
    X  žádné aktivní řízení FVE
```

## Komponenty k implementaci

### 1. GoodWeManager

Centrální komunikační vrstva:
- Inicializace spojení, reconnect, timeout, retry, lock
- Serializace write operací (queue)
- Read-back verification po každém zápisu
- Validace rozsahů
- Normalizace hodnot
- Fallback na Modbus registr (s komentářem, jen pro nepodporované funkce)
- Logging všech operací

**Minimální odpovědnosti:**
- inicializace spojení
- reconnect při chybě
- timeout
- retry s jitter
- lock/mutex nad komunikací
- serializace write operací
- read-back po zápisu
- validace rozsahů
- logging
- normalizace hodnot
- fallback na raw Modbus (explicitní, dokumentovaný)

### 2. Úprava FTE Reader

**Primární zdroj:** knihovna GoodWe

**Čtené hodnoty (minimálně):**
- PV total power, PV1 power, PV2 power
- Battery power, SOC, SOH, voltage, current, state
- BMS charge/discharge current limits
- House/load total power, L1/L2/L3
- Grid total power, L1/L2/L3
- Inverter power, L1/L2/L3
- PV1/PV2 voltage
- Grid voltage L1/L2/L3
- Inverter/module temperature
- Working mode
- Export limit enabled, export limit W
- On-grid/off-grid SOC limits
- Alarm/fault state
- Inverter firmware/version, model

**Nepodporované hodnoty:** značit jako `unsupported`, nehadovat registry

**Normalizovaný výstup JSON:**
```json
{
  "timestamp": "2026-09-07T18:30:00+02:00",
  "source": "goodwe_library",
  "online": true,
  "model": "GW10K-ET",
  "firmware": "0927",
  "pv": {
    "power_w": 0,
    "pv1_power_w": 0,
    "pv2_power_w": 0
  },
  "battery": {
    "soc_pct": 88,
    "soh_pct": 98,
    "power_w": 625,
    "voltage_v": 398,
    "current_a": 1.5,
    "state": "discharge",
    "charge_current_limit_a": 7,
    "discharge_current_limit_a": 18
  },
  "load": {
    "total_w": 598,
    "l1_w": 24,
    "l2_w": 21,
    "l3_w": -12
  },
  "grid": {
    "total_w": 33
  },
  "inverter": {
    "working_mode": "general",
    "temperature_c": 42
  },
  "control": {
    "export_limit_enabled": false,
    "export_limit_w": 10000,
    "on_grid_soc_limit_pct": 10,
    "off_grid_soc_limit_pct": 10
  }
}
```

**Konfigurovatelný interval:** 5–10 sekund (default)

**Graceful degradation:**
- Reader nenablokuje controller
- Při nedostupnosti: `online=false`, ulož chybu, reconnect podle retry policy

### 3. Úprava FTE Writer

**Základní princip:** GoodWe library API → fallback raw Modbus jen jako poslední možnost

**Idempotentní příkazy (set_*, ne toggle_*):**
- `set_export_limit_enabled(true/false)`
- `set_export_limit_w(value)`
- `start_battery_charge(power_pct, start_soc_pct, stop_soc_pct, valid_from, valid_to)`
- `start_battery_discharge(power_pct, start_soc_pct, stop_soc_pct, valid_from, valid_to)`
- `stop_battery_control()` → vrácení do General/self-consumption modu
- `set_on_grid_soc_limit_pct(value)`

**Pracovní režimy (zatím jen pro HEC):**
```text
0 = General (výchozí)
3 = ECO (řízený nabíjení/vybíjení)
```

**Ověření po zápisu:**
```text
1. Načti current state
2. Ověř rozsahy
3. Získej communication lock
4. Proveď write
5. Krátká prodleva
6. Proveď read-back
7. Porovnej requested vs actual
8. Pokud nesouhlasí → retry (s jitter)
9. Ulož audit
10. Uvolni lock
```

**Fallback registry (jen jako poslední možnost):**
```text
47509 = export limit enabled
47510 = export limit W
45356 = On-Grid SOC limit
45358 = Off-grid SOC limit
```

### 4. SDGHistoryReader

Samostatný importér pro historická a diagnostická data z SDG:
- Čte: `Data/trend/min/*.dbf`, `Data/Event2/*.dbf`, `Data/Alarm/*.dbf`
- Normalizace názvů veličin na HEC model
- Incremental import, deduplikace
- Zachování původního timestamp a zdroje (`sdg`)

### 5. Konfigurační rozšíření

**YAML:**
```yaml
goodwe:
  enabled: true
  host: "192.168.2.116"
  read_interval_sec: 5
  timeout_sec: 3
  retry_count: 3
  retry_delay_sec: 2

  control:
    enabled: true
    verify_after_write: true
    write_retry_count: 3

  sdg:
    enabled: true
    log_root_path: "C:/PROMOTIC/Apps/SDG"
```

**JSON (alternativa):**
```json
{
  "goodwe": {
    "enabled": true,
    "host": "192.168.2.116",
    "read_interval_sec": 5,
    "timeout_sec": 3,
    "retry_count": 3,
    "retry_delay_sec": 2,
    "control": {
      "enabled": true,
      "verify_after_write": true,
      "write_retry_count": 3
    },
    "sdg": {
      "enabled": true,
      "log_root_path": "C:/PROMOTIC/Apps/SDG"
    }
  }
}
```

**Povinný nový parametr:** `goodwe.sdg.log_root_path`
- Nikde v kódu hardcode cesty k SDG datům
- Reader skládá podcesty relativně k `log_root_path`:
  - `{log_root_path}/Data/trend/min`
  - `{log_root_path}/Data/trend/solar`
  - `{log_root_path}/Data/Event2`
  - `{log_root_path}/Data/Alarm`
  - `{log_root_path}/SDG.log`
  - `{log_root_path}/SDG_RtStop.log`

### 6. Diagnostická stránka (web)

**Zobrazit:**
- GoodWe connection: OK / ERROR
- Last read, last read duration
- Last write, last write duration
- Last retry count
- Firmware, model, working mode
- Export limit enabled/W
- Current SOC
- Battery power, grid power, load power
- SDG log path
- SDG history available: yes/no

**Editovatelné na settings stránce:**
- GoodWe host/IP
- Read interval
- Timeout
- Retry count
- Verify after write
- Writer enabled
- SDG enabled
- SDG log root path

### 7. Audit Writer

Každý příkaz loguji minimálně takto:
```json
{
  "timestamp": "2026-09-07T18:30:00+02:00",
  "command_id": "fte-20260907-001",
  "command": "battery_discharge",
  "requested": {
    "power_pct": 80,
    "start_soc_pct": 90,
    "stop_soc_pct": 20
  },
  "before": {},
  "after": {},
  "success": true,
  "attempts": 1,
  "source": "HEC"
}
```

## Akceptační kritéria

1. ✅ **GoodWeManager** funguje bez kolizí mezi reader a writer
2. ✅ **Reader** čte primárně přes knihovnu, output je normalizovaný JSON
3. ✅ **Writer** je idempotentní, má read-back, audit log
4. ✅ **SDG** už neřídí FVE (ověřit v SDG projektu – měly by být vypnuty automatické zápisy)
5. ✅ **Konfigurace** je plně dynamická (žádné hardcode cesty k SDG)
6. ✅ **Testy** – reader (success, timeout, reconnect, unsupported), writer (export limit ON/OFF, charge, discharge, stop, read-back mismatch, retry, timeout), SDG import (load DBF, incremental, duplicate handling, bad path, corrupt file)
7. ✅ **Hardware test** – ověřit na reálném GoodWe invertu 192.168.2.116
8. ✅ **Web stránky** – config editování a diagnostika

## Rizika & Opatření

| Riziko | Opatření |
|---|---|
| Kolize SDG reader + HEC writer | Timeout, retry s jitter, read-back verification, GoodWeManager lock |
| Ztráta GoodWe komunikace | Graceful degradation, fallback na last-known state, reconnect |
| Neznámé registry | Nepoužívat, značit jako `unsupported`, nikdy nehadovat |
| Paralelní zápisy | Lock/mutex, queue v GoodWeManager |
| Chyba knihovny GoodWe | Fallback na raw Modbus (explicitní, dokumentovaný) |
| Poškozené SDG logy | Chybové hlášení, skip corrupted file, incremental load bez deduplikace |

## Přípravné kroky (před implementací)

1. ✓ Verifikovat, které funkce knihovna GoodWe podporuje
2. ✓ Identifikovat registry pro fallback (export limit, SOC limits)
3. ✓ Domluvit se na SDG – vypnout automatické zápisy (toggle ECO schedule, export limit, battery charge/discharge)
4. ✓ Vzorky reálných dat z GoodWe (čtení i zápisy)
5. ✓ Návrh audit logu formátu

## Fáze implementace

### Fáze A – Design & Příprava (2–3 dny)

- Návrh `GoodWeManager` API a interface
- Mapování funkcí knihovny GoodWe vs. raw Modbus registry
- Datový model normalizace reader výstupu
- Návrh konfigurace a schéma validation
- Návrh audit logu formátu
- Příprava testovacích vzorků dat

### Fáze B – Core (GoodWeManager + Reader) (3–4 dny)

- Implementace `GoodWeManager` s lock/mutex, retry, read-back
- Nový `FTEReader` přes knihovnu GoodWe
- Normalizovaný output JSON
- Testované čtení (success, timeout, reconnect, unsupported property, malformed response)
- Integracja do hlavní smyčky controlleru

### Fáze C – Writer & Audit (2–3 dny)

- Nový `FTEWriter` s idempotentními příkazy
- Read-back verification po každém zápisu
- Audit log serializace
- Testy writer (export limit ON/OFF, change W, charge, discharge, stop, on-grid SOC limit, read-back success/mismatch, retry, timeout)

### Fáze D – SDG Integration (1–2 dny)

- `SDGHistoryReader` implementace (DBF import)
- Incremental load, deduplikace
- Konfigurovatelná cesta k SDG datům
- Testy (load DBF, incremental, duplicity, nonexistent path, corrupt file)

### Fáze E – Web & Config (1–2 dny)

- Konfigurace GoodWe na settings stránce
- Diagnostická stránka s status informacemi
- i18n klíče (CZ/EN)
- Frontend integracja

### Fáze F – Hardware Test (1–2 dny)

- Ověření na reálném GoodWe invertu 192.168.2.116
- Export limit změny (ON/OFF/W)
- Charge/discharge operace
- Retry testy a timeout
- Ověřit, že SDG nekonfliktuje s HEC
- Ověřit graceful degradation (vypnutí invertu, síť)

### Fáze G – Dokumentace & Uzavření (1 den)

- RESULT.md s evidence of passing all acceptance criteria
- Aktualizace main README.md (zmínka o GoodWe integraci)
- Release notes
- Aktualizace `dev/README.md` status

## Estimace

| Fáze | Trvání |
|---|---|
| A – Design & Příprava | 2–3 dny |
| B – Core (GoodWeManager + Reader) | 3–4 dny |
| C – Writer & Audit | 2–3 dny |
| D – SDG Integration | 1–2 dny |
| E – Web & Config | 1–2 dny |
| F – Hardware Test | 1–2 dny |
| G – Dokumentace & Uzavření | 1 den |
| **CELKEM** | **~11–17 dní** |

## Důležitá pravidla implementace

- ❌ Nepoužívat raw Modbus tam, kde knihovna GoodWe nabízí funkci
- ❌ Nehádej registry
- ✓ Každý použitý fallback registr musí být komentovaný
- ✓ Každý write musí mít read-back
- ❌ Žádný writer toggle (vždy set_enabled/set_disabled)
- ❌ Žádné dvě nezávislé GoodWe write vrstvy
- ✓ SDG není controller
- ✓ Cesta k SDG datům je vždy z configu
- ✓ Reader a Writer fungují i při úplně vypnutém SDG
- ❌ HEC není závislý na interní struktuře SDG víc, než je nutné pro historický import

## Výsledný stav

```text
HEC
  ├── GoodWeManager
  ├── FTEReader (refactored)
  ├── FTEWriter (refactored)
  ├── SDGHistoryReader
  └── Controller (nezměněn)

SDG
  └── pouze reader/logger
```

**Cílem je jednoduchá a dlouhodobě udržitelná architektura:**

> HEC rozhoduje a řídí.  
> GoodWe knihovna zajišťuje standardní komunikaci.  
> Raw Modbus je pouze fallback.  
> SDG slouží jako nezávislá diagnostika a historický zdroj.
