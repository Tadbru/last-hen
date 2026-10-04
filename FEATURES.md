# Features

## Ovládání a drobnosti (4. 10. 2026, po zpětné vazbě)
- **Pevný joystick:** vznikne, kam hráč ťukne, kdekoli na obrazovce (dřív jen ve spodních 2/3). Střed zůstává
  po celou dobu dotyku na místě (dřív se za prstem posouval), páčka se zastaví na okraji a zvíře jde plnou rychlostí
  směrem k prstu. Po puštění joystick zmizí, další ťuknutí jinde vytvoří nový. Tlačítka pauzy a ultimátky mají
  přednost. Test `fixed_joystick_anywhere`.
- **Ultimátka během pohybu:** telefon – druhý prst na tlačítku, zatímco první drží joystick; PC – pravé tlačítko
  myši (i během tažení levým). Dřív hra viděla jen první prst / jedno tlačítko myši, takže při pohybu ultimátka
  nešla. Test `ultimate_while_moving_and_beak_laser` posílá skutečné události SDL (`FINGERDOWN`, pravé tlačítko).
- **Zobák-laser ze zobáku:** paprsek začíná na špičce zobáku každého zvířete (doprava i doleva, ležící tučňák)
  a míří ze zobáku na cíl; dřív vycházel ze středu těla. Poloha se počítá z pixelové mapy (`gfx/sprites.py:
  PLAYER_BEAK`, `beak_offset`), funguje i headless.
- **Názvy zbraní:** Vaječný granát (dřív Vejce granát), Husí štípanec (dřív Zobák-šleh, sjednocené i texty úrovní),
  Páví vějíř (dřív Ocas-vějíř). Id zbraní se nezměnila, uložené hry a sbírka beze změny.
- Ověřeno: smoke testy 20/20, snímek laseru u všech 7 zvířat na obě strany.
- **Denní výzva s výběrem zvířete:** mapa a modifikátor zůstávají pro všechny stejné, zvíře se vybírá šipkami ze
  všech odemčených; dnešní zvíře výzvy je výchozí (zamčené jde dál zapůjčit). Test `daily_character_choice`.
- **Tučňák bez klouzání:** pasivka Klouzání po břiše (setrvačnost, +60 % při jízdě rovně, zranění při nárazu)
  nahrazena pasivkou **Ledová krev** – zmražené lišky od něj dostanou o 30 % víc (souhra s Mraženou rybou a Dobou
  ledovou); slabina „O 5 % pomalejší“. Test `goose_whip_and_penguin_no_slide`.
- **Husí štípanec trefuje:** útok se spustí jen na lišku opravdu na dosah (dosah + její poloměr, tedy maximální
  možný) a míří na ni – žádné štípnutí do vzduchu.

## v1.2.0 – Ultimátky zvířat (4. 10. 2026)

### Co se mění pro hráče
- Každé ze 7 zvířat má místo společného „KIKIRIKÍ“ vlastní **ultimátku** (mezerník / velké tlačítko vpravo dole).
  Liší se mechanikou, názvem, ikonou, efektem i zvukem, takže volba zvířete mění i nejsilnější okamžik runu.
- Tlačítko ukazuje ikonu a krátký název ultimátky, nad ním jméno zvířete; nabíjí se obloukem v barvě ultimátky
  a při plném nabití pulzuje. Při prvním použití v runu se objeví velký banner s názvem, potom už jen malý název
  u zvířete (nejvýš jednou za 20 s); výkřik zvířete zazní při každém použití.
- Ultimátka se dál nabíjí zabíjením lišek (cena podle zvířete) a run začíná nabitý z poloviny. První použití tak
  přijde ve 20–35 s (bot: rychlý mód 21–33 s, plný 23–41 s).
- Výběr zvířete ukazuje ultimátku (ikona + název v panelu, popis pod ním), pauza ukazuje název a počet použití,
  úvodní nápověda prvního runu ji jmenuje.

### Tabulka ultimátek
| Zvíře | Ultimátka | Mechanika | Nabíjení (zabití / nejdřív) | Hlavní parametry (síla 1, dosah 1) | Evoluce startovní zbraně |
|---|---|---|---|---|---|
| Slepice Božena | **Zlatá nadílka** (NADÍLKA) | 14 zlatých vajec vysokým obloukem na lišky kolem (prvních 5 na nejbližší), výbuch omráčí; liška zabitá vejcem dá 2× XP | 70 / 8 s | dosah 330, výbuch r 58, 30 + 35 % max. HP, omráčení 0,5 s, déšť 1,6 s | Zlatá bomba: 18 vajec |
| Kachna Kvak | **Velká voda** (VLNA) | rozstřik kolem kachny + obří vlna ve směru pohybu, která lišky unáší s sebou; promočené zpomalí, na konci náraz s omráčením | 65 / 8 s | vlna 560 × 420 za 1,1 s, 25 + 40 % HP, zpomalení 60 % na 4 s, náraz 10 + 20 % HP, rozstřik r 140 | Hasičská hadice: 700 × 520 |
| Husa Gerta | **Husí řádění** (ŘÁDĚNÍ) | 3 s nesmrtelná a o 35 % rychlejší, každých 0,6 s kejhnutí (odhoz + omráčení), co srazí, zraní; na konci „KEJHHH“ odhodí a omráčí lišky kolem | 75 / 14 s | kejhnutí r 150, 22 + 12 % HP; závěr r 230, 20 + 10 % HP, omráčení 1,6 s | Husí hněv: 4 s |
| Krocan Rambo | **Operace Díkůvzdání** (PALBA) | 4 salvy po 20 brcích do všech stran, průraz, kritické zásahy krocana (×3) platí, Brýle přidají průraz a rychlost | 70 / 7 s | brk = 80 % HP lišky dané minuty, průraz 2, dolet 650 | Peří Gatling: 5 salv po 24 |
| Kohout Elvis | **Královské KIKIRIKÍ** (KIKIRIKÍ) | původní kokrhání beze změny: odhodí a omráčí lišky kolem, smete jejich sliz, krátká nesmrtelnost | 70 / 6 s (pasivka Elvise: 2× rychleji → 35 / 3 s) | r 290, 40 + 25 % HP, odhoz 560, omráčení 2,2 s, nesmrtelnost 1 s | Rockový koncert: ozvěna o 0,5 s později (½) |
| Páv Diva | **Božská krása** (HYPNÓZA) | duhová vlna okouzlí lišky: 5 s bojují za Divu (útočí na nejbližší lišky i bosse), Divy se nedotknou; bez cíle drží stráž ~150 px kolem ní a po konci okouzlení jsou 0,8 s zmatené; auto-aim je ignoruje | 75 / 12 s | r 280, max. 50 lišek (elity 2,5 s), úder 2× poškození lišky nebo 12 % HP cíle za 0,45 s | Duhová show: r 340, 6,5 s |
| Tajný tučňák | **Doba ledová** (MRAZ) | 3 s ledová bouře kolem tučňáka: mrazí, točí zmrzlé lišky dokola (kloužou), nakonec je roztříští; sliz v dosahu zmrzne | 75 / 12 s | r 215, 6 + 1,5 % HP každých 0,25 s, konec 20 + 12 % HP a mráz 1,2 s, vír 150 px/s | Ledová tsunami: r 250, 4,5 s |

Společná pravidla: Megafon zvětšuje dosah, Zlatá skořápka poškození, Budík zkracuje nejkratší dobu nabití
(−8 %/úr., max. −40 %), ale nikdy pod nejkratší rozestup ultimátky (`cd_floor`; Elvis tak zůstává na 3 s, víc už
Budík nepomůže). Explodující lišky zabité ultimátkou vybuchnou jen do lišek, hráče nezraní. Bossové: odhoz, omráčení, mráz, okouzlení ani unášení na ně neplatí, poškození ano, ale
**jedna aktivace ubere bossovi nejvýš 4 % max. HP** (fázové zámky Kohouta platí dál). Tučňák bosse jen zpomalí.
Každá ultimátka přebije vítr Zombie Kohouta (jako dřív kokrhání). Oživení po reklamě spustí ultimátku zdarma.

### Akceptační kritéria a jak dopadla
| Kritérium | Výsledek |
|---|---|
| 7 mechanicky odlišných ultimátek s názvem, popisem, ikonou, efektem a zvukem | ✅ tabulka výše, test `ultimates` (data, registr, ikona, zvuk), screenshoty aktivace |
| `Run.crow()` jen zavolá ultimátku zvířete, nová = řádek v datech + funkce | ✅ `data/ultimates.py` + `@effect` ve `world/ultimates.py` |
| UI: ikona, název (ultimátky i zvířete), nabití, pulzování, název při aktivaci | ✅ HUD, výběr zvířete, pauza, nápověda (screenshoty) |
| Bossové: souboj se nedá přeskočit | ✅ strop 4 % HP za aktivaci (test), nejkratší souboj s Kohoutem v rychlém módu 22 s (před úpravou 25 s) |
| Pauza, level-up, smrt, oživení, výhra, restart uprostřed efektu | ✅ test `ultimates` + sondy |
| Srovnatelné výkonové pásmo, žádná zjevně nejlepší ani zbytečná | ✅ tabulky měření níže (každá vyniká v něčem jiném, výsledky botem v rozptylu) |
| 60 FPS i při ~400 nepřátelích s aktivní ultimátkou | ✅ p95 3,9–6,4 ms, max. 9,5 ms (PC) |
| Staré uložené hry fungují | ✅ skutečný `save.json` z doby před úpravou: načtení, 7 zvířat, uložení – žádný klíč nepřibyl ani nezmizel |

### Hodnoty spočítané z dat (`python tools/ult_lab.py table`)
| Ultimátka | Nabití (zabití / nejdřív s / nejkratší rozestup i s Budíkem) | Dosah | Trvání | Poškození lišce 3. / 8. min | Evoluce |
|---|---|---|---|---|---|
| Zlatá nadílka | 70 / 8 / 5 | 330 (výbuch r 58) | 1.6 s + let | 100 % / 63 % | golden_bomb: eggs=18 |
| – | 14 vajec, omráčí 0.5 s, XP ×2 | | | | |
| Velká voda | 65 / 8 / 5 | 560 × 420 | 1.1 s | 100 % / 92 % | fire_hose: length=700, half_w=260 |
| – | rozstřik r 140, zpomalí 60 % na 4 s | | | | |
| Husí řádění | 75 / 14 / 10 | 150 / závěr 230 | 3.0 s | 100 % / 100 % | goose_rage: dur=4.0 |
| – | nesmrtelnost 3 s, rychlost ×1.35, 6 kejhnutí, závěr omráčí 1.6 s | | | | |
| Operace Díkůvzdání | 70 / 7 / 5 | 650 | 0.7 s | 80 % / 80 % | gatling: salvos=5, count=24 |
| – | 4×20 brků, průraz 2, každý brk 80 % HP lišky | | | | |
| Královské KIKIRIKÍ | 70 / 6 / 3 | 290 | 0,5 s | 100 % / 62 % | rock_concert: echo=1 |
| – | odhoz 560, omráčí 2.2 s, ničí sliz, nesmrtelnost 1 s | | | | |
| Božská krása | 75 / 12 / 8 | 280 | 5 s | nepřímé | rainbow_show: radius=340, dur=6.5 |
| – | okouzlí max. 50 lišek, úder 2× poškození lišky / 12 % HP cíle za 0.45 s | | | | |
| Doba ledová | 75 / 12 / 8 | 215 | 3.0 s | 100 % / 100 % | frozen_tsunami: dur=4.5, radius=250 |
| – | mrazí, vír 150 px/s, konec omráčí mrazem 1.2 s | | | | |

Poškození lišce = podíl jejího HP, který ultimátka ubere jedné lišce při plném zásahu (u husy a tučňáka teoretické
maximum, pokud liška zůstane v dosahu po celou dobu – ve skutečnosti ji kejhnutí nebo vír odnesou dřív).

### Měření 1: jedna aktivace v davu (`ult_lab.py measure`)
Slepice se všemi ultimátkami (srovnání bez vlivu zbraně a pasivky), plný mód, lišky v kruhu 70–340 px, hráč stojí,
nesmrtelný jen pro měření (přijaté poškození se sčítá), medián 4 seedů. „%HP davu“ = skutečně ubrané HP
(bez přebití) / součet HP davu. „Kontrola“ = sekundy lišek omráčených, zmražených nebo okouzlených navíc oproti
stavu bez ultimátky. „Přijato“ = poškození hráče za 3 a 8 s v % stavu bez ultimátky (méně = větší úleva).

| Ultimátka | 3. min (80 lišek): zabití / %HP / kontrola / přijato 3 s / 8 s | 8. min (120 lišek): zabití / %HP / kontrola / přijato 3 s / 8 s | Dosah (nejvzdálenější zásah) | Trvání |
|---|---|---|---|---|
| Zlatá nadílka | 44 / 56 % / 2 s / 78 % / 80 % | 36 / 44 % / 27 s / 63 % / 81 % | 229–248 px | 2,1 s |
| Velká voda | 42 / 59 % / 6 s / 42 % / 79 % | 32 / 46 % / 43 s / 51 % / 79 % | 540 px | 1,1 s |
| Husí řádění | 47 / 73 % / 40 s / 0 % / 23 % | 30 / 41 % / 153 s / 0 % / 28 % | 240 px | 3,0 s |
| Operace Díkůvzdání | 60 / 81 % / 0 s / 28 % / 60 % | 70 / 52 % / 0 s / 70 % / 91 % | 360–470 px | 1,2 s |
| Královské KIKIRIKÍ | 58 / 74 % / 21 s / 23 % / 50 % | 0 / 33 % / 223 s / 5 % / 65 % | 300 px | 0,5 s |
| Božská krása | 32 / 43 % / 199 s / 23 % / 34 % | 49 / 44 % / 192 s / 24 % / 60 % | 300–330 px | 5,3 s |
| Doba ledová | 52 / 68 % / 64 s / 23 % / 59 % | 24 / 30 % / 222 s / 15 % / 48 % | 230 px | 3,0 s |

Každá ultimátka je nejlepší v něčem jiném a v něčem slabá. Díkůvzdání nejvíc zabíjí (52 % HP davu v 8. min), ale
skoro neulevuje. Husí řádění dá 3 s úplné ochrany, ale nabíjí se nejdéle (14 s). KIKIRIKÍ a Doba ledová drží dav
nejdéle (~220 s kontroly), ale v pozdní hře zabíjejí nejméně. Velká voda má dvojnásobný dosah. Zlatá nadílka jako
jediná přidává XP (+75 až +82 XP za aktivaci proti šumu ±35 u ostatních). Na vlastním zvířeti vycházejí čísla
podobně, krocan díky kritickým zásahům ×3 o ~3 % HP davu výš.

### Měření 2: celé runy botem s vlastními zvířaty (`ult_lab.py runs`)
Farma, Normal, bez Hnízda. „Nabití“ = průměrná doba od použití do dalšího nabití, „1. nab.“ = kdy je ultimátka
poprvé připravená, „podíl zabití“ = kolik zabití runu udělala ultimátka, „boss“ = medián souboje s Kohoutem.

| Zvíře | Rychlý mód (8 seedů): výhry · použití · nabití · 1. nab. · podíl zabití · boss | Plný mód (3 seedy): výhry · použití · nabití · 1. nab. · podíl zabití |
|---|---|---|
| Slepice | 7/8 · 2,8× · 21,9 s · 30 s · 2,8 % · 26 s | 2/3 · 18× · 15,1 s · 34 s · 2,5 % |
| Kachna | 8/8 · 5,4× · 15,5 s · 28 s · 1,5 % · 58 s | 3/3 · 34× · 9,5 s · 30 s · 1,9 % |
| Husa | 6/8 · 11,2× · 16,3 s · 33 s · 4,2 % · 81 s | 2/3 · 28× · 17,6 s · 41 s · 11,1 % |
| Krocan | 6/8 · 6,0× · 15,9 s · 30 s · 13,2 % · 53 s | 3/3 · 23× · 9,8 s · 31 s · 4,9 % |
| Kohout | 6/8 · 14,8× · 8,1 s · 22 s · 8,9 % · 77 s | 1/3 · 83× · 4,8 s · 23 s · 7,7 % |
| Páv | 6/8 · 6,6× · 17,1 s · 29 s · 1,7 % · 81 s | 2/3 · 32× · 11,1 s · 33 s · 1,7 % |
| Tučňák | 5/8 · 4,6× · 19,2 s · 32 s · 2,9 % · 64 s | 2/3 · 26× · 13,6 s · 36 s · 3,7 % |
| **Celkem** | **44/56 (79 %)**, před úpravou 18/28 a 22/28 (4 seedy, dva běhy) | **15/21 (71 %)**, před úpravou 9/14 (64 %, 2 seedy) |

Každé zvíře dohrálo rychlý i plný mód včetně Zombie Kohouta aspoň jednou. Stará verze dala na stejných seedech ve
dvou bězích 18/28 a 22/28 výher (id nepřátel se liší mezi procesy), rozdíl je tedy v šumu. Před úpravou se kokrhání
v rychlém módu nabíjelo průměrně za 15–23 s (Elvis ~10 s) a poprvé bylo připravené ve 41–43 s (Elvis 29 s). Teď se
ultimátky nabíjejí za 8–22 s a poprvé jsou připravené ve 22–33 s.

### Měření 3: A/B test – slepice postupně se všemi ultimátkami (`ult_lab.py runs --swap`)
| Ultimátka | Rychlý mód, 10 seedů: výhry · boss | Plný mód, 4 seedy: výhry · boss |
|---|---|---|
| Zlatá nadílka | 7/10 · 25 s | 3/4 · 42 s |
| Velká voda | 8/10 · 42 s | 3/4 · 46 s |
| Husí řádění | 9/10 · 42 s | 3/4 · 54 s |
| Operace Díkůvzdání | 8/10 · 39 s | 3/4 · 40 s |
| Královské KIKIRIKÍ | 6/10 · 22 s | 4/4 · 44 s |
| Božská krása | 8/10 · 34 s | 2/4 · 56 s |
| Doba ledová | 8/10 · 35 s | 3/4 · 107 s |

Rozptyl 6–9/10 a 2–4/4 odpovídá šumu malého vzorku. Žádná ultimátka nevychází jako zjevně nejlepší ani zbytečná.

### Měření 4: souboj se Zombie Kohoutem v rychlém módu (`ult_lab.py boss`, 6 seedů)
Bot dohraje run k příletu Kohouta (všichni stejně, s klasickým kokrháním), pak dostane ultimátku svého zvířete.

| Ultimátka | Výhry | Souboj medián / nejkratší | Použití | Ultimátka ubrala Kohoutovi celkem / max. za aktivaci |
|---|---|---|---|---|
| Zlatá nadílka | 6/6 | 35 s / 22 s | 2,7 | 2,3 % / 3,5 % |
| Velká voda | 4/6 | 60 s / 36 s | 5,0 | 0,2 % / 0,1 % |
| Husí řádění | 3/6 | 94 s / 86 s | 10,3 | 2,2 % / 1,3 % |
| Operace Díkůvzdání | 3/5 | 70 s / 22 s | 7,0 | 11,5 % / 4,0 % |
| Královské KIKIRIKÍ | 4/6 | 90 s / 59 s | 12,5 | 3,0 % / 0,5 % |
| Božská krása | 5/6 | 49 s / 24 s | 4,2 | 2,5 % / 3,1 % |
| Doba ledová | 5/6 | 51 s / 34 s | 3,7 | 1,5 % / 0,7 % |

Strop 4 % za aktivaci drží. Před úpravou trval souboj botem 25–122 s. Žádná ultimátka ho netrivializuje:
nejkratší souboj je 22 s a fázové zámky Kohouta platí. (U krocana jeden ze 6 seedů do příletu bosse nedošel.)

### Měření 5: výkon (PC, `ult_lab.py perf`, logika + render + HUD)
400 nepřátel (nesmrtelných), ~300 projektilů, 700 částic, ultimátka stále aktivní:

| Ultimátka | avg | p95 | max |
|---|---|---|---|
| Zlatá nadílka | 3,8 ms | 4,7 ms | 7,6 ms |
| Velká voda | 3,2 ms | 3,9 ms | 5,5 ms |
| Husí řádění | 3,3 ms | 4,1 ms | 4,8 ms |
| Operace Díkůvzdání | 3,8 ms | 6,4 ms | 9,5 ms |
| Královské KIKIRIKÍ | 5,1 ms | 6,3 ms | 7,7 ms |
| Božská krása | 4,4 ms | 5,3 ms | 7,2 ms |
| Doba ledová | 3,8 ms | 4,8 ms | 5,7 ms |

`tools/profile_run.py` (bez ultimátky): 4,63 ms, s umíráním nepřátel 4,27 ms; před úpravou 4,81 / 4,61 ms, tedy
beze změny. Skill `smoke.py` přes skutečnou hru (v kopii projektu), 14 scénářů `ult_<zvíře>` a
`ult_<zvíře>_boss`, 1 800 snímků, bot mačká mezerník: všechny OK, p95 2,0–4,1 ms, počet objektů beze změny.

### Návrh
- Data: `game/data/ultimates.py` – `UltDef` (název, krátký název, popis, výkřik, ikona, barva, zvuk, zabití na
  nabití, nejkratší doba nabití, třes, zpomalení, parametry, parametry s evolucí), `ULT_BY_CHAR`, `ULT_START`,
  `ULT_BOSS_CAP`, `ULT_CLOCK_*`.
- Logika: `game/world/ultimates.py` – `activate()` (společná zpětná vazba), registr `EFFECTS` (`@effect("id")`),
  `UltSource` (zdroj poškození jedné aktivace: měření + strop bosse), běžící efekty `run.ult_fx`
  (`EggRain`, `Flood`, `GooseFury`, `Volley`, `Delayed`, `Hypno`, `IceAge`), okouzlení (`charm_target`, `charm_hit`).
- Napojení: `Run` (`ult`, `crow()`, `ult_period()`, nabíjení v `kill_enemy`, XP bonus, strop v `damage_enemy`,
  `ULT.update` po zbraních, `stop_all` při smrti a výhře, auto-aim ignoruje okouzlené), `Enemy.charm_t/foe`,
  větev okouzlení v `world/enemies.py`, `Player.ult_speed/ult_aura`.
- Vizuál a zvuk: `game/world/ult_render.py` (vrstvy pod entitami a nad nimi), nové částice srdíčko, vločka, nota,
  kapka a střep (`gfx/particles.py`), 7 ikon (`gfx/icons.py`), brk `feather_t`, 8 zvuků (`audio/synth.py`).
- UI: `ui/hud.py:_crow_button`, výběr zvířete, pauza, nápověda prvního runu, Nastavení, popis výzvy a Budíku.
- Beze změny: zbraně, pasivky (kromě vlivu Budíku na ultimátku), nepřátelé, bossové, XP křivka, ekonomika,
  ovládání, formát uložené hry (žádný nový klíč).

### Ladění a testy
- Scénáře: `python main.py --debug --scenario ult_<zvíře>` (~80 lišek, 3. minuta, nabito),
  `ult_<zvíře>_boss` (Zombie Kohout v rychlém módu + 40 lišek), `ult_stress_<zvíře>` (400 nepřátel, nesmrtelnost,
  ultimátka stále nabitá). Seznam: `python main.py --list-scenarios`, volitelně `--seed N`. Scénář neukládá postup.
- Klávesy s `--debug`: F4 nabije ultimátku, F2 přepne na ultimátku dalšího zvířete (zvíře a zbraň zůstanou).
- Měření: `python tools/ult_lab.py table|measure|boss|runs|perf|shots` (popis v hlavičce souboru).
- Smoke test `ultimates` v `tests/smoke_test.py` (18 testů celkem, všechny OK).
- Ladicí hodnoty: `game/data/ultimates.py` (`params`, `evo_params`, `kills`, `min_cd`, `ULT_*`).

### Rozhodnutí
Všechna jsou v `PLAN.md` → Rozhodnutí → „Ultimátky (v1.2.0)“. Nejdůležitější: KIKIRIKÍ zůstává beze změny Elvisovi
i s pasivkou dvojnásobně rychlého nabíjení; strop bosse 4 % za aktivaci; run začíná s 50 % nabitím; evoluce startovní
zbraně ultimátku posílí; pod panelem výběru zvířete je místo vtipného popisu zvířete popis ultimátky.

### Opravy po bug reportu (B-86 – B-90, 4. 10. 2026)
Ladicí scénář už neukládá postup, první Doba ledová netrhá snímky (16,6 → 2,9 ms), značky vajec nezaplňují cache
(22,6 → 1,7 MB), připravené tlačítko má kontrastní výplň, Budík zmiňuje ultimátku. Podrobnosti: `BUG_REPORT.md`.

### Opravy po bug reportu (B-91 – B-98, 4. 10. 2026)
Měření 1–5 výše proběhla před těmito opravami. Opravy mění jen Budík, konec okouzlení, výbuchy lišek po ultimátce,
pořadí kreslení a texty, nic jiného. Ověřeno stejnými sondami jako v reportu:
- B-91: každá ultimátka má `cd_floor` (nejkratší rozestup i s Budíkem a pasivkou zvířete, data). Elvis s Budíkem 5:
  KIKIRIKÍ nejdřív po 3,0 s místo 1,8 s, přijaté poškození 184 HP/min jako bez Budíku (dřív 15 HP/min). Husa
  s Budíkem 5 nejdřív po 10 s (dřív 8,4 s).
- B-92: zemní vrstva ultimátek se kreslí pod telegrafy útoků; červený okraj úderu medvěda je nad mrazivým diskem
  vidět (snímek).
- B-93: okouzlená liška bez cíle drží stráž ~150 px od Divy a po konci okouzlení je 0,8 s zmatená. Do 110 px od Divy
  na konci okouzlení 0 lišek (dřív 7–18), skok poškození po 5. s zmizel.
- B-94: velký banner jen při prvním použití, pak malý název nejvýš jednou za 20 s. Banner v 7.–10. min na
  obrazovce 0 % času (dřív 34 % u Elvise).
- B-95: okouzlená liška bez cíle hledá jednou za 12 ticků: 50 lišek bez soupeře 0,16 ms/tick (dřív 0,76 ms).
- B-96: liška zabitá ultimátkou (i v řetězu výbuchů) hráče nezraní: poškození z výbuchů po aktivaci 0 HP u všech
  ultimátek kromě Božské krásy (4 HP, zbytek jsou lišky zabité zbraní slepice; dřív 13–17 HP).
- B-97: „bojují za Divu“. B-98: nad tlačítkem ultimátky je jméno zvířete (Božena, Kvak, Gerta, Rambo, Elvis, Diva,
  Tučňák).
- Kontrolní runy botem po opravách (rychlý mód, 6 seedů): slepice 6/6, kachna 6/6, husa 5/6, krocan 6/6, Elvis 3/6,
  Diva 6/6, tučňák 3/6 – celkem 35/42 (83 %), před opravami 44/56 (79 %). Smoke testy 19/19 (nový test
  `ultimates_regressions` hlídá B-91, B-93, B-94, B-96 a B-98), skill `smoke.py` přes hru 6 scénářů OK.

### Známá omezení a nejistoty
- Balanc je laděný botem a sondami, ne lidmi. Bot mačká ultimátku podle jednoduchých pravidel (HP < 45 %, dav > 18,
  boss) a nemíří Velkou vodou záměrně – člověk ji využije lépe.
- Vzorky botů jsou malé (3–10 seedů na řádek). Rozdíly do ±2 výher jsou šum.
- Android (klasický pygame 2.1) a zvuk poslechem neověřeny; výkon je změřený jen na PC.
- Výzva „Kokrhací mistr“ (10 použití za run) je s husou, tučňákem a Divou (nejkratší doba nabití 12–14 s) v rychlém
  módu těžší než s Elvisem; v plném módu jde se všemi.

## v1.1.0 – Nekonečná noc (3. 10. 2026)

### Co se mění pro hráče
- Nový mód **Nekonečná noc** ve výběru (třetí tlačítko vedle Rychlý/Plný). Zamčený, dokud hráč nevyhraje Plný mód
  (výzva „Celá noc“); zamčené tlačítko po klepnutí řekne, jak ho odemknout.
- Prvních 10 minut běží jako Plný mód. Po porážce Zombie Kohouta slunce nevyjde: banner „NOC 2“, boss bedna,
  další kolo silnějších bossů (Špión → Králík → Medvěd → Alfa → Kohout), opakované elity a formace, lišky dál sílí.
- Run končí jen smrtí nebo vzdáním. HUD ukazuje uběhlý čas, číslo noci a rekord; výsledky „REKORD!“.
- **Noční síla**: když už není co vylepšit, level-up v Nekonečné noci kromě léčení přidá trvale +4 % poškození.
- Nová výzva **Věčná tma**: přežij 15 minut v Nekonečné noci (+500 vajec, +3 zlatá vejce).

### Akceptační kritéria
Viz `UPDATE_PROPOSAL.md` (9 bodů) – hlavně: 0:00–10:00 shodné s Plným módem, ostatní módy bit po bitu beze změny
(stejný seed → stejný výsledek), bot přežije medián 13–18 min a nikdy > 30 min, starý save se načte.

### Návrh
- Data: `game/data/waves.py` – `ENDLESS_CYCLE` (bossové další noci, relativně k porážce Kohouta),
  `ENDLESS_ELITES`, `ENDLESS_EVENT_REPEAT` (formace se opakují po 6 min), `endless_boss_hp(night)`,
  `ENDLESS_NIGHT_MIGHT`, `ENDLESS_DARK`. `game/data/meta.py` – výzva `endless15`. `game/save.py` – `best_time_endless`.
- Jádro: `Director.endless/night/next_night()`; `Run.spawn_boss` (HP podle noci, jiný text příletu),
  `Run.boss_killed` (Kohout v endless = nová noc, ne výhra), `Run._open_levelup` (noční síla),
  `Player.recompute` (násobič síly jen při `night_power > 0`), `ZombieRooster.on_death` (hláška bez svítání).
- Integrace: `RunConfig.record`, `build_config`, `SelectScene` (3 tlačítka módu, zámek), HUD (čas nahoru, noc,
  rekord), `RunRenderer._lighting` (nikdy nesvítá), `progression` (rekord, výzva, počet Kohoutů v odměnách),
  `ResultsScene` (titulek/podtitul/rekord), ikona `moon`.
- Beze změny: hodnoty Rychlého/Plného/Denního/Boss rush, XP křivka, ceny, save formát (jen nový klíč).

### Slices
1. Data + director + run (headless bot přežije 10:00, Kohout padne, přijde noc 2).
2. Výběr, HUD, osvětlení, výsledky, rekord, výzva.
3. Balanc botem (HP bossů po nocích, noční síla).
4. Smoke test `endless_night`, dokumentace.

### Rizika a mitigace
Viz pre-mortem v `UPDATE_PROPOSAL.md`: všechny větve za `mode == "endless"`, determinismus ostatních módů ověřen
otiskem (7 runů, 5 módů), dlouhý běh 25+ min na výkon/paměť, screenshoty UI.

### Rozhodnutí
- Odemčení výzvou „Celá noc“ (výhra Plného módu) – mód je pro hráče s hotovým buildem.
- Nekonečná noc neodemyká mapy ani obtížnosti (jako boss rush); Kohout Elvis se odemkne porážkou Kohouta jako jinde.
- Odměny počítá stávající vzorec (čas, zabití, bossové, mince); každý poražený Kohout se počítá (dřív max. 1).
- Formace, které připadnou na souboj s Kohoutem, v endless propadnou (jinak by po jeho smrti přišly všechny naráz).
- Noční síla nepřerušuje hru (stejně jako dnešní automatické léčení).

### Ladění a testy
- Ladicí vstupy: stávající `python main.py --debug` (F5 další boss, F8 nesmrtelnost, F10 +1 min).
  Test: `python tests/smoke_test.py` (test `endless_night`).
- Bot: `python tools/simulate.py --mode endless --runs 3 -v` (končí v 15:00, viz `max_time`).
- Ladicí hodnoty: `game/data/waves.py` (`ENDLESS_*`, `endless_boss_hp`, `endless_hp_mult`, `ENDLESS_BOSS_GAP`), výzva v `game/data/meta.py`.
- Omezení: rekord je lokální; oživení přes (mock) reklamu se do rekordu počítá jako u ostatních módů.

### Opravy po bug reportu (B-81 – B-85, 4. 10. 2026)
- B-81: HP Kohouta dalších nocí ×2 za noc (dřív ×4), zuření po 150 s (dřív 120 s) – do 3. noci se dá dojít.
- B-82: od 2. noci přijde další boss až po porážce předchozího + 20 s oddechu (`ENDLESS_BOSS_GAP`), mini-bossové ×3.
- B-83: HUD ukazuje čas, noc a rekord i během Kohouta („BOSS! · Noc 2 · rekord …“).
- B-84: HP lišek po 10. minutě roste lineárně (`endless_hp_mult`, +75 % HP z 10. minuty za minutu), od 3. noci
  ×1,5 za noc (`ENDLESS_LATE_NIGHT_HP`), noční síla +4 %. Bot: medián 20 min, 3. noc 8/28, max 33 min.
- B-85: rekord pro každou mapu a obtížnost (`records.endless_best`), „první rekord“ v HUD, banner a fanfára při
  překonání, obrázek ke sdílení „NOVÝ REKORD!“.
