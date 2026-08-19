# CLAUDE.md

Pokyny pro práci v tomto repozitáři.

## Co to je

**Home Energy Controller (HEC)** – lokální systém pro měření, analýzu, predikci
a optimalizaci energetických toků domácnosti: FVE GoodWe, baterie, síť, tepelné
čerpadlo TNG, spotové ceny OTE, počasí, Shelly měření spotřebičů.

Cíl není skript pro jednu domácnost, ale **profesionální produkt k nabízení**:
jazykové mutace CZ/EN, rozšiřitelnost o další zařízení, nasaditelnost u zákazníka.

Běží primárně na Raspberry Pi, vyvíjí se na Windows, ovládá se z prohlížeče
(desktop, tablet, Android/PWA). Zadání: `HOME_ENERGY_CONTROLLER_DEVELOPMENT_PROMPT.md`.

## Struktura repozitáře

```text
/                       funkční prototypy – ZMRAZENÉ, viz pravidlo 1
dev/                    veškerý nový vývoj
dev/stepNN/             plány a rozhodnutí jednotlivých etap
dev/hec/                samotný produkt (vzniká od kroku 02)
data/ logs/ history/    provozní data – nikdy se necommitují
```

Aktuální stav a % dokončení každého souboru: `dev/step01/PROJECT_STRUCTURE.md`.
Plán vývoje a fáze M0–M6: `dev/step01/DEVELOPMENT_PLAN.md`.
Vizuální jazyk a paleta grafů: `dev/step01/UI_DESIGN.md`.
Jazykové mutace: `dev/step01/I18N.md`.
Nasazení a API produktu: `dev/hec/docs/DEPLOYMENT.md`, `dev/hec/docs/API.md`.

## Tvrdá pravidla

1. **Skripty v kořeni se nemění.** `tng_controller.py`, `ote_reader.py`,
   `weather_reader.py`, `goodwe-read.py` běží v provozu. Nová funkčnost vzniká
   v `dev/hec/`. Prototyp se smí odstranit teprve tehdy, až je jeho funkce
   přenesena, pokryta testy a ověřena na reálném hardwaru.
2. **Change-gate TNG je nedotknutelný.** Potvrzovací cyklus
   `LastSettingsNotConfirmed: false → true → false` a minimální interval 900 s
   mezi zápisy chrání tepelné čerpadlo. Žádná optimalizace jej neobchází.
   Před úpravou čehokoli okolo zápisu do TNG musí existovat test na stávající chování.
3. **Žádná tajemství do gitu.** Hesla, klíče, tokeny a hashe patří do `.env`.
   `connect.json` v historii repozitáře už jednou uniklo – nezhoršovat to.
   Tajemství se nikdy nevypisuje do logu ani do diagnostického exportu.
4. **Formáty dat jsou kontrakt.** `data/ote-*.json`, `data/weather.json`,
   `data/runtime_state.json` a JSONL telemetrie mají zdokumentovanou strukturu
   (`dev/step01/DEVELOPMENT_PLAN.md`, sekce 2). Zpětná kompatibilita se drží,
   nová pole se přidávají, stávající se nepřejmenovávají.
5. **Bezpečnost a komfort mají přednost před optimalizací.** Při chybějících
   nebo zastaralých datech se optimalizace zastaví (safe mode), nikdy se
   nehádá hodnota.
6. **Žádný text pro uživatele natvrdo.** Ani v Pythonu, ani v JS, ani v hláškách
   controlleru – vždy překladový klíč (`dev/step01/I18N.md`).
7. **Multiplatformnost.** `pathlib.Path`, žádné natvrdo psané oddělovače cest,
   žádný předpoklad Windows ani Linuxu. Kód musí běžet na Pi i na Windows.

## Práce v krocích

Vývoj je členěný na číslované kroky v `dev/stepNN/`. Každý krok má vlastní plán
a akceptační kritéria. Číslo se nikdy nepřepisuje – dokončený krok zůstává jako
záznam rozhodnutí. Nový plán = nový adresář s dalším číslem, plus řádek
v tabulce v `dev/README.md`.

## Příkazy

```bash
# produkt (dev/hec)
py dev/run.py --init                    # vytvoří konfiguraci a .env
py dev/run.py --once                    # jedno kolo čtení všech zdrojů
py dev/run.py --status                  # stav readerů jako JSON
py dev/run.py                           # sběr dat + rozhraní na :8080
py dev/run.py --diagnostics             # ZIP pro podporu (bez tajemství)
pytest                                  # 181 testů
ruff check .                            # lint

# zmrazené prototypy v kořeni
py tng_controller.py --once --dry-run   # bezpečný test TNG bez zápisu
py tng_controller.py --status           # výpis aktuálního stavu TČ jako JSON
py ote_reader.py                        # ceny na dnešek a zítřek
py weather_reader.py                    # aktuální počasí + předpověď
```

Na Linuxu `python3` místo `py`.

**Nikdy nespouštět zápis do TNG bez `--dry-run`**, dokud není jasné, co se pošle.

## Konvence kódu

* Python 3.11+, standardní knihovna má přednost před závislostí.
* Nový reader = jeden soubor v `dev/hec/readers/` implementující `BaseReader`
  + záznam v konfiguraci. Do controlleru se přitom nesahá.
* Readery nikdy nevolají controller; komunikace jde přes `StorageBackend`
  a snapshot.
* Výjimka v jednom readeru nesmí shodit smyčku ani ostatní readery.
* Ukládání do souboru vždy atomicky (zápis do `.tmp` + `replace`).
* Časové značky ISO 8601 **s časovou zónou**, jeden JSON objekt na řádek v JSONL.
* Struktura logu: `ts | level | module | event | key=value`. Logy anglicky,
  UI česky/anglicky přes překlady.
* Komentáře vysvětlují *proč*, ne *co*; hustotou se drží okolního kódu.

## Grafy a UI

Před psaním jakéhokoli grafu si přečíst `dev/step01/UI_DESIGN.md`, sekci 6.
Paleta je ověřená validátorem, barva se váže na entitu (FVE, baterie, síť…),
**dvojitá osa Y je zakázaná** a žlutá (FVE) nesmí sousedit s oranžovou (odběr).

## Git

* Vývoj na větvi `claude/...`, do `main` se nepushuje bez vyžádání.
* Commit message anglicky, v rozkazovacím způsobu, popisuje důvod změny.
* Pull request se zakládá jen na výslovné vyžádání.
* Do commitu nikdy nepatří `data/`, `logs/`, `history/`, `.env` ani `connect.json`
  s reálnými hodnotami.

## Otevřené otázky

Seznam rozhodnutí, která čekají na zadavatele, je na konci
`dev/step01/DEVELOPMENT_PLAN.md` (sekce 9). Při nejistotě se ptát, ne hádat –
zvlášť u čehokoli, co zapisuje do tepelného čerpadla.
