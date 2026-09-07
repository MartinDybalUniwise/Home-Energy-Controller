# GoodWe Integration Refactor – Result

> Status: 📝 PLANNED (soubory struktury, implementace nespuštěna)

## Definice DONE

Krok je DONE když:

1. ✅ Všechna acceptance kritéria projdou (AC 1–9)
2. ✅ Hardware test na 192.168.2.116 potvrdí plnou funkčnost
3. ✅ RESULT.md obsahuje evidence každého AC s datum/čas potvrzení
4. ✅ Žádné unresolved blockers
5. ✅ Kód projde code review
6. ✅ Testy jsou zelené (100% AC coverage)

## Completed Acceptance Criteria

(Vyplní se během Fáze B–G)

### AC 1: GoodWeManager
- [ ] Fáze: B (core)
- [ ] Test: `test_readers_goodwe_manager.py`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

### AC 2: FTEReader
- [ ] Fáze: B (core)
- [ ] Test: `test_readers_fte.py`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

### AC 3: FTEWriter
- [ ] Fáze: C (writer)
- [ ] Test: `test_writers_fte.py`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

### AC 4: SDGHistoryReader
- [ ] Fáze: D (SDG)
- [ ] Test: `test_readers_sdg_history.py`
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

### AC 5: Konfigurace
- [ ] Fáze: E (web)
- [ ] Test: `test_config.py` (update)
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

### AC 6: Web Diagnostika
- [ ] Fáze: E (web)
- [ ] Test: `test_web_api.py` (update)
- [ ] Hotovo: (datum se vyplní)
- [ ] Evidence: (link na commit/PR)

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

- Implementace ještě nespuštěna (plánování 2026-09-07)
- Hardware test je **povinný** – bez něj se step nemůže označit DONE
- Všechny daty budou vyplněny během implementace

## Sign-Off

- [ ] Step vedoucí: (potvrzení completion)
- [ ] Hardware tester: (potvrzení hardware test)
- [ ] Code reviewer: (potvrzení PR)

Datu: ___________
