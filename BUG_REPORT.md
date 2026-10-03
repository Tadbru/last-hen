# Bug report: LAST CHICKEN (5. kolo, po polish pass)
Datum: 3. 10. 2026 · verze 1.0.6 (commit 43f46ab) · číslování navazuje na B-49 až B-66 (předchozí report je v gitu, commit bd206ca).

**Jak jsem testoval:** statická analýza (scanner + ruční čtení run/render/particles/bosses/overlays/hud/scén), smoke testy (16/16 OK), headless sondy mimo projekt: přes 150 botích runů (všech 7 zvířat × rychlý/plný/boss rush, Hard/Nightmare), 2 dlouhé běhy s renderem (21 min hry), snímky obrazovky přes skutečnou GameScene. **Neověřeno:** Android, hraní člověkem, poslech zvuku.

## Souhrn
14 nálezů: 0 kritických, 3 vysoké, 5 středních, 6 drobných.
Hra je stabilní (žádný pád, výkon 1,2 ms render / 0,55 ms logika medián). Největší problém přinesl polish pass: pool částic tiše „vytéká“ a po ~1:45 hry zmizí všechny efekty. Další témata: stavy, kdy hra stojí (záblesk zamrzne), boss trvale bílý od zásahů, a HUD, který zakrývá vstup a hlášky bossů.

## Nálezy

### [B-67] Po ~1:45 hry zmizí všechny částice (pool vyteče)
- Závažnost: vysoká
- Kategorie: game feel/efekty
- Kde: `game/gfx/particles.py` `ParticleSystem.update` (větev `elif k == GLOW or k == POP: continue`)
- Co se děje: exploze, smrt lišek, peří, jiskry, kouř, prach pod nohama, hvězdičky level-upu – od určité chvíle se nevykreslí nic.
- Jak se to projeví / kdy: každý run, po zhruba 700 emisích GLOW/POP (záře + kroužek při každém zabití). Rychlý mód ~1:15–1:45, na telefonu (strop 450) dřív.
- Důkaz: GLOW/POP se po 1. update vyřadí z `alive`, ale nevrátí do `free`. Izolovaný test: 2 emise → po update alive 0, free 8 z 10 (2 sloty ztraceny). Run (hen, quick): t=60 s leaked 330, t=105 s leaked 700/700, od té doby 23 235 emisí zahozeno. Dlouhý běh: `part=0` od 3. minuty do 21. minuty. Srovnání stejného seedu v t=125 s: 0 vs. 69 živých částic.
  ```python
  elif k == GLOW or k == POP:
      continue          # slot se nevrátí do self.free a částice zmizí po 1 snímku
  ```
- Jistota: ověřeno během běhu
- Proč to vadí: celý polish efektů funguje jen první minutu; navíc záře a kroužky žijí jen 1 snímek místo své délky.
- Směr opravy: GLOW/POP nechat v `keep` do vypršení `life` a pak vrátit do `free` jako ostatní druhy.

### [B-68] Záblesk obrazovky zamrzne, když hra stojí (vítězství 3 s v bílém závoji)
- Závažnost: vysoká
- Kategorie: game feel/efekty
- Kde: `game/world/run.py:958` (`flash_t` ubývá jen ve stavu playing), `game/world/render.py:179–184`
- Co se děje: po porážce finálního bosse je celá vítězná animace zahalená bílým závojem (alfa 110). Totéž v pauze hned po kokrhání a pod bednou s evolucí.
- Jak se to projeví / kdy: každá výhra (s výchozím nastavením záblesků).
- Důkaz: 6/6 výher: `flash_t = 0.150` ve všech 181 ticích `victory_anim`. Pauza 5 s po kokrhání: `flash_t` stále 0,15. Bedna s evolucí otevřena s `flash_t = 0.2`. Snímek vítězné animace je celý vybledlý.
- Jistota: ověřeno během běhu
- Proč to vadí: vrchol hry (východ slunce) vypadá jako chyba displeje.
- Směr opravy: odečítat `flash_t` i ve stavech victory_anim/dying/paused/levelup/chest, nebo ho při změně stavu nulovat.

### [B-69] Boss je v pozdní hře skoro pořád bílý
- Závažnost: vysoká
- Kategorie: grafika/animace
- Kde: `game/world/run.py:526–528` (`e.flash = 0.09` při každém zásahu), `render.py:482`
- Co se děje: bílý zásahový sprite se obnovuje každým zásahem, takže boss vypadá jako bílá silueta. Zmizí tónování variant (Mlhoš, Kmotr, Yetti, Robokohout) i vzhled fází.
- Jak se to projeví / kdy: plný mód od Vlčí Alfy, nejvíc finální boss.
- Důkaz: podíl ticků s bílým spritem: finální boss 63 % / 92 % (plný mód), Vlčí Alfa 51–74 %, rychlý mód 12–21 %; elity 17–23 %. Snímek fáze 2: kohout jako bílá skvrna.
- Jistota: ověřeno během běhu
- Proč to vadí: nejdůležitější souboj ztrácí vzhled a čitelnost.
- Směr opravy: u bossů/elit omezit frekvenci záblesku (např. max 1× za 0,3 s) nebo použít jen krátký tint.

### [B-70] Finální boss přiletí pod HUD, hlášky bossů jsou schované pod ikonami
- Závažnost: střední
- Kategorie: UI/UX
- Kde: `run.py:385` (spawn `p.y - 300` → obrazovka y≈180), `render.py:844–849` (bublina `y ≥ th+60`), `hud.py` (sloty y 82–158, boss bar y 182)
- Co se děje: kohout se objeví přesně za svým ukazatelem zdraví, úvodní hláška překrývá „BOSS!“ a řádky zbraní, poslední slova („Kikiri… kí…“) jsou za ikonami zbraní.
- Důkaz: snímky v 0,4 s a 2,0 s po příletu a během vítězné animace – text bubliny nečitelný.
- Jistota: ověřeno během běhu
- Proč to vadí: dramatický vstup a vtip bossů hráč nevidí.
- Směr opravy: spawnovat níž (pod pásem HUD) a bubliny clampovat pod spodní okraj HUD.

### [B-71] Klávesa S (pohyb dolů) = Skip v level-upu, mezerník (kokrhání) zavírá bednu
- Závažnost: střední
- Kategorie: UI/UX (ovládání)
- Kde: `ui/overlays.py:110` (`key=pygame.K_s`), `core/input.py:66`, zámek jen pro dotyk `overlays.py:43`, bedna `overlays.py:308–313`
- Co se děje: hráč na PC, který klepe S pro pohyb dolů, dvěma stisky zahodí level-up za pár mincí.
- Důkaz: sonda: S v 0,05 s → „Opravdu?“, S v 0,45 s → stav playing, pending 1→0, mince 0→5.
- Jistota: ověřeno během běhu
- Proč to vadí: ztracená karta bez úmyslu; README přitom WASD i S=skip uvádí současně.
- Směr opravy: jiná klávesa pro Skip (např. X) a zámek 0,6 s i pro klávesy.

### [B-72] Elity za plotem arény zmizí i s bednou
- Závažnost: střední
- Kategorie: logika
- Kde: `run.py:371–383` (`e.alive = False` pro ne-bosse za plotem), `data/waves.py` ELITES_FULL (555 s, 585 s)
- Co se děje: elita, která jde k hráči, při příletu finálního bosse zmizí v obláčku a její bedna (šance na evoluci) propadne bez zprávy.
- Důkaz: 28 runů: 33 elit naživu při vzniku arény, 21 smazáno. Plný mód: ztráta bedny v 8 ze 14 runů (elity se objeví 15–45 s před bossem).
- Jistota: ověřeno během běhu
- Proč to vadí: stejný typ ztráty odměny, jaký opravovalo B-50.
- Směr opravy: elity přenést do arény jako mini-bosse, nebo jejich bednu vysypat dovnitř.

### [B-73] Kokrhání se v pozdní hře nabíjí každých 1,4 s
- Závažnost: střední
- Kategorie: balanc / game feel
- Kde: `run.py:582` (nabití za zabití), `run.py:870–899` (1 s nesmrtelnost, omráčení 2,2 s, `vibrate(14)`)
- Co se děje: special se mění v kulomet: každou chvíli „KIKIRIKÍ!“, cuknutí kamery o 14 px a všechny lišky v okolí trvale omráčené.
- Důkaz: kokrhání při každém nabití, plný mód: Kohout v 9. minutě 43×/min, nesmrtelný 68 % času; slepice 21×/min, 34 %. 217 ticků s kickem kamery > 10 px. (Na výsledek bota to vliv nemělo.)
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: special ztrácí váhu a obrazovka pravidelně cuká.
- Směr opravy: minimální cooldown kokrhání nebo rostoucí cena nabití s časem.

### [B-74] Rychlý mód: až 7 level-up obrazovek za sebou, hlavně během bosse
- Závažnost: střední
- Kategorie: game feel / balanc (záměr? – B-51)
- Kde: `run.py:1035–1042`, `run.py:1070–1080`
- Co se děje: přerušení je méně, ale obrazovek stejně; po 8 s hraní přijde řetěz 5–7 karet, často v souboji s bossem.
- Důkaz: 30–34 obrazovek za ~3,5 min; řetězy (čas, počet): (149 s, 5), (159 s, 6), (174 s, 7), (175 s, 7).
- Jistota: ověřeno během běhu (bot)
- Proč to vadí: souboj s finálním bossem se rozpadá na klikání karet.
- Směr opravy: opravdu sloučit čekající level-upy do jedné obrazovky (víc karet / vyšší rarita).

### [B-75] Sebraná bedna se otevře až za ~5 s, bez indikace
- Závažnost: drobná · Kategorie: UI/UX · Kde: `run.py:1036–1042`, `hud.py` („+N“ jen pro level-upy)
- Co se děje / důkaz: zpoždění sebrání→otevření medián 4,9 s, max 7,8 s (33 ze 46 beden > 3 s). Hráč neví, že bedna čeká. · Jistota: ověřeno · Směr: ikonka čekající bedny v HUD.

### [B-76] Finální boss říká hlášky jiných fází
- Závažnost: drobná · Kategorie: logika/text · Kde: `world/bosses.py:358–360`, `78–82`
- Co se děje / důkaz: náhodné hlášky berou z celého seznamu: ve fázi 1 „Prší slepice!/krysy!/VYPOUŠTÍM ROBOLIŠKY“ a „TEĎ UŽ JSEM OPRAVDU NAŠTVANÝ!“, ve fázi 3 „Prší…“ i když nic nepadá. · Jistota: ověřeno · Směr: hlášky fází vyřadit z náhodného výběru.

### [B-77] Pozadí obrazovek menu každých 5,3 s poskočí
- Závažnost: drobná · Kategorie: grafika · Kde: `scenes/base.py:319` (`off % BG_TILE`, řádky posunuté o půl dlaždice → svislá perioda 96 px)
- Důkaz: plynulé snímky 0 px rozdílu, při přetečení 25 284 px rozdílných (vzor skočí o půl dlaždice). · Jistota: ověřeno · Směr: modulo 2×BG_TILE ve svislém směru.

### [B-78] Texty, které nesedí
- Závažnost: drobná · Kategorie: UI text
- Kde a co: `share.py:14–17,52` – po prohře „PADLA JSEM… Kurník je zase v bezpečí.“; `collection.py:150` „Ještě jsi to nepotkala“ (rod hráče); `shop.py:152` sezónní skin označený „vlastníš“, po sezóně zmizí.
- Jistota: podle kódu · Směr: vítězné vtipy jen při výhře, neutrální formulace.

### [B-79] Jednorázové zadrhnutí při prvním zobrazení výsledků
- Závažnost: drobná · Kategorie: výkon · Kde: `scenes/results.py:253–311` (pozadí po pixelech přes `set_at`)
- Důkaz: PC 65–70 ms (výsledky), 34 ms (menu). Na telefonu odhad několikanásobek. · Jistota: měřeno na PC, telefon neověřen · Směr: předgenerovat při startu nebo kreslit po pruzích.

### [B-80] Dokumentace a popisy neodpovídají hře
- Závažnost: drobná · Kategorie: spec mismatch
- Co: README Kachna „70 % životů“ (hra 85 %); PLAN Páv „+25 % XP“ (hra 10 %), Android „SCALED | FULLSCREEN“ (hra škáluje sama), prázdné level-upy „mince + 5 %“ (hra 35 % léčení); výběr módu „3 minuty / 10 minut“ – naměřeno 2:52–6:12 a 10:38–12:05.
- Jistota: ověřeno čtením a během běhu · Směr: aktualizovat texty.

## Co jsem nestihl / neověřil
- Android (klasický pygame 2.1, výkon, haptika), hraní člověkem, poslech zvuku.
- Plný mód na Hard/Nightmare; Hory/Továrna jen okrajově.
- `tools/simulate.py` simuluje boss rush **bez** 10 bonusových level-upů (nepředává `bonus_levels`) – čísla z něj jsou pro rush zkreslená (s bonusem 12/21 výher, bez něj 3/14).
- Pickupy mimo XP (mince ze Zlaté bomby) přerostou strop 380 až po 15. minutě (jen v uměle prodlouženém běhu).

## Témata, která se opakují
- **Nový kód bez úklidu stavu:** částice GLOW/POP se nevracejí do poolu (B-67), záblesk neubývá mimo „playing“ (B-68).
- **Efekty laděné na jeden zásah, ne na pozdní hru:** zásahový záblesk bosse (B-69), kokrhání nabíjené zabitími (B-73).
- **HUD a scéna soupeří o horní třetinu obrazovky:** příchod bosse a bubliny (B-70).
- **Konec módu odřízne odměny:** elity za plotem (B-72), čekající bedny (B-75), dříve B-50.
