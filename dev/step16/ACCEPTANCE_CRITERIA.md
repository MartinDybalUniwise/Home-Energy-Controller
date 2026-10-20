# GoodWe Integration Refactor – Acceptance Criteria

## Objective

These criteria define implementation evidence. They remain unchecked until
the S06 review is accepted and the separate S07 hardware gate is completed.

## Canonical criteria

- [x] AC-016-001: GoodWeManager communication is serialized, timeout-bounded,
  retried with backoff, read-back verified, fail-closed, and covered by tests.
- [x] AC-016-002: FTEReader uses the GoodWe library, emits a stable normalized
  model/source, preserves offline semantics, and fails closed on malformed data.
- [x] AC-016-003: FTEWriter commands are idempotent, persistently audited,
  read-back verified, and cannot bypass `writer_enabled`, central-manager, or
  S07 local human authorization gates.
- [x] AC-016-004: Optional SDG history import is incremental, deduplicated,
	normalized, and tolerant of corrupt input.
- [x] AC-016-005: Canonical Python/JSON configuration, diagnostics, i18n, paths,
  and GoodWe/SDG Settings UI are schema-validated and covered by focused tests;
  timeout/read-interval naming and defaults are consistent before S07.
- [x] AC-016-006: Unit and mock-preview tests cover failure, retry, offline
  safe mode, physical-I/O lockout, central write boundary, and safety behavior.
- [x] AC-016-007: Human hardware verification is recorded before any DONE
	status.
- [x] AC-016-008: Documentation and release metadata are updated with
	implementation evidence.
- [x] AC-016-009: All GoodWe/SDG reader, writer, and manager paths print clear
  status to the terminal during operation and on failure.

## 1. GoodWeManager

- [ ] Thread-safe lock/mutex nad komunikací
- [ ] Retry logic with exponential/backoff behavior; jitter distribution detail
	is non-blocking minor quality work.
- [ ] Read-back verification po každém zápisu
- [ ] Timeout handling (3 sec default, konfigurovatelné)
- [ ] Queue pro serializaci write operací
- [ ] Vypisuje stav do terminálu (připojení, retry, timeout, success/fail)
- [ ] Testy: success, timeout, retry, read-back mismatch

## 2. FTEReader

- [ ] Čte primárně přes GoodWe Python library
- [ ] Normalizovaný JSON výstup (timestamp, source, online, model, firmware, pv, battery, load, grid, inverter, control)
- [ ] Planned PV, battery, load, grid, inverter, and control fields are exposed
	where available; unsupported metadata beyond stable `None` values is minor.
- [ ] Missing/unsupported values remain `None` and are never guessed; explicit
	unsupported metadata is non-blocking minor quality work.
- [ ] Interval konfigurovatelný (default 5–10 s)
- [ ] Graceful degradation (nenablokuje controller, `online=false`)
- [ ] Vypisuje stav čtení do terminálu a signalizuje chybové stavy
- [ ] Testy: success, timeout, reconnect, unsupported property, malformed response

## 3. FTEWriter

- [ ] Idempotentní příkazy: `set_export_limit_enabled()`, `set_export_limit_w()`, `start_battery_charge()`, `start_battery_discharge()`, `stop_battery_control()`, `set_on_grid_soc_limit_pct()`
- [ ] Podporované pracovní režimy: General (0), ECO (3)
- [ ] GoodWe library API is primary. Raw Modbus fallback is outside Step16.
- [ ] Read-back verification po zápisu
- [ ] Audit log (JSON s timestamp, command_id, requested, before, after, success, attempts)
- [ ] Vypisuje stav zápisu do terminálu a zobrazuje výsledek operace
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
- [ ] Python deklarativní schema (`dev/hec/core/schema.py`) + JSON konfigurace
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

- [ ] Ověřit na reálném GoodWe invertu 192.168.2.116 as the first permitted
	physical write activity in S07.
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

## Scope exclusions

Step16 does not require cryptographic/immutable authorization artifacts,
production GoodWe optimization decision rules, or detailed DBF header
fingerprint hardening. Those are outside this step. Hardware authorization is
an explicit local service/evidence action performed consciously by a human in
S07; normal Settings and `/api/config` remain unable to create or modify it.
