# Bug report: LAST CHICKEN – opravená verze, zaměřeno na UI a design

Datum: 3. 10. 2026 · verze v1.0.5 (commit `50acc60`, sloučeno do `claude/gallant-pascal-d2usic`)

Nové nálezy pokračují v číslování od **B-29**, aby se nepletly s minulým reportem (B-01 až B-28).

**Jak jsem testoval:**
- **Opravy z minula:** smoke testy 16/16 OK, znovu spuštěné sondy z minulého auditu (třes, záblesky, haptika, level-upy, boss rush, Špión, výhra → smrt, denní výzva).
- **UI a design:** headless screenshoty všech obrazovek a overlayů v logickém rozlišení 540 × 960, včetně stavů (zamčené zvíře, dialogy, bedna, výsledky po stránkách, pauza s potvrzením, chybová obrazovka).
- **Animace:** měření po snímcích (viditelnost rámečků, příletová animace karet, klouzání tučňáka v 6 směrech).
- **Měření:** kontrast podle WCAG, šířky textů skutečným fontem, kontrola pořadí kreslení pixelovým testem.

**Co jsem NEmohl ověřit:** skutečný telefon (fyzická velikost písma, chování „hoveru“ na dotyku, ostrost škálování), zvuk.

## Souhrn

20 nových nálezů: 0 kritických, 2 vysoké, 4 střední, 14 drobných.

Opravy z minulého reportu fungují (viz poslední sekce). Jediná regrese je nové klouzání tučňáka.

V UI se opakují tři příčiny:
- **Zvýraznění pod obsahem:** rámečky výběru se kreslí *pod* panel se stínem, takže spodní hrana bliká nebo chybí. Přesně to je problém, kterého sis všiml u karet.
- **Malé písmo:** velká část důležitých textů je v nejmenším měřítku, na telefonu necelý milimetr.
- **Pevné souřadnice:** řada drobností vzniká tím, že prvky jsou umístěné pevně, ne podle obsahu (schovaný popisek, překryvy, useknuté paprsky).

## Nálezy

### [B-29] Zvýraznění karty v level-upu: spodní hrana rámečku mizí a objevuje se
- **Závažnost:** vysoká
- **Kategorie:** UI/UX, grafika
- **Kde:**
  - `game/ui/overlays.py:223–231` – rámeček se kreslí *před* `draw_panel`
  - `game/ui/widgets.py:16` – `draw_panel` kreslí stín `r.move(0, 5)` přes vše 5 px pod kartou
  - `game/ui/widgets.py:88–90` – stejný vzor u pulzujících tlačítek
- **Co se děje:** Při výběru karty se kolem ní objeví bílý rámeček. Horní, levá a pravá hrana svítí stále, spodní se pravidelně ztrácí a zase objevuje. Když je vidět, má jen 1 px místo 3 px.
- **Jak se to projeví / kdy:**
  - každý level-up, karta pod prstem nebo myší;
  - u vzácných/epických karet chybí spodní hrana vnějšího pulzujícího rámečku **vždy**;
  - u pulzujících tlačítek (Skip „Opravdu?“, aktivní Vyřadit) také chybí spodní hrana vždy.
- **Důkaz:** Pixelový test 120 snímků (2 s):
  - zvýrazněná běžná karta: horní/levá/pravá hrana 120/120, **spodní 31/120** – bliká jednou za ~1,6 s (perioda `sin(t*4)`);
  - vzácná karta: spodní hrana 0/120;
  - tlačítko „Opravdu?“: spodní hrana 0/60.

  Příčina: rámeček je `r.inflate(g, g)` s `g` = 8–12 px (každá strana 4–6 px), stín karty zakrývá pás 0–5 px pod kartou. Spodní hrana vykoukne jen při největším „nádechu“. Lichá `g` (9, 11) navíc posouvají rámeček nesouměrně o 1 px.
- **Jistota:** ověřeno během běhu (pixelový test + zvětšený výřez)
- **Proč to vadí:** Hlavní rozhodovací obrazovka hry vypadá rozbitě a blikání táhne pozornost.
- **Směr opravy:** Rámeček kreslit až po panelu (nebo panel bez stínu, když je zvýrazněný) a nafukovat jen o sudé hodnoty.

### [B-30] Velká část důležitých textů je na telefonu necelý milimetr vysoká
- **Závažnost:** vysoká
- **Kategorie:** UI/UX
- **Kde:**
  - 37× `font.draw(..., 1, ...)` napříč `game/ui/` a `game/scenes/`;
  - podtituly všech tlačítek (`game/ui/widgets.py:109`);
  - zalamované popisy v `select.py:185–186`, `daily.py`, `collection.py`.
- **Co se děje:** Měřítko 1 má výšku verzálek 7 logických px. Při typickém displeji (1080 × 2400, ~400 ppi, integer škála 2×) to je 14 fyzických px ≈ **0,9 mm**. Doporučené minimum pro mobilní text je zhruba 1,3–1,5 mm. Tímto písmem je mimo jiné:
  - instrukce nového potvrzení Skipu „klepni znovu“;
  - rarita karty a nápověda „Evoluce s: …“;
  - pasivka a slabina zvířete na výběru;
  - popisy a odměny výzev, efekty v Hnízdě;
  - podtituly „3 minuty / 10 minut / zamčeno / zbývá 2 / +8 mincí“;
  - úrovně v HUD slotech, „Fáze 1/3“ u bosse, „KOKRHEJ!“, statistiky v pauze;
  - indikátor stránek ve výsledcích.
- **Jak se to projeví / kdy:** Celé UI, nejvíc výběr zvířete, level-up, výzvy, Hnízdo, pauza a HUD.
- **Důkaz:** Metrika fontu (měřítko 1/2/3 = 7/14/21 px výšky verzálek, řádek 12/24 px), výpočet pro 1080p a 720p displeje (~0,9 mm v obou případech), screenshoty.
- **Jistota:** ověřeno výpočtem a screenshoty; skutečný telefon neověřen
- **Proč to vadí:** Hráč na mobilu nepřečte, co dělá pasivka postavy ani karta, a nové potvrzení Skipu nemá čitelnou instrukci. Hra je přitom „pro mobil na výšku“.
- **Směr opravy:** Měřítko 1 nechat jen pro dekoraci, informace dát do měřítka 2 a ubrat text nebo přidat místo.

### [B-31] Nové klouzání tučňáka: dolů vzhůru nohama, nahoru stojí, šikmo rozbitý pixel art (regrese opravy B-11)
- **Závažnost:** střední
- **Kategorie:** grafika/animace
- **Kde:** `game/world/render.py:428–441` – rotace bočního spritu o úhel jízdy, kvantovaný na 16 směrů
- **Co se děje:**
  - Doprava a doleva vypadá klouzání správně (leží břichem dolů, hlavou ve směru).
  - **Dolů** je tučňák otočený o 180°, tedy vzhůru nohama.
  - **Nahoru** je otočený o 0°, takže vypadá jako normálně stojící tučňák, který se vznáší.
  - **Šikmo** se pixel art otáčí o 22,5°/45° a ztrácí pixelovou mřížku (zubaté, deformované obrysy).
- **Jak se to projeví / kdy:** Tajný tučňák při plném klouzání v jakémkoli jiném než vodorovném směru.
- **Důkaz:** Render 6 směrů po 200 ticích klouzání (slide = 1,0): nahoru = vzpřímený sprite, dolů = rotace −180°, úhlopříčky = rotace 45° s rozbitým obrysem.
- **Jistota:** ověřeno během běhu (render)
- **Proč to vadí:** Hlavní mechanika postavy působí jako chyba; ostatní grafika je čistý pixel art.
- **Směr opravy:** Pro svislý a šikmý pohyb použít ležící sprite (vodorovný, otočený podle vlevo/vpravo) nebo dokreslit 2–4 ručně kreslené směry místo volné rotace.

### [B-32] Slepice se schovává pod nepřátele, když stojí u překážky
- **Závažnost:** střední
- **Kategorie:** grafika (čitelnost)
- **Kde:** `game/world/render.py:377–396` – hráč se vkládá do y-řazení před první překážku „pod sebou“
- **Co se děje:**
  - Pokud je kousek pod slepicí (i bokem) balík, plot nebo auto, všichni nepřátelé s y větším než ta překážka se kreslí *přes* slepici.
  - Bez překážky je slepice vždy nahoře.
  - Výsledek: slepice v davu nahodile mizí pod liškami podle toho, co stojí poblíž.
- **Jak se to projeví / kdy:** Hlavně Farma (balíky, ploty), Město (auta), Továrna (stroje); v hustém davu.
- **Důkaz:** Pixelový test (obří liška posunutá o 14 px pod slepici):
  - bez překážky: střed slepice má barvu slepice (143, 136, 188);
  - s balíkem 60 px vpravo (y + 6): barva lišky (133, 51, 38).

  Viditelné i na herním screenshotu ze 70. sekundy.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Hráč ztrácí přehled o vlastní postavě v nejnebezpečnějších chvílích.
- **Směr opravy:** Hráče kreslit nad všemi nepřáteli a pod překážkami řešit zvlášť (průhlednost/obrys), ne přes společné y-řazení.

### [B-33] Na dotyku zůstává zvýrazněná karta i v další nabídce
- **Závažnost:** střední
- **Kategorie:** UI/UX
- **Kde:**
  - `game/ui/overlays.py:118–120` – při nové nabídce se resetuje `t` a `skip_arm`, ale ne `hover` ani `pressed_card`
  - `game/ui/overlays.py:181–185` – `hover` se mění jen při pohybu
- **Co se děje:** Po výběru karty prstem přijde další level-up ve stejném overlayi a karta na stejné pozici je už orámovaná, jako by byla předvybraná nebo doporučená. Na mobilu se hover nikdy „nepustí“.
- **Jak se to projeví / kdy:** Víc level-upů za sebou (boss rush s 8 kartami, rychlé levely na začátku).
- **Důkaz:** Klepnutí na 2. kartu při 3 čekajících level-upech → `overlay is ov` = True, nová nabídka, `hover` = 1.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Zavádějící „doporučení“; navíc na té kartě dál bliká rámeček z B-29.
- **Směr opravy:** Při změně nabídky resetovat `hover`/`pressed_card` a na dotyku zobrazovat zvýraznění jen během držení prstu.

### [B-34] Nízký kontrast u vybrané obtížnosti a zlatých cenových tlačítek
- **Závažnost:** střední
- **Kategorie:** UI/UX
- **Kde:**
  - `game/scenes/select.py:76` – barva obtížnosti jako pozadí tlačítka
  - `game/ui/widgets.py:STYLES` – `gold`, `primary`
  - `game/data/meta.py` – barvy obtížností
- **Co se děje:** Bílý text na světlé výplni je špatně čitelný. Kontrast podle WCAG (doporučeno ≥ 3:1 pro velký text):
  - vybraná „Normal“: **1,57:1**
  - vybraná „Hard“: 1,73:1
  - zlaté cenové tlačítko (Hnízdo, Obchod, Koupit): 2,01:1
  - primární oranžové: 2,15:1
  - zelené „ZAP“: 2,65:1

  Pro srovnání: modrý Rerol 4,06:1, červený Vyřadit 5,02:1.
- **Jak se to projeví / kdy:** Výběr postavy (obtížnost), Hnízdo, Obchod; venku na slunci ještě hůř.
- **Důkaz:** Výpočet WCAG z barev v kódu + screenshot výběru (bílé „Normal“ na světle zelené).
- **Jistota:** ověřeno výpočtem
- **Proč to vadí:** Hůř se čtou právě ceny a nastavení, kde se hráč rozhoduje.
- **Směr opravy:** Na světlých výplních tmavý text s obrysem, nebo tmavší odstíny výplní.

### [B-35] Popisek „Obtížnost“ na výběru je celý schovaný pod tlačítky módu
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/select.py:221` – nadpis na y = 704; tlačítka módu `:38` zabírají y 640–710 + stín
- **Co se děje:** Sekce Mapa má nadpis, sekce obtížnosti ne: její nadpis se kreslí pod tlačítka „Rychlý/Plný“. Sekce módu nadpis nemá vůbec.
- **Jak se to projeví / kdy:** Vždy na obrazovce výběru zvířete.
- **Důkaz:** V oblasti nadpisu je 0 pixelů jeho barvy (nadpis „Mapa“ jich má 244).
- **Jistota:** ověřeno (pixelový test)
- **Proč to vadí:** Nejednotná struktura obrazovky.
- **Směr opravy:** Posunout nadpisy podle skutečné výšky řádků (a doplnit nadpis „Mód“).

### [B-36] Nejednotný vizuální jazyk „vybráno“ vs. „hlavní akce“
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:**
  - `game/scenes/select.py:69–77` – mapa = zlatý rámeček, mód = oranžová výplň, obtížnost = barva obtížnosti
  - `game/scenes/collection.py` – záložka = oranžová výplň
- **Co se děje:**
  - Vybraný mód a vybraná záložka mají stejnou oranžovou jako hlavní akce (HRÁT, START, Pokračovat), takže vypadají jako tlačítka k akci, ne jako zvolená možnost.
  - Výběr mapy přitom používá zlatý rámeček.
- **Jak se to projeví / kdy:** Výběr zvířete, Sbírka.
- **Důkaz:** Screenshoty výběru a Sbírky.
- **Jistota:** ověřeno
- **Proč to vadí:** Hráč musí odhadovat, co je stav a co akce.
- **Směr opravy:** Jeden styl pro „vybráno“ (např. rámeček nebo fajfka) a oranžovou vyhradit akcím.

### [B-37] Karty při příletu přestřelí 54 px za levý okraj obrazovky
- **Závažnost:** drobná
- **Kategorie:** grafika/animace
- **Kde:** `game/ui/overlays.py:222` – `r.x += int((1 - appear) * W)` s `ease_out_back` (špička 1,10)
- **Co se děje:** Karta vletí zprava a přestřelí o 10 % šířky obrazovky (54 px). Levý okraj karty i s ikonou na chvíli zmizí za hranou displeje, pak se vrátí.
- **Jak se to projeví / kdy:** Každý level-up a každý rerol (animace se spouští znovu).
- **Důkaz:** Snímky v čase 0,12–0,32 s, ořezaná ikona/karta vlevo.
- **Jistota:** ověřeno (render po snímcích)
- **Otázka:** Je takto velký odskok záměr?
- **Směr opravy:** Překmit počítat z menší vzdálenosti, nebo použít `ease_out_cubic`.

### [B-38] Bedna: řádky jsou zbytečně vysoké a obsah v nich nesedí
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/ui/overlays.py:338–360`
- **Co se děje:** Při 1–3 položkách má řádek 150 px. Ikona je svisle uprostřed, ale název a popis jsou přilepené nahoru, takže spodní polovina panelu je prázdná a text neleží v ose s ikonou.
- **Jak se to projeví / kdy:** Většina beden (1–3 položky).
- **Důkaz:** Screenshot bedny se 3 položkami.
- **Jistota:** ověřeno
- **Proč to vadí:** Obrazovka odměny působí nevyváženě.
- **Směr opravy:** Strop výšky řádku ~100 px a blok textu centrovat svisle k ikoně.

### [B-39] Paprsky v bedně končí rovnou vodorovnou čarou
- **Závažnost:** drobná
- **Kategorie:** grafika
- **Kde:** `game/ui/overlays.py:321` – plocha paprsků má výšku jen 560 px (y 20–580)
- **Co se děje:** Rotující světelné paprsky se uprostřed obrazovky (y = 580) ostře useknou.
- **Jak se to projeví / kdy:** Každá otevřená bedna.
- **Důkaz:** Zvětšený výřez – paprsek končí ostrou hranou na y = 580.
- **Jistota:** ověřeno
- **Proč to vadí:** Viditelný řez v efektu odměny.
- **Směr opravy:** Plocha přes celou výšku, nebo paprsky směrem dolů vytratit.

### [B-40] Obchod: nadpis „Truhla štěstí“ naráží do tlačítka
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/shop.py:159` (nadpis v měřítku 3 od x = 120) a `:36` (tlačítko od x = 314)
- **Co se děje:** Nadpis končí na x = 312, tlačítko začíná na 314; poslední písmeno se dotýká hrany tlačítka.
- **Jak se to projeví / kdy:** Vždy v Obchodě.
- **Důkaz:** Měření šířky fontem + screenshot.
- **Jistota:** ověřeno
- **Proč to vadí:** Natěsnaný, nedotažený vzhled.
- **Směr opravy:** Menší měřítko nebo užší tlačítko.

### [B-41] Hnízdo: názvy vylepšení střídají velikost písma
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/nest.py:84` – měřítko podle délky názvu
- **Co se děje:** „Silné kosti“, „Ostrý zobák“, „Zrní-radar“, „Kostka osudu“ jsou v měřítku 3, ale „Běžecký trénink“ a „Moudrost předků“ v měřítku 2. Seznam tak působí nesourodě.
- **Jak se to projeví / kdy:** Vždy v Hnízdě.
- **Důkaz:** Měření + screenshot.
- **Jistota:** ověřeno
- **Proč to vadí:** Rozbitá vizuální hierarchie seznamu.
- **Směr opravy:** Jedno měřítko pro všechny řádky (podle nejdelšího názvu), nebo kratší názvy.

### [B-42] Výběr zvířete: tlačítko „Koupit“ zakrývá tečky postav
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:**
  - `game/scenes/select.py:35` – tlačítko y 386–450 + stín 5 px
  - `game/scenes/select.py:200` – tečky na y = 452 ± 7
- **Co se děje:** U zvířat na koupení je indikátor pozice (7 teček) z poloviny pod tlačítkem.
- **Jak se to projeví / kdy:** Kachna, Husa, Krocan na výběru.
- **Důkaz:** Screenshot zamčené kachny.
- **Jistota:** ověřeno
- **Proč to vadí:** Hráč nevidí, kde v seznamu postav je.
- **Směr opravy:** Tečky posunout pod tlačítko nebo tlačítko výš.

### [B-43] Zalamování odděluje číslo od jednotky
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/gfx/font.py:287–301` – zalamuje na každé mezeře; texty v `game/data/` píšou „40 %“, „1 500“ s běžnou mezerou
- **Co se děje:** Na výběru kachny končí řádek „… +5“ a další začíná „% rychlost.“. Totéž hrozí u tisíců („1 | 500 vajec“) v delších zprávách.
- **Jak se to projeví / kdy:** Popisy s procenty a čísly s mezerou tisíců.
- **Důkaz:** Screenshot zamčené kachny.
- **Jistota:** ověřeno
- **Proč to vadí:** Hůř se čte, vypadá to neuhlazeně.
- **Směr opravy:** Nezlomitelná mezera mezi číslem a jednotkou/tisíci, kterou `wrap` nerozdělí.

### [B-44] Nejednotné šipky, nadpisy, umístění měn a okraje mezi obrazovkami
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/select.py:32–33, :166–167`, `shop.py:28, :132`, `nest.py:79`, `menu.py`
- **Co se děje:**
  - **Šipky:** předchozí/další používá šipku „←“ vlevo, ale „▶“ (ikona Přehrát) vpravo.
  - **Nadpisy:** výběr zvířete má nadpis v měřítku 3, ostatní obrazovky 5.
  - **Řádek měn:** jednou vlevo nahoře, jindy zarovnaný vpravo, jindy s pevným posunem `W//2 − 140/150`, takže se při delších číslech posouvá ze středu.
  - **Okraje:** 10 / 14 / 16 / 24 / 30 px podle obrazovky.
- **Jak se to projeví / kdy:** Přechody mezi obrazovkami menu.
- **Důkaz:** Screenshoty všech obrazovek.
- **Jistota:** ověřeno
- **Proč to vadí:** Hra jako celek nepůsobí sjednoceně.
- **Směr opravy:** Sjednotit (vlastní ikona „vpřed“, jedna velikost nadpisu, centrovaný řádek měn, jeden okraj).

### [B-45] Dialogy: pevná výška a nebezpečné klávesové zkratky
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/base.py:38` (vždy 440 px), `:71–74` (zkratky)
- **Co se děje:**
  - Jednořádkové dialogy („Začít znovu?“, „Odemknout?“, „Truhla!“) mají přes polovinu prázdné plochy.
  - Enter/mezerník mačká **první** tlačítko, což je v „Začít znovu?“, „Vzdát se?“, „Odejít?“ a „Smazat postup?“ ta destruktivní akce.
  - Esc / Android Zpět mačká **poslední**, což v „Konec?“ znamená „Vzdát to“.
- **Jak se to projeví / kdy:** Všechny dialogy; klávesnice na PC, tlačítko Zpět na Androidu.
- **Důkaz:** Screenshoty dialogů + kód zkratek.
- **Jistota:** ověřeno (vzhled), zkratky podle kódu
- **Proč to vadí:** Prázdné dialogy působí nedodělaně; zkratky můžou omylem spustit nevratnou akci.
- **Směr opravy:** Výšku dialogu odvodit z obsahu; Enter a Esc vázat na bezpečnou volbu.

### [B-46] Pauza: přes ztlumené HUD prosvítá časovač přímo za nadpisem
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/ui/overlays.py:428` (nadpis „PAUZA“ y 50–116) a `:444–445` (pasivky v měřítku 1)
- **Co se děje:**
  - Za žlutým „PAUZA“ prosvítá ztlumený časovač a 6. slot zbraní.
  - Pravý sloupec (pasivky) má názvy v měřítku 1, levý (zbraně) v měřítku 2, takže dva sousední seznamy mají různou hierarchii.
- **Jak se to projeví / kdy:** Vždy v pauze.
- **Důkaz:** Screenshot pauzy.
- **Jistota:** ověřeno
- **Proč to vadí:** Neklidný nadpis a nesourodé sloupce.
- **Směr opravy:** HUD v pauze skrýt nebo dát nadpis pod něj; sloupcům stejné písmo.

### [B-47] Toasty překrývají obsah a tlačítka
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/base.py:227` – toasty vždy na y = H − 150
- **Co se děje:** Hláška po nákupu v Hnízdě leží přes poslední řádek vylepšení; na výběru zvířete přes tlačítko START.
- **Jak se to projeví / kdy:** Nákup v Hnízdě; hlášky na výběru zvířete.
- **Důkaz:** Screenshot Hnízda po nákupu.
- **Jistota:** ověřeno
- **Proč to vadí:** Zakrývá obsah, na který hráč právě kouká.
- **Směr opravy:** Pozici toastu volit podle obrazovky (nad spodní akční zónu nebo pod nadpis).

### [B-48] Menu ukazuje verzi „v1.0.0“, vydání je v1.0.5
- **Závažnost:** drobná
- **Kategorie:** spec mismatch
- **Kde:** `game/config.py:8` – `VERSION`
- **Co se děje:** Hráč (i ty při hlášení chyb) vidí jinou verzi, než jaká je nainstalovaná. Text má navíc kontrast 1,64:1 na zeleném pozadí.
- **Jak se to projeví / kdy:** Vždy v hlavním menu.
- **Důkaz:** Kód + tagy v gitu.
- **Jistota:** ověřeno
- **Proč to vadí:** Nejde poznat, která verze běží.
- **Směr opravy:** Verzi zvyšovat při vydání (nebo ji brát z buildu).

## Stav oprav z minulého reportu (B-01 až B-28)

Ověřeno znovu spuštěnými sondami:

- **B-01 třes:** opraveno. Posun nad 10 px jen v 0,1–0,4 % snímků (dřív 22–31 %), maximum 18–26 px jen u bossů.
- **B-02 záblesky:** opraveno. 1–12 za 2 minuty (dřív ~130 za minutu), v Nastavení je přepínač.
- **B-03 Skip omylem:** opraveno (0,6 s zámek + potvrzení). Instrukce „klepni znovu“ je ale nečitelně malá, viz B-30.
- **B-04 výplňové level-upy:** opraveno. 43 overlayů za plný run místo 60, žádný jen s výplní.
- **B-05 vibrace:** opraveno. Jednotky haptických volání za 2 minuty.
- **B-06 boss rush:** opraveno, první karta je „Úroveň 2“.
- **B-07 výsledky:** opraveno (stránkování). **B-08 bedna:** opraveno, tlačítko už nic nepřekrývá.
- **B-09 Špión:** opraveno, auto-aim na neviditelného bosse 0×.
- **B-12 výhra → smrt:** opraveno (sekvence `victory_anim → victory`). **B-14 denní výzva:** opraveno („VÝBĚR“ vrací na výběr).
- **B-11 tučňák:** průhlednost opravena, ale nové otáčení přineslo regresi B-31.
- **Ostatní (B-10, B-13, B-15–B-28):** opravy ověřeny čtením kódu.

## Co jsem nestihl / neověřil

- **Skutečný telefon:** fyzická velikost písma (B-30 je výpočet), chování „hoveru“ při dotyku v SDL na Androidu, ostrost neceločíselného škálování (např. 1,33× na 720p).
- **Zvuk** UI (kliknutí, potvrzení).
- **Animace při jiném FPS** než 60.
- **Dlouhé texty v nestandardních stavech**, např. 6 zbraní + 6 pasivek + 2 bossové a 3 bannery najednou v HUD; prošel jsem jen typické kombinace.

## Témata, která se opakují

1. **Zvýraznění kreslené pod obsahem** (B-29, pulzující tlačítka). Rámeček výběru se kreslí před panelem, jehož stín ho přepíše. Jedna úprava pořadí kreslení opraví karty i tlačítka.
2. **Písmo a hustota informací pro mobil** (B-30, B-43, B-46). Nejdůležitější vysvětlující texty jsou nejmenší.
3. **Pevné souřadnice místo layoutu** (B-35, B-38, B-39, B-40, B-42, B-45, B-47). Prvky umístěné „na pixel“ se překrývají nebo schovávají, jakmile se změní obsah.
4. **Nejednotný vizuální jazyk** (B-34, B-36, B-41, B-44). Barvy a styly pro stav a akci se míchají, nadpisy a okraje se liší podle obrazovky.
5. **Stav nebo transformace, které nesedí na pixel art a dotyk** (B-31, B-33). Volná rotace pixel artu a „hover“ na dotykovém displeji.
