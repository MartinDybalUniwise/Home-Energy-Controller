# Výsledek Step27

E-027-001 PASS: 7 testů SDG. Historický import používá SDGHistoryReader; příznak jej zapíná/vypíná. Dokončení importu nepřepisuje živý GoodWe snapshot a Application zachovává metadata vstupního zdroje. Nezavádí se SDG-primary/FTE-backup politika.

E-027-002 PASS: skutečný browser potvrdil příčinu odmítnutí save: prázdná nullable čísla byla odesílána jako 0 (pod minimem 60). Nyní se ukládají jako null. Jazyk se aplikuje po úspěchu, při chybě zůstává původní. Anglický Control & Plan přežije reload. Nové E2E ověřují 600 -> null i odmítnuté uložení bez změny jazyka. Připravený changelog 0.1.1 obsahuje CZ/EN záznam opravy, released_at zůstává null.

E-027-003 PASS: full_validation.py, Windows 11 / Python 3.13.15: 354 unit PASS, 41 browser E2E PASS, 0 selhání a 0 přeskočených E2E, Ruff PASS, 16 SDD struktur PASS, repo hygiene PASS, runtime mock smoke PASS. Samostatná unit fáze má 41 E2E deselected, ta byla následně celá spuštěna v browser fázi.

Evidence mimo Git: C:/TepelneCerpadlo/step27-validation.log a step27-evidence/validation.json. První úplný běh ověřoval pracovní změny nad 0af3b23; finální kontrola implementačního commitu i CI je doplněna níže. Testovací browser je uložen pouze v pracovním adresáři playwright-browsers. Testy používají bezpečné mock preview a dočasná data; uložený mock config se po testech obnovuje. Produkční config, data, aplikace ani proces nebyly změněny či restartovány. Controllery, writery a plánování beze změny.

Gate B a Gate C zůstávají PENDING. Tento krok není DONE. Základ větve je Step26; samostatný PR obsahuje pouze Step27. Předchozí integrace produkční větve do main a review Step26 nadále vyžadují vyřešení před nasazením.

## Commit a CI

Implementační commit: 3a0cb7825439ff0a7651cf3f205e7f219f61af60. Draft PR #41: https://github.com/MartinDybalUniwise/Home-Energy-Controller/pull/41. Push i PR běhy mají test (3.11), test (3.12) a sdd-validation SUCCESS. CI full_validation na přesném commitu: 354 unit PASS, 41 browser E2E PASS, bez skipped E2E. Evidence: https://github.com/MartinDybalUniwise/Home-Energy-Controller/actions/runs/39450789932 a https://github.com/MartinDybalUniwise/Home-Energy-Controller/actions/runs/39451057635.

Produkční API po implementaci potvrzuje 0.1.0 a původní started_at 2026-10-20T11:58:52.561682+02:00. Gate B/C nejsou tímto CI ani tímto zápisem schváleny.

Opakovaná lokální full_validation na implementačním commitu 3a0cb78 rovněž PASS: 354 unit (200.88 s), 41 browser E2E (85.92 s), Ruff/SDD/repo/runtime PASS. Evidence step27-evidence/validation-final.log a validation-final.json. Při závěrečné evidenci byly upraveny pouze dokumenty Step27; produktový kód od commitu zůstal stejný. Testovací mock procesy zastaveny a tracked mock config obnoven.
