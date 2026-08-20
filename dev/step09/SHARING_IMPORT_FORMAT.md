# Formát importu sdílení energie (GoEnergy)

Zjištěno rozborem reálného měsíčního exportu "Rozpis vyúčtování" od GoEnergy
(sdružení, přes které zadavatel sdílí přebytky FVE). Čísla v tomto dokumentu
jsou **syntetická** – reálný soubor obsahuje osobní údaje (jméno, EAN,
konkrétní částky) a do repozitáře nepatří (`CLAUDE.md`, "Žádná tajemství do
gitu" – stejná opatrnost platí i pro osobní/finanční údaje, ne jen hesla).

## Proč soubor, ne živé API

GoEnergy (a pravděpodobně i jiná sdružení) nevystavuje veřejné API – rozpis
vyúčtování se stahuje ručně z portálu jednou měsíčně jako XLSX. `sharing_reader`
proto **neodbavuje síť**, ale sleduje lokální složku (`sharing.import_path`),
kam uživatel soubor po stažení uloží. To je jiný vzor než ostatní readery
(TNG/OTE/weather/Shelly čtou živě), ale pořád platí "readery jen čtou,
controller nezasahuje" – jde jen o to, že zdroj dat je soubor, ne HTTP odpověď.

## Tvar souboru

Jeden list, název listu = EAN výrobny (18místné číslo). Dvě tabulky vedle sebe:

### A) Intervalová data (sloupce A–I, jeden řádek na 15minutovou periodu)

| Sloupec | Význam | Poznámka |
|---|---|---|
| `EAN` | EAN předávacího místa výrobny | shoduje se s názvem listu |
| `DEN` | Datum (bez času) | |
| `HODINA` | Hodina 0–23 | |
| `MINUTA` | Minuta 0/15/30/45 | |
| `Výroba kWh (dodávka do sítě)` | Celková výroba dodaná do sítě v periodě | = sdíleno + prodáno |
| `Výroba kWh (po odečtení sdílení)` | Výroba po odečtení sdílené části | prodává se GoEnergy |
| `Sdílená energie (kWH)` | Kolik z výroby v periodě šlo na sdílení | |
| `Kč/1MWh` | Tržní cena pro danou periodu | obdoba OTE spotu |
| `Celkem` | Hodnota prodané (nesdílené) výroby v periodě | = "po odečtení sdílení" × cena / 1000 |

Ověřeno na reálném souboru (červenec 2026, 2976 řádků = 31 dní × 96 period):
`Celkem = "Výroba po odečtení sdílení" (kWh) × "Kč/1MWh" / 1000`, se zaokrouhlením
na haléře. Sloupec E (dodávka do sítě) se vždy rovná F (po odečtení sdílení) + G
(sdílená energie).

### B) Měsíční souhrn (sloupce K–N, řádky 3–11 prvního listu)

| Buňka | Obsah |
|---|---|
| K3, L3 | "Měsíční vyúčtování", jméno zákazníka |
| K4 | EAN výrobny |
| K5 | Období `DD.MM.RRRR - DD.MM.RRRR` |
| K6:N6 | Hlavička souhrnné tabulky: (popis, množství, jednotková cena, výsledná cena) |
| K7:L7 | "Celková dodávka do sítě", množství v **MWh** |
| K8:L8 | "Sdílená elektřina", množství v MWh |
| K9:L9 | "Elektřina prodaná GoEnergy", množství v MWh |
| K10:N10 | "Srážka z ceny", množství, Kč/MWh (záporné), výsledná srážka v Kč |
| K11:N11 | "Fakturace", množství, Kč/MWh, fakturovaná částka v Kč |

Ověřeno: `množství("Celková dodávka do sítě") = sum(E) / 1000`,
`množství("Sdílená elektřina") = sum(G) / 1000`,
`množství("Elektřina prodaná GoEnergy") = sum(F) / 1000 = dodávka − sdílená`,
`fakturace (Kč) = sum(Celkem) + srážka (Kč)` (srážka je záporná, tj. odečítá se).

## Ukázková struktura (syntetická data)

```text
EAN                 | DEN         | HODINA | MINUTA | Výroba (síť) | Výroba (po sdílení) | Sdíleno | Kč/MWh  | Celkem
859000000000000001  | 2026-07-01  | 10     | 0      | 1.20         | 1.05                 | 0.15    | 3200.0  | 3.36

K3 Měsíční vyúčtování          L3 Jan Novák
K4 859000000000000001
K5 01.07.2026 - 31.07.2026
K6 (popis)                     L6 množství   M6 jednotková cena   N6 výsledná cena
K7 Celková dodávka do sítě     L7 0.876
K8 Sdílená elektřina           L8 0.160
K9 Elektřina prodaná GoEnergy  L9 0.717
K10 Srážka z ceny              L10 0.717     M10 -300.0            N10 -215.0
K11 Fakturace                  L11 0.717     M11 906.0             N11 649.3
```

## Mapování na `EnergyInterval` (dev/step09/EXTENSION_PLAN.md, kap. 3)

Každý řádek intervalové tabulky se převádí takto (pohled je "výrobce", proto
`consumption_kwh`/`shared_received_kwh` zůstávají `None` – tenhle soubor
neříká, kdo konkrétní kWh přijal, jen kolik výrobce sdílel):

```json
{
  "timestamp": "2026-07-01T10:00:00+02:00",
  "source": "sharing",
  "ean": "859000000000000001",
  "role": "producer",
  "consumption_kwh": null,
  "production_kwh": 1.20,
  "shared_received_kwh": null,
  "shared_sent_kwh": 0.15
}
```

## Otevřené otázky, které tento nález nezodpovídá

* Jak vypadá export pro **odběratele** (spotřebitele sdílené energie) – tenhle
  soubor je z pohledu výrobce. Pokud existuje analogický "consumer" export,
  bude potřeba druhý parser/vzor.
* Zda GoEnergy nabízí i strojově čitelnější formát (CSV, API) – zatím ověřen
  jen ruční XLSX export.
