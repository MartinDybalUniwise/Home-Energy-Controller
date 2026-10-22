# Audit energetických údajů — 22. 10. 2026

## Provozní důkaz před změnou

API `/api/status` potvrdilo verzi 0.1.5, PID 17376, working_directory i project_root `C:/TepelneCerpadlo/Home-Energy-Controller`. Produkční Git revize byla `704feee638daf75c014f9cecb050678a5a98bb19`. Nejde o předpoklad podle starého PID; stav byl znovu přečten.

Omezené `/api/current?fast=1` vrátilo snímek GoodWe s časem `2026-10-22T14:15:25.378813+02:00`. Globální poslední měření bylo `14:15:36.336842+02:00` a patřilo jinému okamžiku. Tuto globální značku staré rozhraní používalo i u jednotlivých KPI.

| Údaj | Pole / původ | Hodnota | Význam |
| --- | --- | --- | --- |
| FVE | ppv → pv_w | 736 W | Součet DC výkonů PV vstupů knihovny GoodWe |
| Dům | house_consumption → house_w | 3 179 W | Vypočtená hodnota střídače, nikoli nezávislý elektroměr domu |
| Síť | active_power → grid_w | −2 404 W | V této instalaci záporné znaménko znamená import; normalizováno grid_import_w = 2 404 W |
| Baterie | pbattery1 → battery_w | 39 W | V této instalaci kladné znaménko znamená vybíjení; normalizováno battery_discharge_w = 39 W |
| SOC | battery_soc | 10 % | Stav nabití, nikoli výkon nebo energie |
| TČ | Shelly heatpump_quality | negative | Záporný příkon není platné měření spotřeby; řízení ani polarita se automaticky nemění |

Knihovna GoodWe ET přímo definuje `house_consumption` jako součet ppv1–ppv4 + pbattery1 − active_power (lokálně instalovaný `goodwe/et.py`, Calculated House Consumption). Proto 736 + 39 − (−2 404) = 3 179 W souhlasí přesně z definice. **Není to nezávislý důkaz přesnosti měřidel ani nulových ztrát.** Pole výkonů fází v HEC pocházejí z výkonů AC měniče a nesmějí se automaticky považovat za fázové měření celého domu.

Oba GoodWe adaptéry v repozitáři mapují stejné energetické veličiny. Konfigurované orientace znamének zůstávají zachované; samotné displejové opravy do nich nezasahují.

## Co lze říci ze snímků SDG

Ve snímcích kolem 13:47 jsou HEC 1,21 kW FVE / 3,13 kW dům / 1,88 kW import a SDG schéma 1 214 W / 3 113 W / 1 864 W; baterie 42 W. SDG ukazuje čas střídače 13:44:40 a současně další údaje domu 3 077 W a 3 083 W. Jde o různé odečty nebo měřicí body; snímek stránky není společný přesně synchronní vzorek všech údajů.

Zaokrouhlení a rozdílná čerstvost vysvětlují blízkost těchto hodnot. Příčinu rozdílu jednotlivých interních čísel SDG nelze ze screenshotu definitivně prokázat. Přímé simultánní registry SDG nebyly v této etapě změněny ani kalibrovány. Rozhraní proto vysvětluje původ údaje a zobrazuje čas GoodWe, nepřepisuje měření podle jiného čísla na snímku.

## Potvrzené chyby a oprava

- Tabulka označovala GHI ve W/m² jako elektrickou výrobu v kW. Byla nahrazena grafem skutečné historie v kW a samostatným cenovým panelem.
- Denní prediktor začíná zítřkem. Výběr prvního doporučeného dne se nesmí použít jako dnešní odhad. Nyní se vybírá podle data a doporučení uvádí den; nedostupný dnešní odhad je výslovně přiznán.
- Neplatný příkon TČ zůstával hlavním číslem. Nyní je hlavní údaj nedostupný s výstražným stavem; surová hodnota zůstává v diagnostice.
- Vítr měl nesoulad názvu pole: reader poskytuje wind_kmh. Hlavní stránka nyní používá toto pole se zpětně kompatibilní alternativou.
- Hodinové výkonové odhady v současném API nejsou. Denní součet se nepřevádí na vymyšlenou hodinovou křivku. Graf používá skutečnou historii a publikované cenové intervaly s omezeným horizontem.
- Časová osa, popisky a tabulka používají Europe/Prague. Nejednoznačné cenové intervaly při změně času bez offsetu jsou vynechané s vysvětlením. Chybějící měřicí bucket přerušuje čáru i bez explicitního null záznamu.

Čtení se omezilo na stavové API, konkrétní zdrojové soubory a jeden cenový interval. Zmrazené logy nebyly procházeny, historie nebyla přepisována a k fyzickým zápisům nedošlo.
