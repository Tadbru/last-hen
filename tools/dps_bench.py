"""Benchmark DPS všech zbraní: single-target (boss figurína) a AoE (skupina 25 nepřátel).

    python tools/dps_bench.py
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def bench(wid: str, level: int, mode: str, seconds: float = 12.0) -> float:
    from game.config import DT
    from game.data.weapons import WEAPONS
    from game.world.run import Run, RunConfig
    owner = WEAPONS[wid].owner or "hen"
    if WEAPONS[wid].evolution and WEAPONS[wid].owner:
        owner = WEAPONS[wid].owner
    run = Run(RunConfig(character=owner if owner in ("hen", "duck", "goose", "turkey", "rooster", "peacock", "penguin")
                        else "hen", headless=True, seed=5))
    for w in list(run.weapons):
        w.on_remove()
    run.weapons = []
    run.add_weapon(wid, level)
    run.director.update = lambda dt: None
    run.god = True
    targets = []
    if mode == "single":
        e = run.spawn_enemy("fox", 90, -40)
        e.hp = e.max_hp = 1e12
        e.speed = 0
        e.r = 30
        e.kb_res = 1.0
        targets.append(e)
    else:
        for i in range(25):
            a = i * math.tau / 25
            rr = 60 + (i % 5) * 30
            e = run.spawn_enemy("fox", math.cos(a) * rr, math.sin(a) * rr)
            e.hp = e.max_hp = 1e12
            e.speed = 0
            e.kb_res = 1.0
            targets.append(e)
    run.player.stats.crit_chance = 0.0
    t = 0.0
    while t < seconds:
        for e in targets:
            e.kx = e.ky = 0.0
            e.dmg = 0
        run.update(DT, 0.0, 0.0)
        if run.state != "playing":
            run.state = "playing"
        t += DT
    total = sum(w.damage_dealt for w in run.weapons)
    return total / seconds


def main() -> None:
    pygame.init()
    from game import assets
    assets.init(headless_sim=True, audio_enabled=False)
    from game.data.weapons import ALL_BASE, SECRET_WEAPONS, WEAPONS
    print(f"{'zbraň':18s} {'L1 1×':>7s} {'L4 1×':>7s} {'L8 1×':>7s} {'EVO 1×':>7s} | {'L1 AoE':>7s} {'L8 AoE':>8s} {'EVO AoE':>8s}")
    for wid in ALL_BASE + SECRET_WEAPONS:
        d = WEAPONS[wid]
        s1 = bench(wid, 1, "single")
        s4 = bench(wid, 4, "single")
        s8 = bench(wid, 8, "single")
        se = bench(d.evo_to, 1, "single") if d.evo_to else 0
        a1 = bench(wid, 1, "aoe")
        a8 = bench(wid, 8, "aoe")
        ae = bench(d.evo_to, 1, "aoe") if d.evo_to else 0
        print(f"{wid:18s} {s1:7.0f} {s4:7.0f} {s8:7.0f} {se:7.0f} | {a1:7.0f} {a8:8.0f} {ae:8.0f}")


if __name__ == "__main__":
    main()
