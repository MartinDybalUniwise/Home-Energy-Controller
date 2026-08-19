# Nasazení

Systém běží na Raspberry Pi i na Windows ze stejného kódu. Kromě Pythonu 3.11+
a dvou knihoven (`requests`, `beautifulsoup4`) nepotřebuje nic – žádný Node,
žádnou databázi, žádný Docker.

## Raspberry Pi / Linux

```bash
git clone https://github.com/MartinDybalUniwise/Home-Energy-Controller.git
cd Home-Energy-Controller
sudo ./dev/hec/deploy/install.sh
```

Skript ověří verzi Pythonu, nainstaluje závislosti, vytvoří konfiguraci
a `.env`, nastaví službu `hec.service` a spustí ji.

```bash
systemctl status hec       # stav
journalctl -u hec -f       # logy
systemctl restart hec      # restart po změně .env
```

Provozní data (`data/`, `logs/`, `history/`) instalace nikdy nepřepisuje.

## Windows

```powershell
powershell -ExecutionPolicy Bypass -File dev\hec\deploy\install.ps1
Start-ScheduledTask -TaskName HomeEnergyController
```

## Ruční spuštění

```bash
python3 dev/run.py --init          # vytvoří konfiguraci a .env
python3 dev/run.py --once          # jedno kolo čtení, vypíše výsledek
python3 dev/run.py --status        # stav readerů jako JSON
python3 dev/run.py --no-web        # jen sběr dat
python3 dev/run.py                 # sběr dat + webové rozhraní
python3 dev/run.py --diagnostics   # ZIP pro podporu (bez tajemství)
```

Na Windows `py -3` místo `python3`.

## Tajemství

Hesla, klíče a tokeny patří výhradně do `.env` (viz `.env.example`).
Konfigurace na ně odkazuje zápisem `${HEC_TNG_PASSWORD}`. Do gitu se `.env`
nikdy nedostane a v logu ani v diagnostickém exportu se hodnoty neobjeví.

## Síť a přístup

Rozhraní naslouchá na portu 8080. Prázdné `web.password` znamená přístup bez
přihlášení – vhodné jen v důvěryhodné domácí síti.

**Systém se nikdy nevystavuje přímo do internetu.** Vzdálený přístup se řeší
VPN nebo reverzní proxy s TLS (nginx, Caddy). Ukázka pro Caddy:

```text
energie.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

## Aktualizace

```bash
cd /opt/home-energy-controller
git pull
systemctl restart hec
```

Konfigurace ani data se aktualizací neztrácejí. Nová pole v konfiguraci se
doplní z výchozích hodnot, neznámá pole zůstanou zachována.

## Zálohy

Zálohovat stačí `dev/hec/config/config.json`, `.env` a adresář `history/`.
Historii starší než 30 dní si systém archivuje sám na cestu `storage.archive_path`
(NAS, externí disk); dokud tam kopii neověří, lokální soubor nesmaže.

## Obnova po výpadku

Systém se po restartu dopočítá sám: chybějící denní bilance i cykly spotřebičů
doplní údržba, telemetrie TNG naváže na uložený kurzor a poslední známé hodnoty
se načtou z `data/current_*.json`, takže rozhraní nezačíná prázdné.
