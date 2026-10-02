"""Spojenci hráče: kuřata (Kuřecí armáda), lišky (Vlčí vytí), hnízda (Hnízdo)."""
from __future__ import annotations

import math

from .. import assets
from .entities import M_STRAIGHT


class Ally:
    __slots__ = ("run", "x", "y", "alive", "face", "anim", "spr", "kind", "r")

    def __init__(self, run, x, y) -> None:
        self.run = run
        self.x, self.y = x, y
        self.alive = True
        self.face = 0
        self.anim = 0.0
        self.spr = None
        self.kind = ""
        self.r = 8.0

    def update(self, dt: float) -> None:  # pragma: no cover - přepisují potomci
        pass


class Chick(Ally):
    __slots__ = ("weapon", "slot", "state", "cd", "tx", "ty", "hit", "t", "ang")

    def __init__(self, run, weapon, slot: int) -> None:
        super().__init__(run, run.player.x, run.player.y)
        self.weapon = weapon
        self.slot = slot
        self.state = 0
        self.cd = 0.3 + slot * 0.13
        self.tx = self.ty = 0.0
        self.hit: set = set()
        self.t = 0.0
        self.ang = 0.0
        self.kind = "chick"
        rooster = weapon.s.get("rooster")
        self.spr = assets.sprites.small["rooster_chick" if rooster else "chick"]

    def update(self, dt: float) -> None:
        run = self.run
        w = self.weapon
        s = w.s
        p = run.player
        n = max(1, len(w.chicks))
        self.ang = run.time * 1.6 + self.slot * math.tau / n
        orbit = s["orbit"] * p.stats.area ** 0.5
        ox = p.x + math.cos(self.ang) * orbit
        oy = p.y + math.sin(self.ang) * orbit * 0.8
        self.anim += dt * 10
        if self.state == 0:
            self.x += (ox - self.x) * min(1.0, dt * 12)
            self.y += (oy - self.y) * min(1.0, dt * 12)
            self.cd -= dt
            if self.cd <= 0:
                e = run.nearest_enemy(self.x, self.y, s["range"] * p.stats.area ** 0.5)
                if e is not None:
                    self.state = 1
                    self.tx, self.ty = e.x, e.y
                    self.t = 0.0
                    self.hit.clear()
                else:
                    self.cd = 0.25
        elif self.state == 1:
            self.t += dt
            dx, dy = self.tx - self.x, self.ty - self.y
            d = math.hypot(dx, dy)
            sp = s["speed"] * p.stats.proj_speed
            if d < sp * dt or self.t > 0.6:
                self.state = 2
            else:
                self.x += dx / d * sp * dt
                self.y += dy / d * sp * dt
                self.face = 0 if dx > 0 else 1
            dmg = w.dmg()
            for e in run.grid.query(self.x, self.y, 30):
                if e.alive and e.id not in self.hit and not e.prop:
                    if (e.x - self.x) ** 2 + (e.y - self.y) ** 2 < (e.r + 10) ** 2:
                        self.hit.add(e.id)
                        run.damage_enemy(e, dmg, w, dx, dy, 90)
                        run.sfx("bite", 0.4)
        else:
            dx, dy = ox - self.x, oy - self.y
            d = math.hypot(dx, dy)
            sp = s["speed"] * 1.2
            if d < sp * dt + 2:
                self.state = 0
                self.cd = s["cd"] * p.stats.cooldown
            else:
                self.x += dx / d * sp * dt
                self.y += dy / d * sp * dt
                self.face = 0 if dx > 0 else 1


class AllyFox(Ally):
    __slots__ = ("weapon", "life", "target", "retarget", "bite_cd", "alpha_fox", "anim_spr")

    def __init__(self, run, weapon, x, y, life: float, alpha_fox: bool = False) -> None:
        super().__init__(run, x, y)
        self.weapon = weapon
        self.life = life
        self.target = None
        self.retarget = 0.0
        self.bite_cd = 0.0
        self.alpha_fox = alpha_fox
        self.kind = "fox"
        self.anim_spr = assets.sprites.enemies["ally_alpha" if alpha_fox else "ally_fox"]
        self.r = 16 if alpha_fox else 12

    def update(self, dt: float) -> None:
        run = self.run
        w = self.weapon
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            run.particles.puff(self.x, self.y, 5, (250, 200, 120))
            return
        self.retarget -= dt
        t = self.target
        if t is None or not t.alive or self.retarget <= 0:
            self.retarget = 0.4
            self.target = t = run.nearest_enemy(self.x, self.y, 420)
        sp = w.s["speed"] * (1.15 if self.alpha_fox else 1.0)
        if t is not None:
            dx, dy = t.x - self.x, t.y - self.y
        else:
            p = run.player
            a = run.time + id(self) % 7
            dx, dy = p.x + math.cos(a) * 60 - self.x, p.y + math.sin(a) * 60 - self.y
        d = math.hypot(dx, dy) or 1
        reach = (t.r if t is not None else 0) + self.r
        if d > reach:
            self.x += dx / d * sp * dt
            self.y += dy / d * sp * dt
            self.anim += dt * 8
        self.face = 0 if dx > 0 else 1
        self.bite_cd -= dt
        if t is not None and d <= reach + 6 and self.bite_cd <= 0:
            self.bite_cd = 0.5
            dmg = w.dmg() * (2.5 if self.alpha_fox else 1.0)
            run.damage_enemy(t, dmg, w, dx, dy, 60)
            run.sfx("bite", 0.35)


class Nest(Ally):
    __slots__ = ("weapon", "life", "fire_t", "pulse")

    def __init__(self, run, weapon, x, y) -> None:
        super().__init__(run, x, y)
        self.weapon = weapon
        self.life = weapon.s["dur"] * run.player.stats.duration
        self.fire_t = 0.2
        self.kind = "nest"
        self.pulse = 0.0
        fortress = weapon.s.get("explode")
        self.spr = assets.sprites.small["fortress" if fortress else "nest"]
        self.r = 18

    def update(self, dt: float) -> None:
        run = self.run
        w = self.weapon
        s = w.s
        self.life -= dt
        self.pulse = max(0.0, self.pulse - dt * 4)
        if self.life <= 0:
            self.alive = False
            run.particles.puff(self.x, self.y, 6, (190, 140, 80))
            return
        heal = s.get("heal", 0)
        if heal:
            p = run.player
            if (p.x - self.x) ** 2 + (p.y - self.y) ** 2 < 100 * 100:
                p.heal(heal * dt)
        self.fire_t -= dt
        if self.fire_t > 0:
            return
        e = run.nearest_enemy(self.x, self.y, s["range"])
        if e is None:
            self.fire_t = 0.2
            return
        self.fire_t = s["fire"] * run.player.stats.cooldown
        self.pulse = 1.0
        shots = int(s["shots"])
        base = math.atan2(e.y - self.y, e.x - self.x)
        spread = 0.22
        for i in range(shots):
            a = base + (i - (shots - 1) / 2) * spread
            sp = 360 * run.player.stats.proj_speed
            pr = run.add_proj(self.x, self.y - 12, math.cos(a) * sp, math.sin(a) * sp, 7, w.dmg(), w,
                              pierce=run.player.stats.pierce, life=1.2, spr=assets.sprites.small["egg"], kb=60)
            pr.motion = M_STRAIGHT
            if s.get("explode"):
                pr.explode = 34
        run.sfx("throw", 0.3)
