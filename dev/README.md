# dev/ – vývojový adresář Home Energy Controller

Veškerý nový vývoj probíhá **výhradně v tomto adresáři**. Kořen repozitáře
obsahuje funkční prototypy (`tng_controller.py`, `ote_reader.py`,
`weather_reader.py`, `goodwe-read.py`), které běží v provozu a **nesmí se měnit**,
dokud jejich funkce není přenesena, otestována a ověřena na reálném hardwaru.

## Číslování kroků

Každá etapa vývoje má vlastní adresář `stepNN/` s vlastním plánem a dokumentací.
Číslo se nikdy nepřepisuje – dokončený krok zůstává jako záznam rozhodnutí.

| Krok | Obsah | Stav |
|---|---|---|
| `step01/` | Analýza repozitáře, plán vývoje, struktura projektu s % dokončení, UI design, jazykové mutace | ✅ hotovo |
| `step02/` | Bezpečnostní základ, jádro (config, secrets, logging, model), regresní testy (M0) | ✅ hotovo |
| `step03/` | Úložiště, readery, plánovač smyčky (M1) | ✅ hotovo |
| `step04/` | Web API, frontend, jazykové mutace (M2) | ✅ hotovo |
| `step05/` | Analýza a archivace (M3) | ✅ hotovo |
| `step06/` | Predikce (M4) | ✅ hotovo |
| `step07/` | Řízená optimalizace (M5) | ✅ hotovo |
| `step08/` | Produktizace (M6) | ✅ hotovo |
| `step09/` | Rozšíření: sdílení energie (EDC), predikce, externí měření – plán a fáze A | 🚧 plán hotov, fáze A ve vývoji |

Další kroky se doplňují sem, jakmile vzniknou.

## Obsah kroku

Každý `stepNN/` obsahuje minimálně:

* `PLAN.md` nebo `DEVELOPMENT_PLAN.md` – co se v kroku dělá a proč,
* akceptační kritéria – jak se pozná, že je krok hotový,
* případné doplňující dokumenty (design, datové formáty, měření).

## Krok 01 – dokumenty

| Soubor | Co obsahuje |
|---|---|
| [`step01/DEVELOPMENT_PLAN.md`](step01/DEVELOPMENT_PLAN.md) | Inventura repozitáře, zjištěná rozhraní, cílová architektura, fáze M0–M5, rizika |
| [`step01/PROJECT_STRUCTURE.md`](step01/PROJECT_STRUCTURE.md) | Kompletní adresářová struktura se seznamem skriptů a % dokončení |
| [`step01/UI_DESIGN.md`](step01/UI_DESIGN.md) | Vizuální jazyk webu podle televizní meteo grafiky, design tokeny, ověřená paleta grafů |
| [`step01/I18N.md`](step01/I18N.md) | Jazykové mutace CZ/EN a postup přidání dalšího jazyka |
