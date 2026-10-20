# Důkazy interpretace času a provozní rozsah

## TNG

Pole time ze stávajícího HeatPumpData nese ISO čas s explicitním Z. Uložený sample_time
je původní údaj měření, zatímco původní timestamp byl čas importu. Nový timestamp
zachovává tentýž okamžik v system.timezone, aby denní partition odpovídala místnímu dni.
Historická settings nejsou měřena endpointem; zachované klíče mají null. Živý snapshot
nadále obsahuje současná nastavení, řízení se nemění.

Na offline kopii bylo 88 863 řádků, 82 502 různých měření a 6 361 duplicit bez
konfliktu naměřených hodnot. Oprava změnila časové zařazení a odstranila nepodložená
historická settings. Devět existujících souhrnů změnilo pouze mean_outside_c/degree_days;
energetické a cenové údaje se nepřepočítávaly z neúplné kopie jiných zdrojů.

Přímé čtení existujícího TNG endpointu ověřilo deset mezer >900 s mezi 19. 8. a
20. 10. 2026, včetně 15.–18. 10. Všechny vrácené First byly prázdné. To znamená
nyní nedostupné doplnění z tohoto zdroje, nikoli důkaz, že měření nikdy neexistovala.
Náhrady nulou, odhadem, SDG ani současnou hodnotou se neprovádějí.

## SDG / Promotic

Ve 2026-10-20T14:36:24Z (16:36:24 Prague) obsahoval poslední právě zapsaný DBF řádek
pm_time=2026.10.20 15:36:00; mtime souboru byl 14:36:00Z. Zdroj tedy v tomto okamžiku
používal UTC+1, nikoli UTC ani letní Prague UTC+2.

Oficiální [konfigurace Promotic Trend](https://www.promotic.eu/cz/pmdoc/Objects/Pma/PmaTrendGroup/Cfg/Trend.htm)
popisuje volbu lokálního a pevného zimního času. Binární PRA neposkytlo při tomto
čtení přímo dekódovaný konfigurační přepínač. Režim zdroje proto dokládá nezávislé
měření čerstvého řádku a historické porovnání s přímou telemetrií GoodWe:

| Den | Porovnané vzorky při -3600 s | Medián absolutní chyby pv_w bez opravy | Při interpretaci UTC+1 | Při UTC+2 |
|---|---:|---:|---:|---:|
| 22. 8. 2026 | 565 | 2015 W | 28 W | 2104,5 W |
| 21. 9. 2026 | 7127 | 1236,5 W | 17 W | 1025 W |

Párování nejbližšího GoodWe vzorku do 15 s, pouze PV >300 W. Pro 18. 10. nebyla
v této kopii dostupná odpovídající samostatná GoodWe historie; nevydává se za důkaz.
Závěr pro tento zdroj: pm_time je pevný zimní čas. Parser používá standardní offset
nakonfigurovaného site timezone a převádí výsledný okamžik do místního pásma.
Explicitní offsety se zachovávají; původní hodnoty values.pm_time zůstávají nedotčené.
Ostatní zdrojová pole času nejsou plošně posouvána. DST nemá dvojznačnost u pevného
zimního času; explicitní offsety a oba přechody mají regresní testy.

## Kopie a zálohy

Pracovní vstup je stabilně ověřená kopie jednotlivých souborů za běhu produkce,
nikoli konečná globální produkční záloha. Samotná oprava proběhla s vypnutými writery
v offline kopii. Její konzistentní záloha včetně dotčených checkpointů má manifest SHA256:
C:/TepelneCerpadlo/step26-evidence/repair-copy-backup/manifest.json.
Další záloha odstranění stavových řádků je repair-status-backup/manifest.json.
Druhý dry-run nad stejným opraveným vstupem: changed_files=[] a nulové další změny.

Původní SDG 1 330 463 řádků: odstraněno 6536 přesných duplicit a 28 796 stavových
souhrnů importu; zůstalo 1 295 131 měření před přehráním dostupných DBF. Opraveno
1 294 712 časových značek pm_time. Stavové souhrny mají specifická diagnostická pole
místo values a nejsou měřením. Nově se ukládají pouze do current, nikoli historie.

Raw data, checkpointy, zálohy, síťové soubory a detailní reporty nejsou v Gitu.
Před případným produkčním zásahem je nutná nová konzistentní záloha po zastavení HEC.
