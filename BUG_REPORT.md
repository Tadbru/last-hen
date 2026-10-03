# Bug report: LAST CHICKEN

Datum: 3. 10. 2026 · verze 1.0.0 (commit `86d03e5`)

**Jak jsem testoval:**
- **Statická analýza:** heuristický skener (26 stop, většina záměrná: tiché `except`, alokace v UI) a ruční čtení celého kódu (~13,7 tis. řádků) proti README a PLAN.
- **Headless běh:** smoke testy 16/16 OK. Bot odehrál 7 zvířat × plný mód (Farma), 7 zvířat × 5 biomů v rychlém módu, 6× boss rush a 12× Hard/Nightmare. K tomu 3 dlouhé god-mode runy s měřením po každém ticku (posun kamery, záblesky, vibrace, level-upy, počty entit, čas snímku).
- **Vynucené okrajové stavy:** přes `App(headless=True)` a skutečné scény; screenshoty overlayů.

**Co jsem NEmohl ověřit:**
- skutečný telefon (haptika, dotyk, škálování, výkon na pygame 2.1),
- zvuk poslechem,
- lidské hraní (bot je jen náhrada).

## Souhrn

28 nálezů: 0 kritických, 5 vysokých, 11 středních, 12 drobných.

Hra je technicky stabilní:
- žádný pád v ~70 bot runech ani ve vynucených stavech,
- všech 7 zvířat (bot) dohraje plný mód,
- výkon na PC je hluboko pod 16 ms.

Největší problémy:
- **Pozdní hra plného módu:** efekty evolucí se sčítají bez stropu (trvalý třes, stroboskopické záblesky, nepřetržité vibrace). Obsah se vyčerpá ~2 minuty před koncem, takže finálního bosse přerušují prázdné level-upy.
- **Mobilní ovládání:** chybí ochrana proti omylu (klepnutí = Skip, Restart bez potvrzení).
- **Nehlídané stavy:** sada logických děr kolem stavů, které ostatní systémy neznají (neviditelný boss, vítězná animace, denní výzva přes půlnoc).

## Nálezy

### [B-01] Pozdní hra: obraz se trvale třese
- **Závažnost:** vysoká
- **Kategorie:** game feel/efekty
- **Kde:**
  - `game/world/run.py:563` – `explosion()` přidá třes 0,12, resp. 0,55 za každý výbuch
  - `game/weapons/kinds.py:52` a `:408` – Zlatá bomba a Svatební dort volají `big=True`
  - `game/core/camera.py:33–39` – trauma má strop 1,0, `kick` strop nemá
- **Co se děje:** Od evoluce Zlaté bomby / Svatebního dortu se kamera prakticky nepřestane třást. Obraz poskakuje o desítky pixelů a okolí slepice (a telegrafy) se hůř čte.
- **Jak se to projeví / kdy:** Plný mód, druhá polovina runu, jakékoli zvíře s výbušnými evolucemi. Nejhorší je to během finálního bosse.
- **Důkaz:** Bot (Božena, Farma, plný mód), posun kamery měřený každý tick:
  - do 5:00 je posun nad 10 px v ≤ 1,4 % snímků;
  - od 8:00 do konce ve **22–31 % snímků**, maximum **24–36 px**, trauma drží ~0,95.

  Jeden hod Zlaté bomby = 3 velké výbuchy (3 × 0,55) + 15 klastrových (15 × 0,12).
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Vlastní zbraně „trestají“ hráče. V nejtěžší části hry se ztrácí čitelnost a hrozí nevolnost.
- **Směr opravy:** Třes od hráčových zbraní tlumit nebo stropovat (rozpočet za snímek) a silné otřesy nechat bossům.

### [B-02] Stroboskopické bílé záblesky přes celou obrazovku
- **Závažnost:** vysoká
- **Kategorie:** game feel/efekty (přístupnost)
- **Kde:**
  - `game/weapons/kinds.py:53` – `run.flash(..., 0.12)` při každém dopadu Zlaté bomby
  - `game/world/render.py:129–134` – vykreslení záblesku
- **Co se děje:** Po evoluci Zlatá bomba bliká celá obrazovka bíle ~2× za sekundu.
- **Jak se to projeví / kdy:** Od získání Zlaté bomby do konce runu. Nastavení „Otřesy obrazovky“ to nevypne a vypínač záblesků neexistuje.
- **Důkaz:** Počet volání `run.flash`:
  - do 6:00: 0–4 za minutu,
  - od 7:00: **114–140 za minutu**.

  Bílá vrstva (alfa až 128/255) je viditelná v **15–22 % snímků**.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Blikání nad 2 Hz je riziko pro fotosenzitivní hráče. Unavuje oči a zakrývá telegrafy.
- **Směr opravy:** Záblesk jen pro vzácné události (evoluce, boss) nebo s cooldownem. Přidat přepínač v Nastavení.

### [B-03] Jedno klepnutí hned po otevření level-upu = Skip
- **Závažnost:** vysoká
- **Kategorie:** UI/UX (ovládání)
- **Kde:**
  - `game/ui/overlays.py:31–38` – tlačítka overlaye nemají ochrannou prodlevu
  - `game/ui/overlays.py:139` – prodleva 0,25 s je jen pro karty
  - `game/ui/overlays.py:91` – Skip leží uprostřed dole
- **Co se děje:** Level-up vyskočí uprostřed pohybu. Hráč reflexivně zvedne a znovu položí palec do spodní části (tam se řídí) a okamžitě klikne na „Skip“, případně Rerol/Vyřadit. Přijde tak o kartu.
- **Jak se to projeví / kdy:** Kdykoli na mobilu i myší, nejvíc v rané hře s častými level-upy.
- **Důkaz:** Headless scéna: level-up otevřen, o 1 snímek později klepnutí na (270, H−66). Výsledek: stav `playing`, mince +15, `pending_levelups` = 0.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Hráč přijde o upgrade, aniž by chtěl. Frustrace.
- **Směr opravy:** Stejnou prodlevu (ideálně „až nový dotek“) použít i pro tlačítka overlaye.

### [B-04] Závěr plného módu: level-upy nabízejí jen výplňové karty a přerušují finálního bosse
- **Závažnost:** vysoká
- **Kategorie:** balanc (obsah vs. délka módu)
- **Kde:**
  - `game/progression.py:103–132` – `FILLERS`, `make_offer`
  - `game/world/run.py:895–899` – otevření level-upu
- **Co se děje:** Build je kompletní (6 zbraní/evolucí + 6 pasivek na max.), ale XP dál přitéká. Každých 5–9 s se hra zastaví overlayem se stále stejnými třemi kartami (polévka / mince / kokrhání), i uprostřed finálního bosse.
- **Jak se to projeví / kdy:** Plný mód od ~8:20 do konce včetně finále, všechna zvířata.
- **Důkaz:** Bot v god módu:
  - Božena: 60 level-upů, z toho 17 čistě výplňových od 8:20, průměrný odstup 8,8 s (minimum 0,3 s);
  - Rambo: 65 level-upů, z toho 24 výplňových od 9:11, průměrný odstup 5,1 s.

  Úroveň v 10:00 je 49–59, na konci runu 54–73. Navíc „Pytel mincí“ (+20) je od úrovně 30 horší než Skip (5 + úroveň/2, tj. 35 mincí na úrovni 60).
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Zbytečné pauzy ve vrcholu hry, kde není co volit.
- **Směr opravy:** Po vyčerpání nabídky level-up nepauzovat (dát automatický bonus), nebo zpomalit XP křivku plného módu.

### [B-05] Telefon vibruje 3–4× za sekundu (rozpor se specifikací)
- **Závažnost:** vysoká
- **Kategorie:** game feel/efekty, spec mismatch
- **Kde:**
  - `game/world/run.py:565` – `explosion(big)` volá `vibrate(10)`
  - `game/world/run.py:906` (level-up), `:885`, `:247`
  - `game/ui/overlays.py:136` a `:271` – výběr karty, otevření bedny
  - `game/core/camera.py:41–47` – `vibrate()`
  - `game/scenes/game.py:45` – `haptics = True`
- **Co se děje:** README slibuje vibraci „při úderech bossů“. `Camera.vibrate` (včetně haptiky) ale volá každý velký výbuch vlastních zbraní, každý level-up, výběr karty, otevření bedny i kokrhání.
- **Jak se to projeví / kdy:** Android se zapnutými vibracemi (výchozí stav). Extrémně v pozdní hře.
- **Důkaz:** Počet volání `vibrate()`:
  - do 6:00: 3–12 za minutu,
  - od 7:00: **132–219 za minutu** (≈ 3,6 za sekundu).

  Každé volání znamená `device.vibrate(35 ms)`.
- **Jistota:** počet volání ověřen během běhu; samotná haptika na telefonu podle kódu (neověřeno)
- **Proč to vadí:** Je to nepříjemné, vybíjí to baterii a vibrace ztrácí význam varování.
- **Směr opravy:** Haptiku oddělit od trhnutí kamery a volat ji jen pro zásah hráče a údery bosse, s cooldownem.

### [B-06] Boss rush ukazuje „Úroveň -6“; bonusové level-upy nezvyšují úroveň
- **Závažnost:** střední
- **Kategorie:** UI/UX, logika
- **Kde:**
  - `game/world/run.py:122` – `pending_levelups = cfg.bonus_levels`, ale `level` zůstává 1
  - `game/ui/overlays.py:175` – výpočet nadpisu
- **Co se děje:** Na začátku boss rushe ukazuje nadpis level-upu Úroveň −6, −5 … 1. Po 8 kartách je v HUD stále „Úr. 1“. Stejně u rubber-bandingu: banner slibuje „+1 úroveň“, ale úroveň zůstane 1.
- **Jak se to projeví / kdy:** Každý start boss rushe; run po brzké smrti.
- **Důkaz:** 6 boss rush runů, první zobrazená hodnota pokaždé −6.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Hned první obrazovka módu působí rozbitě.
- **Směr opravy:** Bonusové karty zobrazovat zvlášť (např. „Bonus 1/8“), nebo s nimi zvyšovat úroveň.
- **Poznámka:** Rubber-band se dá vyvolat i tlačítkem „Vzdát se“ v 0:01. Záměr?

### [B-07] Výsledky ukazují jen 3 zprávy – další odemčení a výzvy zmizí
- **Závažnost:** střední
- **Kategorie:** UI/UX
- **Kde:** `game/scenes/results.py:150` – `self.msgs[:3]`
- **Co se děje:** Po prvním vítězství vzniklo 9 zpráv:
  - Odemčeno: Kohout Elvis; Temný les; Hard;
  - Výzva Tisíc lišek, **Odemčeno zvíře: Páv Diva!**;
  - výzvy Celá noc, Kokrhací mistr, Masakr, Arzenál.

  Na obrazovce jsou jen první 3. Hráč se nedozví o odemčeném Pávovi ani o odměnách za výzvy.
- **Jak se to projeví / kdy:** Každý run, který splní víc věcí najednou (typicky první výhry).
- **Důkaz:** Screenshot výsledků, `len(msgs) == 9`.
- **Jistota:** ověřeno (vynucený stav výsledků)
- **Proč to vadí:** Odměny a odemčení jsou hlavní motivace; tady zmizí bez povšimnutí.
- **Směr opravy:** Posuvný seznam, postupné toasty nebo souhrnný řádek („+5 výzev“).

### [B-08] Bedna s 5 položkami: „Pokračovat“ zakrývá pátou položku i mince
- **Závažnost:** střední
- **Kategorie:** UI/UX
- **Kde:**
  - `game/ui/overlays.py:243` – tlačítko na y = 800–880
  - `game/ui/overlays.py:301–316` – řádky po 108 px od y = 290
- **Co se děje:** Pátá položka (y 722–818) i řádek „+X mincí“ (y ≈ 840) leží pod tlačítkem.
- **Jak se to projeví / kdy:** Bedna z bosse má 5 položek s pravděpodobností 30 % × štěstí.
- **Důkaz:** Headless screenshot vynucené 5položkové bedny.
- **Jistota:** ověřeno
- **Proč to vadí:** Hráč nevidí, co dostal, právě u nejcennější bedny.
- **Směr opravy:** Menší řádky, dva sloupce, nebo tlačítko posunout pod obsah.

### [B-09] Pan Liška Špión: v neviditelnosti na něj míří auto-aim a střely mizí naprázdno
- **Závažnost:** střední
- **Kategorie:** logika (boss)
- **Kde:**
  - `game/world/run.py:596–599` – `nearest_enemy` nefiltruje alfu ani nezranitelnost
  - `game/world/bosses.py:121–138` – fáze neviditelnosti
  - `game/world/run.py:1048–1060` – střela se spotřebuje i při 0 poškození
- **Co se děje:** Během teleportu (alfa 60 → 0, nezranitelný) míří zbraně na prázdné místo, kde boss stál. Projektily tam narazí do neviditelného hitboxu a zmizí bez poškození. Okolní lišky mezitím nikdo nestřílí.
- **Jak se to projeví / kdy:** Celý souboj se Špiónem (2:00 v plném módu, boss rush), asi 17 % času souboje.
- **Důkaz:** 5 soubojů: 2 108 ticků neviditelnosti, z toho v 1 928 (91 %) vrátil `nearest_enemy` neviditelného bosse. 2 s střelby na neviditelného bosse = 0 poškození.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Hráč vidí, jak jeho střely letí do prázdna, zatímco ho obklopují lišky.
- **Směr opravy:** Neviditelné/nezranitelné bosse vyřadit z cílení a z kolizí projektilů.

### [B-10] Pauza: „Restart“ a „Vzdát se“ bez potvrzení
- **Závažnost:** střední
- **Kategorie:** UI/UX
- **Kde:**
  - `game/ui/overlays.py:325–331`, `:355–361` – tlačítka pauzy
  - `game/scenes/game.py:126–138` – `give_up()`, `restart()`
- **Co se děje:** Dvě sousední tlačítka 165 × 70 px provedou akci okamžitě. Restart zahodí celý run bez odměn i bez záznamu, klidně po 10 minutách hry.
- **Jak se to projeví / kdy:** Kdykoli v pauze; omyl palcem na mobilu.
- **Důkaz:** Kód – tlačítka volají akci přímo.
- **Jistota:** podle kódu (neověřeno)
- **Proč to vadí:** Nevratná ztráta dlouhého runu jedním klepnutím.
- **Směr opravy:** Potvrzovací dialog (komponenta `Dialog` už existuje).

### [B-11] Tučňák: klouzání průhledně bliká a při jízdě nahoru/dolů leží bokem
- **Závažnost:** střední
- **Kategorie:** grafika/animace
- **Kde:** `game/world/render.py:421–432`
- **Co se děje:**
  1. Cache otočeného spritu (`_slide_rot`) nemá v klíči průhlednost. Když se snímek poprvé uloží během blikání po zásahu, zůstane poloprůhledný do konce runu a tučňák pak při klouzání střídá plný a 50% snímek. Obráceně: uložený neprůhledný snímek způsobí, že při klouzání chybí blikání nezranitelnosti.
  2. Rotace je vždy ±80° podle orientace vlevo/vpravo, takže při svislém klouzání tučňák leží vodorovně, jako by jel bokem.
- **Jak se to projeví / kdy:** Tajný tučňák při plném klouzání (slide > 0,55).
- **Důkaz:**
  - po zásahu během klouzání má položka cache `(0, 1, False)` alfu 120;
  - klouzání čistě dolů: vx = 0, vy = 228, sprite otočen o −80°.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Hlavní pohybová mechanika postavy vypadá rozbitě.
- **Směr opravy:** Alfu aplikovat až po rotaci (nebo ji dát do klíče cache) a úhel odvodit ze směru pohybu.

### [B-12] Výhra → smrt → reklama „Oživ se“ → nekonečný run
- **Závažnost:** střední
- **Kategorie:** logika/stav
- **Kde:**
  - `game/world/run.py:945–957` – `_victory_tick` → `_update_fx` dál spouští callbacky telegrafů
  - `game/world/run.py:924–925` – `on_player_death` přepíše stav `victory_anim`
  - `game/scenes/game.py:166–172` – dialog oživení
- **Co se děje:** Po zabití finálního bosse slepice 3 s nehybně stojí, ale nevybuchlé lisy (Továrna), laviny (Hory) a dopady jiných bossů ji dál zraňují.
  - Když zemře, objeví se „Konec? Slepice padla…“ s reklamou na oživení.
  - Po oživení běží run bez arény a bez bosse dál; časovač ukazuje 0:00 a run skončí až další smrtí (výsledek je pak „VÍTĚZSTVÍ“).
- **Jak se to projeví / kdy:** Vzácně: hlavně Továrna a Hory, nebo když v aréně žije jiný boss.
- **Důkaz:** Vynucený stav (Továrna, lis pod hráčem v okamžiku zabití bosse):
  - sekvence stavů `victory_anim → dying → dead`, dialog „Konec?“;
  - po oživení `arena = None`, `final_boss = None`, run pokračuje.
- **Jistota:** ověřeno vynuceným stavem
- **Proč to vadí:** Hráč vyhrál, a hra mu tvrdí, že padl.
- **Směr opravy:** Během vítězné animace hráče nezraňovat nebo vyčistit telegrafy; smrt po výhře ignorovat.

### [B-13] „Všechny útoky jsou telegrafované“ neplatí; vítr finálního bosse nejde přemoct
- **Závažnost:** střední
- **Kategorie:** spec mismatch, balanc (boss)
- **Kde:** `game/world/bosses.py`:
  - `:410` – vlna při kokrhání ve fázi 1 (e.dmg × 0,6, poloměr 210)
  - `:448–451` – vějíř 7 vajec ve fázi 2 každé 3 s
  - `:155–158` – vějíř šipek Špióna po výpadu
  - `:392` – vítr 220 px/s (v rychlém módu 154 px/s)
- **Co se děje:**
  - README tvrdí, že všechny útoky bossů jsou telegrafované; tyto tři útoky varování nemají.
  - Vítr ve fázi 1 je rychlejší než základní rychlost zvířat (150 px/s, husa 132). Bez Rychlých nohou nebo připraveného kokrhání nejde vzdorovat a hráč skončí na elektrickém plotu.
- **Jak se to projeví / kdy:** Každý souboj s finálním bossem; Špión.
- **Důkaz:** V bot simulacích patří mezi hlavní zdroje poškození „plot“ (až 126 HP za run) a „vlna“ (8–70 HP za run).
- **Jistota:** podle kódu + simulace
- **Proč to vadí:** Poškození bez varování působí nefér.
- **Otázka:** Má vítr hráče odfouknout neodvratitelně? (záměr?)
- **Směr opravy:** Krátký telegraf před vlnou a vějíři; vítr pod rychlostí hráče nebo s postupným náběhem.

### [B-14] Denní výzva otevírá zamčená zvířata a mapy pro běžné runy
- **Závažnost:** střední
- **Kategorie:** logika (exploit progrese)
- **Kde:**
  - `game/scenes/results.py:56–60` – tlačítko „NOVÝ RUN“
  - `game/scenes/game.py:132–138` – Restart v pauze
  - `game/progression.py:297–303` – odemčení další mapy po výhře
- **Co se děje:** Po denní výzvě (nebo Restartem během ní) se spustí obyčejný rychlý run se zapůjčeným zvířetem i mapou, a jde to opakovat donekonečna. Výhra na takové mapě odemkne mapu následující.
- **Jak se to projeví / kdy:** Kdykoli denní výzva losuje zamčené zvíře nebo mapu.
- **Důkaz:** Denní výzva Kohout Elvis + Hory (oba zamčené) → „NOVÝ RUN“ → rychlý run rooster/mountain → výhra → odemčena Továrna. Les, Město ani Hory nebyly odemčeny.
- **Jistota:** ověřeno během běhu
- **Proč to vadí:** Obchází progresi (nákupy za vejce i pořadí map).
- **Směr opravy:** „Nový run“ po denní výzvě vracet na výběr postavy a mapy; u Restartu kontrolovat odemčení.

### [B-15] Pasivka tučňáka (zranění klouzáním) neškáluje
- **Závažnost:** střední
- **Kategorie:** balanc
- **Kde:** `game/world/enemies.py:165–167` – `18 * might`
- **Co se děje:** Plné klouzání dává pevných 18 × síla poškození. Pro srovnání HP nepřátel:
  - liška v 5:00 ≈ 44 HP, v 10:00 ≈ 180 HP;
  - vlk v 10:00 ≈ 1 260 HP.

  Od ~3. minuty je pasivka postavy prakticky bez efektu.
- **Jak se to projeví / kdy:** Tajný tučňák, střední a pozdní hra.
- **Důkaz:** Výpočet z `waves.hp_mult`: 5 min × 4,4, 10 min × 18.
- **Jistota:** podle kódu (výpočet)
- **Proč to vadí:** Identita postavy zmizí právě v delších runech.
- **Směr opravy:** Škálovat s časem nebo úrovní, nebo procentem HP (jako kokrhání).

### [B-16] Boss rush: velmi strmý začátek
- **Závažnost:** střední
- **Kategorie:** balanc
- **Kde:**
  - `game/world/director.py:37–38` – `eff_min = 4 + t/60`
  - `game/scenes/game.py:27–28` – 8 bonusových level-upů
- **Co se děje:** Nepřátelé mají od 0. sekundy HP jako ve 4. minutě (× 3,1) a Špión přichází v 0:03. Hráč má jen startovní zbraň + 8 karet.
- **Jak se to projeví / kdy:** Každý boss rush.
- **Důkaz:** Bot, 6 runů: 1 výhra, 3 smrti v 31–53 s ještě u Špióna. Pro srovnání: v plném módu bot vyhraje se 6 ze 7 zvířat.
- **Jistota:** ověřeno (bot, ne člověk)
- **Otázka:** Je strmý začátek záměr?
- **Směr opravy:** Prvního bosse pustit později, začít s nižší efektivní minutou, nebo dát víc karet.

### [B-17] Denní výzva přes půlnoc zablokuje další den
- **Závažnost:** drobná
- **Kategorie:** logika/stav (datum)
- **Kde:** `game/scenes/results.py:28–29`
- **Co se děje:** Konec denní výzvy po půlnoci zapíše `last_played` i skóre na nové datum. Nová denní výzva je pak „Hotovo“ a skóre se objeví v žebříčku jiného dne.
- **Jak se to projeví / kdy:** Denní výzva rozehraná před půlnocí a dohraná po ní.
- **Důkaz:** Start 10. 10., konec 11. 10. → `last_played = 2026-10-11`, tlačítko „Hotovo“ je neaktivní.
- **Jistota:** ověřeno (simulované datum)
- **Proč to vadí:** Hráč přijde o další den výzvy i o žeton.
- **Směr opravy:** Při zápisu použít datum ze `spec` výzvy, ne `today()` v okamžiku konce.

### [B-18] Mini-boss mimo arénu při příchodu finálního bosse tiše zmizí
- **Závažnost:** drobná
- **Kategorie:** logika
- **Kde:** `game/world/run.py:314–317`
- **Co se děje:** Když v 10:00 ještě žije např. Vlčí Alfa dál než ~410 px, zmizí bez výbuchu, bedny, mincí i zápisu do sbírky. Jeho kontrolér přitom zůstane v `run.bosses`.
- **Jak se to projeví / kdy:** Plný mód, pokud hráč nestihl zabít mini-bosse před finále.
- **Důkaz:** Vynucený stav: `alive = False`, kontrolér stále v `run.bosses`, `boss_log = [..., None]`, boss se nezapočítá.
- **Jistota:** ověřeno vynuceným stavem
- **Proč to vadí:** Boss „zmizí“ bez vysvětlení a bez odměny.
- **Směr opravy:** Přesunout bosse do arény, nebo ho výslovně označit jako uprchlého.

### [B-19] Nepřátelé se zhmotňují přímo na obrazovce (aréna, smečka Alfy)
- **Závažnost:** drobná
- **Kategorie:** grafika/game feel
- **Kde:**
  - `game/world/director.py:58–66` – spawn na kraji arény (r − 30 = 400 px)
  - `game/world/bosses.py:281–284` – vlci 330 px od hráče
- **Co se děje:**
  - Viditelná plocha je ±270 × ±480 px, takže spawny na kraji arény a 4 ze 6 vlků Alfy (úhly 60°/120°/240°/300°) se objeví uvnitř obrazovky bez jakéhokoli efektu.
  - Recyklovaní nepřátelé se do arény přesouvají také viditelně.
  - Vlci se navíc spawnují bez kontroly překážek.
- **Jak se to projeví / kdy:** Finální aréna; každé vytí Vlčí Alfy.
- **Důkaz:** Výpočet ze souřadnic spawnu.
- **Jistota:** podle kódu (výpočet)
- **Proč to vadí:** „Pop-in“ působí levně a nedává hráči šanci reagovat.
- **Směr opravy:** Krátký spawn efekt nebo telegraf; kontrola `blocked()`.

### [B-20] Na ledu „moonwalk“
- **Závažnost:** drobná
- **Kategorie:** pohyb/animace
- **Kde:** `game/world/player.py:158–165`
- **Co se děje:** Animace chůze i otočení se řídí rychlostí, ne vstupem:
  - po puštění ovládání na ledu slepice klouže a nohy dál běží;
  - při obratu se dívá původním směrem, dokud se rychlost neotočí (na ledu až ~1 s, tučňák ~0,6 s).
- **Jak se to projeví / kdy:** Led a olej (Hory, Továrna), tučňák.
- **Důkaz:** 1 s na ledu bez vstupu → animace chůze v 30 z 60 snímků.
- **Jistota:** animace ověřena během běhu; otočení podle kódu
- **Proč to vadí:** Pohyb na ledu vypadá nepřirozeně.
- **Směr opravy:** Na ledu bez vstupu použít klidový nebo klouzací snímek.

### [B-21] Déšť ve fázi 2 ukazuje padající zombie slepici i v jiných biomech
- **Závažnost:** drobná
- **Kategorie:** grafika
- **Kde:** `game/world/render.py:227`
- **Co se děje:** Telegraf „drop“ vždy kreslí `zchick`. Dopadne ale netopýr (Les), potkan (Město), sněžná liška (Hory) nebo robo-liška (Továrna).
- **Jak se to projeví / kdy:** Finální boss ve všech biomech kromě Farmy.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Proč to vadí:** Padá jiný tvor, než který dopadne.
- **Směr opravy:** Kreslit sprite podle `variant["rain"]`.

### [B-22] Kuřecí armáda: kuřata se při každém vylepšení teleportují ke slepici
- **Závažnost:** drobná
- **Kategorie:** grafika
- **Kde:** `game/weapons/kinds.py:109–117`
- **Co se děje:** `on_refresh` zabije a znovu vytvoří všechna kuřata na pozici hráče. Při každém z 8 levelů zbraně kuřata přeruší útok a skočí zpět.
- **Jak se to projeví / kdy:** Každé vylepšení Kuřecí armády.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Proč to vadí:** Viditelný skok uprostřed boje.
- **Směr opravy:** Přidávat a odebírat jen rozdíl v počtu kuřat.

### [B-23] Bedna s evolucí: text Peřinové vichřice je useknutý
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:** `game/ui/overlays.py:311` – max. 2 řádky
- **Co se děje:** „EVOLUCE! Tornádo pírek, které neprorazí nic. Protože prorazí všechno.“ se zalomí na 3 řádky a pointa zmizí.
- **Jak se to projeví / kdy:** Evoluce Peří-shurikenu.
- **Důkaz:** Zalomení skutečným fontem = 3 řádky; jediný takový text ve hře.
- **Jistota:** ověřeno
- **Proč to vadí:** Ztracený vtip / neúplný popis.
- **Směr opravy:** Kratší text, nebo povolit 3 řádky.

### [B-24] Vyřazení výplňové karty nic neudělá a nic neřekne
- **Závažnost:** drobná
- **Kategorie:** UI/UX
- **Kde:**
  - `game/progression.py:166–167` – banish odmítne jiné než zbraň/pasivku
  - `game/ui/overlays.py:124–133` – žádná zpětná vazba
- **Co se děje:** V režimu „Vyřadit“ klepnutí na polévku/mince/kokrhání nic neprovede, bez zvuku i hlášky, a režim zůstane zapnutý.
- **Jak se to projeví / kdy:** Level-up s výplňovou kartou.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Proč to vadí:** Hráč neví, proč se nic nestalo.
- **Směr opravy:** Krátký toast „Tuhle kartu nejde vyřadit“.

### [B-25] PC: hra se při ztrátě fokusu nebo minimalizaci nepozastaví
- **Závažnost:** drobná
- **Kategorie:** vstup/platforma
- **Kde:** `game/app.py:226–244`
- **Co se děje:** Pauzu vyvolávají jen Android události (APP_*BACKGROUND). Alt-Tab nebo minimalizace na PC nechá run běžet a slepice umře.
- **Jak se to projeví / kdy:** PC verze, kdykoli hráč odejde z okna.
- **Důkaz:** Kód – chybí obsluha WINDOWFOCUSLOST / WINDOWMINIMIZED.
- **Jistota:** podle kódu
- **Proč to vadí:** Zbytečná ztráta runu.
- **Směr opravy:** Pauzovat i na WINDOWFOCUSLOST / WINDOWMINIMIZED.

### [B-26] Renderer emituje částice a počítá čas podle počtu vykreslení
- **Závažnost:** drobná
- **Kategorie:** výkon, grafika
- **Kde:**
  - `game/world/render.py:434` – `particles.emit` v `_player`
  - `game/world/render.py:105` – `self.t += 1/60` za každé vykreslení
  - `game/scenes/game.py:203` – volání rendereru
- **Co se děje:**
  - Při klouzání tučňáka se částice emitují i během pauzy/level-upu. Simulace stojí, takže pool (700) se zaplní za ~12 s a po návratu chvíli nejdou spawnovat jiné efekty.
  - Pulzy telegrafů, blikání plotu a nezranitelnosti se řídí počtem vykreslení; na 30 FPS běží polovičním tempem.
- **Jak se to projeví / kdy:** Pauza s klouzajícím tučňákem; slabší telefony.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Proč to vadí:** Chybějící efekty po pauze; nekonzistentní tempo animací.
- **Směr opravy:** Emitovat částice v simulaci; čas rendereru brát ze skutečného dt.

### [B-27] Denní odměna za přihlášení se kontroluje jen jednou za spuštění aplikace
- **Závažnost:** drobná
- **Kategorie:** logika/stav (datum)
- **Kde:** `game/scenes/menu.py:21`, `:47–48`
- **Co se děje:**
  - `_login_checked` je třídní příznak, takže aplikace ponechaná na pozadí přes půlnoc odměnu nevydá, dokud se nerestartuje.
  - Naopak posun systémového data dává opakované odměny i nové pokusy denní výzvy.
- **Jak se to projeví / kdy:** Mobil s aplikací na pozadí; ruční změna data.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Proč to vadí:** Hráč nedostane odměnu, na kterou má nárok.
- **Otázka:** Je zneužití přes změnu data u offline hry přijatelné? (záměr?)
- **Směr opravy:** Kontrolovat datum při každém vstupu do menu.

### [B-28] Sezónní skin zůstává nasazený i po sezóně
- **Závažnost:** drobná
- **Kategorie:** logika
- **Kde:** `game/scenes/game.py:30`, `game/scenes/shop.py:42–43`
- **Co se děje:**
  - Obchod hlásí „Jen v sezóně“, ale jednou nasazená dýně nebo Santa zůstane navždy.
  - Sezónu lze v Nastavení kdykoli vynutit a skiny si tak „odemknout“.
- **Jak se to projeví / kdy:** Po skončení sezóny; přepnutí sezóny v Nastavení.
- **Důkaz:** Kód.
- **Jistota:** podle kódu
- **Otázka:** Je to záměr?
- **Směr opravy:** Pokud ne, ověřit dostupnost skinu při startu runu.

## Co jsem nestihl / neověřil

- **Skutečný Android:**
  - pygame 2.1 bez `fblits`/SIMD a skutečná haptika;
  - neceločíselné škálování (např. 1,33× na 720p displejích);
  - výkon na telefonu. Na PC je průměr ≤ 2,5 ms render + 0,8 ms logika na snímek, ojedinělé špičky 20–29 ms (6. minuta); na telefonu mohou být znatelné.
- **Zvuk poslechem:** mix, hlasitosti, smyčky hudby. Ověřen jen kód (rate-limit existuje).
- **Lidské hraní:** bot je jen náhrada. Husa (boj zblízka) je s botem nejslabší, což je známé z PLAN.md.
- **Hard/Nightmare:** jen 12 bot runů s nejednoznačným výsledkem (část smrtí kolem 2:30–3:15 u Špióna). Závěr nevyvozuji.
- **Denní modifikátory:** kombinace modifikátorů × zvířata jen čtením kódu.
- **Dlouhé sezení přes mnoho runů:** cache fontu a kruhů mají stropy; neměřil jsem.

## Témata, která se opakují

1. **Efekty vlastních zbraní se sčítají bez rozpočtu** (B-01, B-02, B-05). Velké výbuchy evolucí spouští stejné efekty jako boss (třes 0,55, vibrace, záblesk) a v pozdní hře přicházejí několikrát za sekundu. Jedna společná brzda pro „juice“ od hráčových zbraní vyřeší všechny tři.
2. **Obsah neodpovídá délce módu** (B-04, B-15, B-16):
   - XP křivka plného módu přeroste obsah ~2 minuty před koncem;
   - pevná čísla (18 dmg klouzání) neškálují s křivkou HP nepřátel (× 18 v 10. minutě);
   - boss rush startuje na úrovni 4. minuty.
3. **Stav, který ostatní systémy neznají** (B-09, B-11, B-12, B-18, B-26):
   - neviditelný boss pro cílení a kolize;
   - průhlednost pro cache rotace;
   - vítězná animace pro telegrafy;
   - aréna pro žijící bosse;
   - pauza pro renderer.
4. **Chybí ochrana proti nechtěné akci v rozhraní ovládaném palcem** (B-03, B-10, B-24): okamžité akce bez prodlevy, bez potvrzení a bez zpětné vazby.
5. **Datum a „jeden pokus“** (B-14, B-17, B-27): denní obsah se řídí `today()` v okamžiku konce a příznaky na úrovni procesu, ne specifikací výzvy.
6. **Pevné rozložení pro „typický“ počet položek** (B-07, B-08, B-23): obrazovky počítají s 3 zprávami, 4 položkami, 2 řádky textu.
