# GoodWe Integration Refactor – Traceability Matrix

## Requirements → Acceptance Criteria Mapping

| Requirement | Acceptance Criterion | Substeps | Evidence | Status |
|---|---|---|---|---|
| REQ-016-001 | AC-016-001 | S01, S02, S03 | - | PLANNED |
| REQ-016-002 | AC-016-002 | S02, S06 | - | PLANNED |
| REQ-016-003 | AC-016-003 | S03, S06 | - | PLANNED |
| REQ-016-004 | AC-016-004 | S04, S06 | - | PLANNED |
| REQ-016-005 | AC-016-005, AC-016-006, AC-016-007, AC-016-008 | S05, S06, S07 | - | PLANNED |

## Acceptance criteria → substeps

| Acceptance criterion | Requirement | Substeps | Status |
|---|---|---|---|
| AC-016-001 | REQ-016-001 | S01, S02, S03 | PLANNED |
| AC-016-002 | REQ-016-002 | S02, S06 | PLANNED |
| AC-016-003 | REQ-016-003 | S03, S06 | PLANNED |
| AC-016-004 | REQ-016-004 | S04, S06 | PLANNED |
| AC-016-005 | REQ-016-005 | S05, S06 | PLANNED |
| AC-016-006 | REQ-016-005 | S06 | PLANNED |
| AC-016-007 | REQ-016-005 | S07 | PLANNED |
| AC-016-008 | REQ-016-005 | S05, S07 | PLANNED |

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
