# Step 18 Plan

## Goal

Plan and execute the UI/UX redesign of the Home Energy Controller web application
based on authoritative visual references for an 11" Full HD (1920x1080) landscape
wall touchscreen. The redesign maximizes information density, improves readability
from 1–2 meters, enforces touch-first interactions (min 64x64 px), and structures
the Today (`Dnes`) and Energy Flow (`Tok energie`) pages into high-value decision
hubs while maintaining all existing backend contracts, safe mode invariants, and
i18n catalogs.

---

## 1. Cílový UX/UI návrh (Target UX/UI Design)

- **Vizuální styl:** Moderní tmavý motiv s vysokým kontrastem (WCAG AA min. 4.5:1 pro text, 3:1 pro grafické prvky).
- **Hierarchie:**
  1. *Horní panel:* Pozdrav, datum, přesný čas, integrovaná meteo stanice (teplota, stav počasí, vítr, srážky, východ/západ slunce, štítek FVE vhodnosti).
  2. *Hero sekce doporučení:* Dominantní karta nejlepšího okna spotřeby (např. 11:30–14:30), akční tlačítko „Proč právě teď?“ a 3 stavové karty („Teď je“, „Vyhněte se“, „Očekává se“).
  3. *Živá telemetrie (KPI lišta):* 6 karet s velkými čísly (FVE, Spotřeba domu, Baterie SoC/výkon, Síť import/export, Spotová cena, TČ/TUV).
  4. *Energetický rytmus dne:* 24h timeline s barevnými bloky vhodnosti (Best – zelená, OK – modrá, Avoid – oranžová/červená), ikonami počasí, teplotami, pravděpodobností srážek, textovým hodnocením, cenou elektřiny pod každým blokem, vertikální ryskou aktuálního času (`now`) a boxem odhadu výroby.
  5. *Spodní pracovní plocha (3 panely):*
     - Doporučení spotřebičů (časové mini-pruhy, hvězdičky priorit, odhad úspory).
     - Nejbližší vhodné okno (SVG donut gauge odpočet času, přínos v kWh/Kč, 2 další okna).
     - Multi-křivkový graf (FVE, Spotřeba, Cena) s přepínáním horizontu (Den / 2 dny / 7 dní).
  6. *Spodní akční lišta:* Rotující tipy dne, denní očekávaná úspora, tlačítka akcí.
  7. *Navigační sidebar:* Levý sloupec s primární navigací a sbalitelným Servisním menu.

---

## 2. Rozsah stránek (Scope of Pages)

- **Primární stránky:**
  - `Dnes` (`#/overview`): Kompletní redesign hlavní obrazovky podle předlohy.
  - `Tok energie` (`#/flow`): Zpřehlednění toku energie s novými design tokeny a kontrastními kartami.
- **Sekundární stránky a navigace:**
  - `Sidebar Navigation`: Levý panel s hlavním menu (`Dnes`, `Výhled`, `Tok energie`, `Historie`).
  - `Servisní menu`: Sbalitelná sekce pro technické stránky (`Nastavení`, `Stav`, `Data / Logy`, `Finance`).
  - `Výhled` (`#/prediction`) & `Historie` (`#/history`): Sladění typografie a karet s novým systémem tokenů.

---

## 3. Komponenty, které budou měněny (Affected Components)

| Soubor | Účel úpravy |
|---|---|
| `dev/hec/web/frontend/index.html` | Nová struktura DOM: sidebar, topbar widget, modální dialog „Proč právě teď?“, spodní lišta. |
| `dev/hec/web/frontend/css/tokens.css` | Aktualizace barevné palety, proměnných pro velikosti písma, mezer, rádiusů a dotykových cílů. |
| `dev/hec/web/frontend/css/app.css` | Kompletní stylování nového layoutu, zero-waste space, flexbox/grid pro 1080p, animace, responzivita. |
| `dev/hec/web/frontend/js/advisor.js` | Renderování Hero doporučení, KPI lišty, 24h rytmu, spotřebičů, donut gauge a spodní lišty. |
| `dev/hec/web/frontend/js/chart.js` | Kreslení multi-křivkového grafu s vysokým kontrastem, markerem `now` a přepínačem horizontu. |
| `dev/hec/web/frontend/js/flow.js` | Úprava schématu toku energie pro nový vizuální styl a konzistentní barvy. |
| `dev/hec/web/frontend/js/icons.js` | Rozšíření a sjednocení SVG ikon (počasí, trendy, spotřebiče, šipky toků). |
| `dev/hec/web/frontend/js/app.js` | Obsluha rozbalování Servisního menu, modálního dialogu a časovače rotujících tipů. |
| `dev/hec/locales/cs.json` & `en.json` | Překladové klíče pro všechny nové UI texty, popisky a dialogy. |

---

## 4. Vizuální pravidla (Visual & Typography Rules)

- **Typografie a velikosti:**
  - Nadpisy stránek / Sekční titulky: 36–48 px / Semibold.
  - Tělo textu / Základní popisky: 18–22 px / Regular.
  - Dominantní čísla (hlavní KPI / časy): 64–96 px / Bold.
  - Vedlejší čísla a jednotky: 28–36 px / Semibold.
  - Minimální velikost písma: 18 px (žádný drobný nečitelný text).
- **Barevné kódování a kontrast:**
  - Zelená (`#10b981` / `--status-good`): Pozitivní stav, ideální čas, FVE výroba.
  - Modrá (`#3b82f6` / `--status-neutral`): Neutrální stav, spotřeba domu, OK čas.
  - Oranžová / Červená (`#f59e0b` / `#ef4444`): Varování, vysoká cena, nevhodný čas (Avoid).
  - Žlutá (`#fbbf24`): Výhradně pro slunce / FVE výrobu (nesousedí přímo s oranžovou).
  - Kontrast textu vůči pozadí min. 4.5:1.

---

## 5. Pravidla pro Responsive a 11" Full HD Wall Screen

- **Zero-Waste Space:**
  - Padding kontejnerů 16 px, mezery mezi kartami 12–16 px.
  - Žádné prázdné nevyužité plochy.
- **1920x1080 Landscape (Primární cíl):**
  - Veškerý klíčový obsah obrazovky `Dnes` se musí vejít na jednu obrazovku bez nutnosti vertikálního scrollování.
- **Touch-First:**
  - Minimální rozměr interaktivních prvků (tlačítka, přepínače, položky menu): 64×64 px.
  - Ikony min. 32–48 px.
- **Responzivní přizpůsobení:**
  - `1440x900` / `1280x800`: Zachování mřížky s proporcionálním škálováním.
  - `1024x768`: 2-sloupcové přeskupení spodní pracovní plochy.
  - `390x844` (Mobil): Vertikální skládání karet, zachování čitelnosti a touch ergonomics.

---

## 6. Data Binding a zachování existující funkčnosti

- **Zdrojová data:**
  - `/api/current`: Okamžitý stav střídače GoodWe, TČ TNG, OTE ceny a Shelly.
  - `/api/weather`: Aktuální stav, denní předpověď (východ/západ, min/max) a hodinová předpověď (teplota, srážky, GHI).
  - `/api/prices`: Dnešní a zítřejší hodinové spotové ceny OTE.
  - `/api/prediction`: Algoritmická predikce výroby a optimální okno pro spotřebiče.
- **Odolnost proti výpadkům:**
  - Pokud chybí OTE nebo předpověď, komponenty zobrazí korektní zástupný stav („–“ nebo „Awaiting forecast“) bez rozpadu rozvržení a bez chyb v JS konzoli.
- **Bezpečnost:**
  - Žádné změny v backendu, žádný zápis na hardware.

---

## 7. Testovací strategie (Testing Strategy)

1. **Lint a statická kontrola:** `python -m ruff check .`
2. **Unit testy backendu a šablon:** `python -m pytest dev/hec/tests -m "not e2e"`
3. **E2E Browser testy v izolovaném preview:** `python -m pytest dev/hec/tests/e2e -m e2e`
4. **Validace SDD struktury:** `python dev/sdd/tools/validate_step.py --step dev/step18`
5. **Full repository validation:** `python dev/sdd/tools/full_validation.py`

---

## 8. Playwright scénáře (E2E Scenarios)

- `test_today_screen_zero_waste_1080p`: Ověření, že na 1920x1080 nedochází k přetečení a scrollování hlavního pohledu `Dnes`.
- `test_touch_target_sizes`: Ověření minimálních rozměrů navigačních tlačítek a akčních prvků (>= 64px).
- `test_modal_why_now`: Kliknutí na „Proč právě teď?“ otevře vysvětlující dialog s důvody a zavře se křížkem/klikem mimo.
- `test_sidebar_service_menu_toggle`: Rozbalení a sbalení Servisního menu v levém panelu.
- `test_horizon_switcher`: Přepínání grafu (Den / 2 dny / 7 dní).
- `test_i18n_toggle_cz_en`: Ověření správného překladu všech nových UI bloků v češtině i angličtině.
- `test_multi_viewport_smoke`: Ověření zobrazení na 1920x1080, 1440x900, 1280x800, 1024x768 a 390x844.

---

## 9. Human-test kritéria (Human Acceptance Checklist)

- [ ] Vizuální kontrola na 1080p displeji: vzhled odpovídá autoritativním předlohám.
- [ ] Čitelnost z 2 metrů: hlavní číselné hodnoty a doporučení jsou okamžitě rozpoznatelné.
- [ ] Ergonomie dotyku: tlačítka a přepínače lze snadno ovládat prstem bez překliků.
- [ ] Zero waste: žádný prázdný nepoužitý prostor na ploše.
- [ ] Jazyky: plynulé přepnutí mezi CZ a EN bez neznámých klíčů.

---

## 10. Seznam implementačních kroků (Work Packages)

| ID | Pracovní balíček | Hlavní výstup | Závislosti | Stav |
|---|---|---|---|---|
| S01 | Design Tokeny & CSS základy pro Touchscreen | `tokens.css`, nová typografická stupnice, dotykové terče | Žádné | PLANNED |
| S02 | Globální Layout Shellu & Sidebar navigace | `index.html`, `app.css`, layout 1920x1080 bez scrollu | S01 | PLANNED |
| S03 | Topbar meteo widget & Hero Doporučení | `advisor.js`, `app.css`, modal „Proč právě teď?“ | S01, S02 | PLANNED |
| S04 | KPI lišta živé telemetrie (6 karet) | `advisor.js`, `icons.js`, karty s trendy | S01, S02 | PLANNED |
| S05 | Energetický rytmus dne (24h timeline) | `advisor.js`, `app.css`, ryska `now`, box výroby | S01, S03 | PLANNED |
| S06 | Doporučení spotřebičů & Donut Gauge odpočet | `advisor.js`, mini-pruhy, SVG odpočet času | S01, S05 | PLANNED |
| S07 | Multi-křivkový graf, Tok energie & Spodní lišta | `chart.js`, `flow.js`, přepínač horizontu, tip dne | S01, S06 | PLANNED |
| S08 | i18n lokalizace (CZ/EN), Playwright testy a validace | `cs.json`, `en.json`, `test_smoke.py`, validace | S01–S07 | PLANNED |

---

## Execution boundaries

- Tento balíček představuje pouze plánovací fázi a nemění žádný aplikační kód.
- Zmrazené prototypy v kořeni zůstávají nedotčeny.
- Implementace začne až po výslovném schválení Gate A uživatelem.
