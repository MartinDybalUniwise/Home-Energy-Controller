# Přírůstkové release zálohy

Záloha jednoho releasu je malý úplný seznam referencí na ověřené neměnné payloady.
Staré soubory se znovu nekopírují ani nekontrolují. Původní plná záloha zůstává
závislostí nových snapshotů; nové a změněné soubory jsou v samostatném objektovém
úložišti podle SHA-256. Nejde o komprimování ani přesouvání produkční historie.
Celková logická velikost obnovitelného snapshotu se odlišuje od skutečně nově
zkopírovaných bajtů (`copied_bytes`). Malé JSON manifesty se ukládají při každém releasu.

## Registrace existujícího základu

```text
python dev/release_backup.py register --root <produkce> --vault <zalozni-uloziste> --baseline <overena-plna-zaloha>
```

Registrace čte pouze původní `verified.json` a `manifest.json`; historické payloady
neotevírá a nekopíruje. Sama ještě nepředstavuje aktuální release snapshot.
Ve Windows HEC je produkce `C:/TepelneCerpadlo/Home-Energy-Controller`, základ
`C:/TepelneCerpadlo/hec-backup-20261020-201411` a nové úložiště
`C:/TepelneCerpadlo/hec-release-backups`. Úložiště obsahuje soukromou konfiguraci;
nepatří do Gitu ani do veřejných diagnostických exportů.

## První přechod a běžný release

1. Pouze čtením ověřit skutečný kořen, verzi, PID a listener produkce. Uchovat
   konkrétní PID pro danou odstávku, nikoli PID z minulého releasu.
2. Zastavit skutečný proces i všechny samostatné writery/importéry. Ověřit zánik
   procesu a listeneru. `Application.stop()` po časově omezeném joinu není důkaz
   skončení všech vláken. Nástroj žádný proces nezastavuje ani nespouští.
3. Pouze při prvním přechodu spustit:

```text
python dev/release_backup.py capture --root <produkce> --vault <zalozni-uloziste> --stopped-pid <skutecne-zastaveny-pid> --bootstrap
```

Tento explicitní audit jednou projde současnou historii a porovná ji s ověřeným
základem. Stejné payloady se nekopírují. Uloží se jen nové/změněné soubory a
odstraněné soubory se vyřadí z referencí. V této nepřerušené odstávce nasadit
schválený kód se sledováním změn; před jeho aktivací znovu nespouštět starý kód
bez sledování. Úspěšný snapshot je podmínkou změny kódu releasu.

Při následujícím releasu, znovu se skutečně zastavenými writery:

```text
python dev/release_backup.py capture --root <produkce> --vault <zalozni-uloziste> --stopped-pid <skutecne-zastaveny-pid>
```

Rutinní příkaz nikdy nevypisuje ani neprochází adresář denních historických souborů.
Použije trvalou sadu změněných cest v `history.backup-tracking`, kterou storage,
TNG/SDG merge, offline repair a archivátor zapisují před změnou souboru. Zaznamenává
také změny starých dní. Chyba uložení značky zabrání neoznačenému zápisu. Značky
se potvrzují až po atomickém publikování manifestu a `HEAD.json`.
Nevzniká závislost na čistém ukončení aplikace. Pád před prvním appendem může
zanechat značku nevytvořeného dne; tento bezpečný false positive se potvrdí bez dat.
Odstranění dosud nezálohovaného skutečného souboru se naopak nezamlčí.

CLI odmítne živý uvedený PID, živý zaznamenaný writer PID i stále odpovídající
konfigurovaný API port. Operátor stále musí zastavit případné samostatné nástroje;
nemá spouštět writery souběžně s údržbou. Podporované jsou běžné lokální cesty
`data`, `history`, `logs`; externí archive a jiná úložiště jsou explicitně odmítnuta.
Složka `odlozene-logy` se vyloučí před vstupem. Staré diagnostické logy se nečtou.

## Obnova a rollback

```text
python dev/release_backup.py restore --root <produkce> --vault <zalozni-uloziste> --snapshot <id> --target <nova-prazdna-staging-slozka>
```

Obnova je výslovná operace: tehdy se potřebné historické payloady přečtou a ověří.
Příkaz odmítá existující cíl, chybějící závislosti, poškozené payloady, traversal
i odkazované/special tar členy. Obnoví kód, Git repository, konfiguraci a data vybraného snapshotu.
Do produkce nic nepřepisuje a nic nespouští. Kontrolu stagingu a jeho přepnutí do
produkce musí dokončit schválený release postup. Tracker obnoveného stagingu je
zneplatněn; jeho nové spojení s úložištěm vyžaduje explicitní audit při odstávce.

Před rollbackem na kód nebo nástroj bez protokolu sledování:

```text
python dev/release_backup.py invalidate --root <produkce> --vault <zalozni-uloziste> --stopped-pid <skutecne-zastaveny-pid>
```

Nevynechat tento krok. Nezaznamenané ruční zásahy či použití starých externích
importérů znamenají mezeru v pokrytí; další capture má skončit chybou a vyžaduje
výslovný nový bootstrap audit. Automatický plošný fallback není povolen.
Nikdy neodstraňovat původní baseline ani objekty, na které odkazuje zachovaný snapshot.
Automatické mazání/pruning objektů není součástí tohoto nástroje.

## Přerušená záloha

Při výjimce zůstává poslední publikovaný HEAD platný. Značky, které nebyly
potvrzeny, se při opakování znovu ověří; již ověřené objekty se nekopírují podruhé.
Po násilném ukončení zálohovacího procesu může zůstat `.lock`:

```text
python dev/release_backup.py unlock --root <produkce> --vault <zalozni-uloziste>
```

Příkaz ověří, že PID vlastníka zálohovacího zámku již nežije, a odstraní pouze
tento zámek. Živý zámek neodstraní. Potom zopakovat rutinní capture; nepřidávat
`--bootstrap`, pokud nedošlo k prokázané mezeře ve sledování.
