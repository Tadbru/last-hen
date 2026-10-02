"""Headless bot-simulace celých runů – stabilita a balanc.

    python tools/simulate.py --mode full --char hen --biome farm --runs 3
    python tools/simulate.py --all            # všechna zvířata × biomy v rychlém módu
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402


def sim(char: str, biome: str, mode: str, diff: str = "normal", seed: int = 1, mods: tuple = (),
        revive: bool = False, max_time: float = 900.0, verbose: bool = False, meta: int = 0) -> dict:
    from game.bot import Bot
    from game.config import DT
    from game.world.run import Run, RunConfig
    run = Run(RunConfig(character=char, biome=biome, mode=mode, difficulty=diff, seed=seed, modifiers=mods,
                        headless=True, rerolls=2 + meta,
                        meta={k: meta for k in ("hp", "dmg", "speed", "magnet", "xp", "reroll")}))
    bot = Bot(run)
    t0 = time.perf_counter()
    frames = 0
    max_en = 0
    max_pr = 0
    last_report = 0
    revived = False
    min_hp = 1.0
    while run.time < max_time:
        bot.step(DT)
        frames += 1
        max_en = max(max_en, len(run.enemies))
        max_pr = max(max_pr, len(run.projs))
        min_hp = min(min_hp, run.player.hp / run.player.stats.max_hp)
        if run.state == "dead":
            if revive and not revived:
                revived = True
                run.revive()
                continue
            break
        if run.state == "victory":
            break
        if verbose and run.time - last_report >= 60:
            last_report = run.time
            print(f"  t={run.time:5.0f}s lvl={run.level:2d} hp={run.player.hp:5.0f}/{run.player.stats.max_hp:4.0f} "
                  f"kills={run.kills:5d} en={len(run.enemies):3d} pr={len(run.projs):3d} "
                  f"w={[(w.id[:6], w.level) for w in run.weapons]}")
    wall = time.perf_counter() - t0
    return dict(char=char, biome=biome, mode=mode, state=run.state, time=run.time, kills=run.kills, level=run.level,
                victory=run.victory, bosses=list(run.bosses_killed), weapons=[(w.id, w.level) for w in run.weapons],
                passives=dict(run.passives), frames=frames, wall=wall, ms=wall / max(1, frames) * 1000,
                max_enemies=max_en, max_projs=max_pr, revived=revived, coins=run.coins, boss_log=run.boss_log,
                min_hp=min_hp, dmg_taken=run.stats_dmg_taken,
                dmg_log={k: int(v) for k, v in sorted(run.dmg_log.items(), key=lambda kv: -kv[1])})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="quick")
    ap.add_argument("--char", default="hen")
    ap.add_argument("--biome", default="farm")
    ap.add_argument("--diff", default="normal")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--revive", action="store_true")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--meta", type=int, default=0, help="úroveň všech vylepšení Hnízda (0–5)")
    ap.add_argument("--chars", default="", help="čárkou oddělená zvířata pro --all")
    a = ap.parse_args()
    pygame.init()
    from game import assets
    assets.init(headless_sim=True, audio_enabled=False)
    from game.data.biomes import BIOME_ORDER
    from game.data.characters import CHAR_ORDER
    jobs = []
    if a.all:
        chars = a.chars.split(",") if a.chars else CHAR_ORDER
        biomes = [a.biome] if a.biome != "farm" or a.chars else BIOME_ORDER
        for i, c in enumerate(chars):
            for j, b in enumerate(biomes):
                jobs.append((c, b, a.mode, a.seed + i * 10 + j))
    else:
        for r in range(a.runs):
            jobs.append((a.char, a.biome, a.mode, a.seed + r))
    wins = 0
    for c, b, m, seed in jobs:
        res = sim(c, b, m, a.diff, seed, revive=a.revive, verbose=a.v, meta=a.meta)
        wins += res["victory"]
        print(f"{c:8s} {b:9s} {m:8s} -> {res['state']:8s} t={res['time']:6.1f}s kills={res['kills']:5d} "
              f"lvl={res['level']:2d} bosses={len(res['bosses'])} maxE={res['max_enemies']:3d} "
              f"maxP={res['max_projs']:3d} {res['ms']:.2f}ms/tick rev={res['revived']}")
        print("        ", res["weapons"], res["passives"])
        print("         bossové:", res["boss_log"], f"minHP={res['min_hp']:.2f} dmg_taken={res['dmg_taken']:.0f}")
        print("         zdroje poškození:", res["dmg_log"])
    print(f"wins {wins}/{len(jobs)}")


if __name__ == "__main__":
    main()
