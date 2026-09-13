# GoodWe Integration Refactor – Traceability Matrix

## Requirements → Acceptance Criteria Mapping

| Requirement | Acceptance Criterion | Substeps | Evidence | Status |
|---|---|---|---|---|
| REQ-016-001 | AC-016-001 | S01, S02, S03 | focused GoodWe tests; E-016-VALIDATION | IN_REVIEW |
| REQ-016-002 | AC-016-002 | S02, S06 | focused FTEReader test | IN_REVIEW |
| REQ-016-003 | AC-016-003 | S03, S06 | focused FTEWriter test | IN_REVIEW |
| REQ-016-004 | AC-016-004 | S04, S06 | focused SDG test | IN_REVIEW |
| REQ-016-005 | AC-016-005, AC-016-006, AC-016-007, AC-016-008, AC-016-009 | S05, S06, S07 | validation E-016-VALIDATION; safety E-016-SAFETY; no write E-016-NO-HARDWARE-WRITE; pre-S07 remediation | IN_REVIEW |

## Acceptance criteria → substeps

| Acceptance criterion | Requirement | Substeps | Status |
|---|---|---|---|
| AC-016-001 | REQ-016-001 | S01, S02, S03 | IN_REVIEW (focused test) |
| AC-016-002 | REQ-016-002 | S02, S06 | IN_REVIEW (focused test) |
| AC-016-003 | REQ-016-003 | S03, S06 | IN_REVIEW (focused test) |
| AC-016-004 | REQ-016-004 | S04, S06 | IN_REVIEW (focused test) |
| AC-016-005 | REQ-016-005 | S05, S06 | IN_REVIEW (canonical schema/UI; evidence in `test_core_config.py`, `test_web_api.py`, `pages.js`; pre-S07 runtime verification remains) |
| AC-016-006 | REQ-016-005 | S06 | IN_REVIEW (full validation, 286 non-E2E tests; fake-client physical-I/O lockout covered; jitter distribution is minor/non-blocking) |
| AC-016-007 | REQ-016-005 | S07 | PENDING HUMAN/HARDWARE |
| AC-016-008 | REQ-016-005 | S05, S07 | IN_PROGRESS |
| AC-016-009 | REQ-016-005 | S06 | IN_REVIEW (terminal status implementation) |

## Scope decisions

| Decision | Step16 status |
|---|---|
| Physical write default OFF, explicit writer switch, test-runtime I/O lockout | Mandatory safety invariant |
| Offline/missing GoodWe data enters safe mode | Mandatory safety invariant |
| Central GoodWeManager boundary, read-back, persistent audit | Mandatory safety invariant |
| First physical write only in explicit human S07 verification | Mandatory safety invariant |
| Cryptographic/immutable authorization evidence | Out of scope; explicit local human evidence is sufficient |
| Production GoodWe optimization rules | Out of scope |
| Detailed DBF header fingerprint hardening | Out of scope |
| Explicit unsupported metadata, jitter-distribution tests, extra traceability hardening | Minor/non-blocking |
| GoodWe/SDG UI, canonical timeout/config consistency, stale diagnostics, truthful evidence | Required before S07 |

## Komponenta → Soubor Mapping

| Komponenta | Primární soubor | Testy |
|---|---|---|
| GoodWeManager | `dev/hec/readers/goodwe_manager.py` | `dev/hec/tests/test_step16_goodwe_implementation.py` |
| FTEReader | `dev/hec/readers/fte_reader.py` | `dev/hec/tests/test_step16_goodwe_implementation.py` |
| FTEWriter | `dev/hec/writers/fte_writer.py` | `dev/hec/tests/test_step16_goodwe_implementation.py` |
| SDGHistoryReader | `dev/hec/readers/sdg_history_reader.py` | `dev/hec/tests/test_step16_goodwe_implementation.py` |
| Config schema | `dev/hec/core/schema.py` (update) | `dev/hec/tests/test_step16_goodwe_implementation.py` |
| Web API | `dev/hec/web/api.py` (update) | `dev/hec/tests/test_step16_goodwe_implementation.py` |

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
