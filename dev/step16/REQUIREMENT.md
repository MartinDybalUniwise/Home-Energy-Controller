# GoodWe Integration Refactor – Requirement

## Základ

Z dokumentu `HEC_FTE_READER_WRITER_UPRAVA.md`:
- HEC nesmí předpokládat, že SDG provádí jakékoli řízení
- Společná komunikační vrstva bez kolizí
- Reader čte primárně přes knihovnu GoodWe
- Writer je idempotentní, fallback jen pro nepodporované funkce
- Historická data z SDG jako volitelný import

## Komponenty

### 1. GoodWeManager
- Lock/mutex, retry, read-back verification
- Serializace write operací
- Fallback na raw Modbus (dokumentovaný)
- Timeout, reconnect, validace rozsahů

### 2. FTEReader
- Primární: knihovna GoodWe
- Normalizovaný JSON výstup
- Graceful degradation
- Konfigurovatelný interval (5–10 s)

### 3. FTEWriter
- Idempotentní příkazy (set_*, ne toggle_*)
- Export limit, charge, discharge, SOC limits, stop control
- Read-back po každém zápisu
- Audit log

### 4. SDGHistoryReader
- Incremental import z DBF
- Normalizace na HEC model
- Deduplikace, graceful corruption handling

### 5. Konfigurace
- Povinný parametr: `goodwe.sdg.log_root_path`
- Všechny cesty k SDG relativní k root
- YAML a JSON schema

### 6. Web UI
- Settings: GoodWe host, intervaly, SDG path
- Diagnostika: connection status, last read/write, firmware, SOC

## Architektura

```
HEC Controller
    ↓
GoodWeManager (lock, retry, read-back)
    ├── Reader (GoodWe library)
    ├── Writer (GoodWe library + fallback)
    └── Logging
    ↓
GoodWe inverter

SDG: reader/logger only (no control)
```

## Výsledek

HEC rozhoduje a řídí. GoodWe knihovna zajišťuje komunikaci. Raw Modbus jen fallback. SDG je diagnostika.
