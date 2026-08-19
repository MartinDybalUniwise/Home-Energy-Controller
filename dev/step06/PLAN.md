# Krok 06 – predikce (milník M4)

Cíl: odpovědět na třetí otázku UX principu – **co bude dál** – a to bez falešné
přesnosti.

## Co krok obsahuje

`controller/predictor.py` a napojení na údržbu a API:

| Předpověď | Model |
|---|---|
| Výroba FVE | ozáření z předpovědi × poměr naučený z vlastní historie (kWh na kWh/m²) |
| Spotřeba domu | medián denní spotřeby zvlášť pro pracovní dny a víkend |
| Potřeba tepla | spotřeba TČ na denostupeň, naučená z vlastních dat |
| Nabití baterie | jednoduchá bilance přebytku a deficitu, meze 10–100 % |
| Náklad | bilance × ceny OTE pro daný den |
| Okna | nejlevnější souvislé dvouhodinové okno pro spotřebiče a pro ohřev vody (jen v denní době) |

Denní bilance byla rozšířena o `mean_outside_c`, `degree_days`
a `irradiation_kwh_m2` – bez nich se nemá z čeho učit.

## Rozhodnutí

1. **Žádné strojové učení.** Modely jsou poměry a mediány, které jde ručně
   přepočítat a obhájit před zákazníkem. Zadání to říká výslovně (kap. 29).
2. **Každý výstup má interval a jistotu.** Šířka pásma se řídí množstvím
   naučených dat: do 7 dnů ±35 %, do 21 dnů ±20 %, dál ±12 %. Bez historie
   systém neříká „19,4 kWh“, ale „13–26 kWh, jistota nízká“.
3. **Bez cen se náklad nepočítá.** `cost_czk: null` a `prices_known: false`
   je poctivější než číslo z průměru, který nikdo neslíbil.
4. **Bez známé kapacity baterie se nabití nepredikuje.**
5. **Predikce se ukládá** do `history/prediction/`, aby šla zpětně porovnat
   se skutečností. `accuracy` počítá MAPE výroby proti denní bilanci.
6. **Okno pro ohřev vody se hledá jen mezi 8:00 a 17:00.** Levná hodina ve
   tři ráno je k ničemu, když má teplá voda vydržet přes den; pro spotřebiče
   se hledá v celém dni.

## Oprava odhalená testem

Učící okno prediktoru bylo o den kratší než okno denních bilancí, takže
nejstarší den z historie vypadl. Obě okna jsou nyní stejná.

## Akceptační kritéria

- [x] 155 testů zeleně, `ruff check .` bez nálezu.
- [x] Naučený poměr sedí na kontrolním příkladu (40 kWh / 5 kWh/m² = 8).
- [x] Bez počasí, bez cen i bez kapacity baterie systém říká „nevím“, nehádá.
- [x] Zpětné vyhodnocení predikce funguje (MAPE proti skutečné výrobě).
- [ ] Ověření přesnosti na reálném provozu (cíl MAPE < 25 % po 14 dnech).
