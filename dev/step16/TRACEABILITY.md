# GoodWe Integration Refactor – Traceability Matrix

## Requirements → Acceptance Criteria Mapping

| Requirement | Acceptance Criterion | Status |
|---|---|---|
| Centrální GoodWeManager s lock | AC 1.1–1.6 | 📝 planned |
| FTEReader primárně přes knihovnu | AC 2.1–2.7 | 📝 planned |
| FTEWriter idempotentní | AC 3.1–3.7 | 📝 planned |
| SDGHistoryReader s incremental import | AC 4.1–4.5 | 📝 planned |
| Konfigurovatelná cesta k SDG | AC 5.1–5.4 | 📝 planned |
| Web diagnostika a settings | AC 6.1–6.3 | 📝 planned |
| Testy pro všechny komponenty | AC 7.1–7.5 | 📝 planned |
| Hardware test na 192.168.2.116 | AC 8.1–8.6 | 📝 planned |

## Komponenta → Soubor Mapping

| Komponenta | Primární soubor | Testy |
|---|---|---|
| GoodWeManager | `dev/hec/readers/goodwe_manager.py` | `dev/hec/tests/test_readers_goodwe_manager.py` |
| FTEReader | `dev/hec/readers/fte_reader.py` | `dev/hec/tests/test_readers_fte.py` |
| FTEWriter | `dev/hec/writers/fte_writer.py` | `dev/hec/tests/test_writers_fte.py` |
| SDGHistoryReader | `dev/hec/readers/sdg_history_reader.py` | `dev/hec/tests/test_readers_sdg_history.py` |
| Config schema | `dev/hec/config/schema.json` (update) | `dev/hec/tests/test_config.py` (update) |
| Web API | `dev/hec/web/api.py` (update) | `dev/hec/tests/test_web_api.py` (update) |

## Fáze → Acceptance Criteria Mapping

| Fáze | AC Group | Kdy hotovo |
|---|---|---|
| A – Design | Design documents finalized | Konec fáze A |
| B – Core (GoodWeManager + Reader) | AC 1, 2 | Konec fáze B |
| C – Writer & Audit | AC 3 | Konec fáze C |
| D – SDG Integration | AC 4 | Konec fáze D |
| E – Web & Config | AC 5, 6 | Konec fáze E |
| F – Hardware Test | AC 8 | Konec fáze F |
| G – Documentation | AC 7 (complete), 9 | Konec fáze G |

## Risk Traceability

| Riziko | Zdroj | Opatření | AC Requirement |
|---|---|---|---|
| Kolize SDG reader + HEC writer | Architektura | Timeout, jitter, lock, read-back | AC 1.1, 8.5 |
| Ztráta GoodWe komunikace | Síť | Graceful degradation, reconnect | AC 2.5, 8.6 |
| Neznámé registry | Knihovna | Značit unsupported, nehadovat | AC 2.2, 3.4 |
| Paralelní zápisy | Design | Lock/mutex, queue | AC 1.2–1.4 |
| Poškozené SDG logy | Data | Graceful error handling | AC 4.4 |
