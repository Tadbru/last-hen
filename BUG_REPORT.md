# Bug report: LAST CHICKEN – mód Nekonečná noc
Datum: 3. 10. 2026 · verze 1.1.0 (necommitnutý update nad `18e0f4a`) · číslování navazuje na B-67 až B-80 (report v gitu, commit 92de6d1).

**Jak jsem testoval:**
- Statická analýza: celý diff updatu (director, run, bosses, player, render, HUD, výběr, výsledky, progrese, save, data `ENDLESS_*`) a dokumentace (FEATURES, EVOLUTION_REPORT, UPDATE_PROPOSAL, README, PLAN).
- Headless boti, sondy mimo projekt: 18 runů do smrti (7 zvířat, Farma, Normal, bez Hnízda) se sledováním nocí, doby zabití bossů, jejich souběhu, noční síly, zabití a přijatého poškození po minutách a odměn. Dále 4 runy s průběhem po minutách, 12 runů na porovnání výnosu s Plným módem a 2 runy na kontrolu pickupů.
- Snímky přes skutečnou GameScene: výběr se 3 módy, HUD se 3 bossy, HUD po překonání rekordu, výsledky s rekordem.
- Smoke testy: 16/17. Padá `full_game_flow_through_scenes`, viz poznámky na konci.
- **Neověřeno:** hraní člověkem, Android, zvuk, jiné mapy a obtížnosti než Farma/Normal.

## Souhrn
5 nálezů: 0 kritických, 1 vysoký, 3 střední, 1 drobný.
Mód je stabilní: nepadá, výkon je v pořádku a ekonomika sedí (202 vajec/min, Plný mód 198). Hlavní problém je tvar obtížnosti. Každý run skončí na stejném místě, u Kohouta 2. noci, kterého bot nezabil ani jednou. Bossové 2. noci se navíc hromadí. Zpětná vazba k rekordu chybí přesně tam, kde runy končí: HUD během souboje s Kohoutem ukazuje jen „BOSS!“.

## Nálezy

### [B-81] Kohout 2. noci je zeď – do 3. noci se nedá dojít
- Závažnost: vysoká
- Kategorie: balanc / obsah vs. délka módu
- Kde: `game/data/waves.py` `endless_boss_hp` (×4 za noc) a `ENDLESS_ENRAGE = 120`; `game/world/bosses.py` `ZombieRooster.enrage_t`
- Co se děje: Kohout 2. noci má 480 000 HP a po 2 minutách zuří. Hráč ho nestihne porazit, takže run skončí vždy u něj. Další noci, kterými se mód prezentuje („další noci se silnějšími bossy“), hráč bez velkého Hnízda neuvidí.
- Jak se to projeví / kdy: každý run, který přežije první noc, zhruba v 16.–22. minutě.
- Důkaz: 18 runů → 3. noc 0×. Kohout 2. noci se objevil 13× a nepadl ani jednou. V okamžiku smrti hráče mu zbývalo 39 / 55 / 94 % HP. Za 122–138 s souboje mu bot ubral 45–61 %, zabití by tedy trvalo zhruba 3,5–5 min, ale zuří už od 120 s. Zpráva updatu sama uvádí 3. noc ve 3 z 22 runů (s Hnízdem).
  ```python
  def endless_boss_hp(night: int) -> float:
      return 1.0 if night <= 1 else 4.0 ** (night - 1)
  ```
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: rekord určuje jen to, jak dlouho hráč vydrží uhýbat zuřícímu Kohoutovi. Každý run končí stejně a 3. noc (HP ×16) je obsah, který nikdo neuvidí.
- Záměr? Nekonečný mód musí jednou skončit. Otázka je, jestli má končit pokaždé na stejném bossovi.
- Směr opravy: mírnější násobič HP pro Kohouta další noci nebo pozdější zuření ve 2. noci, ověřené na „dojde někdo do 3. noci“.

### [B-82] Bossové 2. noci přicházejí po 60 s, ale padají za 40–170 s – hromadí se
- Závažnost: střední
- Kategorie: balanc / UI/UX
- Kde: `game/data/waves.py` `ENDLESS_CYCLE` (rozestup 60 s) a `endless_boss_hp(2)`; `game/world/director.py` `next_night`; HUD `game/ui/hud.py` (ukazatele bossů po 42 px) proti bannerům na `H*0.3`
- Co se děje: Medvěd a Alfa 2. noci nestihnou padnout, než přijde další boss. Ve hře jsou 2–3 bossové naráz a Kohout 2. noci často přilétá, když Alfa (144 000 HP) ještě žije. Alfa se přenese do arény k němu.
- Jak se to projeví / kdy: 2. noc, od příletu Medvěda. Vizuálně: při 3 bossech leží 3. ukazatel (y 266–280) a „Fáze 1/3“ přesně pod bannerem příletu („ZOMBIE KOHOUT“ na y≈288), takže text banneru překrývá ukazatel.
- Důkaz: doba zabití bossů 2. noci: Špión 5–17 s, Králík 16–108 s, Medvěd 40–169 s, Alfa 87–159 s. Ve 13 runech, které došly do 2. noci, žili aspoň 2 bossové naráz v 10 z nich a 3 bossové ve 3. Při příletu Kohouta 2. noci žil ještě jiný boss v 5 runech. Kritérium z UPDATE_PROPOSAL „bossové 2. kola 30–150 s“ nesplňuje Špión (pod 30 s) ani Medvěd a Alfa (nad 150 s). Snímek: banner přes ukazatel Kohouta.
- Jistota: ověřeno během běhu (bot + snímek)
- Proč to vadí: 2. noc je chaotická hromada bossů místo série soubojů, HUD se překrývá a Kohout 2. noci je ještě tvrdší (viz B-81).
- Směr opravy: rozestup bossů podle noci, nebo další boss až po porážce předchozího; banner posunout pod pás ukazatelů.

### [B-83] Během souboje s Kohoutem HUD neukazuje čas, noc ani „REKORD!“
- Závažnost: střední
- Kategorie: UI/UX
- Kde: `game/ui/hud.py` – větev `if run.final_boss is not None: "BOSS!"` je před větví `elif run.endless`
- Co se děje: v módu, kde jde o čas a rekord, zmizí čas, číslo noci i rekord na celý souboj s Kohoutem. Když hráč v tu chvíli rekord překoná, HUD to neukáže.
- Jak se to projeví / kdy: každý Kohout (1. noc 1–5 min souboje, 2. noc až do smrti). Runy končí většinou právě tady: v 10 ze 13 smrtí ve 2. noci byl Kohout naživu, hráč tedy posledních 0,4–4,7 min runu neviděl čas.
- Důkaz: snímek v čase 18:20 s rekordem 16:52: nahoře jen „BOSS!“, žádný čas ani „REKORD!“.
  ```python
  if run.final_boss is not None:
      font.draw(surf, "BOSS!", ...)
  ...
  elif run.endless:   # čas, noc, rekord – během Kohouta se sem nedojde
  ```
- Jistota: ověřeno během běhu (snímek)
- Proč to vadí: vrchol runu a okamžik překonání rekordu proběhne bez zpětné vazby a hráč neví, jestli „ještě chvíli vydržet“ k něčemu je.
- Směr opravy: v endless ukazovat čas a rekord i během Kohouta („BOSS!“ přidat menší, nebo vedle).

### [B-84] Lišky po 10. minutě sílí mnohem rychleji než hráč, noční síla je skoro neznatelná
- Závažnost: střední
- Kategorie: balanc
- Kde: `game/data/waves.py` `endless_hp` (+20 % HP za minutu nad kubickou `hp_mult`), `ENDLESS_NIGHT_MIGHT = 0.02`; `game/world/run.py` `_open_levelup`
- Co se děje: zhruba od 15. minuty build přestane stíhat. Zabití za minutu klesnou na polovinu a méně, kolem hráče roste hromada a smrt přijde na kontakt. Hláška „Noční síla +2 %“ běží zhruba 2× za minutu, ale znát není.
- Jak se to projeví / kdy: 15.–20. minuta, všechna zvířata.
- Důkaz: HP lišky 180 (10 min) → 1 003 (15 min) → 3 270 (20 min), tedy ×5,6 a ×18. Noční síla při smrti 10–36 úrovní = +20–72 % poškození. Zabití za minutu: slepice 1 451 (12. min) → 350 (18. min), krocan 1 383 → 74. Přijaté poškození skočí z 0–100 na 280–550 HP/min od 15. min. Kontakt s liškami byl hlavní zdroj poškození v 10 z 18 runů.
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: konec je strmá zeď místo postupného přitvrzování a noční síla slibuje růst, který proti ×18 HP nic neznamená.
- Záměr? Endless má hráče nakonec přerůst. Otázka je strmost a jestli má noční síla být viditelná.
- Směr opravy: zmírnit `ENDLESS_HP_RAMP` nebo posílit noční sílu tak, aby křivka zabití za minutu klesala postupně.

### [B-85] Zpětná vazba rekordu je slabá a nekonzistentní
- Závažnost: drobná
- Kategorie: UI/UX / logika
- Kde a co:
  - `game/ui/hud.py`: `if rec and run.time > rec` – v prvním runu (rekord 0) se „REKORD!“ v HUD neukáže nikdy (zpráva updatu to zmiňuje).
  - `game/share.py`: obrázek ke sdílení po rekordním runu říká „PADLA JSEM…“ s vtipem po prohře („Lišky slaví. Zatím.“), přičemž výsledky hlásí „REKORD!“.
  - Záměr? Jeden společný rekord (`records.best_time_endless`) pro všechna zvířata, mapy i obtížnosti, takže run na Nightmare nebo v Továrně proti rekordu z Farmy/Normal prakticky nemá šanci.
  - Záměr? Oživení přes (falešnou) reklamu se do rekordu počítá (uvedeno ve zprávě updatu).
- Jistota: podle kódu; výsledky „REKORD!“ ověřeny snímkem
- Proč to vadí: rekord je hlavní cíl módu a právě jeho oslava a sdílení jsou slabší než u výhry v Plném módu.
- Směr opravy: v HUD slavit i první run, ve sdílení použít titulek a texty pro rekord, případně rekord po obtížnosti.

## Co jsem nestihl / neověřil
- Hraní člověkem (bot kituje) a Android. Zvuk jsem neposlouchal: fanfára při nové noci, návrat hudby biomu.
- Endless na Lese, Městě, Horách a Továrně a na Hard/Nightmare. Varianty Kohouta 2. noci jsou z kódu a ze snímku zprávy updatu.
- 3. noc a dál (HP ×16): bot se tam nedostal, chování tam je neověřené.
- Dlouhý renderovaný běh jsem neopakoval (zpráva updatu: 25 min, render p95 2,48 ms). Pickupy v endless měřené: drží se kolem stropu 380–435, mince na zemi při smrti 19–74 ze 1 565–2 305 sebraných.
- Smoke test `full_game_flow_through_scenes` padl 1× z 1 spuštění („chybí dialog oživení“), v minulém kole 1× z 27. Hráč to nevidí. Pravděpodobně je hráč v okamžiku `take_damage(1e9)` ještě nesmrtelný (zásah, kokrhání). Výsledky ovlivňuje i známý nedeterminismus `game/world/allies.py:132` (`id(self)`).
- Plánovací dokument UPDATE_PROPOSAL uvádí noční sílu +3 % a banner „NOC POKRAČUJE“, hra i FEATURES mají +2 % a „NOC N“. Jde jen o dokumentaci.

## Témata, která se opakují
- **Násobky bez ohledu na sílu hráče:** HP bossů ×4 za noc a lišky +20 %/min nad kubickou křivkou. Obtížnost neroste po křivce, ale naráží na zeď na stejném místě (B-81, B-84).
- **Plán podle hodin, ne podle průběhu:** bossové 2. noci přicházejí po 60 s, ať předchozí padl, nebo ne (B-82). Formace během Kohouta propadají ze stejného důvodu.
- **Nový mód dědí UI větve starých módů:** HUD „BOSS!“ a sdílení „PADLA JSEM“ byly psané pro mód s koncem. V módu na rekord pak chybí zpětná vazba přesně v klíčových chvílích (B-83, B-85).

---

# 6. kolo – ultimátky zvířat (B-86 – B-90)
Datum: 4. 10. 2026 · verze 1.2.0 (necommitnuto nad `18e0f4a`) · rozsah: jen změněné části (přídavek ultimátek).

**Jak jsem testoval:**
- Statická analýza všech nových souborů (`data/ultimates.py`, `world/ultimates.py`, `world/ult_render.py`,
  `scenarios.py`, `tools/ult_lab.py`) a všech změněných míst (run, enemies, entities, player, render, particles,
  icons, sprites, synth/sound, HUD, pauza, výběr, herní scéna, CLI, bot, smoke test) + heuristický `scan.py`.
- Sondy mimo projekt: opakovaná Zlatá nadílka s renderem (25 aktivací, různý Megafon), časy snímků při 1. a 2.
  Době ledové, zpomalení bosse po bouři, krocan + Gatling + 4 projektilové zbraně (strop projektilů), ladicí scénář
  přes skutečné `App` s dočasným save, dopady vajec mimo obrazovku (8 runů botem), snímky HUD, pauzy a tlačítek.
- Smoke testy 18/18 (vč. nového `ultimates`: pauza, smrt a oživení uprostřed efektu, strop bosse).
- **Stav:** všech 5 nálezů jsem po reportu opravil (viz „Opraveno“ na konci).
- **Neověřeno:** Android (klasický pygame 2.1), hraní člověkem, zvuk poslechem.

## Souhrn
5 nálezů: 0 kritických, 0 vysokých, 3 střední, 2 drobné.
Ultimátky jsou stabilní: stavy pauza, level-up, smrt, oživení, výhra i restart fungují, strop poškození bosse drží
(max. 4,0 %) a strop projektilů se nezaplní (salva krocana max. 63 z 360). Problémy jsou okolo: ladicí scénář
píše do skutečné uložené hry a dva vykreslovací cache jsou zbytečně těžké (záseky při první Době ledové, ~23 MB
elips u Zlaté nadílky).

## Nálezy

### [B-86] Ladicí scénář zapisuje výsledky do skutečné uložené hry
- Závažnost: střední
- Kategorie: logika / save
- Kde: `game/app.py` (větev `Flags.scenario`), `game/scenarios.py:start`
- Co se děje: `python main.py --scenario ult_duck_boss` hraje nad skutečným `save.json`. Vzdání, smrt nebo výhra
  zapíše run, vejce, záznamy a sbírku. Výhra nad Kohoutem ve scénáři odemkne Elvise a mapy.
- Jak se to projeví / kdy: každé ladění přes scénář (a smoke.py se scénářem) mění postup vývojáře / testera.
- Důkaz: sonda s dočasným save: po vzdání `runs 0 → 1`, `eggs 30`, sbírka `['water_pistol']`, ačkoli kachna
  nebyla odemčená.
- Jistota: ověřeno během běhu
- Proč to vadí: ladicí stav (zbraň úr. 4–8, 3. minuta, boss hned) by neměl ovlivnit statistiky, odemykání ani sbírku.
- Směr opravy: ve scénáři neukládat (save s `persist=False`).

### [B-87] První Doba ledová v runu trhá snímky
- Závažnost: střední
- Kategorie: výkon
- Kde: `game/world/ult_render.py:_frost_disc` (klíč `(R // 9, alfa)`)
- Co se děje: namrzlá zem se při náběhu a doběhu bouře staví pixel po pixelu pro každý krok průhlednosti
  (až 8 velkých povrchů). V okamžiku aktivace pak snímky trvají řádově víc.
- Jak se to projeví / kdy: první aktivace tučňáka v runu (a po každé změně dosahu – Megafon, evoluce).
- Důkaz: PC, 1. použití max. 16,6 ms/snímek (několik snímků 14–16 ms), 2. použití max. 2,3 ms. Na telefonu
  (pomalejší CPU, klasický pygame) to vyjde na viditelné zaseknutí přesně v nejdůležitější chvíli.
- Jistota: ověřeno během běhu (PC), Android odhad
- Proč to vadí: ultimátka má být nejsilnější okamžik runu; zásek ho kazí. Navíc až 8 povrchů ~0,7–2 MB na poloměr.
- Směr opravy: jeden povrch na poloměr (průhlednost přes `set_alpha` / postupné odhalení), postavit předem.

### [B-88] Značky dopadu Zlaté nadílky plní cache elips bez stropu (~23 MB)
- Závažnost: střední
- Kategorie: výkon / paměť
- Kde: `game/world/ult_render.py:_egg_marks` → `RunRenderer.ellipse` (na rozdíl od `circle` nemá strop)
- Co se děje: každá značka má plynulý poloměr a 10 úrovní průhlednosti → stovky různých povrchů v cache.
- Jak se to projeví / kdy: slepice, delší run, hlavně se zvyšujícím se Megafonem.
- Důkaz: po 25 aktivacích 736 elips v cache, 22,6 MB, nikdy se neuvolní (cache maže jen `circle()` nad 400 položek).
- Jistota: ověřeno během běhu
- Proč to vadí: na telefonu zbytečná paměť (a `circle()` pak čistí i cache ostatních kruhů naráz).
- Směr opravy: kvantovat poloměr a průhlednost značek na pár kroků, nebo cache elips omezit.

### [B-89] Ikona na tlačítku „připraveno“ splývá s barvou ultimátky
- Závažnost: drobná
- Kategorie: UI/UX
- Kde: `game/ui/hud.py:_crow_button` (výplň `mul_color(col, 0.92)`)
- Co se děje: plně nabité tlačítko má výplň v barvě ultimátky a ikona je ve stejných barvách: tučňák (bílá vločka
  na světle modré), slepice (zlatá vejce na zlatém), krocan (červený záblesk na červeném). Čitelné jen díky obrysu.
- Jistota: ověřeno screenshotem všech 7 tlačítek
- Proč to vadí: stav „připraveno“ má být nejčitelnější, ve skutečnosti je méně kontrastní než stav nabíjení.
- Směr opravy: tmavší výplň (např. ~0,6 barvy) a barva ultimátky jen v záři, kroužku a nápisu.

### [B-90] Budík neříká, že zkracuje i nabíjení ultimátky
- Závažnost: drobná
- Kategorie: UI/UX (text)
- Kde: `game/data/passives.py` (Budík „−8 % doba přebíjení“), `game/data/ultimates.py` `ULT_CLOCK_STEP`
- Co se děje: Budík nově zkracuje nejkratší dobu nabití ultimátky (−8 %/úr., max. −40 %), karta to neuvádí.
- Jistota: podle kódu
- Proč to vadí: hráč nemá jak zjistit, že Budík ultimátku posiluje (skrytá mechanika).
- Směr opravy: doplnit do popisu pasivky „zbraní i ultimátky“.

## Ověřeno a v pořádku (bez nálezu)
- Pauza / level-up / bedna uprostřed efektu: efekty stojí (test `ultimates`). Smrt uprostřed efektu: efekty skončí,
  husa dostane zpět rychlost. Oživení spustí ultimátku zdarma. Výhra efekty zastaví. Restart = nový run, tlačítko
  „pop“ se mezi runy nepřenáší.
- Strop bosse: 7 ultimátek v souboji s Kohoutem 0,08–4,0 % HP za aktivaci; fázové zámky platí.
- Zpomalení bosse po Době ledové přetrvává jen kvůli rybě tučňáka (zpomalení 0,5 nastavovala už dřív) – ne nový problém.
- Strop projektilů: krocan s Gatlingem a 4 projektilovými zbraněmi + salva každé 4 s → max. 63 projektilů, 0 zahozených.
- Vajíčka mimo obrazovku: 5 z 212 (2 %).
- Determinismus: herní náhoda ultimátek jen z `run.rng`, vizuál z `particles.rng`.

## Mapa kódu (rozsah této kontroly)
- Data `data/ultimates.py` → `Run.ult` (`ult_for`) → `Run.crow()` odečte nabití → `world/ultimates.activate`
  (registr `EFFECTS`, zdroj `UltSource` se stropem bosse) → efekty v `run.ult_fx` (update v `Run.update` po zbraních,
  jen ve stavu `playing`) → vykreslení `world/ult_render.draw` (pod entitami / nad nimi) + HUD tlačítko.
- Okouzlení: `Enemy.charm_t/foe`, větev v `world/enemies.py`, `charm_target/charm_hit`; auto-aim a bot okouzlené ignorují.
- Stavy: playing, paused, levelup, chest, dying, dead, victory_anim, victory; módy quick/full/daily/bossrush/endless.
- Matice sond: 7 zvířat × (dav 3./8. min, Kohout v rychlém módu); celé runy botem: 7 × rychlý (6–10 seedů),
  7 × plný (3–4 seedy), slepice se všemi 7 ultimátkami (rychlý 10, plný 4 seedy).
- Čteno celé: všechny nové soubory a všechna změněná místa; ostatní kód jen v místech, kterých se změna dotýká.

## Co jsem nestihl / neověřil
- Android (klasický pygame 2.1, výkon `_frost_disc`, paměť), poslech zvuků, ruční hraní.
- Jiné mapy než Farma ve výkonových sondách (render bouře v mlze lesa, arény ostatních biomů).

## Témata, která se opakují
- **Cache bez stropu nebo s plynulými klíči** (B-87, B-88): plynulé hodnoty (poloměr, alfa) jako klíč cache → mnoho
  velkých povrchů. Kvantovat klíče, stavět předem.
- **Ladicí nástroje sahají na skutečná data** (B-86): vše, co běží přes `App`, musí mít vlastní nebo neukládaný save.

## Opraveno (4. 10. 2026, ověřeno sondou nebo screenshotem)
- B-86: scénář běží s neukládaným save (`App`: `save.persist = False`) – smoke.py se scénářem v kopii projektu už
  `save.json` nevytvoří.
- B-87: namrzlá zem = jeden povrch na poloměr kreslený přes `pygame.draw` (průhlednost při kreslení): 1. bouře
  max. 2,9 ms/snímek (dřív 16,6 ms), vzhled čistší (bez šrafování).
- B-88: značky dopadu po krocích (poloměr po 6 px, 4 úrovně průhlednosti): cache 42 elips / 1,7 MB (dřív 736 / 22,6 MB).
- B-89: připravené tlačítko má výplň 0,5× barvy ultimátky a barevný kroužek – ikony všech 7 zvířat čitelné.
- B-90: Budík „−8 % doba přebíjení zbraní i ultimátky“.

---

# Bug report: LAST CHICKEN – ultimátky zvířat, 7. kolo (B-91 – B-98)
Datum: 4. 10. 2026 · verze 1.2.0 (necommitnuto nad `18e0f4a`, po opravách B-86 – B-90) · rozsah: jen ultimátky.

**Jak jsem testoval:**
- Znovu celý kód ultimátek (`data/ultimates.py`, `world/ultimates.py`, `world/ult_render.py`, okouzlení ve
  `world/enemies.py`, napojení v `run.py`, `render.py`, HUD) a heuristický `scan.py` (nic nového).
- Sondy mimo projekt (headless, bez zásahu do hry):
  - telegraf úderu medvěda pod každou vrstvou ultimátek (snímek + měření barvy okraje),
  - konec okouzlení pávice (3 seedy) a cena hledání cíle,
  - Elvis, husa a slepice bez zbraní mezi 150 odolnými liškami s Budíkem 0 a 5,
  - pozdní hra botem (7.–10. min): bannery, pool částic, třes,
  - úroveň slepice v čase, stará verze proti nové (4 seedy),
  - výbuchy explodujících lišek po každé ultimátce (6 seedů).
- Zadavatel mezitím hrál pávici (rychlý mód, Farma, 3 runy): `crash.log` je beze změny, hra nespadla.
- **Neověřeno:** Android, ruční hraní, poslech zvuků, jiné mapy než Farma.

## Souhrn
8 nálezů: 0 kritických, 1 vysoký, 3 střední, 4 drobné.
Nic nepadá a stavy (pauza, smrt, oživení, výhra) drží. Problémy jsou v souhře s existujícími systémy. Budík teď zkracuje
nabíjení ultimátky, a tak z Elvise udělá skoro nezranitelného. Mrazivý disk tučňáka zakrývá telegrafy bossů. Okouzlení
pávice končí prstencem lišek přímo u ní. Banner s názvem ultimátky se u Elvise v pozdní hře skoro nestřídá.

## Nálezy

### [B-91] Elvis + Budík: KIKIRIKÍ každých 1,8 s, lišky trvale omráčené, Elvis skoro nezranitelný
- Závažnost: vysoká
- Kategorie: balanc
- Kde: `game/world/run.py:ult_min_cd` (Budík −8 %/úr., max. −40 %), `data/ultimates.py` (`kikiriki`: min_cd 6 s,
  omráčení 2,2 s), `CharDef.crow_mult = 2.0` (Elvis)
- Co se děje: v pozdní hře nabíjení neomezují zabití, ale nejkratší doba nabití. Elvis ji má poloviční (3 s) a Budík 5
  ji stáhne na 1,8 s. To je kratší než omráčení z KIKIRIKÍ (2,2 s), takže lišky do 290 px stojí pořád.
- Jak se to projeví / kdy: Elvis s Budíkem na 5 (bot ho bere jako 2. pasivku), od zhruba 5. minuty, hráč mačká tlačítko
  pořád dokola.
- Důkaz: Elvis bez zbraní, 150 odolných lišek, minuta mačkání po nabití: Budík 0 → 20 použití, omráčeno 61 % času,
  přijato 184 HP/min. Budík 5 → 34 použití, omráčeno 75 %, **přijato 15 HP/min** (12× méně). Husa: 906 → 417 HP/min
  (nesmrtelnost 37 % času), slepice: 516 → 391 HP/min. Před úpravou Budík kokrhání neovlivňoval (Elvis vždy 3 s).
- Jistota: ověřeno během běhu
- Proč to vadí: jedna kombinace pasivky a zvířete udělá z běžných lišek kulisu; „zjevně nejlepší volba“ pro Elvise.
- Směr opravy: Budík by neměl stáhnout nejkratší dobu nabití pod trvání vlastního omezení davu (nebo u Elvise neplatit
  či zkracovat jen cenu v zabitích).

### [B-92] Mrazivý disk Doby ledové zakrývá telegrafy útoků bossů
- Závažnost: střední
- Kategorie: grafika/čitelnost
- Kde: `game/world/render.py:draw` – `ult_render.draw(..., ground=True)` se kreslí až po `_telegraphs(ground=True)`;
  `game/world/ult_render.py:_ice` (disk r 215 přes celou plochu bouře)
- Co se děje: během 3 s bouře je červený kruh úderu medvěda (a další zemní telegrafy) pod světle modrou vrstvou. Plocha
  zrůžoví a okraj téměř zmizí. Totéž krátce dělá mokrá stopa Velké vody (~1 s) a zlaté značky vajec.
- Jak se to projeví / kdy: tučňák aktivuje ultimátku v souboji s bossem (bot i člověk to dělají právě u bossů).
- Důkaz: snímek se stejným telegrafem s bouří a bez ní; „červenost“ okraje kruhu r 165: 35 → 17 (tučňák), 27 → 11
  (kachna, hřbet vlny přes kruh).
- Jistota: ověřeno během běhu (snímek)
- Proč to vadí: telegrafy jsou jediná férová obrana proti útokům bossů; CODE_MAP to má jako pravidlo („efekty nesmí
  zakrývat telegrafy“).
- Směr opravy: kreslit zemní vrstvu ultimátek před telegrafy (nebo telegrafy znovu nad ni).

### [B-93] Konec Božské krásy: okouzlené lišky stojí kolem pávice a hned koušou
- Závažnost: střední
- Kategorie: game feel / balanc
- Kde: `game/world/enemies.py` větev `charm_t` (`elif d > 90: vx, vy = nx * speed …` – bez cíle jdou k hráči)
- Co se děje: okouzlená liška, která nemá koho napadnout, se stáhne k pávici na ~90 px („stráž“). Po 5 s okouzlení
  skončí a celý prstenec stráží je u pávice, takže kousne naráz.
- Jak se to projeví / kdy: kdykoli okouzlené lišky vybijí okolí nebo je kolem málo neokouzlených lišek.
- Důkaz: 3 seedy, pávice stojí: v 4,9 s je 12–37 z 50 okouzlených bez cíle a 7–18 jich stojí do 110 px od pávice;
  přijaté poškození po sekundách např. `[0, 0, 11, 11, 0, 8, 21, 13, 8]` (skok po 5. s).
- Jistota: ověřeno během běhu
- Proč to vadí: ultimátka, která má chránit, končí „zradou“. Nejvíc to schytá ten, kdo se spolehne na stráž.
- Směr opravy: stráž držet dál (kroužit ve větší vzdálenosti) nebo lišky po konci okouzlení na chvíli zmást.

### [B-94] Banner s názvem ultimátky při každém použití – u Elvise na obrazovce třetinu pozdní hry
- Závažnost: střední
- Kategorie: UI/UX / game feel
- Kde: `game/world/ultimates.py:activate` (`run.banner(ud.name, …, 1.5)` při každé aktivaci)
- Co se děje: každé použití ukáže velký nápis uprostřed horní poloviny obrazovky a navíc výkřik nad zvířetem. Při
  častém používání se z toho stává trvalý text přes hrací plochu („Královské KIKIRIKÍ“ + „KIKIRIKÍ!“ + nápis
  na tlačítku).
- Jak se to projeví / kdy: Elvis v pozdní hře (ultimátka každé ~3–4 s); ostatní zvířata méně.
- Důkaz: bot, plný mód, 7.–10. minuta: banner ultimátky viditelný 34 % času (Elvis, 41 použití za 3 min), slepice 6 %,
  krocan 3 %.
- Jistota: ověřeno během běhu
- Proč to vadí: zakrývá dav i ostatní bannery („FÁZE 2“, „KOHOUT ZUŘÍ!“), po pár použitích už nic neříká.
- Směr opravy: celý název jen při prvním použití v runu (dál jen výkřik), případně kratší a menší.

### [B-95] Okouzlené lišky bez cíle hledají cíl každý tick
- Závažnost: drobná
- Kategorie: výkon
- Kde: `game/world/enemies.py` větev `charm_t` (`if foe is None or …: foe = charm_target(run, e)`)
- Co se děje: pokud lišce cíl chybí, hledá ho (`grid.nearest` do 260 px) v každém ticku, ne jednou za 24 ticků.
- Jak se to projeví / kdy: okouzlené lišky vybijí okolí nebo jsou samy (viz B-93: 12–37 z 50 bez cíle).
- Důkaz: 50 okouzlených lišek bez soupeře: tick 0,10 ms → 0,76 ms (PC). Na telefonu odhadem několik ms po dobu 5 s.
- Jistota: ověřeno během běhu (PC), telefon odhad
- Proč to vadí: zbytečná zátěž přesně ve chvíli, kdy je na obrazovce nejvíc efektů.
- Směr opravy: při chybějícím cíli hledat znovu až za pár ticků (rozložit podle `e.id`).

### [B-96] Ultimátky zabíjejí explodující lišky přímo u hráče
- Závažnost: drobná
- Kategorie: balanc / game feel
- Kde: `EggRain` (prvních 5 vajec na nejbližší lišky), okouzlené stráže pávice (B-93), salva krocana
- Co se děje: ultimátka zabije explodující lišku těsně u hráče a ta za 0,6 s vybuchne. Hráč, který po aktivaci zůstane
  stát, dostane zásah od vlastní ultimátky.
- Jak se to projeví / kdy: od 3. minuty (explodující lišky ve vlnách), slepice, pávice, krocan.
- Důkaz: 8. min, 120 lišek (¼ explodujících), hráč stojí, 6 s: poškození z výbuchů bez ultimátky 0 HP, KIKIRIKÍ / Doba
  ledová / Velká voda / Husí řádění 0 HP, Zlatá nadílka 17 HP, Božská krása 17 HP, Díkůvzdání 13 HP (průměr 6 seedů).
- Jistota: ověřeno během běhu (statický hráč; bomby jsou 0,6 s telegrafované, pohybem se dají ujít)
- Proč to vadí: odměnou za použití ultimátky je zranění, které hráč nečeká. Záměr? („nezabíjej ji u sebe“ platí i dřív)
- Směr opravy: vejce na „nejbližší lišky“ by mohla vynechat explodující do ~70 px, nebo výbuchy z ultimátky šetřit hráče.

### [B-97] „Páv Diva“ vs. „pávice“ v textech ultimátky
- Závažnost: drobná
- Kategorie: UI/UX (text)
- Kde: `game/data/ultimates.py` popis `hypno` („bojují za pávici“), FEATURES/PLAN
- Co se děje: na výběru zvířete stojí „Páv Diva“ a hned pod tím „Lišky kolem se zamilují a 5 s bojují za pávici…“.
- Jistota: podle kódu (vidět na snímku výběru)
- Proč to vadí: dvě jména pro jedno zvíře.
- Směr opravy: sjednotit (např. „za Divu“).

### [B-98] Tlačítko ukazuje název ultimátky, zadání mluví o „ikoně a názvu zvířete“ (záměr?)
- Závažnost: drobná
- Kategorie: spec mismatch
- Kde: `game/ui/hud.py:_crow_button` (pod tlačítkem `ult.short`, např. „VLNA“)
- Co se děje: zadání: „tlačítko ultimátky ukazuje ikonu a název zvířete, stav nabití…“. Tlačítko ukazuje ikonu
  a krátký název ultimátky, jméno zvířete nikde.
- Jistota: podle kódu
- Proč to vadí: pokud zadání myslelo doslova jméno zvířete, chybí. Pravděpodobně šlo o název ultimátky zvířete.
- Směr opravy: potvrdit záměr; případně doplnit jméno zvířete (např. do pauzy, kde už ultimátka je).

## Ověřeno a v pořádku (bez nálezu)
- XP: Zlatá nadílka křivku úrovní neposouvá – slepice v 3./6./9. min: stará verze 15,0 / 29,5 / 45,8, nová
  16,0 / 31,3 / 46,8 (4 seedy, v šumu).
- Pool částic se v pozdní hře nezaplní (0 % snímků v 7.–10. min), efekty ultimátek tedy nemizí.
- Třes: ultimátky mají strop 0,6; maximum 0,97 v pozdní hře dělají bossové (stejně u všech zvířat).
- Doba ledová, Velká voda, Husí řádění a KIKIRIKÍ výbuchy explodujících lišek u hráče nepřidají (0 HP, viz B-96).
- Kachna (podle kódu, neměřeno): lišky těsně za kachnou omráčí rozstřik (0,6 s) dřív, než přes ni projde vlna.

## Co jsem nestihl / neověřil
- Android (výkon okouzlení a disku, klasický pygame 2.1), ruční hraní, poslech zvuků.
- Jiné mapy (mlha lesa nad mrazivým diskem, aréna v ostatních biomech), Hard/Nightmare, Nekonečná noc za 2. nocí.
- Evolvované ultimátky v delším běhu (jen data a jednotlivé aktivace).

## Témata, která se opakují
- **Násobiče se skládají bez spodní meze** (B-91): Elvis 2× × Budík −40 % → nabíjení kratší než účinek. Kde jedna věc
  zkracuje dobu nabití, hlídat, aby nepodlezla trvání efektu.
- **Nové vrstvy kreslené přes čitelnost** (B-92): vše, co se kreslí na zem během boje, musí jít pod telegrafy.
- **Opakovaná zpětná vazba bez útlumu** (B-94): co je skvělé poprvé (banner), je otravné podesáté.
- **Stav po konci efektu** (B-93, B-96): ultimátky jsou laděné na průběh, ne na to, v jakém stavu nechají hráče.

## Opraveno (7. kolo, 4. 10. 2026 – ověřeno stejnými sondami)
- B-91: `UltDef.cd_floor` – nejkratší rozestup použití i s Budíkem a pasivkou zvířete (vejce, vlna, krocan 5 s, Elvis
  3 s, Diva a tučňák 8 s, husa 10 s), `Run.ult_period()`. Elvis s Budíkem 5: 3,0 s a 184 HP/min (jako bez Budíku,
  dřív 1,8 s a 15 HP/min).
- B-92: `RunRenderer.draw` kreslí zemní vrstvu ultimátek před telegrafy – okraj úderu medvěda nad mrazivým diskem
  zřetelný (snímek).
- B-93: stráž bez cíle drží ~150 px od Divy (`guard`), po konci okouzlení 0,8 s zmatení (`end_stun`): 0 lišek do
  110 px od Divy na konci okouzlení (dřív 7–18).
- B-94: velký banner jen poprvé, dál malý název u zvířete nejvýš 1× za 20 s (`ULT_NAME_GAP`): banner v pozdní hře
  0 % času (dřív 34 %).
- B-95: okouzlená liška bez cíle hledá jednou za 12 ticků: 0,16 ms/tick (dřív 0,76 ms).
- B-96: výbuch lišky zabité ultimátkou nese ultimátku jako zdroj a nezraní hráče (ani řetěz dalších výbuchů):
  0 HP u všech ultimátek kromě Božské krásy 4 HP (lišky zabité zbraní, ne ultimátkou), dřív 13–17 HP.
- B-97: „bojují za Divu“ (data, komentáře, dokumentace).
- B-98: nad tlačítkem ultimátky jméno zvířete v jeho barvě (snímek všech 7 tlačítek).
- Pasti: smoke test `ultimates_regressions` (B-91, B-93, B-94, B-96, B-98). Smoke testy 19/19, kontrolní runy botem
  35/42 výher v rychlém módu (před opravami 44/56).

---

# Bug report: LAST CHICKEN – Straka, tajné skiny, vzácná zlatá vejce, truhly hned, 8. kolo (B-99 – B-109)
Datum: 4. 10. 2026 · necommitnutý diff nad `4adb241` (= `origin/main` na GitHubu, 25 souborů, +556 / −107) ·
rozsah: jen nový kód oproti GitHubu.

**Jak jsem testoval:**
- Celý diff proti `origin/main` řádek po řádku: Straka (data, sprite, zbraň `BounceWeapon`, pasivka, ultimátka
  `heist`, zvuk), tajné skiny a Obchod, `check_collection` a `visible_chars`, zlatá vejce za bosse (`boss_gold`),
  truhly hned (`Run.update`), výběr zvířete v boss rushi (`DailyScene`), login, truhla za žeton, týdenní odměna.
- `scan.py` na nový kód: bez nálezu. Smoke testy **24/24**.
- Sondy mimo projekt (headless, bez zásahu do hry), část proti verzi z GitHubu vyexportované přes `git archive HEAD`:
  - truhla sebraná během 8s rozestupu s čekajícím level-upem,
  - přerušení za plný run (3 seedy) stará vs. nová verze,
  - Straka celým plným módem botem (mince, pickupy, cetky, ms/snímek), srovnání se slepicí a tučňákem,
  - výhry bota v rychlém módu, 8 zvířat × 8 seedů,
  - `dps_bench` (cetky vs. ostatní zbraně), `ult_lab measure` a snímky ultimátek,
  - jedna cetka sledovaná snímek po snímku (odrazy, zásahy),
  - zprávy a zlatá vejce po boss rushi a Nekonečné noci, rozpočet zlatých vajec z dat,
  - snímky: denní výzva (nový hráč, plný hráč, 10 řádků žebříčku), Obchod (bez/se všemi tajnými skiny, se Strakou),
    výběr se Strakou, 5 tajných klobouků × 8 zvířat × 2 směry, laser ze zobáku Straky.
- **Neověřeno:** Android, ruční hraní, poslech zvuků, Straka na jiných mapách a obtížnostech, dlouhá Nekonečná noc.

## Souhrn
11 nálezů: 0 kritických, 0 vysokých, 5 středních, 6 drobných.
Nový obsah je stabilní: nic nepadá, rozložení obrazovek sedí a Straka je v balancu uprostřed (bot 7/8 výher, ostatní
4–8/8). Hlavní problémy jsou texty a pravidla, která změnu nesledují. Sbírka pořád slibuje 3 zlatá vejce. Truhla
otevřená hned zruší rozestup level-upů, i když dokumentace tvrdí opak. Ultimátka Straky je výrazně nejslabší a její
zbraň cinká stejným zvukem jako sebraná mince.

## Nálezy

### [B-99] Sbírka pořád slibuje „3 zlatá vejce“, odměnou je přitom tajný skin
- Závažnost: střední
- Kategorie: spec mismatch / UI
- Kde: `game/scenes/collection.py:100`; `game/scenes/shop.py:184`
- Co se děje: nahoře ve Sbírce svítí „100 % kategorie = 3 zlatá vejce“. Po dokončení kategorie ale hráč dostane jen
  skin, zlatá vejce ne. Nadpis v Obchodě „Tajné skiny – za kompletní sbírku“ zase říká, že skiny jsou za celou
  sbírku, ne za jednotlivé kategorie. Že celá sbírka odemkne tajné zvíře, neříká nikde nic (to může být záměr).
- Jak se to projeví / kdy: kdykoli hráč otevře Sbírku. Nejvíc vadí ve chvíli, kdy dokončí kategorii a zlatá vejce
  nepřijdou.
- Důkaz:
  ```python
  font.draw(surf, "100 % kategorie = 3 zlatá vejce", (W // 2, 100), (255, 214, 120), 2, "midtop")
  ```
  `COLLECTION_REWARD_GOLD` v diffu zmizel a `check_collection` zlatá vejce nepřidává.
- Jistota: podle kódu (text ověřen grepem, odměna sondou přes `check_collection`)
- Proč to vadí: hra slibuje měnu, kterou nedá. Hráč, který kvůli tomu sbírku dotahuje, bude mít pocit, že je to chyba.
- Směr opravy: přepsat texty ve Sbírce a v Obchodě podle nového pravidla („kategorie = tajný skin“).

### [B-100] Truhla obchází rozestup level-upů – hned po ní naskočí level-up
- Závažnost: střední
- Kategorie: logika / spec mismatch
- Kde: `game/world/run.py:1098–1103` (nová větev pro truhlu) + `Run.resume()` (`run.py:1140`)
- Co se děje: truhla se teď otevře hned i během 8s rozestupu (`PAUSE_GAP`). Po jejím zavření ale `resume()` rovnou
  otevře čekající level-up a `pause_cd` přitom ignoruje. Hráč tak dostane level-up → truhlu → hned další level-up.
  FEATURES i PLAN přitom slibují „Level-up po zavření truhly dál čeká na rozestup“.
- Jak se to projeví / kdy: kdykoli hráč sebere truhlu (elita, boss) do 8 s po zavření level-upu a mezitím nasbírá XP.
  V pozdní hře je to běžné.
- Důkaz: sonda, `pause_cd = 8`, 2 čekající level-upy, truhla pod hráčem:
  `chest opened, pause_cd=7.82` → `after closing chest -> state=levelup pause_cd=7.82`.
  Plný run botem, přerušení do 2 s po předchozím: GitHub 5 / 3 / 4, nová verze 6 / 7 / 6 (seedy 1–3).
  Test `chest_now_gold_rare_secret_skins_magpie` to nezachytí, protože `pending_levelups` nastaví až po `resume()`.
- Jistota: ověřeno během běhu
- Proč to vadí: rozestup B-51 měl zabránit řetězení obrazovek a truhla ho teď obchází. Navíc se zmenší spojování
  level-upů (B-74), protože se otevřou dřív.
- Směr opravy: v `resume()` otevírat level-up jen při `pause_cd <= 0`, nebo test a dokumentaci sladit s tím, co hra
  skutečně dělá.

### [B-101] Velká loupež je nejslabší ultimátka – od 3. minuty nezabije ani běžnou lišku
- Závažnost: střední
- Kategorie: balanc
- Kde: `game/data/ultimates.py:92` (`heist`: dmg 15, hp_pct 0,10, stun 1,6), `game/world/ultimates.py:692`
- Co se děje: ultimátka Straky dá liškám 15 + 10 % HP. Liška ve 3. minutě má 23 HP, takže dostane 17,3 a přežije.
  V 8. minutě (108 HP) dostane 25,8, tedy 24 %. Na snímku aktivace mají lišky v kruhu čísla 16–18 a počítadlo zabití
  se skoro nehne.
- Jak se to projeví / kdy: celý run se Strakou, nejvíc v pozdní hře.
- Důkaz: `ult_lab measure` (minuta 3, 80 lišek, 3 seedy):

  | ultimátka | zabití | % HP davu | přijaté poškození po 8 s |
  |---|---|---|---|
  | Velká loupež | **14** | **39 %** | **82 %** (nejhorší) |
  | ostatní 7 | 33–59 | 46–83 % | 23–75 % |

- Jistota: ověřeno během běhu
- Proč to vadí: tlačítko, na které hráč 70 zabití čeká, skoro nic neudělá. Mince a přitažení zrní za to slabou
  kontrolu davu nevyváží.
- Záměr? Pokud má být užitková (mince a zrní), chtělo by to aspoň delší omráčení nebo procento HP, které škáluje s
  časem. Bez toho působí jako nefunkční.
- Směr opravy: zvednout procentní složku nebo omráčení tak, aby se ultimátka v 3./8. minutě vyrovnala ostatním.

### [B-102] Lesklé cetky při každém hodu cinkají jako sebraná mince
- Závažnost: střední
- Kategorie: zvuk
- Kde: `game/weapons/kinds.py:670` `run.sfx("coin", 0.35)`; sebrání mince je `game/world/run.py:922`
  `self.sfx("coin", 0.5)`
- Co se děje: zbraň Straky hraje každých 0,7–1,1 s stejný zvuk jako sebraná mince, jen trochu tišší. Straka je
  přitom postavená na mincích (pasivka Zlodějka, mince z ultimátky i z evoluce).
- Jak se to projeví / kdy: celý run se Strakou od první sekundy.
- Důkaz: viz řádky výše, obě volání používají zvuk `"coin"`.
- Jistota: podle kódu (zvuk jsem neposlouchal)
- Proč to vadí: cinknutí přestane znamenat „mám minci“ a z odměny se stane kulisa. Hráč nepozná, kdy pasivka zabrala.
- Směr opravy: dát cetkám vlastní krátký „cink/švih“ a zvuk mince nechat jen pro sebrání.

### [B-103] Odemčení za dřív dokončenou sbírku proběhne potichu
- Závažnost: střední
- Kategorie: UI/UX
- Kde: `game/app.py:63` – `if progression.check_collection(self.save): self.save.save()`
- Co se děje: hráč, který měl sbírku hotovou už před updatem, dostane při startu hry Straku a skiny bez jediné zprávy.
  Zprávy z `check_collection` („Celá sbírka! Tajemství odhaleno: Straka Klepna…“) se zahodí. Straka se jen tiše
  přidá jako 8. tečka na konec výběru.
- Jak se to projeví / kdy: první spuštění po updatu u hráčů, kteří mají 100 % kategorie nebo celé sbírky.
- Důkaz: návratová hodnota (seznam zpráv) se použije jen jako podmínka pro uložení.
- Jistota: podle kódu (neověřeno se skutečným starým savem)
- Proč to vadí: odhalení tajného zvířete je odměna pro nejvěrnější hráče a právě ti ji neuvidí. Možná ani nezjistí,
  že Straka existuje.
- Směr opravy: zprávy si uložit a ukázat v menu jako dialog, podobně jako denní odměnu.

### [B-104] „První porážka bosse: +6 zlatá vejce“ – špatné skloňování
- Závažnost: drobná
- Kategorie: UI/UX (text)
- Kde: `game/progression.py:338–339`
- Co se děje: pro 5 a víc je správně „zlatých vajec“ a při víc bossech „bossů“. První boss rush dá rovnou 6
  (4 mini-bossové + Kohout 2).
- Důkaz: sonda: `['První porážka bosse: +6 zlatá vejce', …]`
  ```python
  word = "zlaté vejce" if rewards["gold"] == 1 else "zlatá vejce"
  ```
- Jistota: ověřeno během běhu
- Proč to vadí: na obrazovce výsledků je to vidět hned po prvním boss rushi.
- Směr opravy: skloňovat podle čísla (1 / 2–4 / 5+) a slovo „boss“ podle počtu.

### [B-105] Tajný skin: „Liščí ušanka nasazen“, sundání bez odezvy
- Závažnost: drobná
- Kategorie: UI/UX (text, zpětná vazba)
- Kde: `game/scenes/shop.py:86–89`
- Co se děje: hláška je jen v mužském rodě. Čtyři z pěti tajných skinů jsou ženského rodu (ušanka, koruna, helma,
  svatozář), takže vznikne „Koruna dvora nasazen“. Druhé klepnutí na nasazený skin ho tiše sundá, bez hlášky a bez
  zvuku. Hráč, který si chtěl jen ověřit, že je nasazený, ho omylem sundá.
- Jistota: podle kódu
- Směr opravy: rod uložit k skinu (nebo neutrální text „Nasazeno: …“) a přidat hlášku i pro sundání.

### [B-106] Boss rush si nepamatuje vybrané zvíře
- Závažnost: drobná
- Kategorie: UI/UX
- Kde: `game/scenes/daily.py:63–66` (`play_rush` neukládá `last_char`)
- Co se děje: PLAN slibuje „výchozí naposledy hrané“. Výchozí je ale zvíře z hlavního výběru, ne to, se kterým hráč
  naposledy hrál rush. Kdo hraje rush s tučňákem a jinak se slepicí, musí šipkami vybírat pokaždé znovu.
- Jistota: podle kódu
- Směr opravy: při startu rushe uložit volbu (třeba do vlastního klíče, ať nepřepíše výběr pro běžné módy).

### [B-107] Jméno zvířete v panelu boss rushe je u Krocana skoro nečitelné
- Závažnost: drobná
- Kategorie: UI/UX
- Kde: `game/scenes/daily.py:131` (jméno v barvě zvířete na panelu `(70, 40, 46)`)
- Co se děje: červená „Krocan Rambo“ `(226, 48, 52)` na tmavě vínovém panelu má kontrast zhruba 2,9 : 1. Obrys
  trochu pomáhá, ale text splývá (snímek `daily_full`).
- Jistota: ověřeno na snímku
- Směr opravy: jméno kreslit světlou barvou a barvu zvířete použít jen jako akcent, nebo dát pod jméno tmavší podklad.

### [B-108] Pirátský klobouk na Strace není vidět
- Závažnost: drobná
- Kategorie: grafika
- Kde: `game/gfx/sprites.py` (hlava Straky `k = (52, 50, 72)`), klobouk `pirate`
- Co se děje: černý klobouk na černé hlavě skoro splyne. Na snímku 7 klobouků × 2 směry je to jediný, který nejde
  rozeznat. Ostatních 5 tajných skinů na všech 8 zvířatech sedí.
- Jistota: ověřeno na snímku
- Směr opravy: světlý obrys klobouku, nebo lebka a lem v kontrastní barvě.

### [B-109] `tools/ult_lab.py table` padá na ultimátce Straky
- Závažnost: drobná
- Kategorie: nástroj (vývoj)
- Kde: `tools/ult_lab.py:370` – větev `else` počítá s Dobou ledovou (`s["dur"]`, `s["tick"]`)
- Co se děje: po přidání `magpie` do `ORDER` skončí `table` výjimkou `KeyError: 'dur'`. Ostatní příkazy
  (`measure`, `shots`) fungují.
- Jistota: ověřeno během běhu
- Směr opravy: přidat větev pro `heist` (podle výpočtu výše 75 % / 24 % HP lišky ve 3. / 8. min).

## Ověřeno a v pořádku (bez nálezu)
- Zlatá vejce: každý boss jen jednou, Kohout zvlášť pro každou mapu. Boss rush poprvé dá 6, Nekonečná noc v Lese pak
  jen `zombie_rooster:forest`. Starý save bez `boss_gold` se načte (`_merge`).
- Rozpočet zlatých vajec z dat: výzvy 38 + bossové 14 = 52 a nikde se neobnovují. Skiny za ně stojí 26, nic se tedy
  nezablokuje (viz otázka v tématech).
- Cetky: 3 odrazy = 4 zásahy, každý odraz míří na nejbližší nezasaženou lišku a sprite se natáčí po směru letu.
  DPS uprostřed pole: L8 144 na cíl / 1 250 do davu (ostatní zbraně 40–310 / 175–1 642). Dokumentace uvádí 112 / 976,
  to je jen nepřesný údaj, ne chyba hry.
- Straka botem: rychlý mód 7/8 výher (ostatní 4–8/8), mince zhruba 2× (225 proti 99–150). Plný mód: 1 255 mincí
  proti 708 u slepice, vejce +26 %. Výkon 0,27 ms/snímek, pickupů nejvýš 384 (slepice 388), živých cetek nejvýš 18.
- Determinismus: náhoda Zlodějky se čerpá jen u Straky a denní výzva bere zvířata z `CHAR_ORDER[:6]`, takže se denní
  výzva ani žebříček nezmění.
- Rozložení: žebříček s 10 řádky se do zkráceného panelu vejde, Obchod (7 řádků + 5 dlaždic + truhla) se vejde do
  960 px, výběr s 8 tečkami sedí, laser vychází ze zobáku Straky na obě strany.
- Truhla otevřená hned nepřeskočí odměnu: overlay má zámek a „Pokračovat“ se ukáže až po ~1,2 s.

## Co jsem nestihl / neověřil
- Poslech zvuků (`ult_magpie`, cetky), Android, ruční hraní.
- Straka na ostatních mapách, Hard/Nightmare a v dlouhé Nekonečné noci. Plný mód jen 1 seed.
- Migraci na skutečném starém savu s hotovou sbírkou. B-103 je jen podle kódu, skutečný save jsem neotevíral.
- Mimo hru: nesledovaná složka `.evolve/` obsahuje lokální cestu k záloze (`C:\Users\…`). Kdyby se omylem commitla
  (`git add .`), dostala by se na GitHub. Není v `.gitignore`.

## Témata, která se opakují
- **Texty a dokumentace nesledují změnu pravidel** (B-99, B-100, B-104): pravidla odměn se změnila v kódu, ale
  Sbírka, Obchod i FEATURES mluví postaru nebo slibují něco, co kód nedělá.
- **Test ověřuje zjednodušený scénář** (B-100): nový test pokryje šťastnou cestu, ne souběh s čekajícím level-upem,
  kde se chyba projeví.
- **Jeden signál pro dva významy** (B-102, B-108): zvuk mince pro hod zbraní, černá na černé. Nové zvíře dědí
  prostředky, které už něco znamenají.
- **Migrace bez zpětné vazby** (B-103): zpětné přidělení odměn funguje, ale hráč se o něm nedozví.
- Otázka (záměr?): zlatá vejce jsou teď „vzácná“, ale po koupi 4 skinů za 26 nemají využití a dá se jich získat 52.
  Vzácná měna bez využití hráče nemotivuje.

## Opraveno (8. kolo, 4. 10. 2026 – ověřeno stejnými sondami)
- B-99: Sbírka „100 % kategorie = tajný skin · vše = ???“ (po odhalení „Straka“), Obchod „Tajné skiny – za
  kompletní kategorie sbírky“.
- B-100 (podle upřesnění zadavatele: truhla se do rozestupu vůbec nepočítá): `Run.resume()` obnoví rozestup jen po
  level-upu; po truhle se rozestup nezmění a čekající level-up počká, až doběhne. Sonda: po zavření truhly
  `state=playing pause_cd=7.82` (dřív hned `levelup`). Řetěz „truhla → hned level-up“ zmizel (min. odstup přerušení
  0,18–0,67 s místo 0,00 s); truhla se pořád otevře okamžitě.
- B-101: Velká loupež 30 + 40 % HP, omráčení 1,8 s (dřív 15 + 10 %, 1,6 s). `ult_lab measure`: 42 zabití, 57 % HP
  davu, přijaté poškození po 8 s 45 % (dřív 14 / 39 % / 82 %) – uprostřed ostatních. Bot se Strakou dál 7/8 výher.
- B-102: nový zvuk `trinket` (švih + skleněné tink, 0,12 s); cetky i Strakatý poklad ho používají, `coin` zůstal
  jen pro sebrání mince.
- B-103: `App.startup_msgs` → menu ukáže dialog „Tajemství odhaleno!“ (po případné denní odměně, jen jednou),
  skiny sloučené do jedné věty (snímek s 5 skiny + Strakou se vejde).
- B-104: „První porážka bossů: +6 zlatých vajec“ (1 / 2–4 / 5+).
- B-105: „Nasazeno: …“ / „Sundáno: …“ + klik i při sundání.
- B-106: boss rush si pamatuje zvíře v `save["weekly"]["char"]` (výchozí, jinak naposledy hrané).
- B-107: jméno zvířete v panelu rushe světlým odstínem jeho barvy (snímek: Krocan čitelný).
- B-108: pirátský klobouk se zlatým lemem – na Strace viditelný (snímek 3 klobouky × 8 zvířat).
- B-109: `ult_lab table` má větev pro Velkou loupež (100 % / 68 % HP lišky ve 3. / 8. min).
- Mimo hru: `.evolve/` v `.gitignore`.
- Pasti: smoke test `round8_regressions`, upravené `chest_now_gold_rare_secret_skins_magpie` (souběh truhly s
  čekajícím level-upem) a `daily_fixed_rush_character_choice` (zapamatování zvířete). Smoke testy 25/25.
- Otázka zlatých vajec bez využití (52 získatelných / 26 k utracení) zůstává otevřená – rozhodnutí o designu.
