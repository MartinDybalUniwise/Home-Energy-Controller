# Krok 09 – plán rozšíření: sdílení energie, predikce, externí měření

Vychází z uživatelem dodaného dokumentu `Prompt pro rozšíření Home Energy
Controlleru`. Tento krok **doplňuje** současné řešení (kroky 01–08), nejde o
přepis. Nic z toho, co dnes funguje – čtení GoodWe/TNG/OTE/počasí/Shelly,
change-gate TNG, řízená optimalizace, web UI – se touto změnou nemění, dokud
to daná fáze výslovně nevyžaduje.

**Rozhodnutí zadavatele k tomuto kroku:** "Považuj vše za schválené a
implementuj to, tvoje rozhodnutí zapiš do commitů." Otevřené otázky, které
opravdu vyžadují vstup od zadavatele (hlavně přístup k EDC), jsou v kapitole 8
a implementace na ně čeká – nehádají se.

---

## 1. Tři pilíře rozšíření

1. **Energy Sharing** – domácnost je součástí sdílení elektřiny přes EDC
   (datové centrum operátora trhu). Potřebujeme vědět, kolik se toho dne
   sdílelo, komu, a jaká je z toho ekonomická hodnota.
2. **Rozšířená predikce** – dnešní `controller/predictor.py` umí PV, spotřebu,
   teplo a náklad na základě lineárního poměru z vlastní historie. Prompt chce
   totéž zformalizovat do samostatného `forecast/` modulu s jasným kontraktem
   (hodnota + interval + jistota + verze modelu + čas výpočtu) a přidat
   predikci sdílené spotřeby.
3. **Externí měření** – rozšířit `ReaderStatus` a datový model tak, aby šlo
   bez zásahu do controlleru přidat další zdroje dat (další EAN, další čítač),
   se standardizovaným stavem `ok/stale/error/disabled`.

## 2. Tvrdé mantinely (platí i pro tento krok)

Nic z toho, co je v `CLAUDE.md`, se tímto krokem neruší:

* Readery jen čtou, controller jen rozhoduje. `forecast/` **predikuje**, ale
  nečte ze sítě ani nezapisuje do TNG – vstupem jsou mu už uložená data
  (přes `StorageBackend`), výstupem jen struktury, které si controller nebo
  API přečte.
* Change-gate TNG se nedotýká vůbec – žádná fáze tohoto kroku nepřidává nové
  cesty k zápisu do tepelného čerpadla.
* Žádný nový hardcoded text v UI – všechny popisky přes `dev/hec/locales/*.json`.
* Žádná nová optimalizace nesmí automaticky zapisovat, dokud nejsou data,
  predikce a pravidla ověřené (fáze F/G, viz níže) – bezpečnost a komfort mají
  přednost.
* Formáty `data/*.json` se nemění zpětně nekompatibilně – nová pole se
  přidávají vedle, ne místo stávajících.

## 3. Datový model

### `EnergyInterval` (15minutová perioda, sjednocený tvar pro EDC i sdílení)

```json
{
  "timestamp": "2026-08-19T12:15:00+02:00",
  "source": "edc",
  "ean": "859...",
  "role": "consumer",
  "consumption_kwh": 0.42,
  "production_kwh": 0.0,
  "shared_received_kwh": 0.31,
  "shared_sent_kwh": 0.0
}
```

`source` odlišuje původ (`edc`, `sharing`, budoucí zdroje). `role` je
`consumer` nebo `producer` podle toho, jaký EAN záznam popisuje. Nepovinná
pole se nevyplňují nulou, ale chybí – stejná zásada jako u zbytku systému
("nikdy nefabrikovat nulu").

### Rozšíření `ReaderStatus`

Dnešní `ReaderStatus` (viz `core/model.py`) už má `enabled`, `last_success`,
`last_error`, `is_stale`. Prompt chce explicitní čtyřstavový status místo
odvozeného booleanu – přidává se vlastnost `state`:

```python
@property
def state(self) -> str:            # "ok" | "stale" | "error" | "disabled"
    if not self.enabled:
        return "disabled"
    if self.last_error and (self.last_success is None or ...):
        return "error"
    return "stale" if self.is_stale else "ok"
```

Zpětně kompatibilní – `is_stale`/`is_enabled` zůstávají, `state` je nové pole
navíc v `/api/status`.

### Tvar predikce (`forecast/`)

Každá predikce z `forecast/` vrací stejnou obálku bez ohledu na veličinu:

```json
{
  "value": 4.2,
  "range": [3.6, 4.9],
  "confidence": "medium",
  "model_version": "linear-ratio-v1",
  "generated_at": "2026-08-19T13:00:00+02:00"
}
```

Přesně odpovídá tomu, co dnešní `Predictor.pv_factor()` a spol. už fakticky
počítají (`CONFIDENCE_BANDS`, interval, žádné strojové učení) – jde o
zformalizování existujícího přístupu do jednotného kontraktu, ne o novou
metodu predikce.

### Ekonomická hodnota

`economics.py` (nový modul ve `forecast/`) počítá `self_consumption_value`,
`sharing_value`, `grid_export_value` z už existujících cen (OTE) a sdílených
množství (EDC/sharing readery) – čistě odvozená hodnota, žádný nový zdroj dat.

## 4. Nová konfigurace

```jsonc
"sharing": {
  "enabled": false,
  "producer_ean": "",
  "consumers": [],           // [{ "ean": "...", "name": "...", "allocation_percent": 0 }]
  "import_path": ""          // fáze C: složka s měsíčními XLSX exporty GoEnergy
},
"forecast": {
  "enabled": true,           // zapíná forecast/ modul vedle stávajícího Predictoru
  "sharing_learning_days": 30
},
"economics": {
  "sharing_value_czk_kwh": 0.0   // přiznaná neznalost dokud není EDC napojené
},
"polling": {
  "sharing_hours": 24        // fáze C: jak často kontrolovat novou přílohu (měsíční soubor, není třeba častěji)
}
```

`sharing.enabled=false` a prázdný `consumers` je bezpečný výchozí stav – nic
se nezapne samo.

## 5. Fázový plán

Každá fáze je samostatně mergovatelná a systém po ní běží. Fáze se nepřeskakují.

| Fáze | Obsah | Akceptační kritérium | Stav |
|---|---|---|---|
| **A** | Rozhraní bez dopadu na běžící kód: `core/model.py` (`EnergyInterval`, `ReaderStatus.state`), kostra `forecast/` balíčku (`__init__.py`, `Forecast` dataclass s `value/range/confidence/model_version/generated_at`), config sekce `sharing`/`forecast`/`economics` v `schema.py` s bezpečnými výchozími hodnotami. **Žádný nový reader, žádná nová stránka.** | `pytest` beze změny v počtu procházejících testů u stávající funkčnosti + nové testy na nové struktury. Appka běží stejně jako před krokem 09. | ✅ hotovo |
| **B** | `forecast/pv_forecast.py` a `forecast/household_consumption_forecast.py` – tenké obálky nad `controller/predictor.py`, vrací už definovaný `Forecast` tvar. Predikční API (`/api/prediction`) přidává pole v novém tvaru vedle starého (zpětná kompatibilita), frontend zatím nezobrazuje nic nového. | Existující stránka Predikce funguje beze změny, nový tvar je ověřitelný testem a `curl`em. | ✅ hotovo |
| **C** | `readers/sharing_reader.py` – ne live API adaptér, ale import měsíčního XLSX exportu GoEnergy (kap. 8, vyřešeno). Sleduje `sharing.import_path`; bez nastavené cesty zůstává v chybovém/vypnutém stavu, nic nehádá. Konfigurace `sharing.producer_ean`/`consumers` se validuje. Historie `history/sharing/`. | Reader existuje, bez `import_path` jasně hlásí chybějící konfiguraci; testy pokrývají parser i dedup souborů (stejný vzor jako ostatní readery). | ✅ hotovo |
| **D** | `forecast/sharing_consumption_forecast.py` – odhad sdílené energie na základě historie z fáze C (naučený poměr sdíleno/výroba) × očekávané výroby z `pv_forecast`. | Test s uměle vloženou historií ukáže rozumnou predikci; bez historie vrací `not_enough_data`/`value=None`, ne fabrikovanou hodnotu. | ✅ hotovo |
| **E** | Nová stránka **Sdílení** (`web/frontend/js/pages.js` + nav): skutečnost vs. predikce sdílené energie, ekonomická hodnota z `economics.py`. `/api/sharing` endpoint. | Stránka se renderuje, i bez zapnutého sdílení (zobrazí "sdílení není nastavené", ne prázdnou/rozbitou stránku). i18n cs/en kompletní. | ⏳ navrženo |
| **F** | Controller dostane **jen doporučení** ze `forecast/` a `economics.py` – žádné nové automatické zápisy. Např. "dnes se vyplatí posunout myčku na 14:00 kvůli sdílené ceně" jako text v UI, ne akce. | Žádná nová cesta k zápisu do TNG ani jinam. Testy prokazují, že controller v této fázi nic nově nezapisuje. | ⏳ navrženo |
| **G** | Automatická optimalizace využívající sdílení – **až po** ověření dat, predikcí a pravidel z fází A–F na reálném provozu. Vlastní podkrok, vlastní schválení. | Mimo rozsah aktuální implementace – jen zapsáno jako budoucí krok. | ⏳ navrženo |

Fáze A byla implementována v první session tohoto kroku. Fáze B (tenké
obálky nad `Predictor`), C (`sharing_reader` nad reálným GoEnergy exportem)
a D (odhad sdílení kombinující historii importu s PV predikcí) byly
implementovány v navazující session, viz kap. 9b. Fáze E–G zůstávají
navržené, ne implementované.

## 6. Vysvětlitelnost

Prompt požaduje, aby každé automatizované rozhodnutí bylo vysvětlitelné.
Dnešní `reason_key`/`reason_params` u `controller`u (viz `locales/*.json`,
sekce `reason`) už tohle dělá pro řízení TČ. Fáze F rozšiřuje stejný vzor na
doporučení ze sdílení/predikce – žádný nový mechanismus, jen použití
stávajícího.

## 7. Historická data

Nová podadresáře `history/edc/`, `history/sharing/`, `history/forecasts/` –
stejný JSONL formát a stejná politika (`data/ logs/ history/` se necommitují,
viz `.gitignore` a `CLAUDE.md`). Archivace (`storage.archive_path`) se
rozšiřuje na nové zdroje automaticky, protože archivuje podle adresáře, ne
podle pevného seznamu.

## 8. Otevřené otázky pro zadavatele

1. **Přístup k EDC/sdílení – VYŘEŠENO.** Zadavatel dodal reálný měsíční
   export "Rozpis vyúčtování" od GoEnergy (sdružení, přes které sdílí
   přebytky FVE). Žádné veřejné API k dispozici není – export se stahuje
   ručně z portálu jako XLSX jednou měsíčně. `sharing_reader` (fáze C) proto
   **nesahá na síť**, ale sleduje lokální složku (`sharing.import_path`), kam
   uživatel soubor po stažení uloží. Přesný formát a ověřené vztahy mezi
   sloupci: [`SHARING_IMPORT_FORMAT.md`](SHARING_IMPORT_FORMAT.md). Reálná
   čísla ze souboru (osobní/finanční údaj) do repozitáře nejdou – dokument
   používá syntetická data.
2. **Sazba `sharing_value_czk_kwh` – VYŘEŠENO částečně.** Export sám nese
   jednotkovou cenu i srážku za dané zúčtovací období (`Kč/MWh`), takže
   ekonomickou hodnotu prodané/sdílené energie lze počítat přímo z importu,
   ne z ručně nastavené sazby. `economics.sharing_value_czk_kwh` zůstává jako
   fallback pro odhad **budoucích** měsíců, kde reálná sazba ještě není
   známá (viz fáze D) – to je jiná potřeba než historická fakturace.
3. **Export pro odběratele (spotřebitele sdílené energie)** – dodaný soubor
   je z pohledu výrobce. Jestli existuje analogický export pro odběratele,
   zatím neověřeno – bude-li potřeba, přidá se druhý parser vedle
   stávajícího, ne přepis.
4. **Rozsah automatizace ve fázi G** – jakou míru autonomie (jen doporučení
   vs. automatický zápis) zadavatel pro sdílení chce, se řeší až po ověření
   fází A–F na reálném provozu.

## 9. Rozsah této implementace (session, krok 09 → fáze A)

* `dev/hec/core/model.py`: `ReaderStatus.state`, `EnergyInterval` dataclass.
* `dev/hec/core/schema.py`: sekce `sharing`, `forecast`, `economics` s
  bezpečnými výchozími hodnotami (`enabled: false` u sdílení).
* `dev/hec/forecast/__init__.py`: `Forecast` dataclass (`value`, `range`,
  `confidence`, `model_version`, `generated_at`) – jen datový kontrakt,
  žádná predikční logika (ta přichází ve fázi B).
* Testy pro všechno výše.
* Žádné změny v `web/`, `readers/` (mimo případné doplnění `ReaderStatus`
  serializace do `/api/status`), `controller/` mimo výše uvedené.

## 9b. Rozsah druhé implementační dávky (fáze B, C, D)

* `dev/hec/forecast/pv_forecast.py`, `household_consumption_forecast.py`:
  čisté funkce, které vezmou už spočítaný denní záznam z
  `Predictor.forecast()` a přebalí ho do tvaru `Forecast` – `controller/
  predictor.py` se nemění, žádná predikční logika se neduplikuje.
* `dev/hec/web/api.py`: `prediction()` obohacuje každý den o `forecast_pv`/
  `forecast_consumption` v novém tvaru vedle starých polí (zpětná
  kompatibilita – frontend na Predikci se nemění).
* `dev/hec/readers/sharing_parser.py`: čisté parsovací funkce nad GoEnergy
  XLSX (`SHARING_IMPORT_FORMAT.md`), testovatelné bez readeru a bez disku.
* `dev/hec/readers/sharing_reader.py`: `SharingReader` – sleduje
  `sharing.import_path`, nové soubory jednou naimportuje (dedup podle jména
  a času změny v perzistentním stavu, stejný vzor jako `TngReader`), zapisuje
  `EnergyInterval` záznamy do `history/sharing/`, jako "aktuální" hodnotu
  vrací poslední známé měsíční vyúčtování. `openpyxl` je volitelná závislost
  (lazy import, `requirements.txt`) – stejný vzor jako knihovna `goodwe`.
* `dev/hec/core/schema.py`: `sharing.import_path`, `polling.sharing_hours`.
* `dev/hec/readers/registry.py`: registrace `"sharing": SharingReader`.
* `dev/hec/forecast/sharing_consumption_forecast.py`: odhad sdíleného
  množství pro nadcházející období = naučený poměr sdíleno/výroba (medián
  z `history/sharing`) × očekávaná výroba (z `pv_forecast`). Bez historie
  vrací `value=None` ("zatím nevíme"), ne odhad od oka.
* Beze změny zůstává: `controller/`, existující stránky UI (fáze E – nová
  stránka Sdílení – je mimo rozsah této dávky), change-gate TNG.
