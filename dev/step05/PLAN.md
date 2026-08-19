# Krok 05 – analýza a archivace (milník M3)

Cíl: z nasbíraných dat udělat čísla, která něco znamenají – a udržet historii
v rozumné velikosti, aby se na Raspberry Pi nezaplnila karta.

## Co krok obsahuje

| Modul | Obsah |
|---|---|
| `storage/archiver.py` | archivace po 30 dnech, gzip, ověření kopie, tolerance nedostupného NAS |
| `analysis/summaries.py` | denní bilance: výroba, spotřeba, odběr, dodávka, baterie, vlastní spotřeba, soběstačnost, náklad |
| `analysis/appliances.py` | detekce cyklů spotřebičů (práh + hystereze + minimální délka) a typický profil |
| `analysis/phases.py` | zatížení L1/L2/L3, nesymetrie, doporučení pro člověka |
| `analysis/heatpump.py` | spotřeba TČ, doba běhu, měrná spotřeba na denostupeň |
| `core/maintenance.py` | vlákno údržby: dopočet bilancí, cyklů a archivace |
| API + UI | `/api/phases`, `/api/heatpump`; sekce Analýza na stránce Historie |

## Rozhodnutí

1. **Topný faktor se nepočítá.** Bez měření tepelného výkonu by šlo o vymyšlené
   číslo. Počítá se, co je měřitelné: spotřeba, doba běhu a kWh na denostupeň.
   Až přibude měření tepla, dopočet je triviální.
2. **Bez ceníku se náklad nedopočítává.** Když pro daný den chybí `ote-*.json`,
   vrátí se náklad 0 a příznak `priced: false` – raději žádné číslo než odhad.
3. **Náklad se počítá po čtvrthodinách**, tedy v periodě, ve které se cena
   skutečně mění, ne z denního průměru.
4. **Detekce cyklů má hysterezi.** Spotřebič v pohotovosti (8 W) běžící cyklus
   neukončí; mezera v měření delší než 10 minut ano – přes díru se nedopočítává.
5. **Fáze se nikdy nepřepojují automaticky** (kap. 10 zadání). Výstupem je
   doporučení s překladovým klíčem, nikoli zásah.
6. **Archivace maže lokální soubor až po ověření otisku kopie.** Odpojený NAS
   je běžný provozní stav – zkusí se příště, historie zůstává.
7. **Údržba běží ve vlastním vlákně** a chyba jednoho kroku neshodí ostatní
   ani sběr dat.

## Nalezená a opravená chyba

Vzorek s časovou značkou přesně o půlnoci se započítával do dvou dnů zároveň
(denní bilance i analýza TČ). `JsonlStorage.query()` proto umí `end_exclusive`
a denní řezy jej používají. Odhaleno testem
`test_run_for_missing_skips_days_without_data`.

## Akceptační kritéria

- [x] 140 testů zeleně, `ruff check .` bez nálezu.
- [x] Nedostupný archiv nikdy nesmaže lokální data (test).
- [x] Poškozená kopie se zahodí a lokální soubor zůstane (test).
- [x] Denní bilance sedí na kontrolním příkladu (2 kW × 24 h = 48 kWh).
- [x] Detekce cyklu myčky najde začátek, konec, trvání, energii i špičku.
- [ ] Porovnání detekovaných cyklů s realitou u zadavatele – čeká na provoz Shelly.
