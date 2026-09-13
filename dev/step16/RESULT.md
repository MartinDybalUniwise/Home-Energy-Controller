# GoodWe Integration Refactor – Result

> Status: IN_PROGRESS / REVIEW REQUESTED. The design and specification for
> S01–S05 are frozen; S06 implementation evidence is recorded below, while
> pre-S07 remediation and acceptance review remain open.
> S07 remains the separate human/hardware verification gate.

## Definice DONE

Krok je DONE když:

1. ✅ Všechna acceptance kritéria projdou (AC 1–9)
2. ✅ Hardware test na 192.168.2.116 potvrdí plnou funkčnost
3. ✅ RESULT.md obsahuje evidence každého AC s datum/čas potvrzení
4. ✅ Žádné unresolved blockers
5. ✅ Kód projde code review
6. ✅ Testy jsou zelené (100% AC coverage)

## Implementation evidence

- S01–S05: design and specification complete and approved for implementation
- S06: GoodWeManager, FTEReader, FTEWriter, SDGHistoryReader, terminal status
  output, canonical config, diagnostics UI, focused tests, safe preview, and
  validation evidence are available for review
- S07: separate human/hardware verification gate before any live write or
  controller enablement is approved

### Automated validation

- `python -m ruff check .`: PASS
- `python -m pytest -m "not e2e"`: PASS, 286 passed, 23 deselected after S06 fixes
- `python dev/sdd/tools/validate_step.py --phase ready --step dev/step16`: PASS
- Safe preview at `http://127.0.0.1:8181`: PASS, runtime smoke passed
- Real E2E: PASS, 23 passed with `HEC_RUN_E2E=1`
- `python dev/sdd/tools/full_validation.py`: PASS, SDD VALIDATION PASSED
- Physical GoodWe writes: NOT RUN
- Controller activation: NOT RUN
- S07 human/hardware verification: NOT STARTED

## Completed Acceptance Criteria

(Vyplní se během Fáze B–G)

### AC 1: GoodWeManager
- [x] Fáze: B (core)
- [x] Test: `test_step16_goodwe_implementation.py`
- [x] Hotovo: automated S06 validation
- [x] Evidence: `dev/hec/tests/test_step16_goodwe_implementation.py`, focused test PASS

### AC 2: FTEReader
- [x] Fáze: B (core)
- [x] Test: `test_step16_goodwe_implementation.py`
- [x] Hotovo: automated S06 validation
- [x] Evidence: focused implementation test and full suite PASS

### AC 3: FTEWriter
- [x] Fáze: C (writer)
- [x] Test: `test_step16_goodwe_implementation.py`
- [x] Hotovo: automated S06 validation
- [x] Evidence: focused implementation test and audit/readback assertions PASS

### AC 4: SDGHistoryReader
- [x] Fáze: D (SDG)
- [x] Test: `test_step16_goodwe_implementation.py`
- [x] Hotovo: automated S06 validation
- [x] Evidence: focused implementation test PASS

### AC 5: Konfigurace
- [ ] Fáze: E (web)
- [x] Test: `test_core_config.py`, `test_web_api.py`, `pages.js`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: `dev/hec/core/schema.py`, `dev/hec/tests/test_core_config.py`, `dev/hec/tests/test_web_api.py`; final review pending

### AC 6: Web Diagnostika
- [ ] Fáze: E (web)
- [x] Test: `test_web_api.py`, `pages.js`, `cs.json`, `en.json`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: `dev/hec/web/frontend/js/pages.js`, `dev/hec/locales/cs.json`, `dev/hec/locales/en.json`; final review pending

### AC 7: Testy
- [ ] Fáze: B–G (průběžně)
- [ ] Coverage: 100% nových komponent
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (pytest report)

### AC 8: Hardware Test
- [ ] Fáze: F (hardware)
- [ ] Zařízení: 192.168.2.116
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (hardware test log)
- [ ] Testované: export limit, charge, discharge, retry, timeout, SDG compatibility, degradation

### AC 9: Dokumentace
- [ ] Fáze: G (closure)
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (commit)

## Phase Completion Dates

| Fáze | Začátek | Konec | Vedoucí |
|---|---|---|---|
| A – Design & Prep | - | - | - |
| B – Core (GoodWeManager + Reader) | - | - | - |
| C – Writer & Audit | - | - | - |
| D – SDG Integration | - | - | - |
| E – Web & Config | - | - | - |
| F – Hardware Test | - | - | - |
| G – Documentation & Closure | - | - | - |

## Risks & Resolutions

| Riziko | Status | Řešení | Uzavřeno |
|---|---|---|---|
| Kolize SDG reader + HEC writer | 🟡 high | Lock/mutex, read-back verification | - |
| Ztráta GoodWe komunikace | 🟡 high | Graceful degradation, last-known state | - |
| Neznámé registry | 🟢 low | Never guess, always check library first | - |
| Poškozené SDG logy | 🟡 medium | Graceful error handling, skip corrupted | - |

## Notes

- S06 application and documentation evidence is returned for review; the step
  remains IN_PROGRESS and must not advance to S07 until the reviewer accepts
  the pre-S07 remediation items.
- Hardware test je **povinný** – bez něj se step nemůže označit DONE
- No physical GoodWe write operation or controller activation was performed.

## Sign-Off

- [ ] Step vedoucí: (potvrzení completion)
- [ ] Hardware tester: (potvrzení hardware test)
- [ ] Code reviewer: (potvrzení PR)

Datu: ___________
