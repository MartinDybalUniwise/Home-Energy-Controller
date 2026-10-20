# Step26 – ověřený postup nasazení a návratu

Historical initial state: PŘIPRAVENO K DOPRACOVÁNÍ PO BRANÁCH; žádný produkční zásah neproveden.

## Ověřené skutečnosti

- Produkce: C:/TepelneCerpadlo/Home-Energy-Controller.
- Python: C:/Users/elektrika/AppData/Local/Programs/Python/Python313/python.exe.
- Příkaz procesu: dev/run.py, working directory produkční kořen, API localhost:8080.
- Výchozí commit 3f0d9c2, verze 0.1.0, start 20. 10. 2026 11:58:52 Europe/Prague.
- Při počátečním pozorování controller.enabled=false, tng.write_enabled=true.
  Před zásahem znovu načíst všechny stavy včetně GoodWe writer a TNG podsekcí.
- Existující restart C:/TepelneCerpadlo/restart_hec_20261020.ps1 používá ověření
  kořene/PID, Stop-Process, Start-Process dev/run.py a kontrolu hashů konfigurace.
- Produkční Python zatím nemá tzdata; instalace této deklarované runtime závislosti
  je nutný krok před nasazením. Testovací venv ji má. Nedochází tím ke změně nastavení zařízení.

## Vstupní brány

1. Vyřešit tři původní SDG unit failures a původní English Control & Plan E2E
   v příslušném samostatném rozsahu; neobcházet povinné kontroly a neoznačovat FAIL jako PASS.
2. Vyřešit nezačleněnou integrační větev claude/reconcile-production-20261020.
   Step26 PR se porovnává proti ní, aby neobsahoval starší změny řízení.
3. Dokončit import/backfill ověření na kopii, review a skutečný Human Gate.
4. Projít kontroly/merge. Teprve poté doplnit skutečný pevný released_at do
   dev/hec/releases.json a ověřit přesný finální commit (včetně této změny).
   Tag v0.1.1 musí ukazovat na něj. Aktuální manifest je explicitně nevydaný.

## Kontrolované nasazení po splnění bran

1. Zapsat finální commit/tag a aktuální /api/status, ověřit proces/root/port.
   Bez výpisu secrets uložit config hash, kopii konfigurace a kompletní enabled/runtime stavy.
2. Zálohu uložit mimo Git do nového časově označeného adresáře v C:/TepelneCerpadlo.
   Připravit předchozí kód 3f0d9c2 jako Git bundle/archive, přesný starý start příkaz,
   konfiguraci, .env a lokální connect.json. Nezaměňovat pracovní zálohu kopie za produkční zálohu.
3. Zastavit pouze ověřený produkční proces stávajícím postupem. Ověřit konec všech
   jeho writer vláken/procesů, nezávislý proces HEC nesmí dál zapisovat. Neaktivovat
   ani nedeaktivovat controllery změnou konfigurace.
4. Teprve nyní konečná konzistentní kopie history/, data/ (checkpointy, current,
   runtime a stav controllerů), konfigurace a případného aktivního archivu.
   storage.archive_path byl při auditu prázdný; před zásahem znovu ověřit.
   Manifest relativních cest, velikostí a SHA256; ověřit kopie, JSON checkpointy
   a JSONL historii. Při poškozeném řádku ponechat původní zálohu a zásah vyhodnotit.
5. Sladit lokální plánovací dokumenty s releasem až po jejich záloze; nevynucovat
   checkout přes nesouvisející změny. Nahradit kód přesně ověřeným commitem/tagem,
   ponechat provozní data a konfiguraci. Nainstalovat deklarované chybějící tzdata.
6. Offline spustit otestovaný nástroj: python -m hec.tools.repair_history
   --root <ověřený-produkční-kořen> --apply --writers-stopped
   --backup <nový-adresář-mimo-kořen> --report <report-mimo-Git>, s PYTHONPATH=dev.
   Následně dry-run nad stejným vstupem musí vykázat changed_files=[].
7. Spustit přesně existující Python dev/run.py z produkčního kořene, skryté okno
   a stdout/stderr do provozních logů; neprovádět další restart při pomalém importu.
8. Ověřit jednu poslouchající instanci, PID/root/commit/verzi, skutečný changelog
   včetně Prague času, nezměněné config hashe a všechny enabled stavy. Ověřit nové
   měření TNG/SDG, dostupné doplnění, log chyby a importní dobu/I-O. Zapsat čas restartu.

## Rollback

Při selhání zastavit pouze právě nasazenou instanci. Z finální konzistentní zálohy
obnovit celý předchozí kód, data/history/checkpointy/souhrny/config jako jeden celek;
nevracet pouze checkpoint a nezachovat kombinaci nových dat se starým stavem.
Nové soubory neobsažené v původním manifestu odložit mimo aktivní adresář,
neprovádět neověřené rekurzivní mazání. Znovu použít starý ověřený start příkaz,
potvrdit verzi 0.1.0, konfiguraci, enabled stavy a jednu instanci. Při druhém selhání
neopakovat neřízené restarty; uchovat logy a zálohy pro dohledání příčiny.

Tento dokument není důkaz provedeného nasazení, restartu, Human Gate ani úspěšného rollbacku.

## Approved release execution update

Review and owner deployment approval are recorded in STEP.json and ../step27/REVIEW.md. Step27 resolves the baseline test failures; combined CI is green. Release integration is PR41 -> PR40 -> existing production reconciliation branch, preserving the already deployed control code. Main synchronization remains separate. Actual storage paths were rechecked: production-root/data, history and logs; archive_path is empty. Production PID14532, baseline3f0d9c2, version0.1.0, controller.enabled=false and all config hashes recorded in deployment-preflight.json outside Git. No switch is changed during deployment. released_at remains null until a successful actual production deployment is recorded; the final metadata commit is then validated and tagged. A planned short metadata reload follows validation, after the initial import has completed, preserving all production state. This avoids labeling a preparation time as an actual release time.
