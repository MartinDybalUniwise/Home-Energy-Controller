# Výkonnost – dočasné lokální měření

Tři identické zkopírované solar DBF, 51 676 záznamů z 16.–18. 10. 2026.
Python 3.13.15 na stejném Windows notebooku. Dočasný skript mimo Git, izolované
úložiště, žádné zařízení. Měřen wall/process CPU, tracemalloc peak (Python alokace,
nikoli RSS), Windows GetProcessIoCounters a zachycený stdout. Instrumentace sama
přidává režii. Notebook současně provozuje původní HEC; nejde o izolovaný laboratorní
ani produkční post-deploy benchmark. Neměřené RSS zlepšení se netvrdí.

## Nulový přírůstek po zahřátí – tři běhy, stejný testovací Python

| Metrika | Původní | Nový |
|---|---:|---:|
| Medián wall | 0,2420 s | 0,000264 s |
| CPU rozlišení 15,6 ms | 0,2344–0,2500 s | pod rozlišením |
| Python peak | přibližně 19,6 MB | 3,2–6,9 kB |
| Čtené bajty/běh | 17 442 181 | 0 |
| Zapsané bajty/běh | 3 773 324 | 0 |
| Checkpoint zápisy/běh | 1 | 0 |
| Velikost checkpointu pro sadu | 3 773 324 B | 9 774 B |
| Přímý stdout/běh | 117 B | 0 B |

To je fast path, kdy není splatný obsahový audit. Zachovaná metadata sama neprokazují
neměnnost: existuje omezený round-robin audit jednoho souboru, nejdříve po 60 s od
jeho skutečné kontroly. Naměřený obsahový audit čte zhruba 5,8 MB jednoho souboru,
trvá 0,021–0,024 s a při nezměněném obsahu stále nezapisuje checkpoint.
Při 369 souborech a poll 10 s může kompletní kontrola stejné size/mtime trvat
přibližně 62 minut bez dalšího backlogu. Běžně změněná metadata se zpracovávají
při následujících bězích, nejvýše čtyři soubory v jedné dávce. Discovery cache 30 s.
Poškozený nezměněný soubor má 60 s retry backoff, aby neblokoval další soubory.

## Větší doplnění

Výchozí opakovaný běh s procesními I/O čítači: wall 108,90 s, CPU 106,94 s,
Python peak 80,18 MB, read 34,84 MB, write 33,09 MB, 51 677 write operací.
Finální nový kód: wall 72,31 s, CPU 71,56 s, Python peak 108,85 MB, read 60,23 MB, write 37,22 MB, 4430 write operací. Při počáteční migraci se čtou sousední partition, aby staré UTC denní soubory nezpůsobily duplicity přes místní půlnoc. Paměť i read objem tohoto jednorázového backfillu jsou vyšší než původní; nejde o plošné zlepšení. Běžný import po migraci sousední soubory navíc neprochází. Podrobnosti v RESULT.md.

Zápis při větším doplnění nemusí být menší: stabilní identita záznamu/bloku přidává
pole potřebná pro opravy a bezpečný retry. Finální naměřená implementace měla
37,22 MB výstupu místo 33,09 MB, ale 4430 write operací místo 51 677. Netvrdí se
plošné snížení všech I/O. Největší úspora je běžný stav bez přírůstku.

## Logy a produkce

Existující hec.log/errors.log mají RotatingFileHandler, max_bytes=5 000 000,
backups=5; přítomné rotované hec.log.1 až .5 odpovídají této velikosti.
Rutinní BaseReader poll_success je DEBUG, přímý SDG print je nahrazen loggerem;
import změn/chyb má souhrn INFO, příkazy a řídicí audit zůstávají.
Počet bajtů trvalých logů po nasazení a změna produkčního CPU/RSS zatím nezměřeny,
protože produkce nebyla aktualizována ani restartována.
