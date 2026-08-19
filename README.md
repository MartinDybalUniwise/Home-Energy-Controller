# Home Energy Controller

Lokální systém pro měření, analýzu, predikci a optimalizaci energetických toků
domácnosti. Běží na Raspberry Pi i na Windows, ovládá se z prohlížeče na
počítači, tabletu i mobilu.

Integruje fotovoltaiku a baterii GoodWe, tepelné čerpadlo TNG, spotové ceny
OTE, počasí a měření spotřebičů přes Shelly. Vše zůstává doma – žádný cloud,
žádná externí služba mimo zdroje dat samotné.

## Co systém dělá

* **Měří** – všechny zdroje v jednom místě, historie v JSONL po dnech.
* **Vysvětluje** – rozhraní odpovídá na tři otázky: co se děje, proč se to
  děje, co bude dál. Každé rozhodnutí má srozumitelné zdůvodnění.
* **Předpovídá** – výrobu, spotřebu, potřebu tepla, náklad a nejlevnější okna,
  vždy s intervalem a mírou jistoty. Žádná falešná přesnost.
* **Řídí** – v mezích komfortu, které si nastavíte, a nikdy proti bezpečnosti.
  Při zastaralých datech se optimalizace zastaví, sběr dat pokračuje.

## Rychlý start

```bash
git clone https://github.com/MartinDybalUniwise/Home-Energy-Controller.git
cd Home-Energy-Controller
python3 -m pip install -r requirements.txt
python3 dev/run.py --init      # vytvoří konfiguraci a .env
python3 dev/run.py             # sběr dat + rozhraní na http://localhost:8080
```

Na Windows `py -3` místo `python3`. Trvalé nasazení (systemd, Plánovač úloh)
popisuje [`dev/hec/docs/DEPLOYMENT.md`](dev/hec/docs/DEPLOYMENT.md).

## Nastavení

Vše podstatné se nastavuje v rozhraní na stránce **Nastavení**: adresy
zařízení, intervaly čtení, cesty k datům a archivu, komfortní meze, ceny,
jazyk a vzhled. Hesla a klíče patří výhradně do `.env`.

Ve výchozím stavu je systém **jen měřicí**: zápis do tepelného čerpadla
(`tng.write_enabled`) i řízení (`controller.enabled`) jsou vypnuté a zapínají
se vědomě.

## Jazyky

Čeština a angličtina, přepínání v rozhraní bez restartu. Další jazyk = jeden
soubor v `dev/hec/locales/`, žádný zásah do kódu
(viz [`dev/step01/I18N.md`](dev/step01/I18N.md)).

## Struktura

```text
/                    funkční prototypy (zmrazené, viz CLAUDE.md)
dev/stepNN/          plány a rozhodnutí jednotlivých etap
dev/hec/             produkt: core, storage, readers, controller, analysis, web
dev/run.py           spouštěč
data/ logs/ history/ provozní data (nikdy se necommitují)
```

Stav dokončení jednotlivých částí:
[`dev/step01/PROJECT_STRUCTURE.md`](dev/step01/PROJECT_STRUCTURE.md).

## Vývoj

```bash
python3 -m pip install -r requirements-dev.txt
pytest          # 181 testů
ruff check .
```

Prototypy `tng_controller.py`, `ote_reader.py`, `weather_reader.py`
a `goodwe-read.py` v kořeni běží v provozu a nemění se, dokud jejich funkce
není přenesena, otestována a ověřena na reálném hardwaru. Pravidla pro práci
v repozitáři shrnuje [`CLAUDE.md`](CLAUDE.md).

## Bezpečnost

* Tajemství jen v `.env`, nikdy v gitu, v logu ani v diagnostickém exportu.
* Zápis do tepelného čerpadla prochází potvrzovacím cyklem a minimálním
  intervalem 900 s – tuto ochranu nesmí obejít žádná optimalizace.
* Systém nepatří přímo do internetu; vzdálený přístup přes VPN nebo reverzní
  proxy s TLS.

## Licence

Zatím neurčena – před nabídkou třetí straně je potřeba doplnit licenci
projektu a přehled licencí závislostí.
