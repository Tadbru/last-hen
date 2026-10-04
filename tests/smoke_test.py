"""Headless smoke testy celé hry.

    python tests/smoke_test.py          # vše
    python tests/smoke_test.py fast     # zkrácená verze

Testuje: start App + menu, všechny scény a tlačítka, všechna zvířata × biomy (bot + render),
všech 32 zbraní, všechny bossy (výhra i prohra), save/load vč. poškozeného souboru, progresi
(karty, rerol, skip, banish, bedny, evoluce), denní obsah, sdílení PNG, výsledky.
"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

FAST = "fast" in sys.argv
TMP = tempfile.mkdtemp(prefix="lastchicken_")
RESULTS: list[tuple[str, bool, str]] = []


def test(fn):
    name = fn.__name__
    t0 = time.perf_counter()
    try:
        fn()
        RESULTS.append((name, True, f"{time.perf_counter() - t0:.1f}s"))
        print(f"[OK]   {name} ({time.perf_counter() - t0:.1f}s)")
    except Exception:
        RESULTS.append((name, False, traceback.format_exc()))
        print(f"[FAIL] {name}\n{traceback.format_exc()}")
    return fn


_app = None


def app():
    global _app
    if _app is None:
        from game import config
        config.SHARES_DIR = os.path.join(TMP, "shares")
        import game.share as share
        share.SHARES_DIR = config.SHARES_DIR
        from game.app import App
        _app = App(headless=True, save_path=os.path.join(TMP, "save.json"), persist=True)
    return _app


def steps(a, n: int, render_every: int = 3) -> None:
    from game.config import DT
    for i in range(n):
        a.step(DT)
        if i % render_every == 0:
            a.render()


# ---------------------------------------------------------------------------------------------
@test
def boot_and_menu():
    a = app()
    from game.scenes.menu import MenuScene
    assert isinstance(a.scene, MenuScene)
    steps(a, 120)


@test
def font_czech():
    from game import assets
    f = assets.font
    txt = "Příliš žluťoučký kůň úpěl ďábelské ódy ÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ áčďéěíňóřšťúůýž 0123456789 „“ ✓ ♥ ★"
    for ch in txt:
        if ch != " ":
            assert ch in f.glyphs, f"chybí glyf {ch!r}"
    img = f.render(txt, (255, 255, 255), 2)
    assert img.get_width() > 100


def _click_all(a, scene_cls, *args, skip=()):
    from game.scenes.base import Ev
    sc = scene_cls(a, *args)
    a.set_scene(sc)
    steps(a, 10)
    n = len(sc.buttons)
    for i in range(n):
        sc = scene_cls(a, *args)
        a.set_scene(sc)
        b = sc.buttons[i]
        if not b.visible or not b.enabled or b.text in skip or b.icon == "back":
            continue
        cx, cy = b.rect.center
        sc.handle(Ev("down", cx, cy))
        sc.handle(Ev("up", cx, cy))
        steps(a, 4)
        # potvrdit případný dialog prvním tlačítkem
        cur = a._next or a.scene
        if getattr(cur, "modal", None) is not None and cur.modal.buttons:
            bb = cur.modal.buttons[0]
            cur.handle(Ev("down", *bb.rect.center))
            cur.handle(Ev("up", *bb.rect.center))
            steps(a, 4)
        a._next = None
        a._fade_dir = 0
        a._fade = 0


@test
def all_scenes_and_buttons():
    a = app()
    a.save["eggs"] = 99999
    a.save["gold"] = 99
    a.save["tokens"] = 5
    from game.scenes import challenges, collection, daily, menu, nest, select, settings, shop
    menu.MenuScene.suppress_login = True
    for cls in (menu.MenuScene, select.SelectScene, nest.NestScene, collection.CollectionScene,
                challenges.ChallengesScene, daily.DailyScene, shop.ShopScene, settings.SettingsScene):
        _click_all(a, cls, skip=("Smazat postup",))
    # scroll + výběr ve sbírce
    from game.scenes.base import Ev
    sc = collection.CollectionScene(a)
    a.set_scene(sc)
    for t in ("enemies", "bosses", "weapons", "evolutions", "passives"):
        sc.set_tab(t)
        sc.handle(Ev("down", 60, 260))
        sc.handle(Ev("up", 60, 260))
        sc.handle(Ev("wheel", dy=-3))
        steps(a, 3)
    # klepání na logo → tučňák
    sc = menu.MenuScene(a)
    a.set_scene(sc)
    for _ in range(10):
        sc.handle(Ev("down", 270, 180))
        sc.handle(Ev("up", 270, 180))
    assert "penguin" in a.save["unlocked_chars"]
    steps(a, 5)


@test
def chars_x_biomes():
    from game.bot import Bot
    from game.config import DT
    from game.data.biomes import BIOME_ORDER
    from game.data.characters import CHAR_ORDER
    from game.ui import hud
    from game.core.input import Joystick
    from game.world.render import RunRenderer
    from game.world.run import Run, RunConfig
    surf = pygame.Surface((540, 960))
    joy = Joystick()
    ticks = 900 if FAST else 2400
    for ci, ch in enumerate(CHAR_ORDER):
        for bi, bm in enumerate(BIOME_ORDER):
            run = Run(RunConfig(character=ch, biome=bm, mode="full" if (ci + bi) % 2 else "quick", seed=ci * 7 + bi,
                                skin=["pirate", "cowboy", "astronaut", "ninja", "pumpkin", "santa", "bunny", "crown",
                                      "halo"][ci % 9],
                                season=[None, "halloween", "christmas", "easter", None][bi]))
            run.time = 100 + bi * 60
            ren = RunRenderer(run)
            bot = Bot(run)
            for i in range(ticks):
                bot.step(DT)
                if run.state == "dead":
                    run.revive()
                if i % 6 == 0:
                    ren.draw(surf, DT)
                    hud.draw_hud(surf, run, joy, i * DT)


@test
def all_weapons_max_and_evolved():
    from game.config import DT
    from game.data.weapons import WEAPONS
    from game.world.render import RunRenderer
    from game.world.run import Run, RunConfig
    surf = pygame.Surface((540, 960))
    for wid, d in WEAPONS.items():
        run = Run(RunConfig(character=d.owner or "hen", seed=3))
        run.god = True
        for w in list(run.weapons):
            w.on_remove()
        run.weapons = []
        run.add_weapon(wid, 1 if d.evolution else 8)
        for i in range(60):
            a = i * math.tau / 60
            run.spawn_enemy("fox", math.cos(a) * (80 + i * 3), math.sin(a) * (80 + i * 3))
        run.spawn_prop(60, 60, None)
        ren = RunRenderer(run)
        for i in range(500 if not FAST else 250):
            run.update(DT, math.cos(i * 0.05), math.sin(i * 0.05))
            if run.state in ("levelup", "chest"):
                run.pending_levelups = 0
                run.pending_chests.clear()
                run.state = "playing"
            if i % 5 == 0:
                ren.draw(surf, DT)
        assert run.weapon(wid) is not None


@test
def evolution_via_chest():
    from game import progression
    from game.data.weapons import BASE_WEAPONS, STARTER_WEAPONS, WEAPONS
    from game.world.run import Run, RunConfig
    for wid in BASE_WEAPONS + STARTER_WEAPONS:
        d = WEAPONS[wid]
        run = Run(RunConfig(character=d.owner or "hen", seed=1))
        if run.weapon(wid) is None:
            run.add_weapon(wid, 8)
        run.weapon(wid).set_level(8)
        run.add_passive(d.evo_passive, 1)
        assert wid in run.evolvable(), wid
        res = progression.open_chest(run, "elite")
        assert res["evolution"] == d.evo_to, (wid, res)
        assert run.weapon(d.evo_to) is not None


@test
def cards_reroll_skip_banish():
    from game import progression
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(seed=4, rerolls=3, banishes=2))
    for _ in range(80):
        run.pending_levelups += 1
        run._open_levelup()
        if not progression.has_choices(run):
            # všechno vylepšeno → levelup jen vyléčí a hru nepřeruší
            assert run.state == "playing" and run.pending_levelups == 0
            continue
        offer = run.offer
        assert 1 <= len(offer) <= 3
        r = random.random()
        if r < 0.1 and run.rerolls:
            assert progression.reroll(run)
        elif r < 0.15 and run.banishes and offer[0].kind in ("weapon", "passive"):
            assert progression.banish(run, offer[0])
            assert offer[0].id in run.banished
        elif r < 0.2:
            progression.skip(run)
            continue
        progression.apply_card(run, run.offer[random.randrange(len(run.offer))])
    assert len(run.weapons) <= 6 and len(run.passives) <= 6
    # při plném buildu: výplň je jen léčení a levelup hru nepřeruší
    for w in run.weapons:
        if not w.evolved:
            w.set_level(8)
    for pid in list(run.passives):
        run.passives[pid] = 5
    run.banished.update(["egg", "crow_wave", "chick_army", "shuriken", "laser", "nest", "lightning", "stink",
                         "wolf_howl", "sky_cake", "water_pistol", "beak_whip", "feather_shotgun", "sound_waves",
                         "fan_tail", "fish"] + list(progression.PASSIVE_ORDER))
    offer = progression.make_offer(run)
    assert [c.kind for c in offer] == ["heal"], offer
    run.player.hp = 10
    run.pending_levelups = 2
    run._open_levelup()
    assert run.state == "playing" and run.pending_levelups == 0 and run.player.hp > 10


def _boss_fight(boss: str, mode: str, win: bool) -> None:
    from game.bot import Bot
    from game.config import DT
    from game.world.render import RunRenderer
    from game.world.run import Run, RunConfig
    surf = pygame.Surface((540, 960))
    run = Run(RunConfig(character="hen", biome="farm", mode=mode, seed=8))
    run.add_weapon("lightning", 8)
    run.add_weapon("egg", 8)
    run.time = 300
    run.director.bosses = []
    run.spawn_boss(boss)
    ren = RunRenderer(run)
    bot = Bot(run)
    run.god = win
    for i in range(1500 if not FAST else 700):
        bot.step(DT)
        if i % 5 == 0:
            ren.draw(surf, DT)
        if run.state in ("dead", "victory"):
            break
    if win:
        for c in list(run.bosses):
            # projít všemi fázemi
            for _ in range(10):
                if c.e.alive:
                    run.damage_enemy(c.e, c.e.max_hp * 0.2, None, crit=False)
                    for _ in range(120):
                        bot.step(DT)
        for _ in range(400):
            bot.step(DT)
            if run.state == "victory":
                break
        if boss == "zombie_rooster":
            assert run.state == "victory", run.state
        else:
            assert boss in run.bosses_killed
    else:
        run.player.invuln = 0.0          # smrtelný zásah nesmí padnout do krátké nesmrtelnosti po předchozím zásahu
        run.player.take_damage(1e9)
        for _ in range(200):
            run.update(DT)
        assert run.state == "dead", run.state


@test
def bosses_win_and_lose():
    for b in ("spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster"):
        _boss_fight(b, "full", True)
    _boss_fight("zombie_rooster", "quick", True)
    _boss_fight("zombie_rooster", "quick", False)
    _boss_fight("rabbit", "full", False)


def tick(run, mx=0.0, my=0.0):
    from game import progression
    from game.config import DT
    run.update(DT, mx, my)
    if run.state == "levelup":
        progression.apply_card(run, run.offer[0])
    elif run.state == "chest":
        run.resume()


@test
def final_boss_variants_all_biomes():
    from game.data.biomes import BIOME_ORDER
    from game.world.run import Run, RunConfig
    for bm in BIOME_ORDER:
        run = Run(RunConfig(biome=bm, mode="quick", seed=2))
        run.god = True
        run.spawn_boss("zombie_rooster")
        c = run.final_boss
        phases = set()
        for ph in (1, 2, 3):
            for _ in range(400):
                tick(run, 0.3, -0.2)
                phases.add(c.phase)
            run.damage_enemy(c.e, c.e.max_hp * 0.35, None, crit=False)
        for _ in range(200):
            tick(run)
        assert phases == {1, 2, 3}, phases
        run.damage_enemy(c.e, 1e9, None, crit=False)
        for _ in range(250):
            tick(run)
        assert run.state == "victory", (bm, run.state)


@test
def full_game_flow_through_scenes():
    """Menu → výběr → hra (bot) → smrt → reklama oživení → výsledky → znovu."""
    a = app()
    from game.bot import Bot
    from game.config import DT
    from game.scenes.game import GameScene, build_config
    from game.scenes.results import ResultsScene
    gs = GameScene(a, build_config(a, "hen", "farm", "quick"))
    a.set_scene(gs)
    bot = Bot(gs.run)
    for i in range(1200):
        if gs.run.state == "levelup":
            gs.overlay.on_key(pygame.K_1)
        elif gs.run.state == "chest":
            a.step(DT)
            for _ in range(80):
                a.step(DT)
            if gs.overlay is not None and hasattr(gs.overlay, "_close"):
                gs.overlay._close()
        else:
            mx, my, crow = bot.control(DT)
            gs.joy.vx, gs.joy.vy = mx, my
            gs.crow_pressed = crow
        a.step(DT)
        if i % 4 == 0:
            a.render()
    gs.run.player.invuln = 0.0
    gs.run.player.take_damage(1e9)
    for _ in range(200):
        a.step(DT)
    assert gs.modal is not None, "chybí dialog oživení"
    gs._ad_revive()
    for _ in range(220):
        a.step(DT)
    assert gs.run.revived and not gs.run.player.dead, gs.run.state
    gs.give_up()
    for _ in range(40):
        a.step(DT)
        a.render()
    rs = a.scene
    assert isinstance(rs, ResultsScene), type(rs)
    rs.share()
    rs.ad_double()
    for _ in range(220):
        a.step(DT)
        a.render()
    assert rs.doubled
    rs.again()
    for _ in range(30):
        a.step(DT)
    assert isinstance(a.scene, GameScene)
    # pauza a vzdání (nejdřív vyřídit případný bonusový levelup z rubber-bandingu)
    from game import progression
    for _ in range(10):
        if a.scene.run.state == "levelup":
            progression.apply_card(a.scene.run, a.scene.run.offer[0])
        a.step(DT)
    a.scene.pause()
    a.render()
    a.scene.overlay._quit()
    assert a.scene.modal is not None, "Vzdát se musí chtít potvrzení"
    from game.scenes.base import Ev
    bb = a.scene.modal.buttons[0]
    a.scene.handle(Ev("down", *bb.rect.center))
    a.scene.handle(Ev("up", *bb.rect.center))
    for _ in range(40):
        a.step(DT)
    assert isinstance(a.scene, ResultsScene)


@test
def save_load_and_corruption():
    from game.save import SaveData
    p = os.path.join(TMP, "s1.json")
    s = SaveData(p)
    s["eggs"] = 1234
    s["unlocked_chars"].append("duck")
    s.discover("enemies", "fox")
    s.save()
    s2 = SaveData(p)
    assert s2["eggs"] == 1234 and "duck" in s2["unlocked_chars"] and s2.is_discovered("enemies", "fox")
    # poškozený soubor
    with open(p, "w", encoding="utf-8") as f:
        f.write("{ tohle není json ]")
    s3 = SaveData(p)
    assert s3["eggs"] == 0 and s3.load_error
    assert any(n.startswith("s1.json.corrupt") for n in os.listdir(TMP))
    # špatné typy
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"eggs": "hodně", "settings": [], "meta": {"hp": 2}}, f)
    s4 = SaveData(p)
    assert s4["eggs"] == 0 and isinstance(s4.settings, dict) and s4["meta"]["hp"] == 2


@test
def daily_and_weekly():
    a = app()
    from game import progression
    spec = progression.daily_spec()
    assert spec["seed"] == int(progression.today().strftime("%Y%m%d"))
    assert progression.daily_spec() == spec        # deterministické
    board = progression.daily_leaderboard(a.save, spec)
    assert len(board) == 9 or len(board) == 10
    a.save["daily"]["login_last"] = ""
    rw = progression.daily_login(a.save)
    assert rw and rw["streak"] >= 1
    assert progression.daily_login(a.save) is None
    from game.config import DT
    from game.scenes.game import GameScene, build_config
    cfg = build_config(a, spec["character"], spec["biome"], "daily", "normal", (spec["modifier"],), spec["seed"])
    gs = GameScene(a, cfg)
    a.set_scene(gs)
    for _ in range(300):
        a.step(DT)
        if gs.run.state == "levelup":
            from game import progression as pg
            pg.apply_card(gs.run, gs.run.offer[0])
    for mod in ("speedy", "glass", "horde", "giants", "lucky", "explosive"):
        from game.world.run import Run, RunConfig
        r = Run(RunConfig(mode="daily", modifiers=(mod,), seed=5))
        for _ in range(300):
            r.update(DT, 0.5, 0.5)
            if r.state == "levelup":
                progression.apply_card(r, r.offer[0])
    cfg = build_config(a, "hen", "farm", "bossrush")
    gs = GameScene(a, cfg)
    a.set_scene(gs)
    assert cfg.bonus_levels == 10
    assert gs.run.level == 11, gs.run.level       # bonusové levelupy zvedají úroveň (dřív „Úroveň -6“)
    for _ in range(1100):
        a.step(DT)
        if gs.run.state == "levelup":
            progression.apply_card(gs.run, gs.run.offer[0])
    assert gs.run.bosses, "boss rush nespawnul bosse"


@test
def results_rewards_and_unlocks():
    a = app()
    from game import progression
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(seed=1, mode="full"))
    run.time = 640
    run.kills = 1200
    run.victory = True
    run.bosses_killed = ["spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster"]
    rw = progression.compute_rewards(run)
    eggs0 = a.save["eggs"]
    msgs = progression.apply_results(a.save, run, rw)
    assert a.save["eggs"] >= eggs0 + rw["eggs"]
    assert "rooster" in a.save["unlocked_chars"]
    assert "peacock" in a.save["unlocked_chars"]          # výzva Tisíc lišek
    assert "forest" in a.save["unlocked_maps"]
    assert "hard" in a.save["unlocked_diffs"]
    assert any("Tisíc" in m for m in msgs)


@test
def share_png():
    a = app()
    from game.share import make_share_image, share_text
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(seed=1))
    run.time = 462
    run.kills = 1284
    assert share_text(run) == "Přežila jsem 7:42 a zabila 1 284 lišek!"
    path = make_share_image(run, True)
    assert os.path.exists(path)
    _ = a


@test
def crash_screen_and_log():
    a = app()
    import game.app as gapp
    log = os.path.join(TMP, "crash.log")
    gapp.CRASH_LOG = log
    from game.config import DT
    from game.scenes.error import ErrorScene
    from game.scenes.menu import MenuScene
    sc = MenuScene(a)
    a.set_scene(sc)

    def boom(dt):
        raise RuntimeError("testovací výjimka")
    sc.update = boom
    assert not a.safe(a.step, DT)
    assert isinstance(a.scene, ErrorScene)
    assert os.path.exists(log) and "testovací výjimka" in open(log, encoding="utf-8").read()
    a.render()
    a.scene.back()
    a.step(DT)
    assert isinstance(a.scene, MenuScene)


@test
def endless_night():
    """Nekonečná noc: zámek, 1. noc = Plný mód, Kohout nevyhrává run, další noc, noční síla, rekord, výsledky."""
    a = app()
    from game import progression
    from game.bot import Bot
    from game.config import DT
    from game.data import waves as WV
    from game.data.passives import MAX_PASSIVE_LEVEL, PASSIVE_ORDER
    from game.data.weapons import BASE_WEAPONS, MAX_WEAPON_LEVEL
    from game.scenes.game import GameScene, build_config
    from game.scenes.results import ResultsScene
    from game.scenes.select import SelectScene
    from game.world.run import Run, RunConfig
    s = a.save
    # zámek: bez výzvy „Celá noc“ nejde vybrat
    s["challenges"].pop("full_night", None)
    sel = SelectScene(a)
    a.set_scene(sel)
    assert not sel.b_endless.enabled and sel.b_endless.sub == "zamčeno"
    s["challenges"]["full_night"] = True
    sel = SelectScene(a)
    a.set_scene(sel)
    assert sel.b_endless.enabled
    sel.b_endless.click()
    assert sel.mode == "endless"
    # 1. noc má stejný rozpis jako Plný mód
    run = Run(RunConfig(mode="endless", seed=3, headless=True))
    run.god = True                  # slepice bez buildu by v 10:00 nepřežila – test hlídá logiku nocí
    assert run.director.bosses == list(WV.BOSSES_FULL) and run.director.elites == list(WV.ELITES_FULL)
    assert run.director.final_time == WV.FULL_LENGTH
    # Kohout padne → žádné vítězství, začne 2. noc se silnějšími bossy
    run.time = 600.0
    run.director.bosses = []        # rozpis 1. noci ověřen výše; Kohout se spawne ručně
    run.director.elites = []
    run.spawn_boss("zombie_rooster")
    ctrl = run.final_boss
    ctrl.state = "fight"
    for _ in range(3):
        if ctrl.e.alive:
            run.damage_enemy(ctrl.e, ctrl.e.max_hp, None, crit=False)
            ctrl.state = "fight"
            ctrl.invuln = 0.0
            for _ in range(120):
                run.update(DT)
                if run.state == "levelup":
                    progression.apply_card(run, run.offer[0])
                elif run.state == "chest":
                    run.resume()
    assert "zombie_rooster" in run.bosses_killed, run.bosses_killed
    assert not run.victory and run.state in ("playing", "chest", "levelup"), run.state
    assert run.arena is None and run.final_boss is None
    assert run.director.night == 2
    assert [b for _, b in run.director.bosses] == [b for _, b in WV.ENDLESS_CYCLE]
    run.director.bosses = [(run.time, "spy_fox")]
    run.update(DT)
    spy = next(c for c in run.bosses if c.e.state == "spy_fox")
    assert abs(spy.e.max_hp - 2000 * WV.endless_boss_hp(2)) < 1, spy.e.max_hp
    # od 2. noci další boss počká, dokud předchozí žije, a po jeho porážce přijde až po oddechu (B-82)
    run.director.bosses = [(run.time, "rabbit")]
    for _ in range(10):
        run.update(DT)
        if run.state == "levelup":
            progression.apply_card(run, run.offer[0])
        elif run.state == "chest":
            run.resume()
    assert not any(c.e.state == "rabbit" for c in run.bosses), "boss 2. noci přišel, i když předchozí žije"
    spy.state, spy.invuln = "fight", 0.0
    run.damage_enemy(spy.e, spy.e.hp + 1, None, crit=False)
    assert not spy.e.alive
    assert run.director.bosses[0][0] >= run.time + WV.ENDLESS_BOSS_GAP - 0.01, run.director.bosses
    run.director.bosses = []
    # noční síla: hotový build → level-up přidá sílu, nepřeruší hru
    for wid in BASE_WEAPONS:
        if len(run.weapons) >= 6:
            break
        if run.weapon(wid) is None:
            run.add_weapon(wid, MAX_WEAPON_LEVEL)
    for w in run.weapons:
        w.set_level(MAX_WEAPON_LEVEL)
    for pid in PASSIVE_ORDER[:6]:
        run.add_passive(pid, MAX_PASSIVE_LEVEL)
    might0 = run.player.stats.might
    run.state = "playing"
    run.pending_levelups = 2
    run.pause_cd = 0.0
    run.update(DT)
    assert run.state == "playing" and run.night_power == 2, (run.state, run.night_power)
    assert abs(run.player.stats.might - might0 * (1 + 2 * WV.ENDLESS_NIGHT_MIGHT)) < 1e-6
    # celý run ve scéně s botem, pak smrt → výsledky, rekord a výzva
    s["records"]["best_time_endless"] = 0
    s["records"]["endless_best"] = {}
    gs = GameScene(a, build_config(a, "hen", "farm", "endless", seed=8))
    a.set_scene(gs)
    bot = Bot(gs.run)
    for i in range(1200):
        bot.step(DT)
        if i % 4 == 0:
            a.render()
    gs.run.time = WV.FULL_LENGTH * 1.6
    gs.run.revived = True
    gs.run.player.invuln = 0.0
    gs.run.player.take_damage(1e9)
    for _ in range(200):
        a.step(DT)
        if isinstance(a.scene, ResultsScene):
            break
    for _ in range(60):
        a.step(DT)
    a.render()
    assert isinstance(a.scene, ResultsScene), type(a.scene)
    assert a.scene.new_record
    assert s["records"]["best_time_endless"] == 960, s["records"]["best_time_endless"]
    # rekord se vede i pro mapu a obtížnost (B-85)
    assert progression.endless_record(s, "farm", "normal") == 960, s["records"]["endless_best"]
    assert progression.endless_record(s, "factory", "nightmare") == 0
    assert s["challenges"].get("endless15")
    # odměny počítají každého poraženého Kohouta
    r2 = Run(RunConfig(mode="endless", seed=1))
    r2.bosses_killed = ["zombie_rooster", "spy_fox", "zombie_rooster"]
    rw = progression.compute_rewards(r2)
    assert rw["gold"] == 1 + 2, rw          # zlatá vejce za každého bosse jen jednou (Kohout jednou na mapu)
    # starý save bez klíče rekordu se načte s výchozí hodnotou
    from game.save import SaveData
    old = os.path.join(TMP, "old_save.json")
    with open(old, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "eggs": 5, "records": {"runs": 3}}, f)
    sd = SaveData(old)
    assert sd["records"]["best_time_endless"] == 0 and sd["records"]["runs"] == 3 and sd["eggs"] == 5


@test
def ultimates():
    """Ultimátky: každé zvíře jinou (data + efekt + ikona + zvuk), aktivace v davu s renderem a HUD, pauza
    uprostřed efektu, strop poškození bosse, smrt uprostřed efektu, oživení = ultimátka zdarma."""
    from game import assets, scenarios as SC
    from game.config import DT
    from game.core.input import Joystick
    from game.data.characters import CHAR_ORDER
    from game.data.ultimates import ULT_BOSS_CAP, ULT_BY_CHAR, ULTIMATES
    from game.ui import hud
    from game.world.render import RunRenderer
    from game.world.ultimates import EFFECTS
    app()
    assert set(ULT_BY_CHAR) == set(CHAR_ORDER)
    assert len({ULT_BY_CHAR[c] for c in CHAR_ORDER}) == len(CHAR_ORDER), "každé zvíře má mít jinou ultimátku"
    try:
        from game.audio import synth
        sounds = synth.sfx_library()
    except ImportError:          # bez numpy hra běží potichu
        sounds = None
    for uid, u in ULTIMATES.items():
        assert uid in EFFECTS, uid
        assert u.icon in assets.icons.base, u.icon
        assert sounds is None or u.sound in sounds, u.sound
        assert u.name and u.short and u.desc and u.shout and u.kills > 0 and u.min_cd > 0
    surf = pygame.Surface((540, 960))
    joy = Joystick()
    for c in CHAR_ORDER:
        run, _sc = SC.make_run(f"ult_{c}", seed=4, headless=False)
        ren = RunRenderer(run)
        assert run.crow_ready and run.ult.id == ULT_BY_CHAR[c]
        assert run.crow() and not run.crow_ready and run.crows_used == 1
        for i in range(24):
            tick(run, 0.5, 0.2)
            ren.draw(surf, DT)
            hud.draw_hud(surf, run, joy, i * DT)
        # pauza uprostřed efektu: efekty stojí
        st0 = [(f.kind, round(getattr(f, "t", 0.0), 4)) for f in run.ult_fx]
        run.state = "paused"
        for _ in range(30):
            run.update(DT)
        assert st0 == [(f.kind, round(getattr(f, "t", 0.0), 4)) for f in run.ult_fx], (c, "pauza")
        run.state = "playing"
        for i in range(420):
            tick(run, 0.5, 0.2)
            if i % 6 == 0:
                ren.draw(surf, DT)
        assert not run.ult_fx, (c, [f.kind for f in run.ult_fx])
        assert run.ult_log[0].damage_dealt > 0, c
        assert run.player.ult_speed == 1.0
        # boss: jedna aktivace ubere nejvýš ULT_BOSS_CAP max. HP a souboj běží dál
        rb, _sc = SC.make_run(f"ult_{c}_boss", seed=4)
        rb.god = True
        boss = rb.final_boss
        for _ in range(100):
            tick(rb)                     # konec úvodu bosse (během něj nebere poškození)
        rb.crow_charge = rb.crow_cap = 1.0
        assert rb.crow()
        for _ in range(480):
            tick(rb, 0.3, -0.2)
        dealt = rb.ult_log[-1].boss_dmg.get(boss.e.id, 0.0)
        assert dealt <= boss.e.max_hp * ULT_BOSS_CAP + 1, (c, dealt / boss.e.max_hp)
        assert boss.e.alive and rb.final_boss is boss, c
        # smrt uprostřed efektu: efekty skončí, oživení spustí ultimátku zdarma
        rd, _sc = SC.make_run(f"ult_{c}", seed=5)
        assert rd.crow()
        for _ in range(10):
            tick(rd)
        rd.player.invuln = 0.0
        rd.player.take_damage(1e9)
        assert rd.state == "dying" and not rd.ult_fx and rd.player.ult_speed == 1.0, c
        for _ in range(120):
            rd.update(DT)
        assert rd.state == "dead"
        n_log = len(rd.ult_log)
        rd.revive()
        assert rd.state == "playing" and len(rd.ult_log) == n_log + 1 and rd.crows_used == 1, c
        for _ in range(60):
            tick(rd)


@test
def ultimates_regressions():
    """Pasti na nálezy 7. kola: B-91 (rozestup ultimátky s Budíkem), B-93 + B-95 (okouzlení), B-94 (název),
    B-96 (výbuch lišky zabité ultimátkou), B-98 (jméno zvířete v HUD)."""
    import random as _r
    from game import scenarios as SC
    from game.config import DT
    from game.data.characters import CHAR_ORDER
    from game.data.ultimates import ULT_NAME_GAP, ULTIMATES
    from game.world.run import Run, RunConfig
    from game.world.ultimates import UltSource
    app()
    # B-91: Budík ani pasivka zvířete nestáhnou rozestup pod cd_floor, ten není kratší než omezení davu
    for c in CHAR_ORDER:
        run = Run(RunConfig(character=c, mode="full", seed=1, headless=True))
        run.add_passive("clock", 5)
        u = run.ult
        assert u.cd_floor > 0 and run.ult_period() >= u.cd_floor - 1e-9, (c, run.ult_period())
    assert ULTIMATES["kikiriki"].cd_floor >= ULTIMATES["kikiriki"].params["stun"], "omráčení delší než nabití"
    elvis = Run(RunConfig(character="rooster", mode="full", seed=1, headless=True))
    elvis.add_passive("clock", 5)
    assert abs(elvis.ult_period() - 3.0) < 1e-6, elvis.ult_period()          # jako před ultimátkami
    # B-93 + B-95: stráž drží odstup, po konci okouzlení je liška chvíli zmatená
    run, _sc = SC.make_run("ult_peacock", seed=3)
    run.director.update = lambda dt: None
    p = run.player
    p.stats.max_hp = p.hp = 1e6
    assert run.crow()
    seen_close, ended = 0, []
    for i in range(int(5.6 / DT)):
        tick(run)
        for e in run.enemies:
            if e.charm_t > 0 and e.foe is None and i > 150:
                if (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < 100 * 100:
                    seen_close += 1
        ended += [e for e in run.enemies if e.charm_t <= 0 and e.stun_t > 0.5]
    assert ended, "po konci okouzlení má liška zmatení"
    assert seen_close < 40, seen_close
    # B-94: velký banner jen poprvé, další název nejdřív po ULT_NAME_GAP
    run = Run(RunConfig(character="duck", mode="full", seed=2, headless=True))
    run.crow(free=True)
    n1 = sum(1 for b in run.banners if b[0] == run.ult.name)
    run.time += 3.0
    run.crow(free=True)
    n2 = sum(1 for b in run.banners if b[0] == run.ult.name)
    run.time += ULT_NAME_GAP
    run.crow(free=True)
    n3 = sum(1 for b in run.banners if b[0] == run.ult.name)
    assert (n1, n2, n3) == (1, 1, 1), (n1, n2, n3)
    assert any(t.text == run.ult.name for t in run.texts), "po prvním použití malý název u zvířete"
    # B-96: liška zabitá ultimátkou vybuchne jen do lišek
    run = Run(RunConfig(character="hen", mode="full", seed=2, headless=True))
    e = run.spawn_enemy("exploder", run.player.x + 20, run.player.y)
    run.kill_enemy(e, UltSource(run, run.ult, dict(run.ult.params)))
    assert run.bombs and run.bombs[-1][4] == 0.0 and not run.bombs[-1][8], run.bombs
    e2 = run.spawn_enemy("exploder", run.player.x + 20, run.player.y)
    run.kill_enemy(e2, None)
    assert run.bombs[-1][4] > 0 and run.bombs[-1][8], "výbuchy jinak zraňují dál"
    # B-98: HUD ukazuje jméno zvířete i název ultimátky
    from game.core.input import Joystick
    from game.ui import hud
    names = []
    from game import assets
    orig = assets.font.draw

    def spy(surf_, text, *a, **k):
        names.append(text)
        return orig(surf_, text, *a, **k)
    assets.font.draw = spy
    try:
        for c in CHAR_ORDER:
            r_ = Run(RunConfig(character=c, mode="quick", seed=1))
            hud.draw_hud(pygame.Surface((540, 960)), r_, Joystick(), 0.0)
            assert hud._short_name(r_.char.name) in names and r_.ult.short in names, (c, names[-5:])
    finally:
        assets.font.draw = orig


@test
def ultimate_while_moving_and_beak_laser():
    """Ultimátka jde zmáčknout i během pohybu: druhý prst (FINGERDOWN) na tlačítku, zatímco první drží joystick,
    a na PC pravé tlačítko myši během tažení. Zobák-laser střílí ze zobáku (ne ze středu těla) na obě strany."""
    a = app()
    from game.config import DT, H, W
    from game.scenes.game import GameScene, build_config
    from game.ui import hud
    gs = GameScene(a, build_config(a, "hen", "farm", "quick"))
    a.set_scene(gs)
    for _ in range(30):
        a.step(DT)
    run = gs.run

    def send(e):
        # stejná cesta jako App.process_events (překlad SDL události → scéna), bez fronty SDL – spolehlivé
        # i v klasickém pygame 2.1 (Android), kde se atributy uměle poslaných událostí nemusí zachovat
        ev = a.translate(e)
        if ev is not None:
            a.scene.handle(ev)

    # první prst / levé tlačítko drží joystick a táhne
    send(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(270, 700), button=1))
    send(pygame.event.Event(pygame.MOUSEMOTION, pos=(330, 700), rel=(60, 0), buttons=(1, 0, 0)))
    a.step(DT)
    assert gs.joy.active and gs.joy.vx > 0.3, (gs.joy.active, gs.joy.vx)
    # druhý prst na tlačítku ultimátky (SDL ho na myš nepřevede – přijde jen FINGERDOWN)
    run.crow_charge = run.crow_cap = 1.0
    cx, cy = hud.CROW_POS
    send(pygame.event.Event(pygame.FINGERDOWN, touch_id=1, finger_id=2, x=cx / W, y=cy / H, dx=0.0, dy=0.0,
                            pressure=1.0))
    a.step(DT)
    assert run.crows_used == 1, "druhým prstem se ultimátka nezmáčkla"
    assert gs.joy.active, "joystick musí zůstat aktivní"
    # PC: pravé tlačítko během tažení
    run.crow_charge = run.crow_cap = 1.0
    send(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(330, 700), button=3))
    a.step(DT)
    assert run.crows_used == 2, "pravé tlačítko myši ultimátku nespustilo"
    send(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(330, 700), button=1))
    a.step(DT)
    # Zobák-laser: paprsek začíná u zobáku, na straně, kam zvíře hledí, a nad středem těla
    from game.data.characters import CHAR_ORDER
    from game.world.run import Run, RunConfig
    for c in CHAR_ORDER:
        for face, side in ((0, 1), (1, -1)):
            r = Run(RunConfig(character=c, mode="full", seed=1, headless=True))
            r.director.update = lambda dt: None
            r.weapons = []
            w = r.add_weapon("laser", 4)
            p = r.player
            e = r.spawn_enemy("wolf", p.x + side * 170, p.y - 40)
            e.hp = e.max_hp = 1e9
            r.update(DT)
            p.face = face
            w.angles = w._dirs()
            w._shoot(1.0)
            (sx, sy), _end = r.beams[-1].pts
            assert (sx, sy) == p.beak(), c
            assert (sx - p.x) * side > 8 and sy < p.y - 15, (c, face, sx - p.x, sy - p.y)


@test
def fixed_joystick_anywhere():
    """Pevný joystick: vznikne, kam hráč ťukne (kdekoli), střed se za prstem neposouvá, po puštění zmizí
    a další ťuknutí ho vytvoří jinde. Pauza a ultimátka mají přednost před joystickem."""
    a = app()
    from game.config import DT
    from game.scenes.base import Ev
    from game.scenes.game import GameScene, build_config
    from game.ui import hud
    gs = GameScene(a, build_config(a, "duck", "farm", "quick"))
    a.set_scene(gs)
    for _ in range(10):
        a.step(DT)
    joy = gs.joy
    # nahoře (dřív jen spodní 2/3)
    gs.handle(Ev("down", 270, 140))
    assert joy.active and (joy.ox, joy.oy) == (270, 140), (joy.active, joy.ox, joy.oy)
    a.mouse_down = True
    gs.handle(Ev("move", 270 + 400, 140))        # daleko za okraj
    assert (joy.ox, joy.oy) == (270, 140), "střed se nesmí posouvat za prstem"
    assert abs(joy.vx - 1.0) < 1e-6 and abs(joy.vy) < 1e-6, (joy.vx, joy.vy)
    gs.handle(Ev("move", 270 - 20, 140))         # zpět dovnitř: páčka podle polohy prstu vůči pevnému středu
    assert -0.3 < joy.vx < 0 and (joy.ox, joy.oy) == (270, 140), (joy.vx, joy.ox)
    for _ in range(10):
        a.step(DT)
    assert gs.run.player.vx < 0, "zvíře jde ve směru páčky"
    gs.handle(Ev("up", 250, 140))
    a.mouse_down = False
    assert not joy.active and joy.vx == 0 and joy.vy == 0
    gs.handle(Ev("down", 100, 800))
    assert joy.active and (joy.ox, joy.oy) == (100, 800), "nový joystick tam, kam se ťuklo"
    gs.handle(Ev("up", 100, 800))
    # tlačítka mají přednost
    gs.run.crow_charge = gs.run.crow_cap = 1.0
    cx, cy = hud.CROW_POS
    gs.handle(Ev("down", cx, cy))
    assert not joy.active and gs.crow_pressed, "ťuknutí na ultimátku nevytvoří joystick"
    gs.handle(Ev("up", cx, cy))
    gs.handle(Ev("down", *hud.PAUSE_RECT.center))
    assert not joy.active and gs.overlay is not None, "ťuknutí na pauzu nevytvoří joystick"


@test
def daily_fixed_rush_character_choice():
    """Denní výzva hraje vždy zvíře dne (i zamčené, zapůjčené); týdenní boss rush si zvíře vybírá
    šipkami ze všech odemčených."""
    a = app()
    from game.config import DT
    from game.scenes.daily import DailyScene
    from game.scenes.game import GameScene
    s = a.save
    old = (list(s["unlocked_chars"]), s["daily"].get("last_played", ""), s["last_char"], s["weekly"].get("char", ""))
    try:
        s["weekly"]["char"] = ""
        s["unlocked_chars"] = ["hen", "turkey", "penguin"]
        s["daily"]["last_played"] = ""
        s["last_char"] = "turkey"
        sc = DailyScene(a)
        a.set_scene(sc)
        spec = sc.spec
        assert sc.chars == ["hen", "turkey", "penguin"], sc.chars
        assert sc.rush_char == "turkey", "výchozí je naposledy hrané zvíře"
        sc.pick(1)
        assert sc.rush_char == "penguin"
        sc.pick(1)
        assert sc.rush_char == "hen", "šipky dokola"
        sc.pick(-1)
        sc.play_daily()
        for _ in range(40):
            a.step(DT)
        gs = a.scene
        assert isinstance(gs, GameScene), type(gs)
        assert gs.cfg.character == spec["character"] and gs.cfg.mode == "daily", gs.cfg.character
        assert gs.cfg.biome == spec["biome"] and gs.cfg.modifiers == (spec["modifier"],) and gs.cfg.seed == spec["seed"]
        sc = DailyScene(a)
        a.set_scene(sc)
        sc.pick(1)
        sc.play_rush()
        for _ in range(40):
            a.step(DT)
        gs = a.scene
        assert isinstance(gs, GameScene), type(gs)
        assert gs.cfg.character == "penguin" and gs.cfg.mode == "bossrush", (gs.cfg.character, gs.cfg.mode)
        assert DailyScene(a).rush_char == "penguin", "boss rush si pamatuje zvíře (B-106)"
    finally:
        s["unlocked_chars"], s["daily"]["last_played"], s["last_char"], s["weekly"]["char"] = old


@test
def goose_whip_and_penguin_no_slide():
    """Husí štípanec štípe jen to, na co dosáhne (každý útok zasáhne), a až do maximálního dosahu.
    Tučňák neklouže (Ledová krev: zmražené lišky berou víc)."""
    app()
    from game.config import DT
    from game.world.run import Run, RunConfig
    for lv in (1, 8):
        run = Run(RunConfig(character="goose", mode="full", seed=1, headless=True))
        run.director.update = lambda dt: None
        w = run.weapons[0]
        w.set_level(lv)
        p = run.player
        reach = w.area(w.s["area"])
        e = run.spawn_enemy("fast_fox", p.x + reach + 5, p.y)          # poloměr 11 → těsně na dosah
        e.speed = 0
        e.hp = e.max_hp = 1e9
        run.update(DT)
        hp0 = e.hp
        assert w.fire(), "liška na maximálním dosahu se musí štípnout"
        assert e.hp < hp0, "útok, který proběhl, musí zasáhnout"
        e.x = p.x + reach + e.r + 6                                    # kousek za dosahem
        run.update(DT)
        n_beams = len(run.beams)
        assert not w.fire(), "husa nesmí štípat do vzduchu"
        assert len(run.beams) == n_beams
    # tučňák: rovná jízda nezrychluje, žádné klouzání ani setrvačnost
    run = Run(RunConfig(character="penguin", mode="full", seed=1, headless=True))
    run.director.update = lambda dt: None
    p = run.player
    for _ in range(240):
        run.update(DT, 1.0, 0.0)
    assert p.slide == 0.0 and abs(p.vx - p.stats.speed) < 1.0, (p.slide, p.vx, p.stats.speed)
    for _ in range(6):                     # běžné zvíře zabrzdí za ~4 snímky (tučňák dřív klouzal ~0,3 s)
        run.update(DT, 0.0, 0.0)
    assert abs(p.vx) < 1.0, "bez setrvačnosti se zastaví hned"
    e = run.spawn_enemy("wolf", p.x + 300, p.y)
    e.hp = e.max_hp = 1e6
    run.damage_enemy(e, 100, None, crit=False)
    plain = 1e6 - e.hp
    e.freeze_t = 2.0
    hp = e.hp
    run.damage_enemy(e, 100, None, crit=False)
    assert abs((hp - e.hp) - plain * 1.3) < 1e-6, (plain, hp - e.hp)


@test
def chest_now_gold_rare_secret_skins_magpie():
    """Truhla se otevře hned po sebrání (pauza jen pro level-upy); zlatá vejce jen za první porážku bosse;
    kompletní kategorie sbírky odhalí tajný skin, celá sbírka odemkne skrytou Straku."""
    a = app()
    from game import progression
    from game.config import DT
    from game.data.meta import LOGIN_REWARDS, SECRET_SKIN_BY_CAT, SKINS
    from game.save import SaveData
    from game.scenes.select import SelectScene
    from game.scenes.shop import ShopScene
    from game.world.entities import P_CHEST, Pickup
    from game.world.run import Run, RunConfig
    # truhla hned, i když běží rozestup mezi level-upy; do rozestupu se nepočítá (B-100)
    run = Run(RunConfig(character="hen", mode="full", seed=3, headless=True))
    run.director.update = lambda dt: None
    run.pause_cd = 6.0
    run.pending_levelups = 2                # XP nasbírané během rozestupu
    run.pickups.append(Pickup(run.player.x + 5, run.player.y, P_CHEST, 1))
    run.update(DT)
    run.update(DT)
    assert run.state == "chest", run.state
    cd = run.pause_cd
    run.resume()
    assert run.state == "playing", "po truhle level-up nenaskočí, dokud neuběhne rozestup"
    assert abs(run.pause_cd - cd) < 1e-9, "truhla rozestup neobnoví ani nezkrátí"
    run.pause_cd = 0.0
    run.update(DT)
    assert run.state == "levelup", "po doběhnutí rozestupu se level-up ukáže"
    # bez čekajícího level-upu: rozestup po truhle běží dál od stejného místa
    run.resume()
    assert run.pause_cd > 7.9 and run.state in ("playing", "levelup")
    # zlatá vejce: každý boss jen jednou, finální Kohout zvlášť pro každou mapu
    s = SaveData(os.path.join(TMP, "gold.json"))
    r = Run(RunConfig(mode="full", biome="farm", seed=1, headless=True))
    r.bosses_killed = ["spy_fox", "zombie_rooster"]
    rw = progression.compute_rewards(r, s)
    assert rw["gold"] == 3, rw
    progression.apply_results(s, r, rw)
    assert progression.compute_rewards(r, s)["gold"] == 0, "druhá porážka už zlatá vejce nedá"
    r2 = Run(RunConfig(mode="full", biome="forest", seed=1, headless=True))
    r2.bosses_killed = ["spy_fox", "zombie_rooster"]
    assert progression.compute_rewards(r2, s)["gold"] == 2, "Kohout na jiné mapě je jiná varianta"
    assert not any("gold" in d for d in LOGIN_REWARDS), "denní přihlášení zlatá vejce nedává"
    # sbírka: tajné skiny a Straka (skrytá, dokud ji hráč nezíská)
    assert "magpie" not in progression.visible_chars(s)
    for cat, (_, items) in progression.COLLECTION_CATS.items():
        if cat != "passives":
            for it in items:
                s.discover(cat, it)
    msgs = progression.check_collection(s)
    assert SECRET_SKIN_BY_CAT["bosses"]["id"] in s["skins_owned"], msgs
    assert SECRET_SKIN_BY_CAT["passives"]["id"] not in s["skins_owned"]
    assert "magpie" not in s["unlocked_chars"]
    for it in progression.COLLECTION_CATS["passives"][1]:
        s.discover("passives", it)
    msgs = progression.check_collection(s)
    assert "magpie" in s["unlocked_chars"] and any("Straka" in m for m in msgs), msgs
    assert "magpie" in progression.visible_chars(s)
    assert progression.check_collection(s) == [], "odměny jen jednou"
    # výběr a obchod ve skutečných scénách
    real = (list(a.save["unlocked_chars"]), list(a.save["skins_owned"]), dict(a.save["skin"]))
    try:
        a.save["unlocked_chars"] = ["hen", "duck"]
        sel = SelectScene(a)
        assert "magpie" not in sel.order and len(sel.order) == 7, sel.order
        a.save["unlocked_chars"] = ["hen", "magpie"]
        sel = SelectScene(a)
        assert sel.order[-1] == "magpie"
        a.save["skins_owned"] = []
        shop = ShopScene(a)
        a.set_scene(shop)
        assert len(shop.tiles) == 5 and len(shop.rows) == len([x for x in SKINS if not x.get("secret")])
        sk, tile = shop.tiles[0]
        shop.secret_action(sk)
        assert a.save["skin"].get(shop.char) != sk["id"], "zamčený tajný skin nejde nasadit"
        a.save["skins_owned"] = [sk["id"]]
        shop.secret_action(sk)
        assert a.save["skin"].get(shop.char) == sk["id"]
        for _ in range(5):
            a.step(DT)
        a.render()
    finally:
        a.save["unlocked_chars"], a.save["skins_owned"] = real[0], real[1]
        a.save["skin"].clear()
        a.save["skin"].update(real[2])


@test
def round8_regressions():
    """B-99 – B-109: texty sbírky, Velká loupež, zvuk cetek, zprávy při startu, skloňování, skiny, pirát."""
    a = app()
    from game import assets, progression
    from game.config import DT
    from game.data.ultimates import ULTIMATES
    from game.data.weapons import WEAPONS
    from game.save import SaveData
    from game.scenes.collection import CollectionScene
    from game.scenes.menu import MenuScene
    from game.scenes.shop import ShopScene
    from game.world.run import Run, RunConfig
    import inspect
    from game.scenes import collection as coll_mod
    from game.weapons import kinds
    # B-99: Sbírka už neslibuje zlatá vejce
    assert "zlatá vejce" not in inspect.getsource(coll_mod)
    a.set_scene(CollectionScene(a))
    a.step(DT)
    a.render()
    # B-101: Velká loupež zabije běžnou lišku ve 3. minutě
    run = Run(RunConfig(character="magpie", mode="full", seed=4, headless=True))
    run.director.update = lambda dt: None
    run.time = 180
    e = run.spawn_enemy("fox", 60, 0)
    s = ULTIMATES["heist"].params
    assert s["dmg"] + s["hp_pct"] * e.max_hp >= e.max_hp, (s, e.max_hp)
    # B-102: cetky mají vlastní zvuk, ne „coin“
    assert 'run.sfx("coin"' not in inspect.getsource(kinds.BounceWeapon)
    assert WEAPONS["trinkets"].sound != "coin"
    if assets.audio is not None and getattr(assets.audio, "sounds", None):
        assert "trinket" in assets.audio.sounds
    # B-103: zprávy ze zpětného odemčení ukáže menu
    old_suppress = MenuScene.suppress_login
    try:
        MenuScene.suppress_login = False
        a.save["daily"]["login_last"] = progression.today().isoformat()     # dnes už odměna byla
        a.startup_msgs = ["Tajný skin v Obchodě: Koruna dvora!"]
        m = MenuScene(a)
        a.set_scene(m)
        assert m.modal is not None and "Koruna" in m.modal.text, getattr(m.modal, "text", None)
        assert a.startup_msgs == [], "zpráva jen jednou"
    finally:
        MenuScene.suppress_login = old_suppress
    a.set_scene(MenuScene(a))
    # B-104: skloňování zlatých vajec
    sv = SaveData(os.path.join(TMP, "gold8.json"))
    r = Run(RunConfig(mode="bossrush", biome="farm", seed=1, headless=True))
    r.bosses_killed = ["spy_fox", "rabbit", "zombie_bear", "wolf_alpha", "zombie_rooster"]
    msgs = progression.apply_results(sv, r, progression.compute_rewards(r, sv))
    assert "První porážka bossů: +6 zlatých vajec" in msgs, msgs
    # B-105: neutrální hláška u tajných skinů
    real = (list(a.save["skins_owned"]), dict(a.save["skin"]))
    try:
        a.save["skins_owned"] = ["crown"]
        shop = ShopScene(a)
        a.set_scene(shop)
        sk = next(s for s, _ in shop.tiles if s["id"] == "crown")
        shop.secret_action(sk)
        assert a.save["skin"].get(shop.char) == "crown"
        shop.secret_action(sk)
        assert a.save["skin"].get(shop.char) is None
    finally:
        a.save["skins_owned"] = real[0]
        a.save["skin"].clear()
        a.save["skin"].update(real[1])
    assert "nasazen\"" not in inspect.getsource(ShopScene)
    # B-108: pirátský klobouk má světlý lem
    from game.gfx.sprites import SKIN_HATS
    assert "y" in SKIN_HATS["pirate"][0]


@test
def long_headless_simulation():
    """Několik tisíc framů plného módu bez výjimky."""
    from game.bot import Bot
    from game.config import DT
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(character="goose", biome="factory", mode="full", seed=99, headless=True))
    bot = Bot(run)
    n = 6000 if FAST else 20000
    for _ in range(n):
        bot.step(DT)
        if run.state == "dead":
            run.revive()
            run.revived = False
        if run.state == "victory":
            break
    assert run.time > 60


def main() -> None:
    pygame.quit()
    ok = sum(1 for r in RESULTS if r[1])
    print(f"\n{ok}/{len(RESULTS)} testů prošlo")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
