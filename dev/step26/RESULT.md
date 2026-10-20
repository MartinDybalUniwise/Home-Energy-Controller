# Result – Step26

## Stav

Gate A schválena vlastníkem 20. 10. 2026 16:24 Europe/Prague. Implementace je
v izolovaném checkoutu C:/TepelneCerpadlo/step26-git. Produkce stále běží z
C:/TepelneCerpadlo/Home-Energy-Controller na původním kódu 3f0d9c2, verzi 0.1.0.
Step IN_PROGRESS; review ani Human Gate nejsou vydávány za splněné.

## Opravy

- TNG historie používá skutečný sample_time v site timezone, historická settings
  jsou null. Překryv je idempotentní upsert a kurzor následuje až po zápisu.
- Jedna dostupná historická denní dávka TNG na stávající poll zachycuje opravy
  starších zdrojových záznamů. Žádná nová služba, reader ani scheduler.
- Promotic pm_time interpretuje prokázaný pevný zimní čas, explicitní offsety
  zachovává. Raw values zůstávají původní. Důkazy v DATA_EVIDENCE.md.
- SDG checkpoint je kompaktní stav bloků, fast path podle metadat a omezený
  round-robin audit zachytí i stejnou size/mtime. Retry zachovává uložené bloky,
  poškozené soubory nemohou trvale blokovat zbývající historii.
- Importní status už není zapisován jako měření. Rutinní úspěchy jsou DEBUG;
  příkazy, změny a chyby mají zachovaný audit a existující rotaci.
- Přidána kandidátní verze 0.1.1 s klikacím changelogem a jedním release manifestem.
  released_at=null znamená nevydaný kandidát, nikoli vymyšlený čas vydání.
  Čas bude pevně zapsán až při skutečném releasu, s tagem na ověřený commit.
- Nutná runtime závislost tzdata na Windows je deklarována v requirements.txt.
  Do produkčního Pythonu zatím nebyla nainstalována. Zmrazené skripty se neměnily.

## Opravená offline kopie

| Zdroj | Před | Po opravě před doplněním DBF | Opravy |
|---|---:|---:|---|
| TNG | 88 863 | 82 502 | čas měření, null settings, 6361 duplicit |
| SDG | 1 330 463 | 1 295 131 | 1 294 712 pm_time značek; 6536 duplicit; 28 796 stavových řádků odstraněno |
| Summary | 58 denních souborů | stejné období | 9 změněných teplotních souhrnů, jiné ukazatele zachovány |

Druhé spuštění nad totožnými opravenými vstupy: changed_files=[], nula dalších
změn času/nastavení/duplicit/souhrnů. Reálný TNG endpoint pro deset ověřených mezer
>15 minut vrátil prázdné First, včetně odstávky 15.–18. 10.; doplnění není nyní
z tohoto zdroje dostupné. Nedošlo k odhadům ani dosazení nuly/současných hodnot.
Celkové přehrání všech 369 dostupných DBF zpracovalo 692 319 platných zdrojových měření a doplnilo 434 nových. SDG po doplnění: 1 295 565 měření. Další úplné přehrání od prázdného testovacího checkpointu a následné opakování: nula dalších změn a nula checkpoint zápisů. 123 zdrojových řádků nemělo normalizovatelný čas, proto nebyly vloženy. Dostupnost SDG nenahrazuje samostatnou GoodWe historii. Kompaktní checkpoint celé kopie: 250 390 B proti původním 94 147 898 B. Přehled podle zdroje a dne: C:/TepelneCerpadlo/step26-evidence/history-before-after-by-period.csv.

## Výkon

Stejná sada 51 676 měření, dočasné měření mimo Git; podmínky a omezení PERFORMANCE.md.
Původní instrumentovaný backfill wall 108,90 s / CPU 106,94 s / Python peak 80,18 MB;
finální kód wall 72,31 s / CPU 71,56 s / peak 108,85 MB. Při počáteční migraci paměť vzrostla 80,18 -> 108,85 MB a čtení 34,84 -> 60,23 MB kvůli kontrole sousedních denních partition; jde o přiznaný jednorázový tradeoff, nikoli ověřené zlepšení paměti backfillu. Výstupní bajty při doplnění
vzrostly 33,09 -> 37,22 MB kvůli identitám; write operace klesly 51 677 -> 4430.
Není tvrzeno plošné zlepšení všech I/O ani produkční RSS.

Při nulovém přírůstku: medián wall 0,2420 -> 0,000264 s. Čtení 17,44 MB -> 0,
zápis 3,77 MB -> 0; checkpoint 3,77 MB -> přibližně 9,8 kB pro sadu. Splatný
obsahový audit čte jeden soubor, nikoli celou historii. Produkční after měření
neprovedeno, protože nasazení neproběhlo.

## Validace

- Cílená historie/TNG/SDG sada: 75 PASS.
- Celá unit sada finálního kódu: 351 PASS, 3 FAIL (původní test_sdg_log kontrakty),
  39 E2E deselected při tomto unit běhu. Tyto tři chyby reprodukovány na 3f0d9c2.
- Skutečné browser E2E: 38 PASS, 1 FAIL (původní English Control & Plan), 0 skipped.
  Selhání reprodukováno na samostatném původním mock preview :8182.
- Nový changelog samostatně znovu ověřen: 2 PASS, desktop/mobil, pořadí, Prague
  zimní/letní datum, zavření tlačítkem/Escape, návrat focusu, žádné pageerror.
- Ruff PASS; validate_repo PASS; validate_readme_status PASS; Step26 ready PASS.
- Povinný full_validation: FAIL na třech původních unit testech. Nenahrazen
  vynecháním testů ani úpravou SDD. Přeskočená kontrola není PASS.
- Diff controllerů, writerů, GoodWe manageru, scheduleru a SDD frameworku prázdný.
  Zápisová část TNG, confirmation gate a 900 s limit beze změny.

## Brány a produkce

Kód commitnut a pushnut: 126cd19c30c5189e407c70f9336b16c58189ebd8. Draft PR https://github.com/MartinDybalUniwise/Home-Energy-Controller/pull/40, základ claude/reconcile-production-20261020. CI na Python 3.11/3.12 a sdd-validation potvrzuje stejné tři původní unit chyby; žádné nové selhání. GitHub konektor tvorbu PR odmítl 403; po výslovném potvrzení přesného repozitáře vlastníkem byl push i draft PR proveden přes existující Git přihlášení. Žádný merge, release tag, skutečný čas vydání, nasazení ani restart zatím neprovedeny.
Blokace: povinné původní testové chyby, předchozí integrační základ main, review a
Human Gate. OUT_OF_SCOPE.md zaznamenává nesouvisející problémy bez jejich oprav.
DEPLOYMENT_RUNBOOK.md obsahuje ověřené cesty, postup zálohy/restartu a návrat.
Konečná konzistentní produkční záloha vznikne až po zastavení HEC; pracovní kopie
ji nenahrazuje. Všechna data, surové reporty a zálohy jsou mimo Git v
C:/TepelneCerpadlo/step26-evidence. Zálohy kopie: repair-copy-backup a repair-status-backup,
oba adresáře s ověřeným manifestem SHA256.

Řídicí logika TČ/FVE, komfort, rozvrhy, konfigurace a aktivní enabled stavy nebyly
změněny. Mimo verzi a changelog nepřibyla žádná nová uživatelská funkce. Žádné
testovací fyzické zápisy do zařízení neproběhly.

Závěrečná čtecí kontrola produkce 20. 10. 2026 17:20 Prague: verze 0.1.0, původní PID 14532, původní start 11:58:52, hlavní controller false, na :8080 jedna poslouchající instance. Živí readery dál sbírají data. Testovací baseline preview :8182 ukončeno; bezpečné mock preview kandidáta :8181 ponecháno k prohlédnutí.
