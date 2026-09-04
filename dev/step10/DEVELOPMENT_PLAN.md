# Krok 10 – HEF (Home Energy Finance) jako integrovaná finanční vrstva

Tento krok zavádí **HEF (Home Energy Finance)** jako analytickou/finanční vrstvu
uvnitř existující aplikace v `dev/hec/`, bez zásahu do provozní řídicí logiky
(GoodWe/TNG/OTE/controller).

---

## 1. Inventura současné architektury (stav před krokem 10)

### Datové úložiště

- `dev/hec/storage/jsonl.py` (`JsonlStorage`) je aktuální runtime storage.
- `data/current_*.json` drží poslední stav zdrojů.
- `history/<source>/<day>.jsonl` drží append-only historii.
- `storage/base.py` už má abstrahované rozhraní (`StorageBackend`) a atomický
  zápis (`atomic_write_json`) – vhodné i pro finance audit trail.

### API a router

- API vrstva: `dev/hec/web/api.py` (testovatelná bez socketu).
- HTTP routing: `dev/hec/web/server.py`.
- Stávající endpointy pokrývají provozní doménu (status, history, prediction,
  metrics, config…), finance endpointy dosud chyběly.

### Služby a aplikační wiring

- Centrální wiring: `dev/hec/core/app.py` (`Application`).
- Readery skládá `dev/hec/readers/registry.py`.
- Readery zapisují data do storage, controller je jen čte přes snapshot.

### Frontend integrace

- SPA shell: `dev/hec/web/frontend/index.html`, `js/app.js`, `js/pages.js`.
- Lokalizace: `dev/hec/locales/cs.json`, `dev/hec/locales/en.json`.
- Navigace je hash-based (`#/overview`, `#/history`, …).

---

## 2. Návrh integrace HEF

### Architektonické pravidlo oddělení

- **Operations**: GoodWe, TNG, OTE, controller – beze změny v logice rozhodování.
- **Finance**: dokumenty, transakce, manuální položky, investice, dotace,
  párování plateb, ekonomika.
- Sdílené vrstvy: stejné API/UI/runtime a stejné storage abstractions.

### Integrace v kroku 10 (MVP scaffold)

1. Nový balíček `dev/hec/finance/`:
   - `FinanceService` pro agregaci dashboardu a ručních položek.
2. Nový reader `finance_document_reader`:
   - sledování `finance.documents.inbox_path`,
   - import PDF/XLS/XLSX/CSV,
   - základní klasifikace (`electricity/gas/water/export/sharing/service/other`),
   - deduplikace přes hash + metadata ze jména souboru,
   - přesun do `archive/` a evidence auditních metadat.
3. Nové API endpointy:
   - `GET /api/finance`
   - `GET /api/finance/manual`
4. Frontend scaffold stránek:
   - `#/finance`
   - `#/finance/manual`
   - připojeno na nové API + i18n klíče.

### Datový model HEF (cílový)

Krok 10 potvrzuje cílové entity pro další fáze:

- `finance_transactions`
- `finance_assets`
- `finance_documents`
- `finance_payments`
- `finance_settings`

V této implementační dávce je nasazen scaffold nad stávající JSON/JSONL
vrstvou, aby bylo možné MVP rozšiřovat inkrementálně bez paralelní aplikace.

---

## 3. Seznam vytvořených/změněných souborů (krok 10)

### Nové

- `dev/step10/DEVELOPMENT_PLAN.md`
- `dev/hec/finance/__init__.py`
- `dev/hec/finance/service.py`
- `dev/hec/readers/finance_document_reader.py`
- `dev/hec/tests/test_readers_finance_document.py`

### Změněné

- `dev/README.md`
- `dev/hec/core/app.py`
- `dev/hec/core/schema.py`
- `dev/hec/config/config.example.json`
- `dev/hec/readers/registry.py`
- `dev/hec/web/api.py`
- `dev/hec/web/server.py`
- `dev/hec/web/frontend/index.html`
- `dev/hec/web/frontend/js/api.js`
- `dev/hec/web/frontend/js/app.js`
- `dev/hec/web/frontend/js/pages.js`
- `dev/hec/locales/cs.json`
- `dev/hec/locales/en.json`
- `dev/hec/docs/API.md`
- `dev/hec/tests/test_core_config.py`
- `dev/hec/tests/test_web_api.py`

---

## 4. MVP akceptační kritéria (HEF – první fáze)

1. **Integrace bez dopadu na operations**
   - Žádná změna rozhodovací logiky controlleru a žádná změna change-gate TNG.
2. **Finance stránka je dostupná**
   - UI má navigaci na `#/finance` a `#/finance/manual`.
3. **Finance API je dostupné**
   - `GET /api/finance` vrátí KPI + audit payload.
   - `GET /api/finance/manual` vrátí seznam ručních položek.
4. **Document reader scaffold funguje**
   - umí zpracovat PDF/XLS/XLSX/CSV ze složky inbox,
   - dělá základní klasifikaci,
   - archivuje dokument,
   - stejný dokument znovu nenaimportuje.
5. **Auditovatelnost**
   - u importovaného dokumentu je uložen `file_hash`, parser metadata,
     source/archivní cesta a čas zpracování.
6. **Konfigurace je validovaná a bezpečná**
   - finance sekce má defaulty, nic se nezapíná samo (`finance.enabled=false`).
7. **I18N**
   - nové finance UI texty existují v `cs` i `en` katalozích.

---

## 5. Navazující fáze po kroku 10

- CRUD API pro ruční položky (`create/edit/delete`), přílohy a CSV export.
- Plnohodnotné parséry faktur (PDF/XLS/XLSX) po typech energií.
- Datový model assets/payments/baseline/economics v persistenci.
- Bankovní integrace přes samostatné rozhraní (`bank_reader`) až po
  stabilizaci API bank (bez fake implementace).
- Ekonomika: simple payback + NPV + IRR nad doložitelným cash-flow modelem.
