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
  core/  input.py          plovoucí joystick + klávesnice, mapování okno → logické souřadnice
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
  data/  characters.py weapons.py passives.py enemies.py bosses.py biomes.py waves.py meta.py
                           vše datově řízené (dicty/dataclassy) – obsah se přidává jen sem
  world/ run.py            Run = celá simulace runu (bez renderu → headless bot/sim)
         entities.py       lehké entity se __slots__ (Enemy, Proj, EProj, Area, Beam, Ring, Telegraph, Pickup…)
         player.py         pohyb, statistiky, squash & stretch, klouzání tučňáka
         enemies.py        jediná rychlá smyčka AI nepřátel (pohyb, separace, překážky, kontakt)
         bosses.py         stavové automaty 5 bossů + biomové varianty finálního Zombie Kohouta
         allies.py         kuřata, spřátelené lišky, hnízda
         director.py       spawn director (křivka, prstence, hordy, obklíčení, elity, bossové)
         mapgen.py         nekonečná mapa z chunků (deterministický seed), překážky, zóny, hazardy
         render.py         RunRenderer: y-sorting, stíny, fblits batch, overlaye
  weapons/ base.py kinds.py  chování zbraní (16 druhů + evoluce přes parametry)
  ui/    widgets.py hud.py overlays.py
  scenes/ menu, select, nest, collection, challenges, settings, shop, daily, game, error
tools/ simulate.py         bot projede celý run a vypíše statistiky (headless)
       profile_run.py      cProfile zátěžové scény (400 nepřátel + 300 projektilů)
       preview_sprites.py  contact sheet všech spritů do PNG (kontrola grafiky)
       dps_bench.py        DPS všech zbraní (single target / AoE) pro balanc
       screenshots.py      headless screenshoty všech scén
tests/smoke_test.py        headless smoke testy všech systémů
```

### Datové struktury (klíčové)
- `RunConfig(character, biome, mode, difficulty, seed, modifiers)` – mode: `quick | full | daily | bossrush`.
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
- **Tajný tučňák**: zbraň „Mražená ryba“ (bumerang, který zmrazuje), pasivka „Klouzání po břiše“ (při pohybu jedním směrem zrychluje až o 60 % a při plné rychlosti zraňuje, čím projede), slabina setrvačnost. Odemčení: 10× klepnout na logo v menu.
- **Páv Diva**: odemčení splněním výzvy „Tisíc lišek“. „Drahé upgrady“ = o 25 % víc XP na úroveň. Hypnóza = zmatený nepřítel bloudí a dostává +25 % damage.
- **Kohout Elvis**: odemčení porážkou finálního bosse (libovolný mód).
- **Obtížnosti**: Hard se odemkne výhrou na Normal, Nightmare výhrou na Hard. Násobí HP/damage/spawn i odměny.
- **Mapy**: Farma od začátku; další se odemknou výhrou na předchozí mapě nebo koupí za vejce.
- **Rubber-banding**: smrt před 1:30 → další run začíná s bonusem XP (1 úroveň zdarma).
- **Mince** v runu (skip, bedny, Zlatá bomba) se na konci převedou na vejce 1:1.
- **Zlatá vejce**: bossové, výzvy, denní série, 100% sbírky. **Žetony**: denní výzva + denní login → truhly v Obchodě.
- **Denní výzva**: seed = datum, jedna šance denně, pevná kombinace zvíře/mapa/modifikátor; lokální žebříček top 10 = vlastní výsledky + deterministicky generovaní „sousedé“ z vesnice (offline hra nemá server).
- **Týdenní boss rush**: všichni bossové za sebou, start s 10 level-upy zdarma (bossové sypou XP), odměna jednou za ISO týden.
- **Sezónní témata**: automaticky podle data (říjen = Halloween, prosinec = Vánoce, březen–duben = Velikonoce), přepínatelné v Nastavení.
- **Reklamy** jsou jen mock (falešný dialog s odpočtem), žádné SDK.
- **Zvuk**: numpy, 22 050 Hz mono; bez numpy nebo bez audio zařízení hra běží potichu.
- **„Vibrace“** = trhnutí kamery (místo pro budoucí haptiku).
- **CLI**: `--quick` rovnou spustí rychlý run na Farmě, `--debug` zapne F3 overlay a debug klávesy.

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
- Na telefonu: `SCALED | FULLSCREEN` (škálování dělá GPU, dotyky se mapují automaticky), nižší stropy entit,
  save v `ANDROID_PRIVATE` (přežije aktualizace), pauza + uložení při odchodu do pozadí, tlačítko Zpět = Esc,
  vibrace a sdílení přes pyjnius, displej nezhasíná.
- Rozhodnutí: ovládání zůstává jednoprsté (podle zadání) – joystick i tlačítko kokrhání jedním palcem,
  multitouch se nepoužívá (méně rizik s mapováním dotyků mezi verzemi SDL).
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
- Prázdné level-upy: když už není co vylepšit, levelup se vyřeší sám (mince + 5 % zdraví) bez pauzy.
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
