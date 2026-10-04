# LAST CHICKEN – plán a architektura

Auto-shooter roguelite (survivors-like) v Pythonu + pygame-ce. Portrait 540×960, ovládání jedním palcem.

## Architektura

```
main.py                    vstupní bod, CLI (--quick, --debug)
game/
  config.py                konstanty (rozlišení, Hz, cesty)
  app.py                   App: okno + letterbox škálování, fixní krok 60 Hz, scény, přechody, crash handling
  assets.py                globální registr (font, sprity, audio) – inicializuje App
  save.py                  SaveData: save.json, atomický zápis, odolnost proti poškození, migrace
  util.py                  matematika, tweeny, formátování času
  progression.py           levelup karty, bedny, výpočet odměn, výzvy, sbírka, denní obsah, sezóny
  share.py                 export PNG výsledku do shares/
  bot.py                   bot pro headless simulace a testy (kiting, sběr, uhýbání telegrafům, výběr karet)
  scenarios.py             ladicí scénáře (--scenario ult_duck …) pro ruční test a tools/ult_lab.py
  core/  input.py          pevný joystick (vznikne, kam hráč ťukne) + klávesnice, mapování okno → logické souřadnice
         camera.py         plynulé sledování, trauma shake, kick („vibrace“)
         spatial.py        spatial hash grid (int klíče, přestavba každý tick)
  gfx/   font.py           vlastní bitmapový font 5×7 s českou diakritikou (skládané akcenty)
         pixelart.py       pixel mapy → Surface (auto-outline, stínování, flip, flash, tint)
         sprites.py        všechny pixel mapy postav/nepřátel/bossů + SpriteBank
         icons.py          ikony zbraní, pasivek, UI
         tiles.py          procedurální dlaždice terénu podle biomu
         particles.py      pool částic (peří, jiskry, sliz…), pevný strop
  audio/ synth.py          numpy syntéza (square/saw/triangle/noise, envelope, formantové „kvok“)
         sound.py          SFX s rate-limitem, vrstvená dynamická hudba (4 vrstvy synchronně)
  data/  characters.py weapons.py passives.py enemies.py bosses.py biomes.py waves.py meta.py ultimates.py
                           vše datově řízené (dicty/dataclassy) – obsah se přidává jen sem
  world/ run.py            Run = celá simulace runu (bez renderu → headless bot/sim)
         entities.py       lehké entity se __slots__ (Enemy, Proj, EProj, Area, Beam, Ring, Telegraph, Pickup…)
         player.py         pohyb, statistiky, squash & stretch, poloha zobáku
         enemies.py        jediná rychlá smyčka AI nepřátel (pohyb, separace, překážky, kontakt)
         bosses.py         stavové automaty 5 bossů + biomové varianty finálního Zombie Kohouta
         allies.py         kuřata, spřátelené lišky, hnízda
         director.py       spawn director (křivka, prstence, hordy, obklíčení, elity, bossové)
         mapgen.py         nekonečná mapa z chunků (deterministický seed), překážky, zóny, hazardy
         render.py         RunRenderer: y-sorting, stíny, fblits batch, overlaye
         ultimates.py      ultimátky zvířat: aktivace, registr efektů, zdroj poškození se stropem bosse
         ult_render.py     vykreslení běžících ultimátek (pod entitami / nad nimi)
  weapons/ base.py kinds.py  chování zbraní (16 druhů + evoluce přes parametry)
  ui/    widgets.py hud.py overlays.py
  scenes/ menu, select, nest, collection, challenges, settings, shop, daily, game, error
tools/ simulate.py         bot projede celý run a vypíše statistiky (headless)
       ult_lab.py          měření ultimátek: jedna aktivace v davu, boss, celé runy, výkon, screenshoty, tabulka z dat
       profile_run.py      cProfile zátěžové scény (400 nepřátel + 300 projektilů)
       preview_sprites.py  contact sheet všech spritů do PNG (kontrola grafiky)
       dps_bench.py        DPS všech zbraní (single target / AoE) pro balanc
       screenshots.py      headless screenshoty všech scén
tests/smoke_test.py        headless smoke testy všech systémů
```

### Datové struktury (klíčové)
- `RunConfig(character, biome, mode, difficulty, seed, modifiers)` – mode: `quick | full | daily | bossrush | endless`.
- `Run` drží seznamy entit (`enemies`, `projs`, `eprojs`, `areas`, `beams`, `allies`, `pickups`, `telegraphs`),
  `grid` (SpatialGrid), `ParticleSystem`, `weapons`, `passives`, stav (`playing | levelup | chest | dying | dead | victory`).
- Entity mají `__slots__`, nepřátelé jednoduchého typu se řídí inline v jedné smyčce (rychlost), komplexní (elity, bossové)
  mají kontroler `ctrl.update()`.
- Zbraň: `WeaponDef(id, kind, base, levels[(změny, text)], evo_passive, evo_to)`; statistika = base + součet delt do úrovně.
- Evoluce = samostatná `WeaponDef` (1 úroveň) se stejným druhem chování a „evo“ parametry.

### Výkon
- Fixní logika 60 Hz, render nezávisle; vše se kreslí na interní 540×960 surface a škáluje (letterbox).
- Spatial hash (buňka 64 px, int klíče), separace nepřátel rozložená do 2 framů s limitem sousedů.
- `Surface.fblits` pro dávky spritů, předrenderované varianty (flip, flash) – žádné transformace v hot loopu.
- Pool částic s pevným stropem, slučování XP zrn nad limit, recyklace vzdálených nepřátel.

## Pořadí implementace
1. Font, pixel art, sprity (+ náhled), audio syntéza, save.
2. Data (postavy, zbraně, pasivky, nepřátelé, bossové, biomy, vlny, meta).
3. Simulace runu (hráč, nepřátelé, projektily, zbraně, director, mapa, bossové).
4. Render + HUD + overlaye (levelup, bedna, pauza, oživení, výsledky).
5. Scény menu (výběr zvířete/mapy/módu, Hnízdo, Sbírka, Výzvy, Obchod, Denní, Nastavení).
6. Smoke testy, bot simulace, profiling, balanc, README.

## Rozhodnutí
- **Rychlý mód**: Zombie Kohout (zkrácená verze, méně HP) přilétá ve 2:30, run končí jeho porážkou (~3 min).
- **Plný mód**: mini-bossové ve 2/4/6/8 min, finální Zombie Kohout v 10:00. Pokud ho hráč neporazí do 3 minut, boss zuří (víc damage) – run nemůže viset donekonečna.
- **Mapa** je nekonečná, generovaná po chuncích deterministicky ze seedu. Finální boss vytvoří kruhovou **arénu** (elektrický plot) – „kraj mapy“ z fáze 1 = okraj arény, který zraňuje.
- **Font**: vlastní bitmapový 5×7, diakritika skládaná (čárka, háček, kroužek) → 100% česká diakritika, jednotný pixel vzhled.
- **Sprity**: pixel mapy (řetězce + paleta) s automatickým obrysem a stínováním, škálované ×3 nearest-neighbour.
- **Zóny** (louže, led, pásy) ovlivňují jen hráče (výkon); hazardy (lisy, laviny, sudy) zraňují hráče i nepřátele.
- **Výbušné sudy** jsou statické „prop“ entity v gridu nepřátel (sdílí damage pipeline, nejsou cílem auto-aimu, nepočítají se do zabití).
- **Rarita karet**: běžná = +1 úroveň, vzácná = +2, epická = +3 (nová zbraň/pasivka začne na vyšší úrovni). Čtyřlístek zvyšuje šanci na vzácné/epické.
- **Startovní zbraně zvířat** jsou exkluzivní pro dané zvíře (každé zvíře hraje jinak); 10 základních zbraní je v poolu pro všechny.
- **Evoluce**: všech 10 základních zbraní + 6 startovních má evoluci (16 celkem). Otevře se bednou z elity/bosse, když je zbraň na úr. 8 a hráč vlastní pasivku.
- **Tajný tučňák**: zbraň „Mražená ryba“ (bumerang, který zmrazuje), pasivka „Ledová krev“ (zmražené lišky od něj dostanou o 30 % víc), slabina o 5 % pomalejší. Odemčení: 10× klepnout na logo v menu. (Do 4. 10. 2026 měl pasivku „Klouzání po břiše“ se setrvačností – na přání zadavatele zrušena; kód klouzání zůstal vázaný na `special == "slide"` a nic ho nepoužívá.)
- **Páv Diva**: odemčení splněním výzvy „Tisíc lišek“. „Drahé upgrady“ = o 10 % víc XP na úroveň (původně 25 %, změněno v B-52). Hypnóza = zmatený nepřítel bloudí a dostává +25 % damage.
- **Kohout Elvis**: odemčení porážkou finálního bosse (libovolný mód).
- **Obtížnosti**: Hard se odemkne výhrou na Normal, Nightmare výhrou na Hard. Násobí HP/damage/spawn i odměny.
- **Mapy**: Farma od začátku; další se odemknou výhrou na předchozí mapě nebo koupí za vejce.
- **Rubber-banding**: smrt před 1:30 → další run začíná s bonusem XP (1 úroveň zdarma).
- **Mince** v runu (skip, bedny, Zlatá bomba) se na konci převedou na vejce 1:1.
- **Zlatá vejce** (od 4. 10. 2026 vzácná): jen za první porážku každého bosse (finální Kohout zvlášť na každé mapě,
  klíč v `save["boss_gold"]`) a za výzvy. Denní login, týdenní boss rush a truhly za žetony dávají místo nich
  vejce/žetony, sbírka tajné skiny. **Žetony**: denní výzva + denní login + týdenní boss rush → truhly v Obchodě.
- **Sbírka** (4. 10. 2026): každá kompletní kategorie odhalí tajný skin (Liščí ušanka, Koruna dvora, Vojenská helma,
  Svatozář, Čarodějný klobouk – v Obchodě do té doby jako otazníky), celá sbírka odemkne tajné zvíře **Straka Klepna**
  (ve výběru úplně skrytá, dokud ji hráč nezíská). Platí i zpětně pro dřív dokončené kategorie. Straka a její
  zbraně/evoluce do sbírky nepatří (jinak by 100 % nešlo splnit). Zbraň Lesklé cetky (odrazy mezi liškami),
  pasivka Zlodějka (mince 6 % ze zabití, +50 % sběr), ultimátka Velká loupež, slabina 90 % životů.
- **Truhly v runu** (4. 10. 2026): sebraná truhla se otevře hned a do rozestupu 8 s (`PAUSE_GAP`) mezi level-upy se
  nepočítá – rozestup neobnoví, nezkrátí, a čekající level-up po ní počká, až rozestup doběhne.
- **Denní výzva**: seed = datum, jedna šance denně, zvíře dne, mapa a modifikátor pro všechny stejné (zamčené zvíře dne se zapůjčí); lokální žebříček top 10 = vlastní výsledky + deterministicky generovaní „sousedé“ z vesnice (offline hra nemá server).
- **Týdenní boss rush**: všichni bossové za sebou, start s 10 level-upy zdarma (bossové sypou XP), odměna jednou za ISO týden;
  zvíře si hráč vybírá šipkami ze všech odemčených (výchozí naposledy hrané) – 4. 10. 2026 přesunuto sem z denní výzvy,
  která má zase pevné zvíře dne (pro všechny stejné podmínky žebříčku).
- **Sezónní témata**: automaticky podle data (říjen = Halloween, prosinec = Vánoce, březen–duben = Velikonoce), přepínatelné v Nastavení.
- **Reklamy** jsou jen mock (falešný dialog s odpočtem), žádné SDK.
- **Zvuk**: numpy, 22 050 Hz mono; bez numpy nebo bez audio zařízení hra běží potichu.
- **„Vibrace“** = trhnutí kamery (místo pro budoucí haptiku).
- **CLI**: `--quick` rovnou spustí rychlý run na Farmě, `--debug` zapne F3 overlay a debug klávesy.
- **Ovládání a drobnosti (4. 10. 2026, po zpětné vazbě)**:
  - Pevný joystick (potvrzeno zadavatelem): vznikne, kam hráč ťukne – kdekoli na obrazovce (dřív jen spodní 2/3),
    střed se za prstem neposouvá (dřív „plovoucí“), páčka se zastaví na okraji a jde se plnou rychlostí, po puštění
    zmizí. Tlačítka pauzy a ultimátky mají přednost.
  - Ultimátka jde zmáčknout i během pohybu: na telefonu druhým prstem (zpracovává se `FINGERDOWN`, SDL převádí na myš
    jen první prst), na PC pravým tlačítkem myši. Joystick dál ovládá jen jeden prst.
  - Zobák-laser (i Oči sokola) střílí ze špičky zobáku podle spritu a směru zvířete (`PLAYER_BEAK`, `Player.beak()`),
    u klouzajícího tučňáka z ležícího spritu; míří ze zobáku na cíl.
  - Husí štípanec (husa) zaútočí, jen když je nějaká liška opravdu na dosah (dosah + poloměr lišky = maximální dosah)
    a míří na nejbližší takovou – každý útok zasáhne; dřív stačilo „dosah + 30 px“ a husa štípala do vzduchu.
  - Přejmenování: Vejce granát → Vaječný granát, Zobák-šleh → Husí štípanec, Ocas-vějíř → Páví vějíř (id beze změny,
    uložené hry nedotčené).
- **Ultimátky (v1.2.0)** – rozhodnuto samostatně během autonomní práce:
  - Systém je datově řízený: tabulka `data/ultimates.py` + registr funkcí `@effect` ve `world/ultimates.py`; `Run.crow()` si nechala jméno kvůli botovi, testům a scéně, ale jen odečte nabití a zavolá ultimátku zvířete.
  - Původní KIKIRIKÍ zůstává beze změny jako Královské KIKIRIKÍ Kohouta Elvise a Elvisova pasivka „2× rychlejší nabíjení“ zůstává (je to teď jeho pasivka pro ultimátku), s evolucí Rockový koncert přidá slabší ozvěnu.
  - Každá ultimátka má vlastní cenu nabití (65–75 zabití) a nejkratší dobu nabití (6–14 s): silnější a delší efekty se nabíjejí déle.
  - Run začíná s ultimátkou nabitou na 50 %, aby ji hráč poznal už v první minutě (první použití ~30 s místo ~45 s v rychlém módu).
  - Bossové: odhoz, omráčení, mráz, okouzlení ani unášení na ně neplatí, poškození ano, ale jedna aktivace ubere nejvýš 4 % max. HP bosse a fázové zámky Kohouta platí dál.
  - Každá ultimátka přebije vítr Zombie Kohouta stejně jako dřív kokrhání (beze změny souboje).
  - Pasivky: Megafon zvětšuje dosah, Zlatá skořápka poškození, Budík zkracuje nejkratší dobu nabití (−8 %/úr., max. −40 %, popis Budíku doplněn), Brýle a kritické zásahy krocana platí pro jeho brky.
  - Budík ani pasivka zvířete nestáhnou rozestup použití pod `cd_floor` ultimátky (delší než její omezení davu) – Elvis s Budíkem dřív kokrhal každých 1,8 s a lišky stály trvale omráčené, teď zůstává na původních 3 s (B-91).
  - Evoluce startovní zbraně zvířete ultimátku posílí (víc vajec, širší vlna, delší řádění, salva navíc, ozvěna, větší okouzlení, delší bouře).
  - Oživení po reklamě spustí ultimátku zvířete zdarma (dřív kokrhání), zabití ultimátkou ji dál nabíjejí jako dřív (řetězení brzdí nejkratší doba nabití).
  - Brky krocana škálují s aktuálním HP lišek (80 % HP lišky na brk), aby ultimátka nezastarala; ostatní mají pevnou část + podíl max. HP jako původní kokrhání.
  - Slepice: zabití zlatým vejcem dá 2× XP (prvních 5 vajec míří na nejbližší lišky kvůli okamžité úlevě).
  - Kachna: vlna jde ve směru posledního pohybu (na telefonu se palec z joysticku zvedne, směr zůstane) a kolem kachny navíc stříkne rozstřik, aby měla i okamžitou úlevu.
  - Husa: po nesmrtelnosti závěrečné „KEJHHH“ lišky odhodí a omráčí – bez něj zůstávala pomalá husa po 3 s v obklíčení, ze kterého ji staré kokrhání vyprostilo omráčením na 2,2 s.
  - Páv: okouzlené lišky útočí i na bosse (strop 4 %), auto-aim a bot je ignorují, jejich zabití se počítají hráči.
  - Výběr zvířete ukazuje ultimátku (ikona + název v panelu) a pod panelem místo vtipného popisu zvířete její popis – plánování runu má přednost a jinde se nevešel.
  - Výzva „Kokrhací mistr“ počítá použití ultimátky (text upraven), pauza ukazuje ultimátku a počet použití.
  - Ladicí nástroje: místo kopírování harnessu ze skillu (projekt už má F3 overlay a debug klávesy) přibyly scénáře `--scenario`, klávesy F4/F2 a `tools/ult_lab.py`; scénář neukládá postup (B-86).
  - Velký banner s názvem ultimátky jen při prvním použití v runu, potom malý název u zvířete nejvýš jednou za 20 s; výkřik zůstává u každého použití (B-94).
  - Okouzlené lišky bez cíle drží stráž ~150 px kolem Divy a po konci okouzlení jsou 0,8 s zmatené, aby ultimátka nekončila kousnutím (B-93).
  - Explodující lišky zabité ultimátkou (i řetězem jejich výbuchů) vybuchnou jen do lišek – hráč nemá dostat zásah od vlastní ultimátky (B-96).
  - Nad tlačítkem ultimátky je jméno zvířete, pod ním název ultimátky – zadání chtělo „ikonu a název zvířete“ (B-98).
  - Zemní vrstva ultimátek se kreslí pod telegrafy útoků bossů (čitelnost má přednost, B-92).

## Stav – hotovo

Všech 7 bodů „Definice hotovo“ je splněno:

1. `python main.py` startuje do menu za ~0,7 s bez chyby (ověřeno i v okně, 60 FPS).
2. Rychlý i plný mód jdou odehrát od začátku do konce včetně Zombie Kohouta, výhry i prohry
   (bot simulace + test `bosses_win_and_lose`, `final_boss_variants_all_biomes`, `full_game_flow_through_scenes`).
3. 7 zvířat, 16 zbraní (10 základních + 6 startovních) × 8 úrovní, 16 evolucí, 11 pasivek, 7 běžných + 3 elitní
   + 4 biomoví + 2 vyvolávaní nepřátelé, 5 bossů (finální ve 3 fázích, 5 biomových variant), 5 biomů.
4. Meta-progrese (Hnízdo), save.json (atomicky, odolný proti poškození), odemykání zvířat/map/obtížností,
   sbírka s odměnami, 18 výzev, denní výzva + žebříček, týdenní boss rush, denní login, obchod se skiny a truhlami,
   sezónní témata, mock reklamy, sdílení PNG.
5. `tests/smoke_test.py` – 16 headless testů (tisíce framů, všechny scény a tlačítka, všechna zvířata × biomy,
   všechny zbraně a evoluce, bossové, save/load, crash obrazovka) – vše prochází. `tools/simulate.py` projede
   celé runy botem.
6. Výkon: zátěž 400 nepřátel + ~300 projektilů + ~500 částic = 4–5 ms/frame (logika + render), cProfile
   hotspoty: kolize projektilů, `fblits`, AI smyčka – vše hluboko pod 16,6 ms.
7. README.md a PLAN.md aktuální.

### Balanc (bot `tools/simulate.py`, Farma)
- Plný mód, čerstvá postava bez Hnízda: ~50 % výher (4/8 v poslední dávce, všech 7 zvířat dohraje do konce);
  s Hnízdem na úr. 2 výrazně víc (6/7). Finální boss trvá 50–180 s, minimum HP vítězných botů 5–75 %.
- Rychlý mód, čerstvá postava (po 4. kole): 40/56 výher, každé zvíře 5–7 z 8. Rozhoduje souboj se Zombie
  Kohoutem (22–150 s) – při jeho příletu se slepici doplní zdraví i kokrhání.
- Boss rush (10 bonusových level-upů): 13/21 výher, každé zvíře aspoň jednou; Špión 19–63 s.
- Těžší biomy (Les → Továrna) jsou výrazně náročnější a počítají s hráčem, který už má meta-vylepšení.
- Nejsilnější zdroje poškození (měřeno `dmg_log`): kontakt s nepřáteli, rázové vlny bosse, projektily.
  Exploze lišek a plot arény byly zmírněny (delší rozbuška, odraz od plotu).
- Husa (melee) je s botem nejslabší – bot kituje, člověk se k liškám přiblíží.
- Data pro balanc zbraní: `tools/dps_bench.py` (single-target vs. AoE DPS pro L1/L4/L8/EVO).

## Zjednodušení
- Zóny (louže, led, pásy) ovlivňují jen hráče; nepřátelé je ignorují (výkon, čitelnost).
- Pathfinding nepřátel je přímý „chase“ s vytlačováním z překážek – žádné A*.
- Lokální žebříček denní výzvy kombinuje vlastní výsledky s deterministicky generovanými „sousedy“ (offline hra).
- Hudba je generovaná smyčka (4 synchronní vrstvy) – žádné skladby s formou sloka/refrén.
- Startovní zbraně zvířat jsou exkluzivní pro dané zvíře (ve sbírce se objeví po zahrání za něj).
- „Vibrace“ jsou simulované trhnutím kamery; haptika na mobilu se napojí v `Camera.vibrate`.

## Co by následovalo
- Port na Android: pygame-ce přes `pygame-ce` + python-for-android/Buildozer (vstup už je dotykový,
  rozlišení portrait, letterbox), případně přepis do Godotu – data v `game/data/` jsou přenositelná 1:1.
- Napojení skutečného share sheetu, haptiky a (volitelně) reklamního SDK místo mocků.
- Online žebříček denní výzvy (seed je už deterministický ze data).
- Další obsah: více evolucí pro kombinace dvou pasivek, unikátní finální bossové pro biomy, další biomy.
- Uživatelské testování balancu (bot je dobrý proxy, ale lidé hrají jinak – hlavně husa jako melee postava).

## Mobilní verze (Android)
- Build: `buildozer.spec` + GitHub Actions (`.github/workflows/android.yml`) → APK v Releases při každém pushnutí.
  Před buildem běží smoke testy proti pygame-ce i proti pygame 2.1.0 (verze, kterou má python-for-android).
- Kód je kompatibilní s pygame-ce (PC) i klasickým pygame 2.1 (Android): `device.fblits` místo `Surface.fblits`,
  noční osvětlení přes průhlednou vrstvu místo `BLEND_MULT` (na klasickém pygame 10× rychlejší).
- Na telefonu: `FULLSCREEN` v nativním rozlišení, 540×960 škáluje hra sama (pygame.SCALED v pygame 2.1
  na Androidu nefungoval), nižší stropy entit,
  save v `ANDROID_PRIVATE` (přežije aktualizace), pauza + uložení při odchodu do pozadí, tlačítko Zpět = Esc,
  vibrace a sdílení přes pyjnius, displej nezhasíná.
- Rozhodnutí: ovládání je jednoprsté (podle zadání) – joystick i tlačítko ultimátky jedním palcem; jediná výjimka
  (4. 10. 2026): druhý prst smí zmáčknout ultimátku nebo pauzu, zatímco první drží joystick (`FINGERDOWN`).
  Joystick je pevný: vznikne kdekoli, kam hráč ťukne, střed stojí, po puštění zmizí.
- Rozhodnutí: APK je podepsané stálým debug klíčem v repozitáři, aby šly aktualizace instalovat přes starou verzi.
  Pro Google Play by se použil release klíč uložený v GitHub Secrets.
- iOS: nativní build z pygame není reálně možný (pygame iOS nepodporuje, Apple vyžaduje App Store/TestFlight
  s placeným účtem a Macem). Cesta pro iOS = port do multiplatformního enginu (Godot) – data v `game/data/`
  jsou přenositelná.

## Opravy podle bug reportu (3. 10. 2026)
- B-01 trvalý třes: třes má strop podle zdroje (vlastní zbraně max. ~1 px, silné otřesy jen bossové a hazardy),
  „kick“ kamery má strop 14 px, výbuchy hráčových zbraní nevibrují. Bot, plný mód: snímky s posunem > 10 px
  z 22–31 % na ≤ 0,6 %.
- B-02 stroboskop: Zlatá bomba už nebliká, běžné záblesky max. 1× za 2 s a slabší, nový vypínač
  „Záblesky obrazovky“ v Nastavení. Záblesky za minutu ze 114–140 na ≤ 8.
- Vibrace: na telefonu min. 0,35 s rozestup.
- Prázdné level-upy: když už není co vylepšit, levelup se vyřeší sám (mince + 5 % zdraví) bez pauzy (později změněno: jen léčí 35 %, viz druhá vlna).
- Mobil: level-up ignoruje dotyky 0,6 s po otevření, Skip se potvrzuje druhým klepnutím,
  Restart a Vzdát se v pauze mají potvrzovací dialog.
- Stavy: mini-boss se při vzniku arény přenese dovnitř (dřív zmizel a zůstal v seznamu bossů –
  boss rush se pak zasekl), během vítězné animace se ruší dobíhající útoky a smrt ve stejném ticku
  jako výhra má přednost výhra, výsledek denní výzvy se zapisuje k datu výzvy (seed), ne k datu dohrání.

### Druhá vlna oprav (celý report B-01 – B-28)
- Výplňové level-upy jen léčí: když zbývá méně než 3 reálné volby, doplní se jediná karta „Kuřecí polévka“;
  když není co vybrat vůbec, levelup hru nepřeruší a jen vyléčí 35 % zdraví (B-04, B-24).
- B-05: haptika oddělená od trhnutí kamerou – vibruje jen zásah slepice a údery bossů (rozestup 0,35 s).
- B-06: bonusové levelupy (boss rush, rubber-banding) zvedají úroveň; rubber-banding jen po skutečné smrti.
- B-07/B-08/B-23: zprávy ve výsledcích po stránkách, bedna s dynamickou výškou řádků a menším písmem místo uříznutí.
- B-09: neviditelný boss není cílem auto-aimu a projektily jím proletí.
- B-11: klouzání tučňáka podle směru jízdy, průhlednost až po rotaci. B-26: částice v logice, animace podle času.
- B-13: telegraf před kokrháním (nádech 0,8 s), vějířem vajec i šipkami Špióna; vítr 115 px/s s náběhem –
  pomalejší než nejpomalejší zvíře, takže se mu dá ujít.
- B-14: po denní výzvě a u zamčeného zvířete/mapy vede „Znovu“/Restart na výběr.
- B-15: kontaktní poškození tučňáka škáluje s HP nepřítele. B-16: boss rush začíná na 1,5. efektivní minutě
  a první boss přijde v 0:15. B-19: vlci Alfy přibíhají zpoza okraje, objevení na obrazovce má efekt.
- B-20: na ledu se nohy hýbou jen při chůzi, otočení podle vstupu. B-21: v dešti padá správné zvíře biomu.
- B-22: kuřata se při vylepšení neteleportují. B-25: PC – ztráta fokusu / minimalizace = pauza.
- B-27: denní odměna se kontroluje při každém vstupu do menu, posun hodin zpět nic nedá.
- B-28: sezónní skin jen v reálné sezóně podle data (vynucená sezóna mění jen vzhled světa).

### Třetí vlna – UI a design (B-29 – B-48)
- Zvýraznění (rámečky výběru, pulzování) se kreslí AŽ po panelu a nafukuje se o sudé hodnoty (B-29).
- Informační texty v měřítku 2 (podtituly tlačítek, karty, výběr zvířete, výzvy, Hnízdo, pauza, HUD); měřítko 1
  zůstalo jen pro dekorace a technické detaily (B-30).
- Tučňák klouže jako ležící sprite otočený přesně o 90° (B-31); hráč vždy nad nepřáteli, překážky před ním
  poloprůhledně (B-32); na dotyku žádný „lepivý“ hover (B-33).
- Tmavší výplně tlačítek + text s obrysem; vybraná možnost = rámeček + fajfka, oranžová jen pro akce (B-34, B-36).
- Výběr zvířete přeskládaný: nadpisy Mapa / Mód / Obtížnost, tečky nad tlačítkem Koupit (B-35, B-42).
- Karty bez přestřelení (B-37), bedna s řádky podle obsahu a paprsky přes celou obrazovku (B-38, B-39),
  Obchod a Hnízdo bez přetékání (B-40, B-41), nezlomitelné „40 %“ a „1 500“ (B-43).
- Jednotné nadpisy, šipky vpřed/zpět, centrovaný řádek měn, okraj 16 px (B-44); dialogy podle obsahu, Enter/Esc/
  Zpět nikdy nespustí nevratnou akci (B-45); pauza bez prosvítajícího HUD (B-46); toasty podle scény (B-47);
  verze v menu odpovídá buildu (B-48).

### Čtvrtá vlna – balanc módů a dotažení (B-49 – B-66)
- B-49: strop pickupů nesmaže XP – nové zrno se sloučí se zrnem u místa zabití, jinak se nejvzdálenější staré
  zrno „přestěhuje“ k hráči i se svou hodnotou. B-50: aréna stáhne bedny a zrní dovnitř plotu, bedny sebrané po
  porážce bosse se ve výsledcích převedou na mince. B-66: čas a skóre se zastaví v okamžiku porážky bosse.
- B-51: nejvýš jedno přerušení za 8 s herního času (`PAUSE_GAP`); level-upy, které mezitím přijdou, se ukážou
  za sebou v jedné pauze a v HUD svítí „+N“ u úrovně. Rychlý mód má XP ×1,6 (dřív 1,8) a vzácnější karty
  (štěstí ×1,3). Výsledek: 6–7 pauz za minutu místo 8–11 (snížení samotného XP skoro nepomáhá, úroveň roste
  zhruba s odmocninou nasbíraného XP).
- B-52: Kachna 85 % HP a +10 % rychlost, Páv potřebuje jen +10 % XP, Ocas-vějíř zesílen (L8 na jeden cíl
  52 → 154 DPS, vějíř zůstává 140°, plný kruh až v evoluci).
- B-53: boss rush – 10 bonusových level-upů, hustota běžných lišek ×0,55 (dřív 0,35), každý poražený boss
  vysype zlatá vejce zhruba na 4 úrovně. Popis módu zmiňuje XP z bossů a bedny z elit.
- B-54: finální boss rychlého módu má 15 % HP plné verze (dřív 10 %), souboj trvá 22–150 s a fáze jsou vidět.
- B-55: od úrovně 30 roste potřeba XP o 12 % za úroveň navíc; build se v plném módu dokončí zhruba v 9:00–10:20
  a automatických léčení je 1–6 místo 16–24. Výplňové level-upy dál jen léčí.
- B-56: banner a bonus „na rozjezd“ jen v rychlém a plném módu. B-57: výhra v boss rushi nic neodemyká.
- B-58: Obři jsou opravdu větší (sprite ×4/3 – art pixel ze 3 na 4 px, kolize odpovídá). B-59: Šťastný den
  zvedne raritu každé karty o stupeň (žádné běžné karty). B-60: pasivka Kachny platí jen v louži a na ledu;
  v závěji a na oleji je Kachna pomalejší jako ostatní.
- B-61: Špión se teleportuje jen na volné místo uvnitř arény, Špión a Králík se o překážky zastaví; medvěd,
  Alfa a Kohout je dál drtí (záměr – velcí bossové se nezaseknou). B-62: zpomalení a zmražení bosse odtikává
  i když boss stojí. B-63: sova, Alfa i déšť ve fázi 2 respektují `MAX_ENEMIES` (telefon 320).
- B-64: dialog oživení a nápověda podle zvířete a rodu („Krocan Rambo padl…“, „střílí sám“), podtitul výhry
  podle mapy, každá varianta finálního bosse má vlastní hlášku fáze 2. B-65: Vyřadit vymění jen vyřazenou kartu.

### Pátá vlna – po polish passu (B-67 – B-80)
- B-67: částice záře a kroužků (GLOW/POP) vracejí slot do poolu – dřív se pool vyčerpal za ~1:45 a pak se
  nevykreslila žádná částice. B-68: záblesk obrazovky dobíhá v každém stavu (vítězná animace už není bílá).
  B-69: boss a elita při zásahu bliknou nejvýš 1× za 0,35 s (finální boss bílý ~18 % času místo 63–92 %).
- B-70: finální boss přiletí 200 px vedle hráče (dřív pod ukazatelem zdraví v HUD); bubliny se drží pod
  pásem HUD, a když nad hlavou není místo, ukážou se pod nohama mluvčího.
- B-71: Skip v level-upu je na X (S je pohyb dolů); zámek 0,6 s platí i pro klávesy; mezerník bednu jen otevře.
- B-72: elita za plotem arény zmizí, ale její bedna spadne dovnitř; neporažené elity při výhře odevzdají bednu.
- B-73: kokrhání se nabije nejdřív za 6 s (Kohout 3 s) – dřív v pozdní hře každých 1,4 s.
- B-74: víc čekajících level-upů (nejvýš 3) se spojí do jedné obrazovky; karta sečte hody rarity za každý
  spojený level a dostane +1 úroveň navíc. Startovní bonus (boss rush) se vybírá dál kartu po kartě.
  Rychlý mód: nejdelší řetěz 5 obrazovek místo 13, ~22 obrazovek za run místo ~27.
- B-75: čekající bedna má v HUD ikonku (×N). B-76: finální boss říká jen hlášky své fáze.
- B-77: pozadí menu plyne bez skoku (svislá perioda vzoru 2 dlaždice). B-78: texty (vtipy po prohře, Sbírka,
  sezónní skin „zdarma v sezóně“). B-79: pozadí výsledků se generuje za ~3 ms místo ~65 ms (pixelově shodné).
  B-80: README/PLAN a popisky módů („boss ve 2:30“ / „boss v 10:00“).
- Balanc po vlně (bot, Farma, Normal, bez Hnízda): rychlý mód 81/112 výher (72 %), plný 9/14, boss rush 13/21.

## v1.1.0 – Nekonečná noc (3. 10. 2026)
- Nový mód `endless`, odemyká ho výzva „Celá noc“ (výhra Plného módu). 1. noc = Plný mód beze změny
  (bossové 2/4/6/8/10 min, elity, formace). Porážka Kohouta není výhra: `Director.next_night()` naplánuje od té chvíle
  další kolo (`waves.ENDLESS_CYCLE`: bossové po 60 s, Kohout za 5:30, elity `ENDLESS_ELITES`), banner „NOC N“,
  boss bedna, zpět hudba biomu. Formace se po 9:30 opakují s posunem 6 min; ty, které připadnou na souboj s Kohoutem,
  propadnou.
- Škálování jen v endless: HP mini-bossů ×3 a Kohouta ×2 za každou další noc (`endless_boss_hp`), HP lišek po 10. minutě
  lineárně (`endless_hp_mult`), Kohout dalších nocí zuří po 150 s (Plný mód 3 min), od 2. noci další boss až po porážce
  předchozího, osvětlení se zastaví před svítáním (`ENDLESS_DARK`). (Hodnoty po opravách B-81 – B-85, viz níže.)
- Noční síla: level-up bez voleb (hotový build) kromě léčení přidá +4 % poškození (`Run.night_power`), bez pauzy.
- Rekord `records.best_time_endless` (nový klíč se doplní do starých savů), HUD: čas nahoru + „Noc N · rekord“,
  výsledky „REKORD!“. Výzva „Věčná tma“ (15 min). Odměny: každý poražený Kohout se počítá (250 vajec, 2 zlatá).
- Nekonečná noc neodemyká mapy ani obtížnosti (porážka Kohouta odemkne Kohouta Elvise jako jinde).
- Balanc (bot, Farma, Normal): slepice bez Hnízda přežije medián 17:51 (6 seedů, 10:47–29:40), Hnízdo 3 → 19:47;
  kachna 18:57, husa 13:42, krocan (Les, Hnízdo 2) 19:06. Konec obvykle přijde při Kohoutovi 2. noci.
- Ostatní módy jsou bit po bitu stejné (7 seedovaných runů quick/full/bossrush/daily starý vs. nový kód).
- Zjištěno: `world/allies.py:132` používá `id(self)` (adresa v paměti) pro bloudění spřátelených lišek, takže runy se
  stejným seedem nejsou mezi procesy totožné (týká se i denní výzvy). Neopraveno – mimo rozsah tohoto updatu.

### Opravy Nekonečné noci (B-81 – B-85, 4. 10. 2026)
- B-81: Kohout 2. noci byl zeď (480 000 HP, zuření po 2 min, 0/13 poražen) → HP ×2 za noc a zuření po 150 s.
- B-82: bossové 2. noci chodili po 60 s, ale padali za 40–170 s (až 3 naráz) → od 2. noci další boss až po porážce
  předchozího + 20 s oddechu (`Director.boss_down`), HP mini-bossů ×3 za noc.
- B-83: HUD v endless ukazuje čas, noc a rekord i během Kohouta (dřív jen „BOSS!“, přitom runy končí právě tam).
- B-84: HP lišek po 10. minutě lineárně místo kubické křivky s přídavkem (20. min 1 530 HP místo 3 270, 30. min 2 880
  místo 17 000), od 3. noci navíc ×1,5 za noc (`ENDLESS_LATE_NIGHT_HP`, ať silný build nevydrží nekonečně),
  noční síla +4 % (dřív +2 %).
- B-85: rekord pro mapu a obtížnost (`records.endless_best`, celkový `best_time_endless` zůstává), „první rekord“ v HUD,
  banner „NOVÝ REKORD!“ a fanfára v okamžiku překonání, sdílení s titulkem „NOVÝ REKORD!“. Oživení přes reklamu se do
  rekordu dál počítá (rozhodnutí updatu v1.1.0).
- Balanc (bot, Farma, Normal, bez Hnízda, 7 zvířat × 4 seedy): medián 20,0 min, rozsah 3,7–33,1 min, 3. noc 8/28
  (dřív 0/18), Kohout 2. noci poražen 8/21 (dřív 0/13), nejvýš 1 boss naráz od 2. noci (dřív 3). Ostatní módy znak
  po znaku shodné se zálohou před v1.1.0.

## v1.2.0 – Ultimátky zvířat (4. 10. 2026)

Každé zvíře má místo společného „KIKIRIKÍ“ vlastní ultimátku (tlačítko vpravo dole / mezerník). Systém je datově
řízený: `game/data/ultimates.py` (tabulka `ULTIMATES`: název, popis, výkřik, ikona, barva, zvuk, nabíjení, parametry)
+ `game/world/ultimates.py` (registr funkcí efektů `@effect("id")`, zdroj poškození jedné aktivace, běžící efekty).
`Run.crow()` jen odečte nabití a zavolá `ultimates.activate(run, ult)`.

### Ověřená fakta (kód vs. zadání)
- 7 zvířat: `hen, duck, goose, turkey, rooster, peacock, penguin` (`data/characters.py`) – sedí.
- `Run.crow()` byla na řádku 912 – sedí. Nabíjení: `Run.kill_enemy` přičte `crow_mult / 70` za každé zabití,
  strop nabití `crow_cap` po použití roste od 0 rychlostí `crow_mult / 6 s` (B-73) – nejdřív za 6 s.
- Elvisova pasivka = `CharDef.crow_mult = 2.0`: násobí zisk za zabití **i** růst stropu (35 zabití, nejdřív 3 s) – sedí.
- Navíc oproti zadání (zjištěno v kódu): kokrhání dává 1 s nesmrtelnosti, ničí nepřátelské projektily, přeruší vítr
  Zombie Kohouta, příchod finálního bosse ho nabije naplno, oživení po reklamě spustí kokrhání zdarma, výzva
  „Kokrhací mistr“ počítá použití (`crows_used`) a bot ho mačká při HP < 45 %, davu > 18 nebo u bosse.

### Mechaniky (konečná čísla po vyvážení; měření ve FEATURES.md)
| Zvíře | Ultimátka | Mechanika | Hlavní parametry (síla 1, dosah 1) | Rizika a jak jsou ošetřena |
|---|---|---|---|---|
| Slepice Božena | Zlatá nadílka | 14 zlatých vajec obloukem (prvních 5 na nejbližší lišky), výbuch omráčí, zabité lišky dají 2× XP | 70 zabití / 8 s, výbuch r 58, 30 + 35 % HP, omráčí 0,5 s | XP ekonomika (bonus jen z vajec), zpožděný dopad → 5 vajec míří na nejbližší |
| Kachna Kvak | Velká voda | rozstřik kolem kachny + vlna ve směru pohybu unáší lišky, promočené zpomalí, na konci náraz | 65 zabití / 8 s, vlna 560 × 420, 25 + 40 % HP, zpomalení 60 % na 4 s | lišky v překážkách (vytlačí je AI), dotazy jen kolem čela vlny |
| Husa Gerta | Husí řádění | 3 s nesmrtelná, +35 % rychlost, kejhnutí každých 0,6 s, co srazí, zraní; na konci „KEJHHH“ odhodí a omráčí | 75 zabití / 14 s, r 150 (závěr 230), 22 + 12 % HP za kejhnutí | uptime nesmrtelnosti → nejdelší nejkratší doba nabití |
| Krocan Rambo | Operace Díkůvzdání | 4 salvy po 20 brcích do všech stran, průraz 2, kritické zásahy platí | 70 zabití / 7 s, brk = 80 % HP lišky dané minuty, dolet 650 | strop projektilů (salva max. ~80, ověřeno 0 zahozených) |
| Kohout Elvis | Královské KIKIRIKÍ | původní kokrhání beze změny (+ ozvěna s Rockovým koncertem) | 70 zabití / 6 s (Elvis 2× rychleji), r 290, 40 + 25 % HP, odhoz 560, omráčí 2,2 s | regresní reference |
| Páv Diva | Božská krása | duhová vlna okouzlí lišky na 5 s: útočí na nejbližší lišky i bosse, Divu nechají být, bez cíle drží stráž ~150 px, po konci 0,8 s zmatené | 75 zabití / 12 s, r 280, max. 50 lišek, úder 2× poškození lišky / 12 % HP cíle | výkon (hledání cíle 1× za 0,4 s), auto-aim je ignoruje |
| Tajný tučňák | Doba ledová | 3 s ledová bouře kolem tučňáka: mrazí, točí lišky dokola, na konci je roztříští | 75 zabití / 12 s, r 215, 6 + 1,5 % HP za 0,25 s, konec 20 + 12 % HP | trvalá kontrola davu → kratší bouře, elity mrznou kratší dobu |

### Společná pravidla
- Bossové: odhoz, omráčení, zmražení, okouzlení a unášení se na ně nevztahují (jen zpomalení tučňáka, kratší).
  Poškození zůstává, ale jedna aktivace bossovi ubere nejvýš `ULT_BOSS_CAP` (4 %) max. HP – souboj se nedá
  přeskočit. Fázové zámky Zombie Kohouta (`modify_damage`) platí dál.
- Každá ultimátka přeruší vítr Zombie Kohouta (jako dosud kokrhání).
- Škálování: Megafon (dosah) zvětšuje poloměry, Zlatá skořápka (síla) poškození, Budík zkracuje nejkratší dobu
  nabití (−8 %/úr., nejvýš −40 %, nikdy pod `cd_floor` ultimátky), Brýle průraz a rychlost brků krocana, kritické zásahy krocana platí.
  Evoluce startovní zbraně zvířete ultimátku posílí (víc vajec, širší vlna, delší řádění, salva navíc, druhá sloka,
  větší dosah okouzlení, delší bouře).
- Pauza, level-up a bedna efekty zastaví (běží v `Run.update` jen ve stavu `playing`), smrt a vítězství je ukončí,
  restart = nový `Run`. Oživení po reklamě spustí ultimátku zvířete zdarma (dřív kokrhání).
- Zpětná vazba: název ultimátky (poprvé banner, pak malý nápis nejvýš 1× za 20 s), výkřik nad zvířetem, vlastní zvuk (syntéza), vrstvený efekt (záře,
  kruhy, částice – nové druhy srdíčko, vločka, kapka, nota), třes jen přes `Camera.shake` se stropem, krátké
  zpomalení přes stávající `slowmo` u velkých ultimátek.

### Rizika a mitigace
- **Balanc**: jedna ultimátka může přebít ostatní → měřit nástrojem `tools/ult_lab.py` (stejné zvíře, stejný seed,
  jiná ultimátka; poškození, zabití, kontrola davu, přijaté poškození, boss), botem v rychlém i plném módu.
- **Výkon** (400 nepřátel + aktivní ultimátka): dotazy přes `SpatialGrid`, stropy (okouzlení max. 60, projektily přes
  pool), žádné nové Surface v `Run`; měřit `ult_lab.py perf`.
- **Determinismus**: herní náhoda ultimátek jen z `run.rng`, vizuál z `particles.rng`.
- **Save**: žádný nový klíč není potřeba; starý save se musí načíst beze změny.
