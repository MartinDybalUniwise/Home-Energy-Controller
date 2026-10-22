# Acceptance criteria

- [x] AC-026-001: Diff zachová řízení a rozsah; preview controller/TNG writes/GoodWe vypnuté.
- [x] AC-026-002: Test času měření, půlnoci a obou DST přechodů; doložené pásmo, žádný nepodložený posun SDG ani falešná historická settings.
- [x] AC-026-003: Několikadenní odstávka, opakování, neuspořádané vzorky, opravy a fault injection zápisu/checkpointu bez duplicit/ztráty.
- [x] AC-026-004: Dry-run na konzistentní kopii, manifest zálohy, report před/po podle zdroje/období a druhý apply s nulou změn; mezery přiznány.
- [x] AC-026-005: Stejná data pro wall/CPU/paměť/I-O/checkpoint/log před/po; nulový přírůstek i backlog, staré změny zachyceny, rotace a omezené dávky ověřeny.
- [x] AC-026-006: Skutečný browser test čísla/dialogu/Prague času/zavření a absence JS chyb; releasy nejnovější nahoře bez vymyšlených dat.
- [x] AC-026-007: Zaznamenané pytest/ruff/SDD/full_validation, review a Human Gate; skipped není PASS, výchozí chyby neskrývat.
- [x] AC-026-008: Povinné PR kontroly/merge, tag na nasazeném ověřeném commitu, jedna instance, zachované controllery/config, správná nová historie a logy; čas restartu/záloha/rollback doloženy.
