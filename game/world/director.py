"""Spawn director – křivka obtížnosti, formace (prstence, hordy, obklíčení), elity a bossové."""
from __future__ import annotations

import math

from ..config import MAX_ENEMIES, H, W
from ..data import waves as WV
from ..data.bosses import BOSS_ORDER
from ..data.enemies import ENEMIES
from ..util import weighted_choice

TAU = math.tau


class Director:
    def __init__(self, run) -> None:
        self.run = run
        mode = run.cfg.mode
        self.quick = mode in ("quick", "daily")
        self.time_scale = WV.QUICK_TIME_SCALE if self.quick else 1.0
        self.acc = 0.0
        if mode == "bossrush":
            self.bosses = []
            self.rush = list(BOSS_ORDER)
            self.rush_t = 3.0
        else:
            self.bosses = list(WV.BOSSES_QUICK if self.quick else WV.BOSSES_FULL)
            self.rush = []
        self.elites = list(WV.ELITES_QUICK if self.quick else WV.ELITES_FULL)
        self.events = list(WV.EVENTS)
        self.final_time = WV.QUICK_LENGTH if self.quick else WV.FULL_LENGTH
        if mode == "bossrush":
            self.final_time = 0
        self.spawn_mult = run.diff.spawn * run.biome.spawn_mult * run.mod_spawn_mult

    def eff_min(self) -> float:
        if self.run.cfg.mode == "bossrush":
            return 4.0 + self.run.time / 60.0
        return self.run.time / 60.0 * self.time_scale

    # --- výběr nepřítele ------------------------------------------------------------------
    def pick(self, weights: dict, em: float) -> str:
        b = self.run.biome
        items = list(weights.keys())
        ws = list(weights.values())
        for eid, w, from_min in b.extra:
            if em >= from_min:
                items.append(eid)
                ws.append(w)
        eid = weighted_choice(self.run.rng, items, ws)
        return b.replace.get(eid, eid)

    # --- pozice -----------------------------------------------------------------------------
    def offscreen_pos(self, margin: float = 70.0) -> tuple[float, float]:
        run = self.run
        rng = run.rng
        cx, cy = run.camera.x, run.camera.y
        if run.arena is not None:
            ax, ay, ar = run.arena
            p = run.player
            for _ in range(8):
                a = rng.uniform(0, TAU)
                x, y = ax + math.cos(a) * (ar - 30), ay + math.sin(a) * (ar - 30)
                if (x - p.x) ** 2 + (y - p.y) ** 2 > 240 * 240:
                    return x, y
            return x, y
        hw, hh = W / 2 + margin, H / 2 + margin
        for _ in range(6):
            per = 2 * (hw + hh)
            r = rng.uniform(0, per * 2)
            if r < hw * 2:
                x, y = cx - hw + r, cy - hh
            elif r < hw * 4:
                x, y = cx - hw + (r - hw * 2), cy + hh
            elif r < hw * 4 + hh * 2:
                x, y = cx - hw, cy - hh + (r - hw * 4)
            else:
                x, y = cx + hw, cy - hh + (r - hw * 4 - hh * 2)
            if not run.map.blocked(x, y):
                return x, y
        return x, y

    # --- update ------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        run = self.run
        t = run.time
        em = self.eff_min()
        if run.cfg.mode == "bossrush":
            self._bossrush(dt)
            rate, max_alive, weights = WV.sample(min(em, 6.0))
            rate *= 0.35
        else:
            rate, max_alive, weights = WV.sample(em)
        rate *= self.spawn_mult
        max_alive = min(MAX_ENEMIES, int(max_alive * min(1.3, self.spawn_mult)))
        if run.final_boss is not None:
            rate *= 0.3
            max_alive = min(max_alive, 80 if self.quick else 140)
        elif run.bosses:
            rate *= 0.6
        self.acc += rate * dt
        alive = len(run.enemies)
        while self.acc >= 1.0:
            self.acc -= 1.0
            if alive < max_alive:
                x, y = self.offscreen_pos()
                run.spawn_enemy(self.pick(weights, em), x, y)
                alive += 1
        # formace
        while self.events and em >= self.events[0][0] and run.final_boss is None:
            _, kind, eid, count = self.events.pop(0)
            if run.cfg.mode != "bossrush":
                self.formation(kind, eid, int(count * min(1.5, self.spawn_mult)), weights, em)
        # elity
        while self.elites and t >= self.elites[0][0]:
            _, eid = self.elites.pop(0)
            if run.final_boss is None:
                x, y = self.offscreen_pos()
                run.spawn_enemy(eid, x, y)
                run.banner(f"Elita: {ENEMIES[eid].name}!", (255, 180, 60), 1.8)
                run.sfx("warning", 0.6)
        # bossové
        while self.bosses and t >= self.bosses[0][0]:
            _, bid = self.bosses.pop(0)
            run.spawn_boss(bid)

    def _bossrush(self, dt: float) -> None:
        run = self.run
        if run.bosses or not self.rush:
            return
        self.rush_t -= dt
        if self.rush_t <= 0:
            self.rush_t = 4.0
            run.spawn_boss(self.rush.pop(0))

    def formation(self, kind: str, eid: str, count: int, weights: dict, em: float) -> None:
        run = self.run
        p = run.player
        rng = run.rng

        def pick():
            return self.pick(weights, em) if eid == "mixed" else run.biome.replace.get(eid, eid)

        if kind == "ring" or kind == "encircle":
            layers = 2 if kind == "encircle" else 1
            per = max(6, count // layers)
            for layer in range(layers):
                rx, ry = W / 2 + 60 + layer * 50, H / 2 + 60 + layer * 50
                off = rng.uniform(0, TAU)
                for i in range(per):
                    a = off + i * TAU / per
                    x, y = p.x + math.cos(a) * rx, p.y + math.sin(a) * ry
                    if not run.map.blocked(x, y):
                        run.spawn_enemy(pick(), x, y)
            run.banner("Obklíčení!" if kind == "encircle" else "Lišky ze všech stran!", (255, 120, 90), 1.6)
        elif kind == "horde":
            a = rng.uniform(0, TAU)
            cx, cy = p.x + math.cos(a) * (H / 2 + 120), p.y + math.sin(a) * (H / 2 + 120)
            for _ in range(count):
                x = cx + rng.uniform(-90, 90)
                y = cy + rng.uniform(-90, 90)
                run.spawn_enemy(pick(), x, y)
            run.banner("Horda!", (255, 120, 90), 1.4)
        run.sfx("warning", 0.5)
