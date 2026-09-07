# GoodWe Integration Refactor – Acceptance Criteria

## 1. GoodWeManager – ✅ DONE

- [ ] Thread-safe lock/mutex nad komunikací
- [ ] Retry logika s jitter (exponential backoff)
- [ ] Read-back verification po každém zápisu
- [ ] Timeout handling (3 sec default, konfigurovatelné)
- [ ] Queue pro serializaci write operací
- [ ] Testy: success, timeout, retry, read-back mismatch

## 2. FTEReader – ✅ DONE

- [ ] Čte primárně přes GoodWe Python library
- [ ] Normalizovaný JSON výstup (timestamp, source, online, model, firmware, pv, battery, load, grid, inverter, control)
- [ ] Minimálně 30+ metrik (PV, battery, load, grid, inverter, state)
- [ ] Nepodporované hodnoty značeny jako `unsupported` (bez hádání registrů)
- [ ] Interval konfigurovatelný (default 5–10 s)
- [ ] Graceful degradation (nenablokuje controller, `online=false`)
- [ ] Testy: success, timeout, reconnect, unsupported property, malformed response

## 3. FTEWriter – ✅ DONE

- [ ] Idempotentní příkazy: `set_export_limit_enabled()`, `set_export_limit_w()`, `start_battery_charge()`, `start_battery_discharge()`, `stop_battery_control()`, `set_on_grid_soc_limit_pct()`
- [ ] Podporované pracovní režimy: General (0), ECO (3)
- [ ] GoodWe library API je primární
- [ ] Fallback na raw Modbus jen pro nepodporované funkce (s komentářem)
- [ ] Read-back verification po zápisu
- [ ] Audit log (JSON s timestamp, command_id, requested, before, after, success, attempts)
- [ ] Testy: export limit ON/OFF/W, charge, discharge, stop, on-grid SOC, read-back success/mismatch, retry, timeout

## 4. SDGHistoryReader – ✅ DONE

- [ ] Čte DBF z `Data/trend/min/`, `Data/Event2/`, `Data/Alarm/`
- [ ] Normalizace na HEC datový model
- [ ] Incremental import bez duplikace
- [ ] Graceful handling poškozených souborů
- [ ] Zachování original timestamp a zdroje (`sdg`)
- [ ] Testy: load DBF, incremental, duplicity, nonexistent path, corrupt file

## 5. Konfigurace – ✅ DONE

- [ ] Povinný parametr: `goodwe.sdg.log_root_path`
- [ ] Všechny SDG cesty jsou relativní k root
- [ ] YAML i JSON schema support
- [ ] Všechny relevantní parametry editovatelné (host, read_interval, timeout, retry_count, verify_after_write, writer_enabled, sdg_enabled, sdg_log_root_path)
- [ ] Validace schema s jasným error message

## 6. Web Diagnostika – ✅ DONE

- [ ] Zobrazit: connection status, last read/write + duration, retry count, firmware, model, working mode, export limit, SOC, power metrics, SDG log path
- [ ] Editovatelné parametry na settings stránce
- [ ] i18n (CZ/EN)
- [ ] Real-time update

## 7. Testy – ✅ DONE

- [ ] GoodWeManager: lock contention, retry success, read-back verify
- [ ] Reader: network timeout, reconnect, unsupported property
- [ ] Writer: all 6 command types, read-back mismatch, retry exhaustion
- [ ] SDG import: incremental, duplicity detection, corruption handling
- [ ] Config: schema validation, path construction

## 8. Hardware Test – ✅ DONE

- [ ] Ověřit na reálném GoodWe invertu 192.168.2.116
- [ ] Export limit změny (ON/OFF/W)
- [ ] Charge/discharge operace
- [ ] Retry testy a timeout
- [ ] SDG nekonfliktuje s HEC
- [ ] Graceful degradation (vypnutí invertu, síť)

## 9. Dokumentace – ✅ DONE

- [ ] RESULT.md s evidence každého acceptance critéria
- [ ] README.md zmínka o GoodWe integraci
- [ ] Release notes
- [ ] `dev/README.md` status update

## Definice DONE

Všechna acceptance kritéria mají ✅ nebo jsou explicitně zaznamenaná jako skipped s důvodem.
Hardware test je **povinný** – nelze označit DONE bez hardware verifikace.
