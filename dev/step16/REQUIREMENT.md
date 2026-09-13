# GoodWe Integration Refactor – Requirement

## Objective

Implement the approved GoodWe integration refactor in which HEC owns the active
controller/writer path and SDG is limited to reading, diagnostics, and optional
history import. This step executes the approved design and implementation scope
without bypassing safety gates or performing device writes before explicit human
and hardware verification.

## Základ

Z dokumentu `HEC_FTE_READER_WRITER_UPRAVA.md`:
- HEC nesmí předpokládat, že SDG provádí jakékoli řízení
- Společná komunikační vrstva bez kolizí
- Reader čte primárně přes knihovnu GoodWe
- Writer je idempotentní, fallback jen pro nepodporované funkce
- Historická data z SDG jako volitelný import

## Requirements

- REQ-016-001: Provide one serialized GoodWe communication boundary with
  timeout handling, retry/backoff, read-back verification, terminal status,
  and fail-closed behavior.
- REQ-016-002: Provide a normalized GoodWe reader contract that preserves
  source identity, reports offline data explicitly, and never advances fresh
  success state for missing data.
- REQ-016-003: Provide idempotent writer commands that can run only through the
  GoodWeManager boundary, require `writer_enabled`, persistent audit, and a
  deliberate local human S07 authorization step.
- REQ-016-004: Provide optional SDG history import with configurable paths,
  incremental progress, deduplication, timestamp preservation, and tolerant
  corrupt-file handling.
- REQ-016-005: Provide the canonical Python declarative schema plus JSON
  configuration, diagnostics, i18n, tests, and the GoodWe/SDG web settings
  required before S07.

## Komponenty

### 1. GoodWeManager
- Lock/mutex, retry, read-back verification
- Serializace write operací
- GoodWe library API is primary; raw Modbus fallback is outside this step
- Timeout, reconnect, validation of supported command inputs
- Physical write is OFF by default and absolutely disabled in automated/test
  runtime
- Every write requires `controller.enabled`, `goodwe.enabled`,
  `goodwe.writer_enabled`, and explicit local human S07 authorization evidence

### 2. FTEReader
- Primární: knihovna GoodWe
- Normalizovaný JSON výstup
- Graceful degradation
- Konfigurovatelný interval (5–10 s)

### 3. FTEWriter
- Idempotentní příkazy (set_*, ne toggle_*)
- Export limit, charge, discharge, SOC limits, stop control
- Read-back po každém zápisu
- Persistent JSONL audit for every write attempt
- First physical write is permitted only during explicit S07 human/hardware
  verification; no production optimization rules are part of Step16

### 4. SDGHistoryReader
- Incremental import z DBF
- Normalizace na HEC model
- Deduplikace, graceful corruption handling

### 5. Konfigurace
- Povinný parametr: `goodwe.sdg.log_root_path`
- Všechny cesty k SDG relativní k root
- Python deklarativní schema (`dev/hec/core/schema.py`) s JSON konfigurací
- Canonical fields are `goodwe.enabled`, `goodwe.writer_enabled`,
  `goodwe.read_interval_seconds` (10 s default), `goodwe.timeout_seconds`
  (3 s default), `goodwe.retry_count` (3 default), `verify_after_write`, and
  independent `goodwe.sdg.enabled`/`log_root_path`

### 6. Web UI
- Settings: GoodWe host, intervaly, SDG path
- Diagnostika: connection status, last read/write, firmware, SOC

### 7. Terminal status output
- Všechny controller komponenty, jak reader, tak writer, musí při běhu vypisovat
  stav do terminálu (např. připojení, retry, timeout, úspěch, chybový stav,
  poslední čtení/zápis, záznam o operaci).
- Výstup musí být přehledný, konzistentní a vhodný pro lokální diagnostiku
  bez nutnosti otevřít webové rozhraní.

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

## Praktický scope boundary

Step16 does not require cryptographic or immutable authorization evidence. The
threat model does not protect against a person who can execute arbitrary Python
on the HEC server. S07 requires an explicit, deliberate local service action
and an auditable evidence record; normal Settings and `/api/config` must not
create or modify that evidence.

The following are outside Step16: production GoodWe optimization decision
rules, cryptographic authorization protection, and detailed DBF header
fingerprint hardening. Explicit `unsupported` metadata beyond stable `None`
values, detailed jitter-distribution tests, and additional traceability
hardening are non-blocking/minor quality work.
