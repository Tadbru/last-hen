"""Základ zbraně: úrovně, cooldown, škálování statistikami hráče."""
from __future__ import annotations

import math

from ..data.weapons import WEAPONS, WeaponDef


class Weapon:
    def __init__(self, run, wdef: WeaponDef, level: int = 1) -> None:
        self.run = run
        self.d = wdef
        self.level = level
        self.s: dict = wdef.stats_at(level)
        self.timer = 0.4
        self.damage_dealt = 0.0
        self.kills = 0
        self.on_refresh()

    @property
    def id(self) -> str:
        return self.d.id

    @property
    def evolved(self) -> bool:
        return self.d.evolution

    def set_level(self, level: int) -> None:
        self.level = level
        self.s = self.d.stats_at(level)
        self.on_refresh()

    # --- škálování --------------------------------------------------------------------
    def dmg(self) -> float:
        return self.s.get("dmg", 10) * self.run.player.stats.might

    def cd(self) -> float:
        return max(0.05, self.s.get("cd", 1.0) * self.run.player.stats.cooldown)

    def area(self, v: float) -> float:
        return v * self.run.player.stats.area

    def pierce(self) -> int:
        return int(self.s.get("pierce", 0)) + self.run.player.stats.pierce

    def pspeed(self, v: float) -> float:
        return v * self.run.player.stats.proj_speed

    def aim(self, max_d: float = 450.0) -> tuple[float, float, object]:
        """Směr na nejbližšího nepřítele, jinak směr pohybu."""
        p = self.run.player
        e = self.run.nearest_enemy(p.x, p.y, max_d)
        if e is not None:
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy) or 1
            return dx / d, dy / d, e
        return p.dir_x, p.dir_y, None

    # --- životní cyklus ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            if self.fire():
                self.timer += self.cd()
                if self.timer < 0:
                    self.timer = self.cd()
            else:
                self.timer = 0.15

    def fire(self) -> bool:
        return False

    def on_refresh(self) -> None:
        pass

    def on_land(self, p) -> None:
        pass

    def on_remove(self) -> None:
        pass


def make_weapon(run, wid: str, level: int = 1) -> Weapon:
    from .kinds import KINDS
    d = WEAPONS[wid]
    cls = KINDS[d.kind]
    return cls(run, d, level)
