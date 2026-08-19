# Krok 07 – řízená optimalizace (milník M5)

Cíl: systém začne sám rozhodovat – ale jen v mezích, které si zákazník nastaví,
a vždy s vysvětlením.

## Co krok obsahuje

| Modul | Obsah |
|---|---|
| `controller/rules.py` | deklarativní pravidla: povolení, priorita, podmínka, akce, limity, důvod jako klíč |
| `controller/controller.py` | rozhodovací kolo, safe mode, provedení přes change-gate, zápis do historie |
| `controller/metrics.py` | doložitelné ukazatele přínosu |
| API + UI | `/api/decisions`, `/api/metrics`; poslední rozhodnutí na Přehledu, přínos v Historii |

Startovní sada pravidel:

1. `dhw_pv_surplus` – přebytek FVE + nabitá baterie + levná elektřina → zvýšit
   cíl TUV na komfortní maximum.
2. `dhw_price_high` – drahá elektřina bez přebytku → stáhnout TUV na komfortní
   minimum a využít setrvačnost.
3. `heating_preheat_cheap` – levné okno a chladno → mírné předtopení o nejvýš
   `max_preheat_k`; v tichém režimu se nespouští.

## Rozhodnutí

1. **Komfortní meze jsou tvrdý strop.** Hodnotu z pravidla controller ještě
   jednou ořízne (`_enforce_limits`) – pravidlo se nemůže „utrhnout“ ani chybou
   v konfiguraci.
2. **Zápis jde výhradně přes change-gate readeru TNG.** Controller nemá vlastní
   cestu do čerpadla; guard 900 s a potvrzovací cyklus platí i pro optimalizaci.
3. **Safe mode při zastaralých datech.** Kritické zdroje (GoodWe, TNG) starší
   než `controller.max_data_age_seconds` → optimalizace stojí, nastavení se
   nemění, sběr dat pokračuje, v UI je varování.
4. **Jedna akce, jedno rozhodnutí za kolo.** Pravidla jsou seřazená podle
   priority; první, které se pro danou akci uplatní, vyhrává. Žádné oscilace
   mezi dvěma pravidly.
5. **Stejný požadavek se neposílá dvakrát.** Opakovaný zápis téže teploty by
   zatěžoval čerpadlo bez užitku.
6. **Zásah do topné křivky se zatím jen doporučuje.** Zápis `HeatTemp_Const`
   nebyl ověřen na reálném hardwaru; do té doby pravidlo rozhodnutí zaznamená,
   ale neodešle. Zapnutí je jednořádková změna, až bude ověřeno.
7. **Přínos se netvrdí, dokud není doložitelný.** Metriky ukazují skutečné
   toky, náklady a počty rozhodnutí; hypotetická úspora proti provozu bez
   optimalizace se nepočítá, protože referenční období neexistuje
   (`counterfactual_available: false`).
8. **Řízení je ve výchozím stavu vypnuté** (`controller.enabled: false`)
   a zápis do TNG také. Zákazník je zapíná vědomě.

## Akceptační kritéria

- [x] 174 testů zeleně, `ruff check .` bez nálezu.
- [x] Zastaralá data → safe mode, žádný zápis (test).
- [x] Pravidlo nemůže překročit komfortní mez (test).
- [x] Chyba v pravidle neshodí controller ani sběr dat (test).
- [x] Každé rozhodnutí má překladový klíč a parametry, ne hotovou větu.
- [ ] Týden provozu bez zásahu u zadavatele – čeká na zapnutí řízení.
