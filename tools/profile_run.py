"""Profilování zátěžové scény: ~400 nepřátel + ~300 projektilů, logika i render.

    python tools/profile_run.py            # měření časů
    python tools/profile_run.py --cprofile # + cProfile top funkcí
"""
from __future__ import annotations

import cProfile
import math
import os
import pstats
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def build(biome: str = "farm"):
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(character="duck", biome=biome, mode="full", seed=9, headless=False))
    run.time = 420
    for wid, lv in (("water_pistol", 8), ("shuriken", 8), ("feather_shotgun", 8), ("egg", 8), ("lightning", 8),
                    ("stink", 8)):
        if run.weapon(wid):
            run.weapon(wid).set_level(lv)
        else:
            run.add_weapon(wid, lv)
    run.god = True
    run.show_damage = True
    rng = random.Random(1)
    kinds = ["fox", "fast_fox", "armored_fox", "bat", "wolf", "spitter", "exploder"]
    for _ in range(400):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(80, 600)
        e = run.spawn_enemy(rng.choice(kinds), math.cos(a) * d * 0.6, math.sin(a) * d)
        if not KILLS:
            e.hp = e.max_hp = 1e9
    run.director.update = lambda dt: None
    return run


KILLS = "--kills" in sys.argv


def keep_full(run, rng) -> None:
    while len(run.enemies) < 400:
        a = rng.uniform(0, math.tau)
        e = run.spawn_enemy("fox", run.player.x + math.cos(a) * 400, run.player.y + math.sin(a) * 600)
        if not KILLS:
            e.hp = e.max_hp = 1e9


def main() -> None:
    pygame.init()
    pygame.display.set_mode((540, 960))
    from game import assets
    assets.init(headless_sim=False, audio_enabled=False)
    from game.config import DT, H, W
    from game.ui import hud
    from game.core.input import Joystick
    from game.world.render import RunRenderer
    biome = "farm"
    for a in sys.argv[1:]:
        if a.startswith("--biome="):
            biome = a.split("=", 1)[1]
    run = build(biome)
    ren = RunRenderer(run)
    surf = pygame.Surface((W, H))
    joy = Joystick()
    rng = random.Random(2)
    # zahřát
    for _ in range(60):
        run.update(DT, 0.3, 0.2)
        if run.state != "playing":
            run.state = "playing"
    frames = 600
    tl = tr = 0.0
    max_pr = max_en = max_pa = 0
    win = pygame.Surface((540, 960))

    def loop():
        nonlocal tl, tr, max_pr, max_en, max_pa
        for i in range(frames):
            keep_full(run, rng)
            # udržet ~300 projektilů
            while len(run.projs) < 300:
                a = rng.uniform(0, math.tau)
                run.add_proj(run.player.x, run.player.y, math.cos(a) * 300, math.sin(a) * 300, 6, 30 if KILLS else 1, None,
                             pierce=2 if KILLS else 999,
                             life=1.5, spr=assets.sprites.small["water"])
            t0 = time.perf_counter()
            run.update(DT, math.cos(i * 0.02), math.sin(i * 0.02))
            if run.state != "playing":
                run.state = "playing"
                run.offer = None
            t1 = time.perf_counter()
            ren.draw(surf, DT)
            hud.draw_hud(surf, run, joy, i * DT)
            win.blit(surf, (0, 0))
            t2 = time.perf_counter()
            tl += t1 - t0
            tr += t2 - t1
            max_pr = max(max_pr, len(run.projs))
            max_en = max(max_en, len(run.enemies))
            max_pa = max(max_pa, len(run.particles))

    if "--cprofile" in sys.argv:
        pr = cProfile.Profile()
        pr.enable()
        loop()
        pr.disable()
        st = pstats.Stats(pr)
        st.sort_stats("tottime").print_stats(25)
    else:
        loop()
    print(f"kills={run.kills} pickups={len(run.pickups)} texts={len(run.texts)}")
    print(f"biome={biome} enemies~{max_en} projectiles~{max_pr} particles~{max_pa}")
    print(f"logika {tl / frames * 1000:.2f} ms/frame, render {tr / frames * 1000:.2f} ms/frame, "
          f"celkem {(tl + tr) / frames * 1000:.2f} ms  -> {1000 / ((tl + tr) / frames * 1000):.0f} FPS")


if __name__ == "__main__":
    main()
