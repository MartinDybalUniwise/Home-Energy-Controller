# Changelog

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/).
Verze odpovídá `hec.__version__`.

## [0.1.0] – 2026-08-19

První ucelená verze produktu. Prototypy v kořeni repozitáře zůstávají v provozu
beze změny, nová funkčnost žije v `dev/hec/`.

### Přidáno

* **Jádro** – konfigurace se schématem (83 polí), validací, zálohou a atomickým
  zápisem; tajemství z `.env`; strukturované logy s rotací a filtrem tajemství.
* **Úložiště** – JSONL historie po dnech a zdrojích, atomický aktuální stav,
  podvzorkování časových řad, archivace starších dat s ověřením kopie.
* **Readery** – GoodWe, TNG, OTE (s přepočtem na CZK a kurzem ČNB), počasí
  (Open-Meteo včetně východu/západu slunce), Shelly gen1 i gen2.
* **Analýza** – denní bilance, cykly spotřebičů, zatížení fází, spotřeba
  tepelného čerpadla na denostupeň.
* **Predikce** – výroba, spotřeba, potřeba tepla, nabití baterie, náklad
  a nejlevnější okna; vše s intervalem a mírou jistoty.
* **Řízení** – deklarativní pravidla s komfortními limity, safe mode při
  zastaralých datech, zápis výhradně přes change-gate TNG.
* **Rozhraní** – responzivní PWA (Přehled, Historie, Predikce, Nastavení),
  vlastní SVG grafy, schéma toku energie, dynamické pozadí podle počasí.
* **Jazyky** – čeština a angličtina, 170 překladových klíčů, formátování
  přes `Intl`.
* **Provoz** – instalace pro Linux i Windows, systemd jednotka, diagnostický
  export bez tajemství, 180 automatických testů a CI.

### Poznámky

* Zápis do tepelného čerpadla i řízení jsou ve výchozím stavu **vypnuté**.
* Změna hesla k tngsmart.cz a odstranění `connect.json` z historie repozitáře
  zůstávají otevřené – čekají na rozhodnutí zadavatele.
