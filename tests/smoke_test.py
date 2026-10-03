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
    menu.MenuScene._login_checked = True
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
                                skin=["pirate", "cowboy", "astronaut", "ninja", "pumpkin", "santa", "bunny"][ci],
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
        coins0 = run.coins
        run._open_levelup()
        if not progression.has_choices(run):
            # všechno vylepšeno → levelup se vyřeší sám (mince + léčení) a hru nepřeruší
            assert run.state == "playing" and run.pending_levelups == 0 and run.coins > coins0
            continue
        offer = run.offer
        assert len(offer) == 3
        r = random.random()
        if r < 0.1 and run.rerolls:
            assert progression.reroll(run)
        elif r < 0.15 and run.banishes and offer[0].kind in ("weapon", "passive"):
            assert progression.banish(run, offer[0])
            assert offer[0].id in run.banished
        elif r < 0.2:
            progression.skip(run)
            continue
        progression.apply_card(run, run.offer[random.randrange(3)])
    assert len(run.weapons) <= 6 and len(run.passives) <= 6
    # při plném buildu jsou nabízeny výplňové karty
    for w in run.weapons:
        if not w.evolved:
            w.set_level(8)
    for pid in list(run.passives):
        run.passives[pid] = 5
    run.banished.update(["egg", "crow_wave", "chick_army", "shuriken", "laser", "nest", "lightning", "stink",
                         "wolf_howl", "sky_cake"])
    offer = progression.make_offer(run)
    assert len(offer) == 3


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
    assert cfg.bonus_levels == 8
    for _ in range(400):
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
