# Zpráva o updatu: LAST CHICKEN v1.1.0 – Nekonečná noc (3. 10. 2026)

## Shrnutí
- **Vybráno:** nový mód **Nekonečná noc**, protože po výhře Plného módu chyběl cíl. Bot vyhrál Plný mód 4/4
  s úplně vyvinutým buildem (úroveň 49–58) a hotový build pak neměl kde fungovat.
- **Pro hráče:** po výhře Plného módu se odemkne třetí mód. Prvních 10 minut je stejných jako Plný mód. Potom slunce
  nevyjde a začínají další noci se silnějšími bossy. Hraje se na rekord času, je tu noční síla a nová výzva „Věčná tma“.
- **Vyzkoušet:** `python main.py` → HRÁT → Mód „Noc“. Mód se odemkne výhrou Plného módu.
- **Ověřeno:** 17/17 smoke testů, 35/35 kombinací zvíře × biom, ostatní módy bit po bitu shodné se starou verzí,
  25 min renderovaný běh bez propadů.
- **Nejisté:** balanc je laděný jen botem. Nikdo to zatím nehrál rukama a na Androidu to neběželo.

## Záloha staré verze
Cesta: `C:\Users\tadea\Desktop\chicken pop_backup_20261003-212221`. Záloha má 161 souborů a hash manifest.
Příkaz `versions.py verify` vrátil „backup intact: YES“.
Git: nic nebylo commitnuto. HEAD je pořád `18e0f4a` („git HEAD unchanged: YES“). Všechny změny jsou neuložené
v pracovní kopii, commit je na tobě.

## Co se změnilo (`versions.py diff`: 3 nové, 18 změněných, +485 / −20 řádků)
| Soubor | Proč |
|---|---|
| `game/data/waves.py` +23 | Ladicí tabulky endless: cyklus bossů a elit další noci, opakování formací, násobiče HP, noční síla, dřívější zuření Kohouta, tma |
| `game/world/director.py` +16 | `endless`, `night`, `next_night()`, opakované formace (během Kohouta propadnou) |
| `game/world/run.py` +28 | HP podle noci a rampy, Kohout v endless = nová noc (bedna, banner, hudba), noční síla v level-upu, `RunConfig.record` |
| `game/world/bosses.py` +9 | Hláška Kohouta bez svítání, zuření od 2. noci po 120 s |
| `game/world/player.py` +3 | Násobič síly, jen když `night_power > 0` |
| `game/world/render.py` +3 | V endless se osvětlení zastaví před svítáním |
| `game/ui/hud.py` +10 | Čas běží nahoru, pod ním „Noc N · rekord m:ss“ nebo „REKORD!“ |
| `game/scenes/select.py` +20/−8 | Tři tlačítka módu, zamčený mód s toastem, ikona měsíce, rekord v podtitulu |
| `game/scenes/results.py` +11 | Titulek „REKORD!“, podtitul s nocí a rekordem, zpráva o novém rekordu |
| `game/scenes/game.py` +2 | Rekord jde do `RunConfig` |
| `game/progression.py` +10/−3 | Uložení rekordu, výzva `endless15`, `endless_unlocked()`, počítání více Kohoutů v odměnách |
| `game/save.py` +1 | Nový klíč `records.best_time_endless` (starý save ho dostane doplněný) |
| `game/data/meta.py` +3 | Výzva „Věčná tma“, konstanty odemčení a cíle |
| `game/gfx/icons.py` +12 | Pixelová ikona `moon` |
| `game/config.py` | Verze 1.0.6 → 1.1.0 |
| `tests/smoke_test.py` +113 | Nový test `endless_night` |
| README, PLAN, FEATURES, GAME_STATE, UPDATE_PROPOSAL | Dokumentace |

**Změny existujícího chování (před → po):**
- Výběr módu: dvě tlačítka (polovina šířky, ikona ×3) → tři tlačítka (třetina šířky, ikona ×2). Texty jsou stejné.
- Odměny: `compute_rewards` počítá Kohouty přes `count()` místo `in`. V ostatních módech padne nejvýš jeden, takže
  výsledek je stejný.
- Počet výzev 18 → 19.
- Herní hodnoty Rychlého, Plného, Denního módu a Boss rush: **beze změny** (ověřeno otiskem determinismu, viz níže).

## Jak to vyzkoušet
```bash
python main.py                      # HRÁT → Mód „Noc“ (zamčený do výhry Plného módu, klepnutí řekne proč)
python tests/smoke_test.py          # 17 testů vč. endless_night
python tools/simulate.py --mode endless --runs 3 -v   # bot (končí v 15:00)
```
Pro rychlou zkoušku bez výhry: v `save.json` přidej do `"challenges"` položku `"full_night": true`
(nebo vyhraj Plný mód).

## Důkazy (ověření)
| Kritérium (UPDATE_PROPOSAL) | Výsledek | Důkaz |
|---|---|---|
| 1. Zámek a výběr, pamatuje se | ✅ | Test `endless_night`; screenshoty zamčeného (s toastem) i odemčeného výběru |
| 2. 0:00–10:00 = Plný mód | ✅ | Test: `director.bosses == BOSSES_FULL`, `elites == ELITES_FULL`, `final_time == 600` |
| 3. Kohout → noc 2, bedna, silnější bossové | ✅ | Test: `victory False`, `night == 2`, Špión 2. noci má HP 2000 × 4; screenshot banneru „NOC 2 / Slunce nevyšlo…“ |
| 4. Konec jen smrtí, výsledky, uložený rekord | ✅ | Test: `new_record`, `best_time_endless == 960`, výzva splněna; screenshot výsledků „REKORD!“ |
| 5. HUD: čas, noc, rekord | ✅ | Screenshoty v 0:39 („Noc 1 · rekord 16:52“) a ve 12:08 („Noc 2 · …“) |
| 6. Bot: medián 13–18 min, nikdy > 30 | ✅ (těsně) | Slepice bez Hnízda: 10:47 / 14:52 / 16:07 / **17:51** / 19:21 / 29:40 (6 seedů) |
| 7. Ostatní módy beze změny | ✅ | 7 seedovaných runů (rychlý ×3, plný ×2, boss rush, denní s modifikátorem): výstup starý = nový znak po znaku |
| 8. Smoke + screenshoty | ✅ | 17/17 (baseline 16/16); screenshoty výběru, HUD, Kohouta, noci 2, výsledků a výzev zkontrolované |
| 9. Starý save | ✅ | Test: save bez nového klíče se načte s výchozí 0, ostatní hodnoty zůstanou; skutečný `save.json` netknutý (stejný SHA-1 před i po) |

**Další měření**
- Balanc botem (Farma, Normal): Hnízdo 3 → medián 19:47; kachna 18:57; husa 13:42; krocan (Les, Hnízdo 2) 19:06.
  Konec obvykle přijde při zuřícím Kohoutovi 2. noci; noc 3 se dosáhla ve 3 z 22 runů.
- Výkon, renderovaný běh 25 min (god mód, až 404 nepřátel v noci 3): render p95 **2,48 ms**, logika p95 **1,14 ms**,
  max. 5,5 ms. Plný mód ve stejném měření: 2,72 / 0,84 ms.
- Paměť: žádný únik. Růst objektů tvoří živí nepřátelé, pickupy (mají strop) a navštívené chunky mapy (+2 za minutu).
  Chunky rostou stejně i v Plném módu, je to existující chování.
- Skill `smoke.py` (sandbox, `--quick`, 3600 snímků): starý p95 0,89 / 0,84 ms, nový 0,88 / 0,82 ms. `compare_runs`
  (menu, 3 seedy): bez regresí.
- Matice: 7 zvířat × 5 biomů v endless s renderem, přechod do 2. noci (biomová varianta Kohouta) a všech 5 bossů
  2. noci naráz → 35/35 bez chyby.
- game-bug-hunter jen na změnách: 0 chyb. Ke zvážení zůstaly 2 záměry (viz Nedodělky).

## Rozhodnutí, která jsem udělal sám (můžeš je zvrátit)
- Odemčení výhrou Plného módu (`meta.ENDLESS_UNLOCK`). Mód je pro hráče s hotovým buildem.
- Tlačítko se jmenuje „Noc“ (celé „Nekonečná noc“ se na šířku třetiny nevejde); v HUD, toastu a výsledcích je celé jméno.
- Ladění: HP bossů ×4 za noc, lišky od 10. minuty +20 % HP za minutu, Kohout od 2. noci zuří po 2 min, noční síla
  +2 % za level. Vše je v `game/data/waves.py`.
- Během souboje s Kohoutem formace propadnou. Jinak by po jeho smrti přišly všechny najednou.
- Nekonečná noc neodemyká mapy ani obtížnosti. Kohout Elvis se odemkne porážkou Kohouta jako jinde.
- Odměny počítá stávající vzorec, bez bonusu za výhru. Každý Kohout dá 250 vajec a 2 zlatá vejce.
- Verze 1.1.0 je jen lokálně. GitHub Actions dál přepisuje verzi na `1.0.<build>` (workflow jsem neměnil).

## Nedodělky a rizika
- **Balanc je jen z bota.** Bot kituje, člověk hraje jinak (hlavně husa). Medián 17:51 je na horní hraně cíle a jeden
  seed došel do 29:40. Po prvních hrách stačí upravit `ENDLESS_HP_RAMP` nebo `endless_boss_hp`.
- Oživení přes (falešnou) reklamu se počítá do rekordu, stejně jako u ostatních rekordů času. Pokud chceš „čistý“
  rekord, zakaž revive v endless (`scenes/game.py:185`).
- V prvním endless runu HUD neukazuje „REKORD!“ (rekord je 0), výsledky ano.
- Na Androidu (pygame 2.1) jsem nic nespouštěl. Nové jsou jen texty, ikona a tři tlačítka, žádné nové blend režimy.
- Hudba a zvuky jsou stávající (fanfára při nové noci, návrat hudby biomu). Poslech jsem neověřoval.
- **Existující nález mimo rozsah:** `game/world/allies.py:132` používá `id(self)` (adresu v paměti) pro bloudění
  spřátelených lišek. Runy se stejným seedem proto nejsou mezi spuštěními totožné, což se týká i denní výzvy.
  Neopraveno. Pro srovnání starý/nový jsem `id` v sondě nahradil stabilním pořadím.

## Další kroky (žebříček příště)
1. **C2 Prokletí** (61 b.): 6 hotových modifikátorů denní výzvy volitelných pro běžné runy za bonus odměn. Hodí se
   i k Nekonečné noci (rekord pro každé prokletí).
2. **C3 Pixel-art telegrafy útoků bossů** (55 b.): POLISH_REPORT je uvádí jako nejvíc „prototypové“. V delších
   nocích je bossů víc, takže čitelnost bude vadit víc.
3. **C4 Duo-evoluce ze dvou pasivek** (54 b.): plánované v PLAN „Co by následovalo“. Přidá hloubku buildu, který
   v endless žije déle.
- Malý úkol: opravit `allies.py:132` (stabilní fáze místo `id(self)`) kvůli determinismu denní výzvy.

## Jak se vrátit ke staré verzi
Záloha nemá `.git`, venv ani cache. Po návratu případně `pip install -r requirements.txt`.

Windows (PowerShell):
```
# 1) Přejmenuj aktuální projekt (nic nemaž)
Rename-Item "C:\Users\tadea\Desktop\chicken pop" "chicken pop_NOVA_verze"
# 2) Zkopíruj zálohu jako projekt
Copy-Item "C:\Users\tadea\Desktop\chicken pop_backup_20261003-212221" "C:\Users\tadea\Desktop\chicken pop" -Recurse
# 3) Git historii vrať z přejmenované složky (záloha .git nemá)
Copy-Item "C:\Users\tadea\Desktop\chicken pop_NOVA_verze\.git" "C:\Users\tadea\Desktop\chicken pop\.git" -Recurse
```
Linux/macOS:
```
mv "chicken pop" "chicken pop_NOVA_verze"
cp -r "chicken pop_backup_20261003-212221" "chicken pop"
cp -r "chicken pop_NOVA_verze/.git" "chicken pop/.git"
```
Protože nic není commitnuté, jde to i přes git: `git stash` nebo `git checkout -- .` vrátí změněné soubory
(nové soubory FEATURES.md, GAME_STATE.md, UPDATE_PROPOSAL.md, EVOLUTION_*.md a `.evolve/` pak smaž ručně).
Jednotlivý soubor: `python <skill>/scripts/versions.py restore-file "<záloha>" <cesta>`.
Uložená hra zůstane kompatibilní oběma směry: stará verze nový klíč `best_time_endless` jen ignoruje.
