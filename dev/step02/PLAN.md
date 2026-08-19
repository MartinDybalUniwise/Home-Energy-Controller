# Krok 02 – bezpečnostní základ, jádro a regresní testy (milník M0)

Předpoklad všeho dalšího vývoje. Cíl: mít čím chránit stávající funkční kód
při refaktoru a mít kam ukládat konfiguraci bez tajemství.

## Co krok obsahuje

| Oblast | Výsledek |
|---|---|
| Ochrana repozitáře | `.gitignore` (data, logy, historie, `.env`), `.env.example`, `connect.example.json` |
| Konfigurace | `hec/core/schema.py` (83 polí s typem, rozsahem, výchozí hodnotou), `hec/core/config.py` (validace, zálohy, atomický zápis, cesty) |
| Tajemství | `hec/core/secrets.py` – načtení `.env`, dosazení `${VAR}`, maskování, sběr hodnot pro filtr logu |
| Logování | `hec/core/logging_setup.py` – formát `ts \| level \| module \| event \| key=value`, rotace, filtr tajemství |
| Datové typy | `hec/core/model.py` – `Sample`, `ReaderStatus`, `Decision` |
| Čas | `hec/core/timeutil.py` – ISO 8601 s zónou, stáří dat, okna přes půlnoc |
| Testy | 43 testů: regrese TNG / OTE / weather + jádro |
| CI | GitHub Actions – `ruff` + `pytest` na Pythonu 3.11 a 3.12 |

## Rozhodnutí

1. **Bez `jsonschema` a bez `fastapi`.** Konfigurační schéma i budoucí web stojí
   na standardní knihovně. Na Raspberry Pi u zákazníka je každá závislost
   něco, co se musí instalovat, aktualizovat a auditovat. Runtime závislosti
   zůstávají dvě: `requests` a `beautifulsoup4` – obě už proveřeně obsluhují
   TNG a OTE. `goodwe` je volitelná.
2. **`connect.json` zatím zůstává verzovaný.** Heslo je v historii repozitáře
   od prvního commitu; odstranění souboru z indexu by tajemství nezneplatnilo,
   ale rozbilo by běžící instalaci při dalším `git pull`. Skutečné řešení je
   změna hesla, kterou zadavatel zatím odložil. Připraveno je vše ostatní:
   `.env`, `connect.example.json` s `${VAR}` a dosazování v `config.load()`.
   **Až padne rozhodnutí o změně hesla:** změnit heslo na tngsmart.cz →
   vyplnit `.env` → `git rm --cached connect.json`.
3. **Minimální interval zápisu do TNG má v schématu tvrdé minimum 900 s.**
   Konfigurace jej neumí snížit; ochrana čerpadla se nedá odkliknout omylem.
4. **Neznámé klíče konfigurace se zachovávají.** Starší verze systému nesmí
   při zápisu zahodit nastavení, které přidala novější.
5. **Regresní testy pracují proti falešným odpovědím**, ne proti síti. Test
   `test_read_state_parses_settings_and_telemetry` prochází celou skutečnou
   parsovací cestou včetně dělení telemetrie deseti a zápisu JSONL.

## Akceptační kritéria

- [x] `pytest` zelený (43 testů), `ruff check .` bez nálezu.
- [x] Chování `tng_controller.py` nezměněno – soubor se v tomto kroku vůbec
      neupravoval, testy popisují jeho současné chování.
- [x] Konfigurace se validuje, zálohuje a zapisuje atomicky.
- [x] Tajemství se nedostane do logu ani do veřejného výpisu konfigurace.
- [ ] Změna hesla k TNG a odstranění `connect.json` z indexu – čeká na zadavatele.

## Poznámka k lintu

Prototypy v kořeni jsou z kontroly `ruff` vyňaty. Nejsou zanedbané – jsou
zmrazené a jakákoli automatická úprava by porušila pravidlo 1 v `CLAUDE.md`.
