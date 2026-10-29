---
name: hec-status
description: Vytvoř stručný grafický mobilní přehled HEC při dotazu na stav domu, topení, bojleru nebo denní plán; používej také pro pravidelné kontroly HEC.
---

# Stav HEC

Odpovídej česky. Mobilní a pravidelné zprávy posílej jako přehledný nativní
Markdown s barevnými stavovými emoji, krátkými bloky a časovou osou plánu.
Telefon vlastníka nevykresluje lokální visualize HTML: nikdy v těchto zprávách
neposílej interní visualize značky, lokální HTML odkazy ani cesty C:/. Celý
přehled musí být čitelný přímo ve zprávě. Interaktivní vizualizaci používej
jen na výslovně vyžádaném podporovaném klientu; tehdy načti skill visualize.

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

Sensor invariant: water_output_temperature is the TNG heat-pump outlet (tw), not floor-loop water, buffer storage or floor surface. No separate floor-loop sensor is currently provided. Never infer floor temperature/comfort or stored heat from that field alone; heating_set_temperature is a requested setpoint.

The owner confirmed the desired heating-store reading is AKU/buffer temperature. The physical panel has a distinct buffer sensor (owner photo 40.2 C); current cloud history exposes only t/tw/tb/tt. Do not claim the hardware lacks an AKU sensor. Live AKU is now provided by the independent receive-only tng_wire source. Require sample_time <= 180 seconds old and field_quality not outside_verified_range; never substitute outlet or a photo. Keep cloud tng as fallback for common temperatures only.

Owner clarification 2026-10-28: Direct LAN TNG access is READ-ONLY. Existing cloud API control remains authorised and enabled. Local investigation is explicitly paused until the owner supplies further information/credentials; do not probe the LAN controller while paused.

For wire/command analysis read ../../dev/hec/docs/TNG_WIRE.md. The passive mirror is integrated in HEC; do not restart the old standalone logger on UDP 37008. Inspect both source timestamps and tng_wire_receiver counters. Candidate bits and unresolved temperature branches remain observational only. Cloud confirmation of heating/boiler and thermostat are separate gates; neither proves physical compressor operation.

Room comfort is now enforced inside TNG control: fresh distinct cloud samples below 21 C for 15 minutes request exclusive heating42 and room21.5. A sudden >=0.5 C drop within10 minutes while heating enabled gets30 minutes recovery time. Release at21.5. Persisted guard state survives restart; existing gates/900 s and explicit off/disabled heating remain authoritative. Read sources.tng.comfort_guard_active for effective status; do not override this guard from a periodic plan merely to restore a boiler window.
