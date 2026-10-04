# Stav hry: LAST CHICKEN (3. 10. 2026, v1.0.6, commit 18e0f4a)

## Co to je
Auto-shooter roguelite (survivors-like) pro mobil na výšku (540×960), vyvíjený a hratelný na PC.
Hráč ovládá jen pohyb (jeden palec), zvíře střílí samo, kokrhání je jediná aktivní schopnost.
Smyčka: přežít noc → level-up karty → build se 6 zbraněmi a 6 pasivkami → evoluce z beden → bossové →
Zombie Kohout za svítání. Pilíře: humor a česká farma proti zombie liškám, pixel art generovaný v kódu,
krátké runy pro mobil, žádné externí assety.

## Technika
- Python 3.11+ a pygame-ce (PC), klasický pygame 2.1 přes python-for-android (APK přes GitHub Actions).
- Vstup `main.py` → `game/app.py:App` (fixní logika 60 Hz, letterbox, crash obrazovka).
- `game/world/run.py:Run` = celá simulace bez renderu (headless bot, testy, `tools/simulate.py`).
- `game/world/director.py` spawny/elity/bossové podle `game/data/waves.py`; bossové `game/world/bosses.py`.
- `game/progression.py` karty, bedny, odměny, výzvy, sbírka; `game/save.py` (atomický zápis, doplňování klíčů).
- Scény `game/scenes/*`, UI `game/ui/*` (HUD, level-up/bedna/pauza), render `game/world/render.py`.
- Testy: `python tests/smoke_test.py` (16 headless testů), `tools/simulate.py` (bot), `tools/screenshots.py`.

## Obsah (inventura)
| Kategorie | Počet | Stav |
|---|---|---|
| Zvířata | 7 (slepice, kachna, husa, krocan, kohout, páv, tajný tučňák) | hotovo, každé s vlastní zbraní a pasivkou |
| Zbraně | 16 × 8 úrovní + 16 evolucí | hotovo |
| Pasivky | 11 × 5 úrovní | hotovo |
| Nepřátelé | 7 běžných + 3 elity + 4 biomové + 2 vyvolávaní | hotovo |
| Bossové | 4 mini-bossové + Zombie Kohout (3 fáze, 5 biomových variant) | hotovo |
| Biomy | 5 (Farma, Les, Město, Hory, Továrna) | hotovo |
| Módy | Rychlý (2:30), Plný (10:00), Denní výzva, Týdenní boss rush | hotovo |
| Obtížnosti | Normal / Hard / Nightmare | hotovo |
| Meta | Hnízdo 6×5, Sbírka 64, 18 výzev, Obchod (skiny, truhly), denní login, sezóny | hotovo |
| Modifikátory | 6 (Splašené lišky, Skleněné kuře, Horda, Obři, Šťastný den, Ohňostroj) | jen v denní výzvě |

## Slíbeno vs. hotovo
- `PLAN.md` „Stav – hotovo“: všech 7 bodů definice hotovo splněno; 5 vln oprav (B-01 – B-80) zapracováno.
- `PLAN.md` „Co by následovalo“: online žebříček (vyžaduje server), skutečné SDK reklam/share (část hotová na
  Androidu), „více evolucí pro kombinace dvou pasivek“, „unikátní finální bossové pro biomy, další biomy“ – nehotové.
- `POLISH_REPORT.md` „Co pořád není store-grade“: zvuk, telegrafy útoků bossů (jednoduché tvary), joystick a
  tlačítko kokrhání (vektorové), ilustrace do obchodu, idle pohyb v podobrazovkách.
- Release (POLISH_REPORT): AAB místo APK, target API 35+, ostrý podpisový klíč – vyžaduje vlastníka/CI.

## Základní měření (baseline, před změnou)
- `tests/smoke_test.py`: **16/16 OK** (chars × biomes 34 s, long_headless_simulation 4,9 s).
- `smoke.py` (sandbox, `--quick`, 3600 snímků): drag i keys bot **OK**, p95 0,97 / 0,90 ms, gc objektů beze změny.
- Screenshoty všech scén: `%TEMP%/…/scratchpad/base_shots/` (menu, výběr, Hnízdo, Sbírka, Výzvy, Denní, Obchod,
  Nastavení, level-up, bedna, boss, pauza) – UI soudržné, čitelné.
- Balanc podle PLAN (bot, Farma, Normal, bez Hnízda): rychlý 72 % výher, plný 9/14, boss rush 13/21.
- B-55: build se v plném módu dokončí zhruba v 9:00–10:20; potom level-upy jen léčí.

## Známé problémy a dluh
- Žádný otevřený nález z BUG_REPORT (B-67 – B-80 opraveno v 18e0f4a).
- `Run.rng` je herní RNG (determinismus denní výzvy) – vizuál nesmí čerpat z něj.
- Smoke test `full_game_flow_through_scenes` je citlivý na spotřebu globálního `random` v menu.
- Android: pomalé `BLEND_MULT`, žádné nové celoobrazovkové alfa vrstvy za snímek.
- Výsledek runu a odemykání závisí na řetězcích módu (`quick | full | daily | bossrush`) na ~25 místech.

## Zážitek hráče
- **Prvních 10 s**: menu s živou scénou, jasné „HRÁT“, výběr zvířete s popisem, nápověda ovládání v prvním runu. Dobré.
- **První 3 minuty**: rychlý mód je svižný, level-upy spojované (B-74), kokrhání čitelné. Dobré.
- **První run → desátý run**: Hnízdo, mapy, zvířata a obtížnosti dávají jasné cíle.
- **Pozdní hra (desítky runů)**: po výhře plného módu na všech mapách a obtížnostech nezbývá mód, kde by hotový
  build měl smysl – každý run končí nejpozději v 10:00 + boss. Hráč nemá „jak dlouho vydržím“ rekord, modifikátory
  jsou zamčené v denní výzvě a level-upy po dokončení buildu jen léčí.

## Pravidla pro změny (co nesahat)
- Herní hodnoty stávajících módů (TIMELINE, bossové, XP křivka, odměny) beze změny.
- Save: jen aditivní klíče s výchozí hodnotou (`save._merge` doplní), žádná migrace.
- `Run` bez pygame Surface práce (headless); vizuál nečerpá `run.rng`.
- Kompatibilita s pygame 2.1 (Android): `device.fblits`, žádné nové blend režimy za snímek.
