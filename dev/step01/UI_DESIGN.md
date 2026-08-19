# Vizuální jazyk webového rozhraní

Podklad: tři snímky televizní meteorologické grafiky (VÝHLED na 8 dnů, letní
varianta, POČASÍ PODROBNĚ – NA 3 DNY). Bereme z nich **kompoziční a barevný
princip**, nikoli konkrétní grafiku.

> **Právní hranice.** Vysílatelovo logo, jeho ikony a jeho grafika se nepoužijí –
> ani v prototypu. Přebíráme obecný princip (tmavě modrý poloprůhledný panel nad
> fotografií, sloupcová mřížka dnů, velké číslo jako hlavní hodnota), který není
> chráněn. Ikony a fonty musí mít vlastní licenci použitelnou komerčně
> (fonty OFL, ikony MIT/CC-BY nebo vlastní kresba). Před nasazením u zákazníka
> projít licence všech vizuálních assetů.

---

## 1. Co si z předlohy bereme

| Princip z předlohy | Jak jej použijeme |
|---|---|
| Fotografické pozadí odpovídající počasí a ročnímu období | dynamické pozadí podle aktuálního počasí a denní doby (kap. 17 zadání) |
| Tmavě modrý poloprůhledný panel přes celou šířku | hlavní obsahový panel („stripe“), pod ním prosvítá pozadí |
| Záložka s nadpisem nad panelem (`VÝHLED`) | nadpis sekce jako samostatná tmavá záložka vlevo nahoře |
| První sloupec širší a bohatší (datum, ikona, min/max, vítr, srážky, BIO) | první sloupec = **teď**: aktuální výkony, SOC, cena, stav TČ |
| Následující stejně široké sloupce = dny | další sloupce = hodiny nebo dny predikce |
| Velké bílé číslo = hlavní hodnota, menší světle modré = doplňková | výkon/teplota bílá; sekundární hodnota (min, noc, cena) světle modrá |
| Jemné svislé oddělovače se světlem nahoře | oddělovače sloupců, gradient shora |
| Karty s vlastní hlavičkou (POČASÍ PODROBNĚ) | detailní karty na stránce Predikce |
| Klidná, nerušivá animace | úrovně animace `full / reduced / off` |

**Co nepřebíráme:** logo a znělkové prvky vysílatele, konkrétní kresbu ikon,
poměr stran 16:9 jako pevný rám (web musí být responzivní), zlom hodnot
„+1/-4°“ (pro energetiku nečitelný).

---

## 2. Design tokeny

Výchozí režim je **tmavý** – odpovídá předloze a je čitelný na displeji v obýváku
i na mobilu venku. Světlý režim je plnohodnotná alternativa, ne automatická inverze.

```css
:root {
  color-scheme: light;

  /* plochy */
  --bg-photo:        url("/static/bg/day-clear.jpg");   /* mění se dle počasí */
  --scrim:           rgba(255, 255, 255, 0.35);         /* čitelnost nad fotkou */
  --panel:           linear-gradient(180deg, rgba(255,255,255,.88), rgba(238,244,251,.94));
  --panel-solid:     #f4f7fb;   /* plocha grafů – bez průhlednosti */
  --panel-border:    rgba(13, 27, 42, .12);
  --divider:         rgba(13, 27, 42, .10);
  --tab-bg:          #0b2545;   /* záložka nadpisu zůstává tmavá v obou režimech */
  --tab-ink:         #ffffff;

  /* text */
  --ink-primary:     #0d1b2a;
  --ink-secondary:   #40566e;
  --ink-muted:       #6b7f95;
  --ink-value:       #0d1b2a;   /* velké hlavní číslo */
  --ink-value-alt:   #1f6fb2;   /* doplňkové číslo (min, noc, cena) */

  /* stav */
  --state-good:      #1b7f4b;
  --state-warning:   #a86b00;
  --state-serious:   #b4531a;
  --state-critical:  #b3261e;

  /* geometrie */
  --radius-panel:    6px;
  --radius-card:     4px;
  --gap-col:         2px;
  --pad-panel:       20px;
  --shadow-panel:    0 8px 32px rgba(4, 16, 32, .18);
}

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --scrim:         rgba(4, 16, 32, .45);
    --panel:         linear-gradient(180deg, rgba(19,72,134,.86), rgba(10,42,82,.93));
    --panel-solid:   #0d1b2a;
    --panel-border:  rgba(255, 255, 255, .10);
    --divider:       rgba(255, 255, 255, .14);
    --ink-primary:   #ffffff;
    --ink-secondary: #bcd6f2;
    --ink-muted:     #8fb0d4;
    --ink-value:     #ffffff;
    --ink-value-alt: #4fb3ff;
    --state-good:    #3ecf8e;
    --state-warning: #e8b13a;
    --state-serious: #ef8a4a;
    --state-critical:#ff6b64;
  }
}

/* Tmavé hodnoty se deklarují DVAKRÁT: v media query výše (systémové nastavení)
   a zde (přepínač v UI, který musí vyhrát v obou směrech). Blok níže obsahuje
   tytéž deklarace jako blok v media query – při implementaci se generuje ze
   společného zdroje, ne ručním kopírováním. */
:root[data-theme="dark"] {
  color-scheme: dark;
  --scrim:         rgba(4, 16, 32, .45);
  --panel:         linear-gradient(180deg, rgba(19,72,134,.86), rgba(10,42,82,.93));
  --panel-solid:   #0d1b2a;
  --panel-border:  rgba(255, 255, 255, .10);
  --divider:       rgba(255, 255, 255, .14);
  --ink-primary:   #ffffff;
  --ink-secondary: #bcd6f2;
  --ink-muted:     #8fb0d4;
  --ink-value:     #ffffff;
  --ink-value-alt: #4fb3ff;
  --state-good:    #3ecf8e;
  --state-warning: #e8b13a;
  --state-serious: #ef8a4a;
  --state-critical:#ff6b64;
}
```

Žádná barva nesmí být definovaná **jen** uvnitř media query nebo `[data-theme]`
bloku – světlá sada na holém `:root` je základ, tmavá ji přepisuje.

Barevný akcent a název produktu jsou **white-label proměnné** (`--brand-accent`,
`--brand-name`, logo jako SVG v konfiguraci instalace) – viz fáze 6 plánu.

---

## 3. Typografie

| Role | Font | Velikost | Styl |
|---|---|---|---|
| Nadpis sekce (záložka) | Inter | 18 px | uppercase, `letter-spacing: .10em`, 600 |
| Popisek sloupce (den, hodina) | Inter | 15 px | uppercase, `letter-spacing: .08em`, 500 |
| **Hlavní hodnota** | Barlow Semi Condensed | 44–64 px | 600, `font-variant-numeric: tabular-nums` |
| Doplňková hodnota | Barlow Semi Condensed | 28–36 px | 500, barva `--ink-value-alt` |
| Meta řádky (vítr, srážky) | Inter | 14 px | 400, `--ink-secondary` |
| Vysvětlení rozhodnutí | Inter | 15 px | 400, řádkování 1,5 |

Oba fonty jsou pod OFL (komerčně použitelné), obsahují úplnou českou diakritiku
(ě š č ř ž ý á í é ů ú ň ť ď) a self-hostují se – **žádné volání na Google Fonts
z lokálního zařízení**, systém musí fungovat bez internetu.

Jednotka se sází menším písmem a nezalamuje: `7,2 kW` → `<span class="v">7,2</span><span class="u">kW</span>`.
Desetinná čárka v CZ, tečka v EN – řeší formátovač, ne šablona (viz `I18N.md`).

---

## 4. Komponenty

### 4.1 Stripe – hlavní panel

Vodorovný panel s mřížkou sloupců, převzatý z předlohy.

```text
┌ NADPIS ┐
├────────┴──────┬────────┬────────┬────────┬────────┐
│  TEĎ          │ +1 h   │ +2 h   │ +3 h   │  …     │
│  ikona        │ ikona  │ ikona  │ ikona  │        │
│  velká hodnota│  hodn. │  hodn. │  hodn. │        │
│  doplňky      │  alt   │  alt   │  alt   │        │
└───────────────┴────────┴────────┴────────┴────────┘
```

* první sloupec 2× širší, obsahuje 3–4 meta řádky,
* oddělovač `1px` `--divider` + jemný světelný gradient v horních 40 % sloupce,
* na mobilu vodorovný scroll se `scroll-snap`, první sloupec zůstává „přilepený“.

### 4.2 Detailní karta

Karta s vlastní tmavou hlavičkou (předloha „POČASÍ PODROBNĚ – NA 3 DNY“).
Použití: dny predikce, doporučená okna spotřebičů, denní bilance.

### 4.3 Schéma toku energie (Overview)

Jediná komponenta bez předlohy v televizní grafice – kreslí se jako SVG:

```text
        FVE ─┐
             ▼
   BATERIE ◄ DŮM ► SÍŤ
             │
             ▼
             TČ
```

* šipka má **směr** (odběr/dodávka) a **tloušťku úměrnou výkonu** (2–8 px),
* pohyb toku = animované čárkování, při `reduced` jen statická šipka,
  při `off` bez pohybu,
* u každé větve číslo ve stejné hierarchii jako ve stripe.

### 4.4 Ikony počasí a stavů

Vlastní sada v SVG, jednobarevná s akcentem (ne fotorealistické 3D jako předloha –
hůř se škáluje a naráží na licence). Stavy: jasno, polojasno, oblačno, zataženo,
déšť, přeháňky, bouřka, sníh, mlha + noční varianty.

---

## 5. Mapování na stránky

| Stránka | Horní stripe | Obsah pod ním |
|---|---|---|
| **Přehled** | teď + 6 h dopředu (PV, spotřeba, cena) | schéma toku energie, dlaždice: SOC, TČ, TUV, dnešní bilance, vysvětlení posledního rozhodnutí |
| **Historie** | volba rozsahu (dnes / 24 h / 7 d / 30 d / vlastní) | grafy podle sekce 6 + tabulkový pohled |
| **Predikce** | dny D+1 až D+3 jako detailní karty | očekávaná výroba a spotřeba s rozptylem, výhled ceny, doporučená okna |
| **Nastavení** | – | sekce dle kap. 18 zadání, jazyk, animace, motiv |

UX princip (kap. 33): každá stránka musí odpovědět **co se děje, proč se to děje,
co bude dál**. Rozhodnutí controlleru se vždy zobrazuje s důvodem, ne jen výsledkem.

---

## 6. Grafy

Paleta je ověřená skriptem, ne odhadnutá. Slot = entita, barva se **váže na
entitu**, ne na pořadí v grafu; filtr, který skryje sérii, ostatní nepřebarví.

| Entita | Tmavý režim | Světlý režim |
|---|---|---|
| Výroba FVE | `#c98500` | `#eda100` |
| Baterie (nabíjení +, vybíjení −) | `#199e70` | `#1baf7a` |
| Spotřeba domu | `#3987e5` | `#2a78d6` |
| Síť – odběr | `#d95926` | `#eb6834` |
| Tepelné čerpadlo | `#d55181` | `#e87ba4` |
| Síť – dodávka | `#008300` | `#008300` |
| Spotřebiče | `#9085e9` | `#4a3aa7` |

Ověření (`validate_palette.js`, plocha grafu `#0d1b2a` / `#f4f7fb`):

* pořadí pro spojnicový a plošný graf **FVE → baterie → spotřeba → síť**:
  všechny kontroly PASS, nejhorší sousední pár CVD ΔE 8,4, normální vidění 19,8;
* trojice pro rozptylové grafy a small multiples (FVE, spotřeba, baterie):
  PASS i při kontrole všech dvojic;
* světlý režim: PASS, ale tři barvy mají kontrast pod 3:1 vůči světlé ploše →
  **povinné přímé popisky nebo tabulkový pohled** (relief rule).

**Nikdy nedávat FVE (žlutá) a odběr ze sítě (oranžová) vedle sebe v legendě ani
v rozptylovém grafu** – tato dvojice u barvosleposti neprojde (ΔE 4,8).
V pořadí výše je rozdělena baterií a spotřebou.

Pravidla, která platí bez výjimky:

* **žádná dvojitá osa Y.** Výkon [kW] a cena [Kč/kWh] jsou dva grafy nad sebou
  se sdílenou časovou osou a společným zaměřovačem – ne jeden graf se dvěma škálami;
* čáry 2 px, značky ≥ 8 px, mezera 2 px mezi segmenty ve skládaném grafu;
* legenda vždy při 2 a více sériích, u ≤ 4 sérií navíc přímé popisky;
* zaměřovač + tooltip na spojnicových a plošných grafech je součást dodávky,
  ne doplněk;
* mřížka a osy ustupují (`--ink-muted`, 1 px), data jsou nejvýraznější prvek;
* ke každému grafu tabulkový pohled (přepínač „Tabulka“) – kvůli přístupnosti
  i kvůli exportu;
* teploty jako samostatný graf, sekvenční jednohuová škála pro mapy typu
  „výkon podle hodiny a dne“ (modrá 100→700), nikdy duha.

---

## 7. Dynamické pozadí

Stav pozadí = kombinace `weather_code` + denní doba (z východu/západu slunce,
které do weather readeru doplní fáze 1) + roční období.

| Stav | Pozadí | Animace při `full` |
|---|---|---|
| jasné ráno | teplý gradient, nízké slunce | pomalý posun světla |
| jasný den | modrá obloha, řídké mraky | pomalu plující mraky |
| oblačno | šedomodrý gradient | pomalý posun vrstev |
| déšť | tmavší obloha | jemné kapky, nízká hustota |
| bouřka | tmavý gradient | vzácný záblesk (ne stroboskop) |
| sníh | světle šedomodrá | pomalé vločky |
| mlha | mléčný závoj | statický |
| západ slunce | teplé oranžovo-fialové | pomalé stmívání |
| noc | tmavě modrá | volitelné hvězdy |

Pravidla:

* pozadí **nikdy nesnižuje čitelnost** – nad ním leží `--scrim` a panel;
* přepínač `full / reduced / off` v nastavení, `off` = statický obrázek nebo
  plná barva;
* `prefers-reduced-motion: reduce` → chová se jako `reduced`, i když je v UI `full`;
* na Androidu maximálně jedna běžící animační vrstva; při `visibilitychange`
  na skryté kartě se animace zastaví (šetří baterii Pi i telefonu);
* obrázky jako WebP, každý ≤ 250 kB, přednačítá se jen aktuální stav.

---

## 8. Responzivita

| Šířka | Chování |
|---|---|
| ≥ 1200 px | stripe 8 sloupců, trvalé boční menu |
| 768–1199 px | stripe 5–6 sloupců, kompaktní menu |
| < 768 px | stripe vodorovně scrollovatelný se `scroll-snap`, spodní navigace + ikona menu; přepínání stránek gestem **i** menu (kap. 13 – gesto nesmí být jediná cesta) |

Dotykové cíle ≥ 44 × 44 px. Rozvržení flexbox/grid, žádné pevné pixelové šířky
panelů. Graf se nesmí zmenšovat pod čitelnost – na mobilu radši méně sérií
a vodorovný posun.

---

## 9. Přístupnost

* kontrast textu ≥ 4,5:1 vůči ploše, na které leží (nad fotkou vždy přes scrim);
* identita série nikdy jen barvou – legenda + přímý popisek nebo vzor;
* plná ovladatelnost klávesnicí, viditelný focus;
* `aria-live` pro hodnoty, které se samy mění (aktuální výkon), ale s rozumnou
  frekvencí – ne každých 10 s;
* stavy (varování, safe mode) mají ikonu + text, ne jen barvu.
