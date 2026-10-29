# OpenAI klíč pro oddělenou MCP službu

Vlastník výslovně požádal o vstupní pole v Nastavení HEC dne 29. 10. 2026. Jde o malou konfigurační změnu; řízení, readery, plány a řídicí kredenciály zůstávají beze změny. Souhlas vlastníka a AGENTS.md pokrývají implementaci, test a nasazení.

V Nastavení je samostatný formulář MCP / ChatGPT. Není součástí formuláře konfigurace HEC a používá vlastní tlačítko. Klíč se nevkládá do `config.json`, `.env` HEC, Git repozitáře nebo exportu nastavení. Uloží se jednorázově do chráněného `C:/TepelneCerpadlo/hec-ai-gateway/private/openai-runtime-key.txt`, který používá samostatná MCP/tunnel služba. GET vrací pouze available/configured, nikoli klíč. Existující klíč webový formulář nepřepíše.

Přenos: stejný HTTPS origin jako HEC, loopback na domácím PC, nebo výhradně konkrétní privátní origin `http://192.168.2.115:8080`, pro který vlastník výslovně potvrdil přístup přes vlastní VPN. Aplikace sama nemůže určit, zda je VPN na telefonu zapnutá; vzdálený uživatel ji musí používat. Server odmítá chybějící/cizí Origin a jiný content-type než application/json. Ostatní HTTP adresy ani veřejné HTTP hosty formulář nepřijme. Tato změna neotevírá žádný port ani nevytváří veřejný tunel. HTTP úsek v domácí síti zůstává součástí existující důvěryhodné sítě, nejde o HTTPS od telefonu až k HEC.

Práva: stávající HEC přihlášení platí také pro endpoint. Na Windows produkci se nejprve vytvoří prázdný soubor s create-new, vypne se dědičnost, přístup dostanou pouze vlastník ze souboru owner-sid, SYSTEM a Administrators, a teprve potom se zapíše klíč. Selhání oprávnění končí bez uložení klíče. Žádné klíče ani jejich prefix/suffix se nevracejí nebo nelogují. V test/preview instalacích je endpoint ve výchozím stavu vypnutý.

Plán ověření: unit testy transportu, pevného cíle, no-overwrite a ACL-before-write; regresní HTTP/config testy; izolovaný browser test s falešnou klíčovou hodnotou a vlastním dočasným úložištěm; před produkčním nasazením podporovaná přírůstková záloha. Žádný falešný klíč se nezapisuje do produkčního úložiště. Živý OpenAI doctor a připojení ChatGPT následují až po zadání skutečného klíče vlastníkem.
