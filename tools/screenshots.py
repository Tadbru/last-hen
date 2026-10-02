"""Headless screenshoty všech scén (kontrola UI). Výstup do zadané složky.

    python tools/screenshots.py [složka]
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "screens"
    os.makedirs(out, exist_ok=True)
    from game.app import App
    from game.config import DT
    from game.scenes import challenges, collection, daily, menu, nest, select, settings, shop
    from game.scenes.game import GameScene, build_config

    app = App(headless=True, persist=False)
    app.save["eggs"] = 2400
    app.save["gold"] = 9
    app.save["tokens"] = 3
    app.save["unlocked_chars"] += ["duck", "goose"]
    for cat, items in (("enemies", ["fox", "bat", "wolf"]), ("weapons", ["egg", "laser"])):
        for i in items:
            app.save.discover(cat, i)

    def shot(name, frames=20):
        for _ in range(frames):
            app.step(DT)
        app.render()
        pygame.image.save(app.screen, os.path.join(out, f"{name}.png"))
        print("saved", name)

    sc = menu.MenuScene(app)
    menu.MenuScene._login_checked = True
    app.set_scene(sc)
    shot("menu")
    for name, cls in (("select", select.SelectScene), ("nest", nest.NestScene), ("collection", collection.CollectionScene),
                      ("challenges", challenges.ChallengesScene), ("daily", daily.DailyScene), ("shop", shop.ShopScene),
                      ("settings", settings.SettingsScene)):
        app.set_scene(cls(app))
        shot(name)
    biome = sys.argv[2] if len(sys.argv) > 2 else "farm"
    char = sys.argv[3] if len(sys.argv) > 3 else "hen"
    gs = GameScene(app, build_config(app, char, biome, "full"))
    app.set_scene(gs)
    rng = random.Random(3)
    run = gs.run
    from game import progression
    t = 0
    while run.time < 70:
        gs.joy.vx, gs.joy.vy = rng.uniform(-1, 1), rng.uniform(-1, 1)
        for _ in range(30):
            app.step(DT)
            if run.state == "levelup":
                progression.apply_card(run, run.offer[0])
            elif run.state == "chest":
                run.resume()
            if run.player.hp < 30:
                run.player.hp = run.player.stats.max_hp
        t += 1
        if t == 20:
            app.render()
            pygame.image.save(app.screen, os.path.join(out, "game_early.png"))
    app.render()
    pygame.image.save(app.screen, os.path.join(out, "game_70s.png"))
    run.pending_levelups += 1
    app.step(DT)
    shot("levelup", 30)
    progression.apply_card(run, run.offer[0])
    run.pending_chests.append("elite")
    app.step(DT)
    shot("chest", 90)
    run.resume()
    app.step(DT)
    run.spawn_boss("zombie_rooster")
    shot("boss", 200)
    gs.pause()
    shot("pause", 5)


if __name__ == "__main__":
    main()
