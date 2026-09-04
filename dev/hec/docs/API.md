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
