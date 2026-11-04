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

Price/FTE shift (owner approved2026-10-30): read sources.tng.price_shift as the
effective runtime phase and targets. Saved dated windows are conditional, not proof
of an executed preheat/coast or compressor run. Preserve planner-owned heating and
thermostat dates unless a deliberate adjustment is needed; routine reviews must not
flatten them to42. Actual GoodWe surplus can permit extra heat; forecast PV alone
cannot. No guaranteed cost savings until measured with reliable consumption data.

Unified control2026-10-30: status.controller is the sole production planner.
Read thermal_plan for the resolved operation/targets, tng_write_enabled for the
effective writer permission, and goodwe_control_enabled for separate inverter
actuation. controller.enabled is the master switch. plan_tng history entries are
resolved plans, never proof of sending or acknowledgement. TNG remains transport;
do not re-enable retired thermal rules or enable battery/export changes as part
of an ordinary heating review.

## Kontrola každé dvě hodiny — rozšíření vlastníkem 2026-10-31

Toto rozšíření je povinnou součástí již aktivní dvouhodinové kontroly. Při každém
běhu zapiš skutečný čas zahájení Europe/Prague, proveď kontrolu a vždy pošli do
chatu stručný mobilní report. Zachovej existující četnost; nevytvářej druhý plánovač.
Nový výslovný souhlas vlastníka umožňuje ekonomické řízení GoodWe společným
controllerem; starší pokyn zachovat GoodWe vypnutý tímto pozbývá platnosti.

- Ověř běh služby, controller.enabled, goodwe_control_enabled a economic.enabled,
  čerstvost GoodWe/TNG a publikované ceny pro dnešní a následující den. Chybějící
  zítřejší ceny označ; nenahrazuj je dnešními. Čti status.controller.battery_plan.
- Porovnej uložený plán, rozhodnutí controlleru, goodwe_audit/TNG potvrzení a
  naměřený průběh od poslední kontroly (nejvýše posledních 7 dní). Samotné povolení
  zápisu či úspěšný readback neprokazuje fyzické nabíjení ani běh kompresoru.
- FVE/baterie: sleduj skutečné PV, spotřebu, import/export, nabíjecí/vybíjecí výkon,
  SOC a změnu energie. Ověř levné časové okno, konec nativního programu, shodu hodin
  měniče do120 s, výkon<=20 %, cíl ze sítě<=60 %, BMS/teplotní omezení a rezervu
  pro FVE. Importní rozpočet7 kW je omezení přídavného nabíjení, nikoli ochrana
  jističe či záruka celkového odběru. Baterie musí ustoupit TČ a spotřebě domu.
- Ekonomika: porovnej skutečnou celkovou nákupní cenu s cenou nahrazené vlastní
  spotřeby. Model: účinnost90 %, opotřebení0,30 Kč/dodané kWh, požadovaný rozdíl
  alespoň0,50 Kč/kWh po těchto nákladech. Tyto hodnoty jsou konzervativní předpoklady,
  nikoli změřená účinnost, cena degradace nebo dosažená úspora. Odděl síť/PV energii;
  při neúplných datech skutečnou úsporu nevyčísluj. Nepouštěj vynucené vybíjení do sítě.
- Zkontroluj držení nakoupené energie do dražšího období a následné uvolnění rezervy
  do režimu GENERAL pro spotřebu domu. Rezervu nezvyšuj nad aktuální SOC. Exportní
  omezení nejsou součástí nového řízení. Při neplatných datech ukončit vlastní
  vynucené nabíjení; přirozený provoz FVE a ochrany měniče ponechat.
- TČ: zhodnoť, zda skutečně potvrzený předehřev předcházel růstu ceny, nebo zda ho
  zabrzdila brána900 s, nepotvrzený povel či komfort. Neoznač zmeškanou noc jako
  vykonaný předehřev. Uveď pokojovou teplotu/trend, AKU jen z ověřeného čerstvého
  čidla, výstup TNG a bojler. Posuzuj komfort>=21 °C, běžný cíl21,5 °C, přetápění,
  večerní zásobu TV, výlučné režimy a účinné komfortní/solární veto.
- Při změně plánu použij jen společný controller a schválené parametry/datované
  výjimky. Neobnovuj vyřazená samostatná pravidla. Zachovej stav potvrzení TNG.
  Neupravuj účinnost ani opotřebení podle jedné epizody. U závady uveď konkrétní
  rozdíl plán→povel→potvrzení→měření, provedenou nápravu a co ještě není ověřené.

V reportu vždy aktuální stav, naměřený trend, dnešní další okna a krátká tabulka
Zhodnocení | Doporučení. Drahé vytápění může být nutné pro komfort: vysvětli důvod,
nepokládej samotnou vysokou cenu za závadu. Poškození komfortu kvůli nabíjení je závada.

EVV1/D57d tariff review (2026-10-31 owner approval): check that OTE API prices
include the shared current distribution_pricing projection and valid date range.
NT00-06,07-09,10-13,14-16,17-24 every weekday. VT otherwise. Check for distributor
schedule changes; exported times are not live HDO confirmation. Never use the old
SDG00-06/19-21 schedule. Preserve price-owned overrides; review differences between
planned preheat, comfort/PV veto, confirmed TNG settings and measured behaviour.

Coordinated repair2026-11-01: verify native grid charging ends before VT. Read
thermal-response.json freshness/outcome and thermal_plan.required_preheat_minutes;
2-4h preheat is conditional, not a readiness guarantee. Battery coordination may
release to20% General reserve for a fresh cold-house VT peak with sufficient
estimated cheaper refill within6h. Compare battery_plan.coordination and
release_reason=comfort_peak to audited reserve changes, physical battery/grid power
and SOC. Distinguish estimated refill/load from measurements and do not promise
financial optimality. Never re-lock the same VT release during ordinary warming.

Hourly floor check2026-11-01: inspect thermal_plan.floor_check (phase, next_check_at,
request_sent_at, acknowledged_at, observations and last_cycle). Pump activity is an
owner assumption from thermostat demand, not measurement. During a cycle cloud
polling is60s; no second hourly chat task/controller exists. Distinguish requested
restoration from native acknowledgement;900s gates can delay delivery. Review AKU
range/cloud crosschecks and missing/late samples. Reheating threshold35C, stable
recovery38C, earliest15min and restoration request by45min. Native autonomous
pump-only control is NOT verified. Check that the temporary room service request
(+0.5C,max24C) returns to the CURRENT common plan and explicitoff/DHW take priority.

Daily-review optimisation2026-11-04 (dev/step49/PLAN.md): review battery_plan.
peak_reservation (configured capacity/current load estimate) against measured
SOC/native reserve and later sustained peaks; comfort exceptions still win.
Hourly floor evaluation may defer warm/safe pulses to120min, never cold-store/room
needs. Inspect restoration_wait_minutes/confirmation_delayed and actual basic/
thermostat readbacks, not an overdue next_check_at or an assumed pump runtime.
Second ordinary DHW window may be skipped with fresh probe>=target (resume at
target-2), retaining first/hygienic/dated-owner windows. Check dhw_readiness.
Consumption forecasts now include heating once and expose consumption_components
and consumption_progress (measured today + estimated remainder); compare with
fresh GoodWe load counter. Never present an empirical weather component as COP.
