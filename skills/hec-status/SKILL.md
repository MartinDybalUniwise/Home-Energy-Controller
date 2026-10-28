---
name: hec-status
description: Vytvoř stručný grafický mobilní přehled HEC při dotazu na stav domu, topení, bojleru nebo denní plán; používej také pro pravidelné kontroly HEC.
---

# Stav HEC

Odpovídej česky. Primárním výstupem je přehledná grafika do chatu pro mobil,
nikoli dlouhé vysvětlení. Pro inline grafiku načti úplné aktuální instrukce
dostupného skillu visualize. Při nedostupném vykreslení použij stručný mobilní
Markdown a přiznej omezení.

## Obsah a pořadí

1. Aktuální stav: běh HEC, pokojová teplota, výstupní voda topení TNG,
   bojler, aktuální výroba a spotřeba, baterie. Uveď časy měření.
2. Naměřený vývoj za dnešek: teploty a podle významu energetický průběh.
   Odliš chybějící data a odhad od skutečného měření.
3. Nastavený plán na dnešek včetně časů a cílových teplot. Výslovné „zítra“
   či „pozítří“ mění datum plánu; aktuální stav zůstává vždy aktuální.
   Budoucí návrh jasně odliš od skutečně uloženého rozvrhu.
4. Pod vizualizací stavu a plánu dej dva struččné sloupce:
   **Zhodnocení** a **Doporučení**. Na mobilu zachovej čitelnost; případně je
   při příliš malé šířce poskládej. Každý obsahuje nejvýše několik krátkých vět.

Nevkládej další dlouhou slovní kopii grafiky. Rutinní technické poznámky
schovej pod klikatelné ⓘ; zásadní chybu nebo potřebný zásah nezakrývej.
Pokud je reálně nutné schválení, výrazně graficky upozorni přímo v chatu:
konkrétní akce, důvod a přesný krok uživatele. Nežádej znovu o již udělené
souhlasy; systémová oprávnění však nevydávej za udělená bez ověření.

## Data a interpretace

Produkce: C:/TepelneCerpadlo/Home-Energy-Controller,
API http://127.0.0.1:8080, služba HomeEnergyController.
Ověř čerstvá data přes /api/current, /api/prediction a potřebnou omezenou
/api/history. Z /api/config čti pouze potřebné rozvrhy; nezobrazuj tajné údaje.
Denní výjimky mají přednost před běžným rozvrhem v časové zóně Europe/Prague.
Stav, čas, čerstvost a skutečné potvrzení zařízení vždy ověř nově.

Výstupní topná voda není teplota povrchu podlahy. Povolení topení není
potvrzený chod kompresoru. Cílová teplota není dosažená teplota.
Dnešní odhad FVE uváděj jako naměřeno + zbývající odhad, s nejistotou.
Nepřebírej čísla z minulého náhledu jako aktuální data.

Prioritou je komfort topné vody bez přetápění domu a zásoba teplé vody
na večerní sprchování, přednostně ze slunce. Nevyvozuj dostupný objem
teplé vody bez parametrů zásobníku.

Samotný dotaz na stav není nový příkaz měnit nastavení. Pro provozní změny
respektuj platnou autorizaci, projektové instrukce, potvrzovací cyklus TNG
a minimální interval zápisů. Nenavštěvuj zmrazenou složku odlozene-logy.

Operational rules are maintained in dev/hec/web/frontend/hec-rules.json and shown at /#/rules. Read this registry before changing HEC plans. Never enable heating and DHW simultaneously: use tng.operation exclusive heating/boiler windows with bounded DHW duration. Keep this registry and its change log updated when the owner adds a rule. Use compact, colourful graphical status and plan views.
