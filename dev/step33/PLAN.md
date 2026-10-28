# Plán Step33 — pravdivá data a čitelná hlavní stránka

## Goal

Obnovit čitelnou hlavní stránku a graf podle referencí při zachování doložených hodnot, jednotek a dat.

Plán a nasazení vlastník výslovně schválil. Implementace, testy, review i produkční ověření dokončené. Nasazena verze0.1.6; důkazy v RESULT.md.

## Doložená zjištění

- Okamžitá čísla HEC a schématu SDG jsou blízká: FVE 1,21 kW / 1 214 W, dům 3,13 kW / 3 113 W, import 1,88 kW / 1 864 W. SDG současně ukazuje jiné hodnoty domu 3 077 W a 3 083 W. Hodiny stránky 13:47 nejsou časem měření střídače 13:44:40. Samotné snímky nedokazují chybu měřidla.
- Bilance schématu SDG je přibližně 1 214 + 1 864 + 42 = 3 120 W proti domu 3 113 W. Malý zbytek vyžaduje posoudit synchronizaci, měřicí místa, ztráty a přesnost.
- advisor.js v tabulce Vývoj v dalších hodinách používá ghi_wm2 a buňky W/m² pod hlavičkou FVE výroba (kW): prokázaná záměna veličiny v rozhraní.
- predictor.py::forecast začíná zítřkem, ale advisor.js::bestAdvice vybírá první vhodný den a renderToday jeho rozsah používá i pod dnešním odhadem. Datum není správně svázané.
- Záporný příkon TČ −1,74 kW zůstává hlavní hodnotou navzdory chybě měření. CSS má několik pravidel podle výšky desktopu, která výrazně zmenšují písmo a karty.

## Postup

| Step | Purpose | Status |
| --- | --- | --- |
| S01 | Doložit původ a časovou shodu údajů HEC/SDG | DONE |
| S02 | Sjednotit hodnoty, kvalitu, jednotky a datum | DONE |
| S03 | Obnovit rozložení podle zářijových referencí | DONE |
| S04 | Vrátit graf skutečné historie a doložené předpovědi | DONE |
| S05 | Cílené datové a prohlížečové ověření | DONE |
| S06 | Review, PR a samostatné schválení nasazení | DONE |

## S01 — audit měření

Po schválení ověřit běžící verzi a kořen procesu. Omezenými dotazy porovnat HEC a dostupná SDG data ve stejném intervalu. Vytvořit tabulku: údaj, pole/registr, měřicí bod, znaménko, jednotka, čas měření/přijetí a perioda obnovy. Rozlišit součet fází, dopočtený dům, Back-Up, AC a DC výkon baterie. Čas stránky není společným časem přístrojů.

Bilanci hodnotit s ohledem na ztráty a přesnost; toleranci doložit daty. Případné mapování opravit pouze na základě důkazu, ne plošným otočením znamének. Nové fyzické měření nebo změna řízení vyžadují další konkrétní plán.

## S02 — pravdivé a jednotné údaje

Dnes a Tok energie budou používat společný normalizovaný snímek včetně směru šipek a textu baterie. Stručně zobrazit stáří a v detailu zdroj/čas. Neplatný příkon TČ zobrazit jako nedostupný s vysvětlením; surovou hodnotu ponechat v diagnostice. Chybějící údaj není nula a záporné číslo neopravovat absolutní hodnotou bez ověření.

Dnešní výrobu, zbývající odhad a zítřejší odhad vybírat podle explicitního data a pojmenovat samostatně. Bez dnešního podkladu přiznat nedostupnost. Doporučení bude mít datum a platné budoucí okno. Ověřit cenu, počasí a čas Europe/Prague včetně přechodu času.

## S03 — vzhled a rozložení

Nejprve náhled s označenými testovacími nebo skutečnými daty a desktopovým/mobilním snímkem. Desktop: postranní navigace, větší uvítání a počasí; výrazná karta doporučení a tři stavové karty; šest přehledných KPI; energetický rytmus a níže výrazný graf s doporučeními spotřebičů. Převzít hierarchii, odsazení, barvy a zaoblení z referencí, zklidnit rušivé pozadí.

Nenutit celý dashboard na jednu obrazovku zmenšováním písma. Odstranit konfliktní zhušťování podle výšky; přirozený svislý posun a pružné sloupce. Na mobilu karty pod sebou, graf podle šířky. Posun grafu nesmí přepnout stránku ani posouvat celý dokument do strany. Zachovat kontrast, klávesnici a čitelnost při zvětšení.

## S04 — skutečný graf

Výchozí řady: žlutá FVE, modrá spotřeba a fialová cena. Výkon vlevo v kW, cena vpravo v Kč/kWh. SOC případně odděleně. Naměřená minulost plnou čarou, budoucí odhad přerušovaně; značka Teď, datum/jednotky/původ v tooltipu. Výpadky ponechat jako mezery, nepoužívat vyhlazení vytvářející neexistující extrémy. Tabulka bude doplňkem grafu.

Prediktor nyní nabízí denní součty, nikoli hodinové výkonové řady. Ověřit dostupné agregáty. Hodinový odhad FVE může navázat na existující převod ozáření a výroby pouze s doloženými jednotkami, kalibrací, pokrytím, konfigurací instalace a souladem s denním odhadem. Odhad hodinové spotřeby vyžaduje dostatek platných srovnatelných historických profilů. Denní součet neopravňuje kreslit libovolnou křivku. Bez podkladů budoucí řada zůstane nedostupná s vysvětlením. Rozšíření předpovědi je pouze informační; nesmí změnit fyzické řízení.

Den / 2 dny / 7 dní nabídnou dostupnou historii a skutečný horizont budoucnosti. Ceny a počasí mohou mít různý horizont. Chybějící dny označit, neextrapolovat kvůli vzhledu. Historii číst omezeně pro požadovaný interval, přednostně existující agregáty.

## S05 — ověření

- Stejný vstupní snímek musí dát na Dnes a Tok energie stejné hodnoty a směry. Testy importu/exportu, nabíjení/vybíjení, nuly, chybějících/starých údajů, záporného příkonu TČ a různých časů zdrojů.
- Regrese jednotek W/kW/kWh/W/m², dnes/zítra, uplynulých doporučení, cenové osy a změny času Europe/Prague. Odhady testovat i při neúplném pokrytí a omezeném horizontu.
- Skutečný prohlížeč: desktop 1280×800, 1440×900 a 1920×1080; mobil šířky 360, 390 a 430 px; zvětšení 200 %. Ověřit přetékání, čitelnost, tooltipy, přepínače a dotykový posun. Uložit snímky před/po. Staré testy vynucující kompaktní rozložení výslovně přizpůsobit novým kritériím, ne pouze vypnout.

## S06 — review a předání

Po testech nezávislé review a konkrétní výsledky s důkazy. Následně PR podle schváleného rozsahu a nový Human Gate pro nasazení. Případná záloha pouze změněného rozsahu schváleným inkrementálním postupem, bez nové kopie 1 GB dat. V původní plánovací fázi se žádná záloha ani nasazení neprováděly; schválený release nyní dokládá RESULT.md.

## Omezení a rizika

Neměnit konfiguraci, fyzické řízení, TNG write gate, opravy Step32 ani surovou historii. Preview má controller.enabled=false a tng.write_enabled=false; produkční nastavení se nekopíruje do preview. Neměnit zmrazené kořenové prototypy. Složku C:/TepelneCerpadlo/odlozene-logy vůbec neprocházet. Diagnostické logy jen posledních 7 dní podle metadat; žádné plošné skeny, importy ani backfill. Při nedostatku hodinových podkladů je výsledkem pravdivě částečný graf, nikoli ilustrativní náhrada.
