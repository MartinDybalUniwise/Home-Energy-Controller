# Step26 – historie, výkon a verze

## Goal

Opravit existující historii a import, odstranit změřenou zbytečnou práci a doplnit pouze verzi s changelogem. LARGE; Gate A APPROVED 20. 10. 2026 16:24 Europe/Prague, výslovný souhlas vlastníka v chatu.

## Step sequence

| Step | Purpose | Status |
|---|---|---|
| S01 | Výchozí důkazy, časové kontrakty a měření | PASS |
| S02 | Korektní TNG/SDG import a obnova po pádu | PASS |
| S03 | Inkrementální I/O, paměť a logování | PASS |
| S04 | Autoritativní verze a changelog | PASS |
| S05 | Servisní oprava na kopii dat | PASS |
| S06 | Regrese, browser E2E, výkon a review | PASS |
| S07 | Human Gate, PR, release a produkce | PASS |

## Detailed implementation strategy

### S01 – stav a důkazy

Základ je nasazený 3f0d9c2, origin/main 67b9b8f. Další vývoj v izolované pracovní kopii v C:/TepelneCerpadlo; běžící checkout obsahuje do nasazení pouze dokumentaci. Preview controller.enabled=false, tng.write_enabled=false, goodwe.enabled=false, bez produkčních credentials. Ověřit registry a aktivní readery: nález v neaktivním SDGHistoryReader není důkaz incidentu.

Inventarizovat denní/archivní soubory, rozsahy, duplicity, mezery, kurzory a souhrny. Ověřit TNG time a Promotic pm_time včetně DST na skutečných datech. Bez důkazu neposouvat SDG o hodinu. SDG není důkaz úplnosti samostatné GoodWe historie.

Jednorázově měřit na stejných vstupech wall/CPU čas, RSS/špičku paměti, read/write bajty, checkpoint velikost/četnost a objem log řádků/bajtů. Scénáře: nulový přírůstek, append, oprava starého řádku, několikadenní backlog. Opakované srovnatelné běhy; uvést cache podmínky a lokální versus síťové I/O. Neměřené neoznačit jako zlepšení.

### S02 – spolehlivý import

TNG timestamp odvodit z měření, současná settings nepřipojovat starým vzorkům. Zachovat klíče, neznámé null dle kontraktu. Kurzor potvrdit až po uložení. Deterministická identita zdroj/měření; opakování po pádu mezi JSONL a checkpointem bez duplicity, opravený zdrojový řádek aktualizuje původní záznam.

SDG rozlišit append, změnu, truncation/replacement, částečný konec a vadný DBF. Kompatibilně načíst starý checkpoint. Atomické opravy dotčených denních souborů a bounded dávky; konkrétní identitu/checkpoint strategii zvolit podle S01. Žádná nová DB ani změna veřejných formátů mimo nezbytnou opravu.

### S03 – výkon

Omezit discovery/síťové čtení, fast path podle metadat, proudové hashování, bounded paměť/dávky. Metadata nejsou důkaz neměnnosti: zachovat omezenou následnou kontrolu starých dat, testovat stejnou velikost i zachované mtime a uvést latenci detekce. Checkpoint nepsat bez změny, nepřestavovat všechny hashe; případná kompaktní migrace musí zachovat idempotenci. Efektivní dávkové zápisy pouze podle měření.

Ověřit/zabránit překryvu stejné úlohy v současném scheduleru. Neprodlužovat polling jako náhradu opravy. Omezit rutinní INFO/print, zachovat příkazy/chyby/změny/incidentní diagnostiku. Ověřit skutečnou rotaci i stdout. Žádný nový scheduler, služba nebo monitoring.

### S04 – verze

Existuje __version__=0.1.0. Ověřit tagy/vydání; předpoklad patch 0.1.1, pokud není doložena novější verze. Jeden autoritativní release manifest, __version__ a API/UI odvozovat. Pevný čas vydání s offsetem, zobrazení Europe/Prague, existující CZ/EN i18n. Nevymýšlet datum starého vydání.

Malé klikací číslo ve stávajícím rozložení; dialog s nejnovějšími vydáními nahoře, zavření/Escape a návrat focusu. Žádný opakovaný Git z UI/smyčky. Tag vMAJOR.MINOR.PATCH musí ukazovat na nasazený finální ověřený commit; hash zaznamenat mimo release manifest kvůli kruhové závislosti commitu.

### S05 – oprava dat

Jednorázový servisní nástroj dry-run/apply, manifest vstupů/změn a záloha. Konzistentní pracovní kopie pomocí existujícího snapshotu nebo ověření stability kopírovaných souborů; jinak krátké koordinované zastavení až po schválení. Živá data během vývoje neopravovat.

Pouze prokázané timestampy, duplicity a falešná historická nastavení. Doplnit jen skutečně dostupná měření současnými zdroji, žádné odhady/nuly/současné hodnoty. Přepočítat pouze ovlivněné existující souhrny. Druhý apply na stejném vstupu nula změn. Report podle zdroje/období: před/po, doplněné/opravené/odstraněné duplicity a zbývající mezery s doloženou obnovitelností.

### S06 – testy a review

Půlnoc a oba DST přechody, několikadenní odstávka, neuspořádané vzorky, opakování, nové/opravené staré řádky, fault injection před/po každém bodě persistence. Stejné vstupy pro výkon před/po. Existující pytest/ruff, validate_step structural/ready, validate_repo, validate_readme_status, full_validation. Reálné browser E2E na bezpečném preview: číslo/dialog/čas/zavření, stávající stránky a JS konzole. Skipped není PASS. Výchozí nesouvisející selhání zaznamenat, neskrývat. Review proti požadavkům; žádné testovací fyzické zápisy.

### S07 – brány a produkce

Po automatech zastavit před povinným Human Gate; úvodní souhlas není provedený lidský test. DONE až po branách. Jeden krok/větev/PR. Základ obsahuje starší dosud nezačleněné změny včetně řízení: před PR vyřešit integrační závislost/vhodný základ, aby Step26 nepřibalil nesouvisející diff. Nevydávat je za tuto opravu.

Commit/push, PR, povinné kontroly, merge dle pravidel a tag přesně ověřeného finálního commitu s pevným časem vydání. Znovu ověřit produkční kořen/proces/spouštění. restart_hec_20261020.ps1 je podklad k ověření, nikoli automaticky hotový migrační postup.

Před zastavením zaznamenat commit, konfiguraci bez secrets a všechny enabled/runtime stavy. Připravit konkrétní rollback kódu/dat/checkpointů. Zastavit ověřenou instanci, zajistit konec zápisů. Konečná konzistentní záloha dotčené historie/archivů, souhrnů, checkpointů, konfigurace a runtime stavu mimo Git s manifestem/hash ověřením. Následně nasadit otestovaný release, apply ověřené opravy a spustit existujícím způsobem se zachovanými enabled stavy. Při selhání rollback, žádné opakované neřízené restarty.

Ověřit právě jednu instanci, API/verzi, changelog, nová měření/čas, stav doplnění, logy a importní dobu/zátěž. Report Prague času restartu, commit/PR/tag, data a výkon před/po, testy/neprovedené kontroly, záloha/obnova.

## Risks and approval gate

Rizika: nedoložená zóna, nedostupná historie, pád mezi JSONL/checkpointem, nesouvisející rozdíly proti main, výchozí testové chyby a LAN přístup. Neznámé přiznat a při blokaci dokončit bezpečně proveditelnou část. Žádné rozšíření SDD ani implementace architektury Step25.

Gate A byla schválena. Původní pravidlo podle dev/sdd/README.md Workflow 4–6: dokončený plán předložit a zastavit před implementací pro výslovné schválení. Ready validátor požaduje APPROVED; očekávané selhání před Gate A není důvod přepsat bránu.
