# GoodWe Integration Refactor – Acceptance Criteria

## Objective

These criteria define future implementation evidence. They are intentionally
unchecked while Step 16 is `PLANNED`.

## Canonical criteria

- [ ] AC-016-001: GoodWeManager communication is serialized, retried safely,
	timeout-bounded, read-back verified, and covered by tests.
- [ ] AC-016-002: FTEReader uses the GoodWe library, emits the normalized model,
	and fails closed on unsupported or malformed data.
- [ ] AC-016-003: FTEWriter commands are idempotent, audited, read-back
	verified, and cannot bypass approved safety gates.
- [ ] AC-016-004: Optional SDG history import is incremental, deduplicated,
	normalized, and tolerant of corrupt input.
- [ ] AC-016-005: Configuration, diagnostics, i18n, and paths are
	schema-validated and covered by focused tests.
- [ ] AC-016-006: Unit and mock-preview tests cover failure, retry, and safety
	behavior.
- [ ] AC-016-007: Human hardware verification is recorded before any DONE
	status.
- [ ] AC-016-008: Documentation and release metadata are updated with
	implementation evidence.

## 1. GoodWeManager

- [ ] Thread-safe lock/mutex nad komunikací
- [ ] Retry logika s jitter (exponential backoff)
- [ ] Read-back verification po každém zápisu
- [ ] Timeout handling (3 sec default, konfigurovatelné)
- [ ] Queue pro serializaci write operací
- [ ] Testy: success, timeout, retry, read-back mismatch

## 2. FTEReader

- [ ] Čte primárně přes GoodWe Python library
- [ ] Normalizovaný JSON výstup (timestamp, source, online, model, firmware, pv, battery, load, grid, inverter, control)
- [ ] Minimálně 30+ metrik (PV, battery, load, grid, inverter, state)
- [ ] Nepodporované hodnoty značeny jako `unsupported` (bez hádání registrů)
- [ ] Interval konfigurovatelný (default 5–10 s)
- [ ] Graceful degradation (nenablokuje controller, `online=false`)
- [ ] Testy: success, timeout, reconnect, unsupported property, malformed response

## 3. FTEWriter

- [ ] Idempotentní příkazy: `set_export_limit_enabled()`, `set_export_limit_w()`, `start_battery_charge()`, `start_battery_discharge()`, `stop_battery_control()`, `set_on_grid_soc_limit_pct()`
- [ ] Podporované pracovní režimy: General (0), ECO (3)
- [ ] GoodWe library API je primární
- [ ] Fallback na raw Modbus jen pro nepodporované funkce (s komentářem)
- [ ] Read-back verification po zápisu
- [ ] Audit log (JSON s timestamp, command_id, requested, before, after, success, attempts)
- [ ] Testy: export limit ON/OFF/W, charge, discharge, stop, on-grid SOC, read-back success/mismatch, retry, timeout

## 4. SDGHistoryReader

- [ ] Čte DBF z `Data/trend/min/`, `Data/Event2/`, `Data/Alarm/`
- [ ] Normalizace na HEC datový model
- [ ] Incremental import bez duplikace
- [ ] Graceful handling poškozených souborů
- [ ] Zachování original timestamp a zdroje (`sdg`)
- [ ] Testy: load DBF, incremental, duplicity, nonexistent path, corrupt file

## 5. Konfigurace

- [ ] Povinný parametr: `goodwe.sdg.log_root_path`
- [ ] Všechny SDG cesty jsou relativní k root
- [ ] YAML i JSON schema support
- [ ] Všechny relevantní parametry editovatelné (host, read_interval, timeout, retry_count, verify_after_write, writer_enabled, sdg_enabled, sdg_log_root_path)
- [ ] Validace schema s jasným error message

## 6. Web Diagnostika

- [ ] Zobrazit: connection status, last read/write + duration, retry count, firmware, model, working mode, export limit, SOC, power metrics, SDG log path
- [ ] Editovatelné parametry na settings stránce
- [ ] i18n (CZ/EN)
- [ ] Real-time update

## 7. Testy

- [ ] GoodWeManager: lock contention, retry success, read-back verify
- [ ] Reader: network timeout, reconnect, unsupported property
- [ ] Writer: all 6 command types, read-back mismatch, retry exhaustion
- [ ] SDG import: incremental, duplicity detection, corruption handling
- [ ] Config: schema validation, path construction

## 8. Hardware Test

- [ ] Ověřit na reálném GoodWe invertu 192.168.2.116
- [ ] Export limit změny (ON/OFF/W)
- [ ] Charge/discharge operace
- [ ] Retry testy a timeout
- [ ] SDG nekonfliktuje s HEC
- [ ] Graceful degradation (vypnutí invertu, síť)

## 9. Dokumentace

- [ ] RESULT.md s evidence každého acceptance critéria
- [ ] README.md zmínka o GoodWe integraci
- [ ] Release notes
- [ ] `dev/README.md` status update

## Definice DONE

Všechna acceptance kritéria musí mít důvěryhodnou evidenci a hardware test je
**povinný**. Automated checks are not hardware verification.
