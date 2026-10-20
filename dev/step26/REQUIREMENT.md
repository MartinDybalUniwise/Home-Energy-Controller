# Requirement

## Objective

Spolehlivá historie, změřená nižší zátěž a verze s changelogem; ověřený release v produkci.

## Requirements

- REQ-026-001: Zachovat pevné hranice rozsahu, řízení TČ/FVE, konfiguraci a veřejné kontrakty.
- REQ-026-002: Ověřený čas měření a pásmo včetně DST; dnešní nastavení nepatří starším vzorkům.
- REQ-026-003: Idempotentní doplnění dostupné historie, opravy starých řádků a bezpečná obnova po pádu.
- REQ-026-004: Konzistentní záloha, dry-run na kopii a opakovatelný apply; souhrny jen dotčené dny, neznámé bez odhadů.
- REQ-026-005: Číselné měření před/po a skutečně inkrementální zpracování bez omezení historie/aktuálnosti.
- REQ-026-006: Jedna autorita verze, pevné doložené časy, Prague changelog a stávající i18n bez redesignu.
- REQ-026-007: Existující automatické/browser testy, review a skutečné lidské brány, žádné fyzické testovací zápisy.
- REQ-026-008: Jeden krok/větev/PR, čistý diff, commit/push/merge/tag, kontrolované nasazení a rollback se zachovanými enabled stavy.

## Safety

Change-gate a 900 s TNG beze změny; atomické zápisy, JSONL, ISO časy, pathlib a multiplatformnost. Data/logy/zálohy/secrets mimo Git.
