# Krok 08 – produktizace (milník M6)

Cíl: z běžícího systému udělat něco, co lze nabídnout a nainstalovat u zákazníka
bez ručního skládání souborů.

## Co krok obsahuje

| Oblast | Výsledek |
|---|---|
| Instalace | `deploy/install.sh` (systemd), `deploy/install.ps1` (Plánovač úloh), `deploy/hec.service` |
| První spuštění | `dev/run.py --init` – konfigurace, `.env`, adresáře; existující soubory nepřepisuje |
| Podpora | `dev/run.py --diagnostics` – ZIP se stavem, konfigurací a logy, **bez tajemství** |
| Dokumentace | `docs/DEPLOYMENT.md`, `docs/API.md`, `CHANGELOG.md`, přepsaný `README.md` |
| White-label | název instalace a barevný akcent z konfigurace, rozhraní si je bere ze `/api/status` |
| Stav projektu | aktualizovaný `dev/step01/PROJECT_STRUCTURE.md` (≈ 79 % cílového produktu) |

## Rozhodnutí

1. **Instalace nepřepisuje provozní data.** `rsync` vynechává `data/`, `logs/`,
   `history/` a `.env`; aktualizace je `git pull` + restart služby.
2. **Diagnostický export čistí i logy**, nejen konfiguraci – tajné hodnoty se
   sbírají z konfigurace i z `connect.json` a nahrazují v celém obsahu.
   Ověřeno testem proti skutečnému heslu i klíči.
3. **Služba čte tajemství z `.env`**, ne z jednotky systemd – jinak by skončila
   v `journalctl`.
4. **Systém se nevystavuje do internetu.** Dokumentace popisuje VPN nebo
   reverzní proxy s TLS; vlastní TLS server neimplementujeme.
5. **Licence zatím není určena.** Před nabídkou třetí straně je potřeba doplnit
   licenci projektu a přehled licencí závislostí – uvedeno v README i v seznamu
   otevřených bodů.

## Akceptační kritéria

- [x] 181 testů zeleně, `ruff check .` bez nálezu.
- [x] `--init` vytvoří konfiguraci i `.env` a nic existujícího nepřepíše.
- [x] Diagnostický export neobsahuje heslo ani klíče (test proti reálným hodnotám).
- [x] Dokumentace pokrývá instalaci, aktualizaci, zálohy, obnovu i API.
- [ ] Test čisté instalace na Raspberry Pi do 30 minut – čeká na hardware.
