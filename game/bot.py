"""Jednoduchý bot pro headless simulace a testy: kiting, sběr zrní, vyhýbání se telegrafům, výběr karet."""
from __future__ import annotations

import math

from . import progression
from .data.weapons import WEAPONS
from .world.entities import P_CHEST, P_GOLDEGG, P_WORM, P_XP

PASSIVE_PRIO = ["shell", "clock", "grain", "legs", "megaphone", "magnet", "vest", "feed", "lucky_egg", "glasses",
                "clover"]


class Bot:
    def __init__(self, run, skill: float = 1.0) -> None:
        self.run = run
        self.skill = skill
        self.wander = 0.0
        self.t = 0.0
        self.side = 1

    # --- pohyb ---------------------------------------------------------------------------------
    def control(self, dt: float) -> tuple[float, float, bool]:
        run = self.run
        p = run.player
        self.t += dt
        fx = fy = 0.0
        threat = 0.0
        close = 0
        for e in run.grid.query(p.x, p.y, 240):
            if not e.alive or e.prop:
                continue
            dx, dy = p.x - e.x, p.y - e.y
            d2 = dx * dx + dy * dy + 1
            d = math.sqrt(d2)
            if d < 240:
                w = (e.r + 40) ** 2 / d2 * (3.0 if e.boss or e.elite else 1.0)
                fx += dx / d * w
                fy += dy / d * w
                threat += w
                if d < 110:
                    close += 1
        for ep in run.eprojs:
            dx, dy = p.x - ep.x, p.y - ep.y
            d2 = dx * dx + dy * dy + 1
            if d2 < 160 * 160:
                d = math.sqrt(d2)
                # uhnout kolmo na dráhu
                vx, vy = ep.vx, ep.vy
                vl = math.hypot(vx, vy) or 1
                px_, py_ = -vy / vl, vx / vl
                s = 1 if (dx * px_ + dy * py_) > 0 else -1
                fx += px_ * s * 900 / d
                fy += py_ * s * 900 / d
        for b in run.bombs:
            if b[8]:
                dx, dy = p.x - b[0], p.y - b[1]
                d = math.hypot(dx, dy) + 1
                if d < b[3] + 40:
                    fx += dx / d * 7
                    fy += dy / d * 7
        for t in run.telegraphs:
            if t.kind in ("circle", "drop", "stamper"):
                dx, dy = p.x - t.x, p.y - t.y
                d = math.hypot(dx, dy) + 1
                if d < t.r + 50:
                    fx += dx / d * 6
                    fy += dy / d * 6
            elif t.kind == "line":
                ax, ay, bx, by = t.x, t.y, t.x2, t.y2
                lx, ly = bx - ax, by - ay
                l2 = lx * lx + ly * ly or 1
                k = max(0.0, min(1.0, ((p.x - ax) * lx + (p.y - ay) * ly) / l2))
                cx, cy = ax + lx * k, ay + ly * k
                dx, dy = p.x - cx, p.y - cy
                d = math.hypot(dx, dy) + 1
                if d < t.w + 50:
                    fx += dx / d * 6
                    fy += dy / d * 6
            elif t.kind == "band":
                if abs(p.y - t.y) < t.r:
                    fy += (1 if p.y > t.y else -1) * 8
        # sběr
        target = None
        best = 1e18
        lim = 320 if threat < 2.5 else 140
        for pk in run.pickups:
            if pk.kind in (P_XP, P_GOLDEGG, P_WORM, P_CHEST):
                d2 = (pk.x - p.x) ** 2 + (pk.y - p.y) ** 2
                pri = d2 * (0.2 if pk.kind == P_CHEST else 0.5 if pk.kind == P_WORM and p.hp < p.stats.max_hp * 0.6 else 1)
                if d2 < lim * lim * (4 if pk.kind == P_CHEST else 1) and pri < best:
                    best = pri
                    target = pk
        if target is not None:
            dx, dy = target.x - p.x, target.y - p.y
            d = math.hypot(dx, dy) + 1
            fx += dx / d * 1.2
            fy += dy / d * 1.2
        # kiting – kroužit kolem hrozby
        if threat > 0.3:
            tl = math.hypot(fx, fy) or 1
            fx += -fy / tl * 0.6 * self.side
            fy += fx / tl * 0.6 * self.side
        else:
            self.wander += dt
            if self.wander > 3:
                self.wander = 0
                self.side *= -1
            fx += math.cos(self.t * 0.4) * 0.4
            fy += math.sin(self.t * 0.4) * 0.4
        # aréna
        if run.arena is not None:
            ax, ay, ar = run.arena
            dx, dy = ax - p.x, ay - p.y
            d = math.hypot(dx, dy)
            if d > ar - 120:
                fx += dx / (d or 1) * 4
                fy += dy / (d or 1) * 4
        fl = math.hypot(fx, fy)
        if fl < 0.05:
            mx, my = 0.0, 0.0
        else:
            mx, my = fx / fl, fy / fl
        crow = run.crow_ready and (p.hp < p.stats.max_hp * 0.45 or close > 18 or bool(run.bosses))
        return mx, my, crow

    # --- karty ---------------------------------------------------------------------------------
    def choose(self) -> None:
        run = self.run
        offer = run.offer or []
        if not offer:
            return
        owned_evo_passives = {WEAPONS[w.id].evo_passive for w in run.weapons if not w.evolved}

        def score(c):
            s = c.rarity * 2.0
            if c.kind == "weapon":
                if not c.new:
                    s += 10 + c.cur
                elif len(run.weapons) < 4:
                    s += 8
                else:
                    s += 3
            elif c.kind == "passive":
                if c.id in owned_evo_passives:
                    s += 9
                s += 6 - PASSIVE_PRIO.index(c.id) * 0.4 if c.id in PASSIVE_PRIO else 2
                if c.new and len(run.passives) >= 5:
                    s -= 3
            elif c.kind == "heal":
                s += 6 if run.player.hp < run.player.stats.max_hp * 0.5 else 0
            return s
        best = max(offer, key=score)
        progression.apply_card(run, best)

    def step(self, dt: float) -> None:
        run = self.run
        if run.state == "levelup":
            self.choose()
            return
        if run.state == "chest":
            run.resume()
            return
        if run.state == "playing":
            mx, my, crow = self.control(dt)
        else:
            mx, my, crow = 0.0, 0.0, False
        run.update(dt, mx, my, crow)
