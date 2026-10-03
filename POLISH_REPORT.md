# Polish report – LAST CHICKEN

Datum 3. 10. 2026 · výchozí stav `bd206ca` (pre-polish checkpoint) → commity „Polish A/B/…“.
Podklady: `CODE_MAP.md` (mapa kódu, tabulky událostí a obrazovek), `POLISH_LOG.md` (audit + všechna rozhodnutí).
Screenshoty: před `polish/before/`, po `polish/after/` (stejná sada a stejný seed), ostatní biomy `polish/after_biomes/`.

## Co se změnilo

### A) Efekty (největší viditelná změna)
- **Částice** už nejsou čtverečky `surf.fill`. Jsou to předrenderované pixel-art sprity na mřížce 3 px (kulaté chuchvalce kouře s objemem, jiskry s ocáskem, dvoubarevná peříčka, úlomky s obrysem, aditivní záře), kreslené jednou dávkou `fblits`. Pool, strop, API i čísla druhů zůstaly, takže stávající volání fungují beze změny.
- **Výbuch** má vrstvy: záblesk → ohnivé koule (bílá → žlutá → oranžová → šedá) → jiskry s gravitací → stoupající kouř → úlomky → spáleniště na zemi (4 s). Kruh poškození má dál přesný poloměr zásahu. Viz `polish/after/fx_explosion_f2/5/12/24.png` vs `polish/before/…`.
- **Zásah nepřítele**: 2–3 jiskry ve směru úderu (žluté při kritu), nejvýš jednou za záblesk spritu.
- **Smrt nepřítele**: malý „pop“ kruh, chuchvalec chlupů a peří v barvě daného druhu. Elita má navíc záři, kouř a kruh.
- **Level-up, bedna, magnet, žížala, mince, zlaté vejce, XP**: věnce hvězdiček, záře a třpytky. **Boss**: kouř a kruh při příchodu, věnec při smrti. **Zásah slepice**: červená záře. **Smrt slepice**: záře a kouř.
- **Čitelnost**: nepřátelské střely mají pulzující záři ve své barvě (sliz zelená, mrkev oranžová), takže jsou vidět i v davu. Hustota efektů se sama snižuje při 80+ nepřátelích (až na 40 %).
- **Život světa**: světlušky na Farmě (k úsvitu mizí), listí v Lese, prach ve Městě, sníh na Horách, jiskry v Továrně. Prach pod nohama při chůzi, záře pod sběratelnými předměty, jemná trvalá vinětace na okrajích.

### B) UI
- Panely, tlačítka, pruhy a rámečky ikon mají **zkosené pixelové rohy** a světlo shora. Jedna změna ve `widgets.py` sjednotila všechny obrazovky.
- Hlavní (oranžová) tlačítka mají jednou za 4 s **šikmý lesk**.
- **Ghost stopa** (světlý zbytek ztraceného HP, který pomalu dobíhá) na pruhu bosse i pod slepicí.
- Podobrazovky menu (Výběr, Hnízdo, Obchod, Nastavení, Sbírka, Výzvy, Denní) mají místo ploché barvy **pomalu ujíždějící vzor vajíček a vinětaci**. Každá si nechala svou barvu.
- **Menu**: předrenderované noční pozadí (tráva z dlaždice Farmy), pixelový měsíc se září, světlušky a třpytky na logu.
- **Výsledky**: čísla se postupně napočítávají, při výhře padají konfety, při prohře peří.
- **Nastavení**: nové tlačítko „O hře“ s verzí, autory, prohlášením o soukromí a odkazem na licence.
- Kreslicí bubliny bossů ve stejném pixelovém rámečku. Ztmavení u dialogů a overlayů se už nealokuje každý snímek.

### C) Obchod (store)
- `tools/make_store_assets.py` vyrobí `store/`: ikonu 512×512, feature graphic 1024×500 a 5 screenshotů 1080×1920 s českými popisky (menu, boj, level-up, boss, vítězství).
- `LICENSES.md`: licence závislostí a prohlášení o soukromí.

### Kolo 2 (podle zpětné vazby)
- **Světlušky** jsou pryč z menu i ze hry.
- **Dorty a smrad – „velké růžové skvrny“**: nedělaly je částice, ale **bílé bliknutí celého davu**, protože šlehačka i mrak zraňují všechny uvnitř naráz každých 0,4–0,5 s. Plošné poškození teď nebliká a nechrlí čísla, místo toho občas drobná jiskřička. Poškození i RNG zůstaly stejné (ověřeno).
- **Dort**: místo růžových kruhů stín padajícího dortu a tečkovaný kroužek. Dopad = šlehačkový cákanec s posypem (žádný oheň). Šlehačka na zemi = rozházené pixelové kopečky.
- **Smrad**: pixelový mrak z otáčejících se chuchvalců plynu, bubliny a komiksové „smradlavé čárky“. Aura Biologické zbraně = toxický prstenec.
- **Lišky v menu** chodí normálním tempem (snímek se dřív měnil s každým pixelem posunu).
- **Menu**: nová krajina v art pixelech: obloha s ditherem, vzdálené kopce se smrky, kopec s kurníkem, strašákem a stodolou, louka bez předělu s trsy trávy a kytkami, plot a balíky sena. Feature graphic do obchodu používá stejnou krajinu.
- Snímky: `polish/after/menu.png`, `polish/after_weapons/` (dort a smrad v pozdní hře).

### Kolo 3 (podle zpětné vazby)
- **Menu**: dýně stojí u plotu a lišky chodí před nimi. Stavby mají opar, stín a trávu přes spodek, takže sedí v krajině. Kurník je bez rampy (jen v menu). Spodní část louky plynule tmavne do klidné barvy a dole ji rámuje vysoká tráva.
- **Výběr zvířete**: obsah panelu je posunutý, takže text má vždy rezervu. Tečky stránek jsou pixelové kuličky s obrysem.
- **Země ve hře**: dlaždice bez švů (skvrny se neořezávají na hraně, cesta a výstražný pruh nahrazené uzavřenými motivy).
- **Smrad**: vzdouvající se oblak z mnoha chuchvalců jako kouř výbuchů. Aura je prstenec stejného plynu.

### Kolo 4 (podle zpětné vazby)
- Hvězdy v menu nezhasínají, jen jemně mění jas. Dole v menu už nejsou tmavé cípy trávy, zůstal jen gradient.
- Slepice se při kličkování už nedeformuje: squash & stretch je jen naznačený (renderer, hratelnost beze změny).
- Pauza: místo téměř černé je za panelem lehce ztmavená hra.
- Bedna: dvouvrstvé paprsky proti sobě, záře, třpytky a pohupování. Pozadí výsledků: parallax pruhy a při výhře sluneční paprsky.

### Kolo 5 (podle zpětné vazby)
- Kurník nemá rampu ani ve hře.
- Bedna: paprsky jako v původní verzi, ale jen jednou vystřelí a vyblednou (žádné trvalé efekty).
- Pozadí výsledků: klidná pixelová scéna. Výhra = svítání se sluncem za kopcem a plujícími mráčky, prohra = noc s hvězdami a měsícem.

## Zjištění z kódu, která stojí za pozornost
- **Hra už byla vizuálně soudržná.** Pixel art, vlastní bitmapový font s diakritikou, stíny, y-sorting, omezený třes (trauma model), omezovač záblesků a nastavení přístupnosti tu byly. Rozšiřoval jsem existující systémy, nic paralelního nevzniklo.
- **`Run.rng` je herní RNG** (deterministické denní výzvy). Všechen nový vizuální kód používá vlastní RNG částic, ambientu nebo menu. Pozor ale na **existující únik**: `damage_enemy` bere `run.rng` na posun čísla poškození jen když hra není headless. Headless simulace a skutečná hra se stejným seedem se proto rozejdou. Nebyl to úkol této práce, nechal jsem to být.
- **Smoke test `full_game_flow_through_scenes` je křehký.** Když menu spotřebovalo pár hodnot z globálního `random`, změnil se seed dalších runů a test spadl („chybí dialog oživení“). Pravděpodobně proto, že `take_damage(1e9)` v testu nic neudělá, když je slepice zrovna nesmrtelná po zásahu nebo kokrhání. Menu teď používá vlastní RNG a test prochází. Samotný test bych ale zpevnil (před zabitím vynulovat `invuln`).
- `add_ring(..., r)` ve výbuchu = skutečný poloměr poškození. Vizuál ho čte, nikdy nemění.
- **Hratelnost se nezměnila (ověřeno):** 6 seedovaných běhů bota (3 biomy × headless/s renderem) dává před i po stejný stav, zabití, HP, mince i pozici.

## Rozhodnutí, která můžeš chtít zvrátit
- Vzor vajíček na pozadí podobrazovek (velmi jemný). Kdyby rušil, stačí v `draw_scene_bg` vrátit `surf.fill`.
- Lesk na oranžových tlačítkách každé 4 s (`widgets._shine`).
- Trvalá vinětace v okrajích herní plochy (`RunRenderer._make_edges`).
- Spáleniště po výbuších (max 24, mizí za 4 s).
- Hustota efektů 100 % pod 80 nepřáteli, lineárně dolů na 40 % při 350+.

## Výkon (PC, `tools/profile_run.py`, 400 nepřátel + ~300 projektilů, medián ze 3 běhů)
| scéna | před | po |
|---|---|---|
| nesmrtelní nepřátelé (jiskry z každého zásahu) | 4,42 ms (render 2,31) | 5,21 ms (render 3,04) – **+18 %** |
| `--kills` (masové umírání) | 3,90 ms (render 2,31) | 4,34 ms (render 2,68) – **+11 %** |

Celkem pod limitem +25 %. Kreslení částic stojí asi 0,6 ms při 550 částicích. Na telefonu je strop částic nižší (450). Na zařízení jsem to neměřil, takže první test na slabším Androidu je doporučený krok.

## Co pořád není „store-grade“ (podle dopadu)
1. **Zvuk** jsem neměnil. Syntetizované SFX a hudba jsou funkční, ale pro obchod by nejvíc pomohla ručně laděná sada zvuků a hudby.
2. **Telegrafy útoků bossů** (kruhy, čáry, pásy) jsou pořád jednoduché tvary. Fungují, ale působí nejvíc „prototypově“ ze zbytku.
3. **Joystick a tlačítko kokrhání** jsou hladké vektorové kruhy, ne pixel art.
4. **Feature graphic a ikona** jsou generované. Ilustrace od výtvarníka by v obchodě udělala víc.
5. Podobrazovky menu nemají kromě pozadí žádný idle pohyb (maskota apod.).
6. Mezi obrazovkami je původní stírací přechod (0,16 s). Je funkční, jen jsem ho neměnil.

## Připravenost na obchod
**Hotovo v tomto passu**
- Nastavení: hudba, zvuky, vibrace, otřesy, záblesky, čísla poškození, FPS (existovalo) + nové „O hře“ (verze, autoři, soukromí, licence).
- `LICENSES.md`, prohlášení „hra nesbírá data“.
- Grafika do obchodu v `store/` (ikona 512, feature graphic 1024×500, 5 screenshotů 1080×1920).
- Už existovalo: pauza při ztrátě fokusu / odchodu do pozadí, Android Zpět = pauza/návrat, nápověda při prvním spuštění, debug overlay jen přes F3 / `--debug`.

**Potřebuje tebe**
- Google Play Console účet (jednorázově 25 USD) a ověření identity.
- **Ostrý podpisový klíč.** Teď se podepisuje `app_assets/debug.keystore`, který je v repozitáři. Pro Play vytvořit vlastní upload klíč, nedávat ho do gitu a zapnout Play App Signing.
- URL zásad ochrany soukromí (stačí jednoduchá stránka s textem z „O hře“). Play ho vyžaduje i u her bez sběru dat.
- Texty do obchodu (krátký a dlouhý popis), kategorie, věkové hodnocení (dotazník IARC) a formulář Data safety.
- Rozhodnutí o reklamách: teď jsou falešné (mock). Buď je odstranit, nebo napojit skutečné SDK (to by změnilo Data safety i soukromí).

**Technické překážky**
- **Formát AAB místo APK.** Play přijímá jen Android App Bundle; buildozer umí `buildozer android release` s `android.release_artifact = aab`. Úprava workflow cca 0,5–1 den.
- **Cílové API.** `buildozer.spec` má `android.api = 33`, Play pro nové aplikace vyžaduje aktuální target (35+). Zvednout a otestovat recept pygame 2.1, cca 0,5–2 dny podle toho, jestli recept projde.
- Výkon na slabém telefonu ověřit na skutečném zařízení (pygame 2.1 bez SIMD blendů), cca 0,5 dne.

## Jak vrátit změny
- Celý polish pass: `git reset --hard bd206ca` (pre-polish checkpoint).
- Po jednotlivých fázích: `git revert <commit>` u commitů „Polish A…“, „Polish B…“ a posledního (dokončení + store).
