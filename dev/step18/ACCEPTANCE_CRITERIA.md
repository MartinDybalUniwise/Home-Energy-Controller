# Step 18 Acceptance Criteria

## Objective

These criteria define the completion conditions for Step 18 (UI/UX Redesign for
Touchscreen Wall Display). In the planning phase, all checkboxes remain unchecked.

## Canonical criteria

- [ ] AC-018-001: 1920x1080 Full HD rozvržení bez zbytečného scrollování a s
  efektivním využitím celé plochy (zero waste space).
- [ ] AC-018-002: Vysoká čitelnost hlavních hodnot a stavů z 1–2 metrů
  (dominantní čísla 64–96 px, základní text 18–22 px, kontrast >= 4.5:1).
- [ ] AC-018-003: Dotykové ovládání s cílovou velikostí interaktivních prvků
  min. 64×64 px, mezerami 12–16 px a zamezením jalových prázdných ploch.
- [ ] AC-018-004: Zachování všech současných funkcí, datových toků, API
  kontraktů a bezpečné chování při výpadku externích dat.
- [ ] AC-018-005: Kompletní jazyková lokalizace CZ a EN pro všechny nové texty,
  popisky a dialogy bez natvrdo vepsaných řetězců.
- [ ] AC-018-006: Správné zobrazení a chování stránky Today (`Dnes`) podle
  autoritativních předloh (Hero sekce, KPI lišta, 24h rytmus, spotřebiče, donut
  gauge, multi-křivka) a stránky Energy Flow (`Tok energie`).
- [ ] AC-018-007: Playwright E2E testy PASS napříč definovanými viewporty
  (1920x1080, 1440x900, 1280x800, 1024x768, 390x844) s nulovými chybami
  v konzoli.
- [ ] AC-018-008: Plná validace repozitáře a SDD kroků (`dev/sdd/tools/validate_step.py`
  a `dev/sdd/tools/full_validation.py`) PASS.
- [ ] AC-018-009: Formální schválení Gate A před implementací a úspěšný
  lidský test (Gate B / Gate C) před finálním označením kroku jako DONE.

## Definition of ready

Step 18 is ready when the planning package is complete, all standard files are
mutually consistent, the manifest validates against schema, and the human
approver authorizes Gate A.
