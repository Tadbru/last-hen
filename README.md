# LAST CHICKEN 🐔

Jsi poslední slepice na farmě, kterou přepadla armáda zombie lišek. Pohybuješ se, slepice střílí sama.
Přežij do svítání a poraz Zombie Kohouta. Auto-shooter roguelite (survivors-like) pro mobil na výšku,
vyvíjený a hratelný na PC. Veškerá grafika, zvuky i hudba se generují v kódu – žádné externí assety.

## Spuštění

```bash
pip install -r requirements.txt
python main.py
```

- Python 3.11+ a `pygame-ce`. `numpy` je volitelný (syntéza zvuku) – bez něj hra běží potichu.
- `python main.py --quick` – rovnou rychlý run na Farmě.
- `python main.py --debug` – debug overlay a debug klávesy.

## Hra na mobilu (Android) – přes GitHub

Repozitář obsahuje GitHub Actions workflow (`.github/workflows/android.yml`), který při každém pushnutí
automaticky otestuje hru a sestaví **Android aplikaci (APK)**. Hotové APK se objeví na stránce **Releases**.

1. Vytvoř na GitHubu nový repozitář (např. `last-chicken`) a nahraj do něj tuto složku:
   ```bash
   git remote add origin https://github.com/TVUJ-UCET/last-chicken.git
   git push -u origin main
   ```
2. Na GitHubu otevři záložku **Actions** a počkej na zelený build „Android APK“
   (první build trvá 40–60 minut, protože se stahuje Android SDK; další jsou rychlejší).
3. Na telefonu otevři `https://github.com/TVUJ-UCET/last-chicken/releases/latest`, klepni na **LastChicken.apk**,
   otevři stažený soubor a povol instalaci z tohoto zdroje. Ikona „Last Chicken“ se objeví mezi aplikacemi.
4. Novou verzi stačí nainstalovat přes starou – uložená hra zůstane (APK je podepsané stálým klíčem
   `app_assets/debug.keystore`).

Na telefonu: ovládání palcem (kam ťukneš, tam vznikne joystick; táhni), ultimátka velkým tlačítkem vpravo dole,
systémové tlačítko Zpět = pauza / návrat, při odchodu z aplikace se hra sama pozastaví a uloží.
Hra telefonem zavibruje při zásahu slepice a při úderech bossů (lze vypnout v Nastavení) a „Sdílet výsledek“ uloží obrázek do Galerie
a otevře systémové sdílení.

**iPhone / iOS:** Apple nedovoluje instalovat aplikace stažené z GitHubu – jen přes App Store / TestFlight,
což vyžaduje Mac, placený Apple Developer účet (99 USD/rok) a nástroje, které pygame na iOS nepodporují.
Pro iOS by bylo potřeba hru přepsat do multiplatformního enginu (např. Godot). Viz `PLAN.md`.

Ikona a úvodní obrazovka se generují skriptem `python tools/make_app_assets.py`.

## Ovládání

| Akce | PC | Mobil (do budoucna) |
|---|---|---|
| Pohyb | drž levé tlačítko myši kdekoli a táhni (pevný joystick: vznikne, kam klikneš, po puštění zmizí), nebo WASD / šipky | palec kdekoli na obrazovce, stejný pevný joystick |
| Útok | automaticky | automaticky |
| Ultimátka zvířete | mezerník, pravé tlačítko myši (i během tažení) nebo velké tlačítko vpravo dole (nabíjí se zabíjením, run začíná napůl nabitý) | tlačítko vpravo dole – i druhým prstem, zatímco první drží joystick |
| Pauza | Esc / P / tlačítko vpravo nahoře | tlačítko vpravo nahoře |
| Karty při levelupu | klepnutí / klávesy 1, 2, 3, R = rerol, X = skip, B = vyřadit | klepnutí |
| Debug | F3 overlay (FPS, entity, kolizní grid), F11 celá obrazovka | – |
| Debug (s `--debug` nebo po F3) | F5 další boss, F6 levelup, F7 zabij vše, F8 nesmrtelnost, F9 připrav evoluce, F10 +1 min, F4 nabij ultimátku, F2 ultimátka dalšího zvířete | – |

Tajemství: zkus 10× klepnout na logo v menu.

## Obsah

**Módy:** Rychlý (Zombie Kohout přilétá ve 2:30, celkem ~3–4 min), Plný (mini-bossové ve 2/4/6/8 min, finální boss v 10:00),
Nekonečná noc (odemkne výhra Plného módu: prvních 10 minut jako Plný mód, pak slunce nevyjde – další noci se silnějšími
bossy (další přijde až po porážce předchozího), lišky dál sílí, hraje se na rekord času pro každou mapu a obtížnost;
„noční síla“ +4 % poškození za level-up s hotovým buildem),
Denní výzva (seed z data, jeden pokus, zvíře dne, mapa a modifikátor pro všechny stejné, lokální žebříček), Týdenní boss rush (všech 5 bossů za sebou, zvíře podle volby).
Obtížnosti Normal / Hard / Nightmare.

**Zvířata (7 + 1 tajné):**

| Zvíře | Startovní zbraň | Pasivka | Slabina | Ultimátka | Odemčení |
|---|---|---|---|---|---|
| Slepice Božena | Vaječný granát | každých 20 s zlaté vejce plné XP | průměrná | Zlatá nadílka – déšť zlatých vajec, 2× XP | od začátku |
| Kachna Kvak | Vodní pistole (prorazí řadu) | ve vodě/na ledu +40 % rychlost | 85 % životů | Velká voda – vlna ve směru pohybu unáší lišky | 500 vajec |
| Husa Gerta | Husí štípanec | +30 % životů | pomalá | Husí řádění – 3 s nesmrtelná, kejhá a rozhazuje | 1 500 vajec |
| Krocan Rambo | Brokovnice z peří | kritické zásahy ×3 | střílí pomaleji | Operace Díkůvzdání – salvy brků do všech stran | 3 000 vajec |
| Kohout Elvis | Zvukové vlny | ultimátka se nabíjí 2× rychleji | křehký | Královské KIKIRIKÍ – původní kokrhání | poraz Zombie Kohouta |
| Páv Diva | Páví vějíř | hypnóza nepřátel | o 10 % víc XP na úroveň | Božská krása – okouzlené lišky bojují za ni | výzva „Tisíc lišek“ |
| Tajný tučňák | Mražená ryba (bumerang, mrazí) | Ledová krev – zmražené lišky od něj dostanou o 30 % víc | o 5 % pomalejší | Doba ledová – mrazivý vír kolem tučňáka | easter egg |
| Straka Klepna (tajná) | Lesklé cetky (odrážejí se z lišky na lišku) | Zlodějka – lišky jí občas upustí minci, +50 % dosah sběru | 90 % životů | Velká loupež – oslní lišky, okrade je o mince, stáhne zrní | celá sbírka (do té doby ve výběru skrytá) |

Podrobnosti ultimátek (čísla, nabíjení, měření) jsou v `FEATURES.md`.

**Zbraně (16, každá 8 úrovní) a evoluce (16):** Vaječný granát → Zlatá bomba, Kokrhací vlna → Apokalypsa,
Kuřecí armáda → Kohoutí legie, Peří-shuriken → Peřinová vichřice, Zobák-laser → Oči sokola, Hnízdo → Pevnost Kurník,
Kvaltík → Bouřková křídla, Slepičí smrad → Biologická zbraň, Vlčí vytí → Liščí kmotr, Koláč z vajec → Svatební dort,
Vodní pistole → Hasičská hadice, Husí štípanec → Husí hněv, Brokovnice z peří → Peří Gatling, Zvukové vlny → Rockový koncert,
Páví vějíř → Duhová show, Mražená ryba → Ledová tsunami. Evoluce = zbraň na úr. 8 + správná pasivka + bedna z elity/bosse.

**Pasivky (11, 5 úrovní):** Zdravé zrno, Rychlé nohy, Magnet na zrní, Zlatá skořápka, Budík, Peřová vesta,
Šťastné vejce, Megafon, Krmivo, Čtyřlístek, Brýle.

**Nepřátelé:** Liška Zombie, Rychlá liška, Obrněná liška (helma), Plivající liška, Explodující liška, Vlk Zombie, Netopýr;
elity Obří liška (bedna), Necromancer Sova (oživuje padlé), Medvěd Berserker (při 50 % zuří); biomové varianty
(Sněžná liška, Robo-liška, Městský potkan, Mlžný vlk), kostlivé lišky a zombie slepice.

**Bossové:** Pan Liška Špión (teleport za záda), Králík Zabiják (mrkvové salvy), Obří Zombie Medvěd (shockwave
a praskliny), Vlčí Alfa (smečky a nájezdy), ZOMBIE KOHOUT – 3 fáze v aréně s elektrickým plotem:
(1) kokrhání odfoukává ke kraji arény, (2) déšť zombie slepic, (3) obří rychlá forma. Každý biom má vlastní
variantu (Kohout Mlhoš, Kohout Kmotr, Kohout Yetti, Robokohout 3000). Všechny útoky jsou telegrafované.

**Biomy:** Farma (louže, ploty, stodoly, výbušné sudy), Temný les (koruny stromů, mlha, vlci), Opuštěné město
(auta, bloky domů, potkani), Hory (kluzký sníh, led, laviny), Továrna na kuřata (pásy, lisy, robo-lišky).

**Progrese:** levelup karty (běžná/vzácná/epická = +1/+2/+3 úrovně; víc čekajících level-upů se spojí do
jedné karty s úrovní navíc), rerol, skip za mince, vyřazení karty, bedny.
Hnízdo (6 trvalých vylepšení × 5 úrovní), Sbírka (64 položek; každá kompletní kategorie odhalí tajný skin, celá
sbírka tajné zvíře Straku), 19 výzev,
Obchod (skiny pirát/kovboj/astronaut/ninja za zlatá vejce, 5 tajných skinů za sbírku, truhly za žetony),
zlatá vejce jen za první porážku každého bosse a za výzvy, denní login se sérií,
sezónní témata (Halloween/Vánoce/Velikonoce podle data, přepínatelné v Nastavení), rubber-banding po brzké smrti.
Reklamy („Zdvojnásob vejce“, „Oživ se“) jsou jen mock s falešným dialogem. Po runu „Sdílet výsledek“ uloží PNG do `shares/`.

## Struktura projektu

```
main.py                 vstupní bod + CLI
game/app.py             okno, letterbox, fixní krok 60 Hz, přechody, crash handling
game/assets.py          registr fontu, spritů, ikon a zvuku
game/save.py            save.json (atomický zápis, oprava poškozeného souboru)
game/progression.py     karty, bedny, odměny, výzvy, sbírka, denní obsah
game/bot.py             bot pro simulace a testy
game/share.py           PNG pro sdílení
game/core/              joystick + klávesnice, kamera, spatial hash grid
game/gfx/               bitmapový font s diakritikou, pixel art, sprity, ikony, dlaždice, částice
game/audio/             numpy syntéza SFX a vrstvené hudby, správce zvuku
game/data/              datově řízený obsah: postavy, zbraně, pasivky, nepřátelé, bossové, biomy, vlny, meta
game/world/             simulace runu (run.py), hráč, AI nepřátel, bossové, spojenci, mapa, director, renderer,
                        ultimátky (ultimates.py logika, ult_render.py vykreslení)
game/weapons/           základ zbraně + 16 druhů chování
game/ui/                widgety, HUD, overlaye (levelup, bedna, pauza)
game/scenes/            menu, výběr, Hnízdo, Sbírka, Výzvy, Obchod, Denní, Nastavení, hra, výsledky, chyba
game/scenarios.py       ladicí scénáře (`python main.py --debug --scenario ult_duck`)
game/device.py          rozdíly PC / Android (úložiště, vibrace, sdílení, kompatibilita pygame 2.1)
tools/                  simulate.py, profile_run.py, dps_bench.py, screenshots.py, preview_sprites.py,
                        make_app_assets.py (ikona a presplash)
app_assets/             ikona, úvodní obrazovka a podpisový klíč pro Android
buildozer.spec          konfigurace Android buildu (python-for-android)
.github/workflows/      automatický test + build APK + zveřejnění v Releases
tests/smoke_test.py     headless smoke testy
```

Nový obsah se přidává hlavně do `game/data/` (zbraň = záznam ve `weapons.py`, případně nový druh chování v `weapons/kinds.py`;
ultimátka = řádek v `data/ultimates.py` + funkce `@effect("id")` ve `world/ultimates.py`).

## Nástroje a testy

```bash
python tests/smoke_test.py            # všechny smoke testy (headless), "fast" = zkrácená verze
python tools/simulate.py --mode full --runs 3 -v      # bot odehraje celé runy a vypíše statistiky
python tools/simulate.py --all --mode quick           # všechna zvířata × biomy
python tools/simulate.py --mode endless --runs 3 -v   # Nekonečná noc (bot hraje do smrti, max. 15 min)
python tools/profile_run.py [--cprofile] [--kills] [--biome=forest]   # zátěž 400 nepřátel + 300 projektilů
python tools/dps_bench.py             # DPS všech zbraní (single target / AoE) pro balanc
python tools/screenshots.py out_dir   # screenshoty všech scén
python tools/preview_sprites.py sheet.png             # contact sheet všech spritů
python tools/make_store_assets.py   # grafika pro Google Play do store/ (ikona, feature graphic, screenshoty)
python tools/ult_lab.py measure|boss|runs|perf|shots   # měření ultimátek (balanc, výkon, screenshoty)
python main.py --debug --scenario ult_duck           # ladicí scénář (seznam: python main.py --list-scenarios)
```

## Výkon (ověřeno profilingem)

Zátěžová scéna `tools/profile_run.py`, ~400 nepřátel + ~300 projektilů + ~500 částic: logika ~1,5–2,2 ms,
render ~2,2–2,9 ms na frame (cca 200–250 FPS bez limitu); v okně běží hra na stabilních 60 FPS.
Start do menu < 1 s, restart runu < 1 s. Použito: spatial hash grid s int klíči, pool projektilů, pool částic
s pevným stropem, `Surface.fblits`, předrenderované varianty spritů (flip, flash, led), slučování XP zrn,
recyklace vzdálených nepřátel, separace nepřátel rozložená do 2 ticků.

## Soubory za běhu

- `save.json` – postup (při poškození se zazálohuje jako `save.json.corrupt-*` a začne se nanovo),
- `crash.log` – záznam výjimek (hra místo pádu ukáže přátelskou chybovou obrazovku),
- `shares/` – obrázky „Sdílet výsledek“.
