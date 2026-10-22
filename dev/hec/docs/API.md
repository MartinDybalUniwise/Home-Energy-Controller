# Lokální API

Všechny odpovědi jsou JSON, kódování UTF-8. Při zapnutém heslu vyžadují
endpointy kromě `/api/session`, `/api/login` a `/api/i18n/*` platnou cookie
`hec_session` (`POST /api/login`).

| Metoda | Cesta | Popis |
|---|---|---|
| GET | `/api/session` | zda je vyžadováno přihlášení a zda je platné |
| POST | `/api/login` | `{"password": "…"}` → nastaví cookie |
| GET | `/api/current` | snapshot všech zdrojů + stav |
| GET | `/api/status` | stav readerů, stáří dat, safe mode, verze, vzhled |
| GET | `/api/history` | `source`, `from`, `to`, `fields`, `bucket` |
| GET | `/api/sources` | seznam zdrojů v historii |
| GET | `/api/prices` | ceny OTE na dnešek a zítřek |
| GET | `/api/weather` | aktuální počasí a předpověď |
| GET | `/api/prediction` | predikce na následující dny |
| GET | `/api/summaries` | denní bilance (`days`) |
| GET | `/api/appliances` | detekované cykly spotřebičů (`days`) |
| GET | `/api/phases` | analýza zatížení fází (`days`) |
| GET | `/api/heatpump` | analýza tepelného čerpadla |
| GET | `/api/decisions` | rozhodnutí controlleru a jeho stav |
| GET | `/api/metrics` | doložitelné ukazatele přínosu |
| GET | `/api/config` | konfigurace (tajemství zamaskovaná) |
| PUT | `/api/config` | `{"config": {...}}` – validuje, zálohuje, uloží |
| GET | `/api/config/schema` | popis polí pro nastavení v UI |
| GET | `/api/goodwe/authorization` | stav lokální GoodWe autorizace a posledního ověření |
| POST | `/api/goodwe/authorization/verify` | read-only ověření nakonfigurovaného měniče GoodWe |
| POST | `/api/goodwe/authorization/approve` | explicitní vytvoření autorizačního artefaktu po úspěšném ověření |
| GET | `/api/finance` | KPI a auditní souhrn HEF dashboardu |
| GET | `/api/finance/manual` | seznam ručních položek HEF (`limit`) |
| GET | `/api/i18n/{lang}` | překladový katalog |

## Časové rozsahy

`from` a `to` přijímají ISO 8601, `now`, `today` nebo relativní zápis
`-24h`, `-7d`, `-30m`.

## Zhuštění dat

Server podvzorkuje sám podle délky rozsahu (do 6 h minutové koše, do 48 h
pětiminutové, do 8 dní čtvrthodinové, dál hodinové). Vlastní hodnotu lze
vynutit parametrem `bucket` v sekundách.

Historické záznamy s vnořeným objektem `values` (například `sdg_history`) se
pro `/api/history` vracejí ve stejném plochém tvaru jako ostatní zdroje.
Numerická pole jsou uvedena v `fields` a v každém řádku pod svým názvem.

## Příklady

```bash
curl localhost:8080/api/current
curl "localhost:8080/api/history?source=goodwe&from=-24h&fields=pv_w,house_w"
curl "localhost:8080/api/summaries?days=7"
```

## Poznámky pro integrace

* Tajemství se z `/api/config` nikdy nevrací v čitelné podobě a zamaskovanou
  hodnotu server při zápisu ignoruje.
* Formáty `data/ote-*.json`, `data/weather.json` a JSONL historie jsou
  stabilní kontrakt: pole se přidávají, nepřejmenovávají.


### Measurement quality (Step29)

Shelly keeps the original signed `power_w`/`heatpump_power_w`. New additive
`measurement_quality`, `heatpump_quality` and `device_status` fields distinguish
valid, negative, phase, missing and offline observations. An all-offline read
returns `online:false` and diagnostic values through the existing failed-sample
path; it never becomes a successful measurement or invokes the controller.

`/api/heatpump` energy/run time may be null when no valid interval exists.
`measured:true` includes a genuinely measured zero. `power_quality` reports valid,
invalid and missing sample counts, covered seconds, day coverage percentage and
method `adjacent-valid-v1`. Energy is trapezoidal between adjacent valid samples;
running time holds the preceding >=200W electrical state until the next valid
sample. Gaps over 900s and invalid samples break intervals. This is an estimate
of electrical operation, not compressor telemetry or thermal output/COP.
Unknown historical heating flags produce null `heating_share_pct`, not zero.

Summary `heatpump_kwh` is nullable and includes additive `heatpump_quality`.
Legacy negative summary energy is masked only on read; raw files remain intact.
Metrics retain null if any daily heatpump energy in the requested period is
unknown and expose `heatpump_reported_days`. No bulk history rewrite occurs.

`/api/current` projects OTE's current dated quarter from the local daily cache
without fetching or mutating the controller snapshot. `period_end`,
`price_valid_at` and `price_valid` describe validity; a missing cache/quarter
produces null prices. `timestamp` still denotes the original reader observation.


### GoodWe energy domains (Step32)

ET library sensors `e_day_imp`/`e_day_exp` describe inverter AC energy, not
grid exchange. Both adapters expose them as additive
`inverter_ac_import_day_kwh`/`inverter_ac_export_day_kwh`. Meter GRID sensors
`meter_e_total_imp`/`meter_e_total_exp` become `grid_import_total_kwh` /
`grid_export_total_kwh` (cumulative kWh). Missing, invalid or disconnected
meter counters remain null; measured zero remains zero.

`e_import_day_kwh`/`e_export_day_kwh` are retained but null: this ET runtime
response has no daily GRID sensors and no verified midnight meter baseline.
Do not substitute AC energy, lifetime totals, or an unlabelled partial
integration. `energy_counter_semantics=ac-grid-separated-v1` identifies the
corrected contract. Legacy current/history fields from the earlier AC mapping
are masked on read, with their original valid AC value exposed under the
explicit name. Original records and controller input are not rewritten.
The control-plan page does not use SDG `e_day_imp/exp` as grid energy.
Existing power-based daily summaries remain independently calculated; their
historical source is labelled and small grid energies show two decimals.
