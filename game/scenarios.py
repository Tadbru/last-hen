"""Ladicí scénáře – jedním příkazem do stavu, kde se nová věc dá vyzkoušet.

    python main.py --debug --scenario ult_duck            # kachna, ~80 lišek kolem, ultimátka nabitá
    python main.py --debug --scenario ult_duck_boss       # totéž proti Zombie Kohoutovi (rychlý mód)
    python main.py --debug --scenario ult_stress_duck     # 400 lišek, nesmrtelnost, ultimátka se hned dobíjí
    python main.py --list-scenarios

Ve hře (s --debug): F4 = nabít ultimátku, F2 = vyzkoušet ultimátku dalšího zvířete.
Stejné scénáře používá `tools/ult_lab.py` (měření bez okna).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .data.characters import CHAR_ORDER
from .data.ultimates import ULT_BY_CHAR

MIXES = {
    3: ["fox", "fox", "fast_fox", "bat", "armored_fox", "spitter"],
    8: ["fox", "fast_fox", "bat", "armored_fox", "spitter", "exploder", "wolf"],
}


@dataclass
class Scenario:
    name: str
    desc: str
    cfg: dict
    setup: object                    # setup(run, rng)
    tick: object = None              # volitelně každý tick: tick(run)
    extra: dict = field(default_factory=dict)


SCENARIOS: dict[str, Scenario] = {}


def ring_of_enemies(run, n: int, rng: random.Random, r0: float = 70, r1: float = 340, kinds=None,
                    tough: bool = False) -> None:
    p = run.player
    kinds = kinds or MIXES[3]
    for _ in range(n):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(r0, r1)
        e = run.spawn_enemy(rng.choice(kinds), p.x + math.cos(a) * d, p.y + math.sin(a) * d * 1.2)
        if tough:
            e.hp = e.max_hp = 1e9


def _charge(run) -> None:
    run.crow_charge = run.crow_cap = 1.0


def _skip_to(run, t: float) -> None:
    """Posun času runu bez dohánění všeho, co mělo přijít dřív (bossové, elity, formace)."""
    run.time = t
    d = run.director
    em = d.eff_min()
    d.bosses = [b for b in d.bosses if b[0] > t]
    d.elites = [b for b in d.elites if b[0] > t]
    d.events = [ev for ev in d.events if ev[0] > em]


def _ult_basic(char: str):
    def setup(run, rng):
        _skip_to(run, 180.0)                   # 3. minuta plného módu (lišky už něco vydrží)
        w = run.weapons[0]
        w.set_level(4)
        ring_of_enemies(run, 80, rng)
        _charge(run)
    return Scenario(f"ult_{char}", f"{char}: ~80 lišek kolem, ultimátka nabitá",
                    dict(character=char, mode="full"), setup)


def _ult_boss(char: str):
    def setup(run, rng):
        _skip_to(run, 150.0)
        run.weapons[0].set_level(6)
        run.director.bosses = []
        run.spawn_boss("zombie_rooster")
        ring_of_enemies(run, 40, rng, kinds=MIXES[3])
        _charge(run)
    return Scenario(f"ult_{char}_boss", f"{char}: Zombie Kohout v rychlém módu + 40 lišek, ultimátka nabitá",
                    dict(character=char, mode="quick"), setup)


def _ult_stress(char: str):
    def setup(run, rng):
        _skip_to(run, 420.0)
        run.god = True
        run.weapons[0].set_level(8)
        ring_of_enemies(run, 400, rng, 60, 620, kinds=MIXES[8], tough=True)
        _charge(run)

    def tick(run):
        # udržet 400 nepřátel a mít ultimátku pořád připravenou (smoke bot mačká mezerník)
        if len(run.enemies) < 400:
            ring_of_enemies(run, 400 - len(run.enemies), random.Random(run.tick), 300, 620, kinds=MIXES[8],
                            tough=True)
        if not run.ult_fx:
            _charge(run)
    return Scenario(f"ult_stress_{char}", f"{char}: 400 nepřátel, nesmrtelnost, ultimátka stále nabitá",
                    dict(character=char, mode="full"), setup, tick)


for _c in CHAR_ORDER:
    for _mk in (_ult_basic, _ult_boss, _ult_stress):
        _s = _mk(_c)
        SCENARIOS[_s.name] = _s


def make_run(name: str, seed: int = 1, headless: bool = True, ult: str | None = None, **cfg):
    """Run připravený podle scénáře (pro nástroje a testy)."""
    from .world.run import Run, RunConfig
    sc = SCENARIOS[name]
    kw = dict(sc.cfg)
    kw.update(cfg)
    run = Run(RunConfig(seed=seed, headless=headless, ult=ult, **kw))
    sc.setup(run, random.Random(seed))
    return run, sc


def start(app, name: str, seed: int = 1):
    """GameScene se scénářem (python main.py --scenario NAME)."""
    from .scenes.game import GameScene
    from .world.run import RunConfig
    sc = SCENARIOS[name]
    gs = GameScene(app, RunConfig(seed=seed, **sc.cfg))
    sc.setup(gs.run, random.Random(seed))
    gs.debug_tick = sc.tick
    gs.run.banner(f"SCÉNÁŘ: {name}", (180, 255, 180), 2.0)
    return gs


def next_ult(run) -> None:
    """F2: vyzkoušet ultimátku dalšího zvířete (jen ladění – zvíře a zbraň zůstávají)."""
    from .data.ultimates import ULTIMATES
    order = [ULT_BY_CHAR[c] for c in CHAR_ORDER]
    i = order.index(run.ult.id) if run.ult.id in order else -1
    run.ult = ULTIMATES[order[(i + 1) % len(order)]]
    _charge(run)
    run.banner(f"Ultimátka: {run.ult.name}", run.ult.color, 1.5)
