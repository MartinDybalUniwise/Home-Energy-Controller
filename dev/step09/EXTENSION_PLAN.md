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
  "consumers": []            // [{ "ean": "...", "name": "...", "allocation_percent": 0 }]
},
"forecast": {
  "enabled": true,           // zapíná forecast/ modul vedle stávajícího Predictoru
  "sharing_learning_days": 30
},
"economics": {
  "sharing_value_czk_kwh": 0.0   // přiznaná neznalost dokud není EDC napojené
}
```

`sharing.enabled=false` a prázdný `consumers` je bezpečný výchozí stav – nic
se nezapne samo.

## 5. Fázový plán

Každá fáze je samostatně mergovatelná a systém po ní běží. Fáze se nepřeskakují.

| Fáze | Obsah | Akceptační kritérium |
|---|---|---|
| **A** | Rozhraní bez dopadu na běžící kód: `core/model.py` (`EnergyInterval`, `ReaderStatus.state`), kostra `forecast/` balíčku (`__init__.py`, `Forecast` dataclass s `value/range/confidence/model_version/generated_at`), config sekce `sharing`/`forecast`/`economics` v `schema.py` s bezpečnými výchozími hodnotami. **Žádný nový reader, žádná nová stránka.** | `pytest` beze změny v počtu procházejících testů u stávající funkčnosti + nové testy na nové struktury. Appka běží stejně jako před krokem 09. |
| **B** | `forecast/pv_forecast.py` a `forecast/household_consumption_forecast.py` – tenké obálky nad `controller/predictor.py`, vrací už definovaný `Forecast` tvar. Predikční API (`/api/prediction`) přidává pole v novém tvaru vedle starého (zpětná kompatibilita), frontend zatím nezobrazuje nic nového. | Existující stránka Predikce funguje beze změny, nový tvar je ověřitelný testem a `curl`em. |
| **C** | `readers/edc_reader.py` – adaptér, ne pevná implementace. Skutečný způsob přístupu k EDC (API, export, ruční import?) je otevřená otázka (kap. 8) – dokud není zodpovězená, reader běží v `disabled` stavu a nic nefetchuje. Konfigurace `sharing.producer_ean`/`consumers` se validuje. Historie `history/edc/`. | Reader existuje, je vypnutý, testy pokrývají validaci configu a to, že vypnutý reader nic nedělá (stejný vzor jako ostatní readery). |
| **D** | `forecast/sharing_consumption_forecast.py` – predikce sdílené spotřeby na základě historie z fáze C. Závisí na reálných datech z EDC, takže dokud fáze C neběží naostro, tahle fáze zůstává implementovaná, ale bez dat vrací "nedostatek dat" (stejně jako dnešní Predictor). | Test s uměle vloženou historií ukáže rozumnou predikci; bez historie vrací `not_enough_data`, ne fabrikovanou hodnotu. |
| **E** | Nová stránka **Sdílení** (`web/frontend/js/pages.js` + nav): skutečnost vs. predikce sdílené energie, ekonomická hodnota z `economics.py`. `/api/sharing` endpoint. | Stránka se renderuje, i bez zapnutého sdílení (zobrazí "sdílení není nastavené", ne prázdnou/rozbitou stránku). i18n cs/en kompletní. |
| **F** | Controller dostane **jen doporučení** ze `forecast/` a `economics.py` – žádné nové automatické zápisy. Např. "dnes se vyplatí posunout myčku na 14:00 kvůli sdílené ceně" jako text v UI, ne akce. | Žádná nová cesta k zápisu do TNG ani jinam. Testy prokazují, že controller v této fázi nic nově nezapisuje. |
| **G** | Automatická optimalizace využívající sdílení – **až po** ověření dat, predikcí a pravidel z fází A–F na reálném provozu. Vlastní podkrok, vlastní schválení. | Mimo rozsah aktuální implementace – jen zapsáno jako budoucí krok. |

Tento krok (step09) v této session pokrývá **fázi A**. Fáze B–G jsou navržené,
ne implementované – další session/krok na ně naváže postupně, stejně jako
dosavadní kroky 02–08 postupně stavěly na plánu z kroku 01.

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

Implementace na tyto odpovědi čeká – nehádá se:

1. **Přístup k EDC** – jaké reálné rozhraní je k dispozici? Web export, API s
   klíčem, ruční CSV? Bez odpovědi zůstává `edc_reader.py` (fáze C) ve stavu
   `disabled` s jasnou hláškou v UI, ne s odhadovaným/smyšleným endpointem.
2. **Sazba `sharing_value_czk_kwh`** – reálná ekonomická hodnota sdílené
   kWh závisí na smlouvě/tarifu, který systém nezná. Výchozí `0.0` je vědomě
   přiznaná neznalost, ne odhad.
3. **Rozsah automatizace ve fázi G** – jakou míru autonomie (jen doporučení
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
