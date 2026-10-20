# Požadavky

- REQ-027-001: Testy registrace SDG a Application.accept musí ověřovat skutečný kontrakt: samostatný historický import, žádné implicitní přepínání živé telemetrie.
- REQ-027-002: Formulář musí zachovat null u prázdných volitelných čísel a použít nový jazyk až po úspěšném uložení. Browser test ověří uložený anglický jazyk po reloadu, konkrétní limit i návrat na null a odmítnuté uložení.
- REQ-027-003: Povinná validace bez potlačení chyb; žádná změna controllerů, writerů, plánování ani produkčních dat/configu.

## Objective
Odstranit čtyři reprodukované testové blokace bez změny řízení zařízení.
