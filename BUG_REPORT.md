# Bug report: LAST CHICKEN (4. kolo)
Datum: 3. 10. 2026 · verze 1.0.6 (commit 8b40820, po opravách B-01 až B-48)
Číslování navazuje na předchozí reporty (B-49 a dál), aby se nepletlo s už opravenými B-01 až B-48.

**Jak jsem testoval**
- Statická analýza: heuristický scanner (26 tipů, většinou šum) + ruční čtení `run.py`, `player.py`, `bosses.py`, `enemies.py`, `director.py`, `progression.py`, `weapons/*`, `allies.py`, `mapgen.py`, `camera.py`, `sound.py`, `app.py`, `input.py`, `hud.py`, `overlays.py`, `game.py`, `results.py`, `daily.py`, `save.py` a dat v `game/data/`.
- Dynamické sondy (headless, pygame-ce 2.5.8, skripty mimo projekt): přes 170 botích runů. Rychlý mód: 7 zvířat × 5 map, 8 seedů × 4 zvířata, Hard/Nightmare. Plný mód: 4 zvířata + další seedy. Boss rush: 7 zvířat. Denní výzva s modifikátorem Ohňostroj. Měřil jsem třes kamery, záblesky, pauzy na level-up, rychlost odhozu nepřátel, obsazení zvukových kanálů, strop pickupů, stav arény při příletu bosse, dokončení buildu a dosažitelnost evolucí. Headless snímky obrazovky: Farma, Hory, Továrna.
- **Neověřeno:** skutečné hraní člověkem, Android (klasický pygame 2.1, výkon, haptika), poslech zvuku, plný mód na Hard/Nightmare.
- Za zmínku stojí: opravy B-01/B-02 drží. Snímky s posunem kamery nad 6 px tvoří 0,24–1,15 %, záblesky jsou ~5 za minutu, odhoz nepřátel má max. ~850 px/s, zvukové kanály se nevyčerpají a žádný run nespadl.

## Souhrn
18 nálezů: 0 kritických, 2 vysoké, 5 středních, 11 drobných.
Hra je stabilní a „juice“ systémy jsou po minulých opravách v pořádku. Zbývající problémy jsou hlavně systémové. Zrní a bedny se v delším runu ztrácejí: strop pickupů, plot arény a vítězná animace. Balanc postav a módů je nevyrovnaný: placená a odemykací zvířata jsou slabší než startovní slepice, rychlý mód je přerušovaný a jeho finální boss je moc krátký. Drobnosti se týkají modifikátorů, jejichž popis neodpovídá kódu, a textů napsaných natvrdo pro slepici a farmu.

## Nálezy

### [B-49] Po zaplnění stropu pickupů padá XP z poloviny zabití do vzdáleného zrní mimo obrazovku
- Závažnost: vysoká
- Kategorie: logika / game feel
- Kde: `game/world/run.py:716` `drop_xp`, strop `MAX_PICKUPS = 380` v `config.py`
- Co se děje: od určité chvíle lišky po smrti často nic neupustí. Jejich XP se tiše připíše k náhodnému zrnu kdekoli na mapě, většinou daleko za okrajem obrazovky.
- Jak se to projeví / kdy: plný mód zhruba od 5. minuty (strop byl dosažen ve 4:58), v rychlém módu ke konci (300–389 pickupů ve 2:30). Staré zrní nikdy nezmizí, takže strop se dřív nebo později zaplní.
- Důkaz: hen/full/seed 3, 0–10 min: 6 346 dropů, z toho 3 074 sloučeno, z nich **2 589 do zrna dál než 600 px od hráče**. To je 44 % veškeré XP z celého runu.
  ```python
  if len(self.pickups) >= MAX_PICKUPS:
      for _ in range(4):
          pk = self.pickups[self.rng.randrange(len(self.pickups))]
          if pk.kind == P_XP: pk.value += value; return
  ```
- Jistota: ověřeno během běhu
- Proč to vadí: zabití přestane dávat viditelnou odměnu, hráč přichází o XP a mimo obrazovku vznikají obří zrna, ke kterým se nikdy nevrátí.
- Směr opravy: slučovat do nejbližšího zrna u místa zabití, případně nechat vzdálené staré zrní mizet nebo ho „nasát“ do jednoho velkého.

### [B-50] Bedny a zrní za plotem finální arény propadnou, bedna sebraná ve vítězné animaci se neotevře
- Závažnost: vysoká
- Kategorie: logika / obsah
- Kde: `run.py:317` `spawn_boss` (aréna kolem hráče), `clamp_to_arena`, `_victory_tick` (`magnet_all`), `pending_chests` se po vítězství už neotevírají
- Co se děje: když přiletí Zombie Kohout, vznikne aréna o poloměru 430 px. Bedna z elity, která leží kousek za plotem, je pak nedosažitelná, protože plot hráče nepustí. Ve vítězné animaci ji magnet sice přitáhne, ale bedna se už neotevře a odměna (evoluce nebo upgrade) se ztratí bez jakékoli zprávy.
- Jak se to projeví / kdy: oba módy v okamžiku příletu finálního bosse. V rychlém módu přichází poslední elita ve 2:08 a boss ve 2:30, takže bedna často ještě leží na zemi.
- Důkaz: 24 runů (3 zvířata × 2 módy × 4 seedy): **v 16 z nich byla v okamžiku vzniku arény aspoň jedna bedna víc než 20 px za plotem**. V 9 runech ležela jen 27–310 px za plotem, tedy na dohled. V rychlém módu zůstalo za plotem typicky 1,5–3,5 úrovně XP (`xp_beyond` 300–600 při `xp_next` ~150). Ve 2 runech skončil run se sebranou, ale neotevřenou bednou (`pending_chests_at_end = 1`).
- Jistota: ověřeno během běhu
- Proč to vadí: hráč vidí bednu za plotem a nemůže pro ni dojít. Evoluce mu propadne zrovna před nejtěžším soubojem.
- Směr opravy: při vzniku arény stáhnout bedny (a případně XP) dovnitř, nebo je rovnou vyřešit. Po vítězství nevyřízené bedny aspoň převést na mince.

### [B-51] Rychlý mód přerušuje hru level-upem nebo bednou zhruba každých 6 sekund
- Závažnost: střední
- Kategorie: game feel / balanc
- Kde: `run.py:90` `xp_mult = 1.8` pro quick/daily, `xp_needed()`
- Co se děje: v rychlém módu hra ustavičně zastavuje na výběr karet. Mezi pauzami je jen pár sekund hraní.
- Jak se to projeví / kdy: celý rychlý mód, nejvíc v 1. a 2. minutě. Plný mód má zhruba poloviční frekvenci.
- Důkaz: hen/quick: pauzy za minutu {0: 8, 1: 11, 2: 10}, celkem **29 pauz za 3 minuty**. Daily: 31. Plný mód 4–9 za minutu.
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: 3minutový mód má být svižný, ale působí trhaně. Na telefonu je to navíc pokaždé 0,6 s zámek, joystick se uvolní a pak se musí znovu chytit.
- Směr opravy: snížit násobič XP v rychlém módu a místo toho dát silnější karty (vyšší rarita), nebo spojit víc čekajících level-upů do jedné obrazovky.

### [B-52] Placená a odemykací zvířata jsou slabší než startovní slepice
- Závažnost: střední
- Kategorie: balanc
- Kde: `game/data/characters.py` (Kachna hp 0.7, Páv xp_req 1.25), startovní zbraně v `data/weapons.py`
- Co se děje: zvíře koupené za vejce nebo získané výzvou vyhrává výrazně méně často než zdarma dostupná Božena.
- Jak se to projeví / kdy: rychlý mód, Farma, Normal, bez Hnízda.
- Důkaz: 8 seedů na zvíře, výhry: **slepice 6/8, krocan 3/8, kachna 1/8 (500 vajec), páv 1/8 (odměna za výzvu)**. Páv navíc prohrál na všech 5 mapách (0/5) a Kachna na 3 z 5.
- Jistota: ověřeno během běhu (bot, kituje, takže výsledky jsou orientační)
- Proč to vadí: odemčení nové postavy má být odměna. Tady je to krok dolů a hráč se k Boženě vrátí.
- Směr opravy: přeměřit slabiny (70 % HP u Kachny, +25 % XP u Páva) proti síle startovních zbraní (`tools/dps_bench.py`).

### [B-53] Boss rush silně závisí na zvířeti, první boss trvá u některých přes minutu
- Závažnost: střední
- Kategorie: balanc / bossové
- Kde: `director.py` (boss rush: spawn ×0,35, `ELITES_FULL` platí i v rushi), `scenes/game.py:27` (bonus 8 level-upů)
- Co se děje: po 8 bonusových level-upech skoro nechodí XP. Postavy se slabou startovní zbraní se pak s prvním bossem (Pan Liška Špión, 1 500 HP) tahají přes minutu a na druhém zemřou.
- Jak se to projeví / kdy: týdenní boss rush (Farma, Normal, zvíře podle `last_char`).
- Důkaz: výhry 2/7 (husa, krocan). Délka souboje se Špiónem: páv **98,5 s**, tučňák **78,8 s**, kachna 71 s, krocan 34 s, husa 19 s. Páv i tučňák padli na Králíkovi.
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: týdenní výzva je s polovinou zvířat skoro nehratelná a hráč to dopředu neví.
- Záměr? V boss rushi se objevují i elity z plného módu (obří liška ve 0:50 a dál). To je asi jediný zdroj beden a evolucí, ale v popisu módu to není.
- Směr opravy: škálovat HP bossů podle síly buildu, případně přidat XP z bossů nebo víc bonusových level-upů.

### [B-54] Finální boss rychlého módu padne za 15–40 s, fáze skoro nejsou vidět
- Závažnost: střední
- Kategorie: bossové / balanc
- Kde: `run.py:325` `if final and quick: hp *= 0.1`
- Co se děje: hlavní souboj rychlého módu je s průměrným buildem hotový dřív, než boss předvede útoky. Fáze 1 vystřelí jedno kokrhání, fáze 2 a 3 trvají pár sekund.
- Jak se to projeví / kdy: rychlý mód a denní výzva, Farma a Hory.
- Důkaz: délky souboje (slepice) 14,7 / 25,1 / 28,8 / 38,1 s, krocan 25,2 s, kachna (Továrna) 24,7 s. V plném módu trvá 60–290 s. Samotné přechody fází s nesmrtelností zaberou 2 × 1,6 s a intro 1,2 s.
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: vrchol 3minutového módu působí jako mini-boss a obsah fází 2 a 3 hráč v rychlém módu skoro nevidí.
- Směr opravy: zvednout HP rychlé verze (např. 0,15–0,2), nebo zkrátit fáze, aby se každá stihla ukázat.

### [B-55] V plném módu je build hotový minuty před koncem, zbytek level-upů jen léčí
- Závažnost: střední
- Kategorie: balanc / obsah vs. délka módu
- Kde: `progression.has_choices`, `run._open_levelup` (automatické léčení)
- Co se děje: všechny zbraně jsou vyvinuté a pasivky na maximu. Další level-upy se vyřeší samy (+35 % zdraví) a progrese končí.
- Jak se to projeví / kdy: plný mód, Farma, Normal.
- Důkaz: build kompletní: krocan **7:08**, slepice 9:11, husa 9:27. Potom 24 / 16 / 22 automatických level-upů. Konečná úroveň 59–74.
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: poslední 3–4 minuty (včetně finálního bosse) nepřinášejí žádné rozhodování. Rostoucí XP bar ztrácí smysl.
- Směr opravy: strmější XP křivka po ~úr. 40, nebo nějaký trvalý odbyt pro level-upy (např. malé procentní bonusy).

### [B-56] Boss rush spotřebuje bonus za brzkou smrt a ukáže falešný banner
- Závažnost: drobná
- Kategorie: logika
- Kde: `scenes/game.py:67` (`if app.save["rubber_band"] and cfg.bonus_levels`), `build_config` (bossrush má bonus 8)
- Co se děje: když hráč zemře před 1:30 a pak spustí boss rush, objeví se „Bonus na rozjezd: +1 úroveň!“. Úroveň navíc ale nedostane (rush má pevných 8) a nárok na bonus se smaže.
- Jak se to projeví / kdy: brzká smrt v rychlém nebo plném módu, potom boss rush.
- Důkaz: podmínka hlídá jen `cfg.bonus_levels`, ne mód. V `build_config` je pro bossrush `bonus = 8` nezávisle na `rubber_band`.
- Jistota: podle kódu (neověřeno)
- Proč to vadí: nepravdivá zpráva a ztracený bonus.
- Směr opravy: mazat příznak a ukazovat banner jen v módech quick/full.

### [B-57] Výhra v boss rushi odemyká další mapu i obtížnost Hard
- Závažnost: drobná
- Kategorie: spec mismatch (záměr?)
- Kde: `progression.apply_results` (`if run.victory:` vyjímá jen `daily`)
- Co se děje: vítězný boss rush (vždy Farma, Normal) odemkne Temný les a Hard, přestože se v něm nehraje mapa ani přežití.
- Jak se to projeví / kdy: první výhra v boss rushi.
- Důkaz: PLAN uvádí „Hard se odemkne výhrou na Normal“ a „mapy výhrou na předchozí mapě“. Podmínka vynechává jen denní výzvu.
- Jistota: podle kódu (neověřeno)
- Proč to vadí: obchází zamýšlenou cestu odemykání. Je to ale možná záměr.
- Směr opravy: rozhodnout, zda boss rush počítat jako „výhru na mapě“. Pokud ne, vyjmout ho stejně jako daily.

### [B-58] Modifikátor „Obři“ zvětší jen kolizi, ne vzhled
- Závažnost: drobná
- Kategorie: spec mismatch / grafika
- Kde: `run.py:288` (`e.r *= 1.25`). Sprite se neškáluje (`render._entities`).
- Co se děje: denní výzva „Nepřátelé jsou větší…“ ale lišky vypadají stejně. Jen narážejí a zraňují o ~3–5 px dál od okraje spritu.
- Jak se to projeví / kdy: denní výzva s modifikátorem Obři (1 ze 6 dní).
- Důkaz: v renderu není žádné škálování podle `giants`. `grep giants` najde jen HP, XP a poloměr.
- Jistota: podle kódu (neověřeno)
- Proč to vadí: slib z popisu se nesplní a zásah „ze vzduchu“ působí nefér.
- Směr opravy: předrenderovat zvětšené sprity (nearest), nebo upravit popis.

### [B-59] „Šťastný den“ slibuje vyšší raritu všech karet, 42 % karet je ale běžných
- Závažnost: drobná
- Kategorie: spec mismatch / UI text
- Kde: `progression.roll_rarity` (luck ×2), popis v `data/meta.py:95`
- Co se děje: s modifikátorem padá epická karta na 18 %, vzácná na 40 % a běžná pořád na **42 %**.
- Důkaz: `r < 0.045*4 → epická`, `r < 0.18 + 0.20*2 → vzácná`, jinak běžná.
- Jistota: podle kódu (výpočet)
- Proč to vadí: hráč uvidí běžné karty a bude si myslet, že modifikátor nefunguje.
- Směr opravy: buď opravdu zvednout každou kartu o stupeň, nebo text změnit na „vzácné karty padají častěji“.

### [B-60] Kachna je o 40 % rychlejší i v závějích a na oleji, ne jen ve vodě a na ledu
- Závažnost: drobná
- Kategorie: pohyb / spec mismatch
- Kde: `player.py:118` (`zone_mult < 1.0 or self.on_ice` → 1,4)
- Co se děje: pasivka „Ve vodě a na ledu o 40 % rychlejší“ se spustí v jakékoli zpomalující zóně: v závěji (Hory) i na oleji (Továrna).
- Jistota: podle kódu (neověřeno)
- Proč to vadí: nesoulad popisu s chováním. V Horách je Kachna nečekaně silná.
- Směr opravy: kontrolovat druh zóny (puddle/ice), nebo upravit popis.

### [B-61] Bossové procházejí překážkami
- Závažnost: drobná
- Kategorie: pohyb / grafika
- Kde: `bosses.py` `BossCtrl.move` (bez `push_out`). Běžní nepřátelé se z překážek vytlačují v `enemies.py`.
- Co se děje: medvěd, alfa nebo kohout projdou stodolou či stromem. Špión se teleportuje „za hráče“ i do překážky (`p.x - p.dir_x * 95`).
- Jistota: podle kódu (neověřeno vizuálně)
- Proč to vadí: proti bossům překážky nekryjí, proti liškám ano. Bossové pak „plavou“ přes kulisy.
- Záměr? U velkých bossů to může být úmysl (nezaseknou se), u Špiónovy teleportace do domu spíš ne.
- Směr opravy: pro cíl teleportace a pro malé bosse použít `map.blocked` / `push_out`.

### [B-62] Zpomalení na bossovi odtikává jen při pohybu
- Závažnost: drobná
- Kategorie: logika
- Kde: `bosses.py` `BossCtrl.move` (jediné místo, kde klesá `slow_t`/`freeze_t`)
- Co se děje: ve stavech, kdy boss stojí (Králík míří, Medvěd dupe, Kohout se nadechuje, Špión je neviditelný), časovač zpomalení stojí. Zpomalení pak vydrží déle, než zbraň slibuje.
- Jistota: podle kódu (neověřeno)
- Proč to vadí: nekonzistentní a nečitelná síla zpomalovacích zbraní na bossy.
- Směr opravy: odečítat časovače v `BossCtrl.update`, ne v `move`.

### [B-63] Vyvolávání nepřátel obchází mobilní strop entit
- Závažnost: drobná
- Kategorie: výkon (mobil)
- Kde: `run.py:430` sova (`< 400`), `bosses.py` déšť ve fázi 2 (`< 380`), Vlčí Alfa (6–9 vlků po 6,5–8,5 s bez stropu). `MAX_ENEMIES` je na telefonu 320.
- Co se děje: na telefonu může boj s Alfou nebo s Kohoutem ve fázi 2 přesáhnout limit, na který je výkon laděný.
- Jistota: podle kódu (výkon na zařízení neověřen)
- Proč to vadí: riziko propadu FPS na slabších telefonech právě ve vrcholných soubojích.
- Směr opravy: všude používat `MAX_ENEMIES` z configu.

### [B-64] Texty napsané natvrdo pro slepici a farmu
- Závažnost: drobná
- Kategorie: UI text
- Kde a co:
  - `scenes/game.py:186`: dialog oživení „Slepice padla…“ i pro Kohouta, Tučňáka a Krocana. Výsledky přitom už rozlišují PADLA/PADL.
  - `scenes/results.py:137`: „Slunce vyšlo. **Farma** je zachráněna!“ i ve Městě, Horách, Továrně a v boss rushi.
  - `data/bosses.py:48`: Kohout Mlhoš, Kmotr, Yetti i Robokohout ve fázi 2 hlásí „Prší slepice!“, přitom padají netopýři, krysy, sněžné nebo robo lišky.
  - `scenes/game.py:243`: nápověda „Slepice střílí sama!“ (první run může být denní výzva za jiné zvíře).
- Jistota: podle kódu
- Proč to vadí: drobné, ale viditelné nedotažení po přidání dalších zvířat a map.
- Směr opravy: dosazovat jméno zvířete a biomu, u variant bosse mít vlastní hlášku pro fázi 2.

### [B-65] „Vyřadit“ přelosuje celou nabídku, takže funguje jako rerol zdarma
- Závažnost: drobná
- Kategorie: balanc (záměr?)
- Kde: `progression.banish` (`run.offer = make_offer(run)`)
- Co se děje: vyřazení jedné karty vymění všechny tři. Se 2 vyřazeními má hráč fakticky 2 rerolly navíc.
- Jistota: podle kódu
- Proč to vadí: rerol (Kostka osudu v Hnízdě) ztrácí hodnotu.
- Směr opravy: nahradit jen vyřazenou kartu.

### [B-66] Vítězný čas a skóre obsahují 3 s vítězné animace
- Závažnost: drobná
- Kategorie: UI / logika
- Kde: `run.py:848` (`victory_anim` přičítá `self.time += dt`), `progression.score`, `records.best_time_*`
- Co se děje: ve výsledcích je čas o 3 s delší, než kdy boss padl, a skóre roste o 15 bodů za „nic“.
- Jistota: podle kódu
- Proč to vadí: drobná nepřesnost v rekordech a v žebříčku denní výzvy.
- Směr opravy: během `victory_anim` čas runu nezvyšovat.

## Co jsem nestihl / neověřil
- Skutečné hraní člověkem: bot kituje, takže balanc (B-52 až B-55) je orientační, hlavně u Husy.
- Android: klasický pygame 2.1, výkon v soubojích s mnoha vyvolanými nepřáteli (B-63), haptika, chování po návratu z pozadí.
- Poslech zvuku a hudby: změřil jsem jen, že se nevyčerpají kanály (17 077 přehrání, 0 zahozených).
- Plný mód na Hard/Nightmare a na Horách nebo v Továrně. Rychlý mód jsem otestoval na všech mapách.
- Scény menu (Hnízdo, Obchod, Sbírka, Výzvy, Nastavení) jen na snímcích. Detailně je řešilo minulé kolo B-29 až B-48.
- Vizuální ověření B-58, B-61 a B-62 ve hře (jsou jen z kódu).

## Témata, která se opakují
- **Věci zůstávají ležet a ztrácejí se.** Pickupy nemizí, a proto naráží na strop (B-49). Aréna je odřízne (B-50). Bedny po vítězství propadnou (B-50). Chybí „úklid“ starých pickupů a pravidlo, co se stane s nevyzvednutou odměnou.
- **Obsah laděný pro plný mód.** Rychlý mód má XP ×1,8, takže pauzy padají každých 6 s (B-51), a bosse ×0,1, takže padne za 15 s (B-54). Boss rush dává 8 level-upů a pak skoro nic (B-53). V plném módu je build hotový minuty před koncem (B-55). Každý mód potřebuje vlastní kontrolu, kolik progrese se do jeho délky vejde.
- **Testováno hlavně se slepicí na Farmě.** Slabší placené postavy (B-52), texty pro slepici a farmu (B-64), pasivka Kachny v cizích zónách (B-60).
- **Popis modifikátoru se liší od kódu.** Obři (B-58), Šťastný den (B-59) a obecně popisy zóny a pasivky (B-60).
- **Výjimky pro bosse mimo společnou smyčku.** Bossové mají vlastní `move`. Chybí tam kolize s překážkami (B-61) a odečet zpomalení mimo pohyb (B-62). Co se přidá do smyčky nepřátel, bossové automaticky nedostanou.
