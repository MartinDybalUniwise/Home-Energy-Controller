# Krok 03 – úložiště, readery a plánovač (milník M1)

Cíl: systém, který spolehlivě sbírá data ze všech pěti zdrojů a ukládá je do
JSONL historie. Žádná nová automatika – zápis do TNG zůstává vypnutý.

## Co krok obsahuje

| Modul | Obsah |
|---|---|
| `storage/base.py` | `StorageBackend` a atomický zápis JSON |
| `storage/jsonl.py` | denní soubory `history/<zdroj>/YYYY-MM-DD.jsonl`, `data/current_<zdroj>.json`, dotaz na rozsah |
| `storage/series.py` | podvzorkování pro grafy, integrace výkonu na kWh |
| `readers/base.py` | retry s exponenciálním backoffem, stav readeru, izolace výjimek |
| `readers/goodwe.py` | mapování veličin měniče včetně fází a směru toků |
| `readers/tng.py` | přenos ověřené logiky včetně change-gate |
| `readers/ote.py` | ceny OTE + přepočet na CZK/kWh, kurz z ČNB |
| `readers/weather.py` | Open-Meteo + východ/západ slunce + kód počasí |
| `readers/shelly.py` | Shelly gen1 i gen2, spotřebiče i Pro 3EM |
| `core/scheduler.py` | jedno vlákno na reader, vlastní interval |
| `core/app.py` | propojení konfigurace, úložiště, readerů a snapshotu |
| `hec/__main__.py`, `dev/run.py` | vstupní body pro Windows i Linux |

## Rozhodnutí

1. **Vlákno na reader.** GoodWe se čte po 10 s a nesmí čekat na pomalou odpověď
   tngsmart.cz. Vlákna jsou daemon, o časový limit se stará samotný reader.
2. **Znaménko toků je konfigurovatelné** (`goodwe.grid_positive_is_import`,
   `battery_positive_is_charge`). Konvence se mezi instalacemi liší a hádat ji
   z dat by znamenalo tiše prohodit odběr s dodávkou.
3. **Chybějící fázové veličiny nejsou chyba.** Každý klíč se hledá mezi několika
   kandidáty; co firmware nevystaví, se prostě nezapíše. Až bude ověřeno na
   reálném měniči, doplní se konkrétní klíče do `FIELD_MAP`.
4. **Každé zařízení Shelly má vlastní časovou řadu** `history/shelly_<název>/`.
   Grafy spotřebičů se tak čtou přímo, bez rozbalování vnořené struktury.
   Nedostupná zásuvka neshodí měření ostatních; teprve když selžou všechny,
   hlásí reader chybu.
5. **Ceny se ukládají v EUR i v CZK.** Konečná cena = spot + distribuce +
   poplatky, celé × (1 + DPH); všechny složky jsou v konfiguraci a ve výchozím
   stavu nulové, takže systém nic nepředstírá. Kurz bere z ČNB s denní cache
   a pádem zpět na hodnotu z konfigurace.
6. **`data/ote-YYYY-MM-DD.json` a `data/weather.json` si drží tvar z prototypu.**
   Nová pole přibyla, žádné se nepřejmenovalo (pravidlo 4 v `CLAUDE.md`).
7. **Zápis do TNG je ve výchozím stavu vypnutý** (`tng.write_enabled: false`).
   Bez něj reader jen loguje, co by poslal. Rozvrhy a change-gate fungují stejně
   jako v prototypu.

## Nalezená a opravená chyba

`Scheduler.run_once()` volal `reader.poll()` přímo a obcházel tím callback
aplikace – jednorázový běh by nenaplnil snapshot a controller by vzorek nikdy
neviděl. Odhaleno testem `test_application_wires_readers_storage_and_snapshot`.

## Akceptační kritéria

- [x] 88 testů zeleně, `ruff check .` bez nálezu.
- [x] Výpadek jednoho readeru neovlivní ostatní (test).
- [x] Historie vzniká v `history/<zdroj>/<den>.jsonl`, aktuální stav v `data/current_<zdroj>.json`.
- [x] Poškozený řádek v JSONL nezneplatní zbytek historie (test).
- [x] Systém startuje na Windows i Linuxu stejným příkazem (`python -m hec`).
- [ ] Ověření na reálném hardwaru (GoodWe fáze, Shelly modely) – čeká na přístup k instalaci.
