# Krok 04 – webové API, rozhraní a jazykové mutace (milník M2)

Cíl: systém přestává být službou na pozadí a začíná odpovídat na tři otázky
z `UX principu` zadání – co se děje, proč, co bude dál.

## Co krok obsahuje

| Oblast | Výsledek |
|---|---|
| API | `/api/current`, `/status`, `/history`, `/sources`, `/prices`, `/weather`, `/prediction`, `/summaries`, `/appliances`, `/config`, `/config/schema`, `/i18n/{lang}`, `/session`, `/login` |
| Server | `web/server.py` nad `ThreadingHTTPServer` – směrování, statické soubory, přihlášení tokenem v cookie |
| Rozhraní | Přehled, Historie, Predikce, Nastavení; navigace menu **i** gestem |
| Grafy | vlastní SVG graf se zaměřovačem, legendou a tabulkovým pohledem |
| Tok energie | SVG schéma se směrem a tloušťkou šipky podle výkonu |
| Pozadí | dynamické podle počasí a denní doby, úrovně animace `full/reduced/off` |
| Jazyky | `core/i18n.py`, katalogy `cs.json` a `en.json` (154 klíčů), formátování přes `Intl` |
| PWA | manifest, service worker s offline shellem |

## Rozhodnutí

1. **Bez frameworku a bez build kroku.** Backend stojí na `http.server`,
   frontend na ES modulech bez bundleru, graf je vlastní SVG. Důvod je
   provozní: u zákazníka na Raspberry Pi nemá co běžet Node, a instalace
   nesmí záviset na dostupnosti npm ani CDN.
2. **Data se do offline cache neukládají.** Service worker cachuje jen shell;
   `/api/*` jde vždy ze sítě. Zobrazit stará měření jako aktuální by bylo
   horší než nezobrazit nic.
3. **Přihlášení je volitelné.** Prázdné `web.password` = rozhraní bez hesla
   (důvěryhodná domácí síť). S heslem se vydává token v `HttpOnly`,
   `SameSite=Strict` cookie. Systém se nikdy nemá vystavovat přímo do internetu –
   od toho bude v kroku produktizace reverzní proxy.
4. **Tajemství se z UI nikdy nezapisují zpět.** Konfigurace se do rozhraní
   posílá zamaskovaná a zamaskovanou hodnotu server ignoruje; hesla se mění
   výhradně v `.env`.
5. **Server data zhušťuje sám.** Rozsah 30 dní by v syrové podobě znamenal
   statisíce řádků; `/api/history` vrací hodinové koše, den minutové.
6. **Zaměřovač a tooltip nejsou doplněk.** Graf bez nich se v prohlížeči čte
   špatně, na mobilu vůbec. Ke každému grafu patří i tabulkový pohled.
7. **Dvojitá osa Y je zakázaná** (viz `UI_DESIGN.md`). Výkon a cena jsou dva
   grafy nad sebou, ne jeden se dvěma škálami.
8. **Ikony jsou vlastní jednobarevná SVG.** Kresba televizní grafiky se
   nepřebírá – u produktu k prodeji je licenční čistota podmínka.

## Nalezená a opravená chyba

`PUT /api/config` hlásil prázdný seznam polí vyžadujících restart: porovnával
se stav *po* uložení. Konfigurace se teď porovnává proti kopii pořízené před
zápisem. Odhaleno testem `test_config_put_reports_fields_needing_restart`.

## Akceptační kritéria

- [x] 115 testů zeleně, `ruff check .` bez nálezu.
- [x] Přepnutí CZ↔EN přeloží celé UI včetně formátu čísel a data (`Intl`).
- [x] Test hlídá, že žádný klíč použitý v UI nechybí v katalogu a že oba
      jazyky mají shodnou sadu klíčů i shodné parametry ve větách.
- [x] Změna intervalu čtení jde z UI, bez editace souborů.
- [x] Pokus o průchod adresářem (`/../../etc/passwd`) server odmítne.
- [ ] Ověření na reálném mobilu a tabletu – čeká na nasazení u zadavatele.
