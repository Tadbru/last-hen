"""Hráčské zvíře – pohyb, statistiky, poškození, squash & stretch."""
from __future__ import annotations

import math

from ..data.characters import CharDef
from ..data.meta import NEST_BY_ID
from ..data.passives import PASSIVES

BASE_HP = 100.0
BASE_SPEED = 150.0
BASE_MAGNET = 72.0


class Stats:
    __slots__ = ("max_hp", "speed", "magnet", "might", "area", "cooldown", "proj_speed", "pierce", "armor",
                 "armor_pct", "regen", "luck", "growth", "crit_chance", "crit_mult", "crow_mult", "xp_req",
                 "duration")

    def __init__(self) -> None:
        self.max_hp = BASE_HP
        self.speed = BASE_SPEED
        self.magnet = BASE_MAGNET
        self.might = 1.0
        self.area = 1.0
        self.cooldown = 1.0
        self.proj_speed = 1.0
        self.pierce = 0
        self.armor = 0.0
        self.armor_pct = 0.0
        self.regen = 0.0
        self.luck = 1.0
        self.growth = 1.0
        self.crit_chance = 0.05
        self.crit_mult = 2.0
        self.crow_mult = 1.0
        self.xp_req = 1.0
        self.duration = 1.0


class Player:
    def __init__(self, run, char: CharDef, meta: dict) -> None:
        self.run = run
        self.char = char
        self.meta = meta
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.r = 12.0
        self.face = 0
        self.dir_x = 1.0
        self.dir_y = 0.0
        self.moving = False
        self.stats = Stats()
        self.hp = 1.0
        self.invuln = 0.0
        self.flash = 0.0
        self.anim = 0.0
        self.sq = 1.0          # squash & stretch (scale y)
        self.sq_v = 0.0
        self.slide = 0.0       # tučňák
        self.cluck_t = 4.0
        self.dead = False
        self.hit_count = 0
        self.no_hit_time = 0.0
        self.zone_mult = 1.0
        self.zone_push = (0.0, 0.0)
        self.on_ice = False
        self.golden_t = 20.0
        self.extra_dmg_mult = 1.0
        self.recompute(first=True)

    # --- statistiky -----------------------------------------------------------------
    def recompute(self, first: bool = False) -> None:
        c = self.char
        m = self.meta
        p = self.run.passives
        lv = lambda pid: p.get(pid, 0)  # noqa: E731
        st = self.stats
        old_max = st.max_hp
        st.max_hp = BASE_HP * c.hp * (1 + NEST_BY_ID["hp"]["step"] * m.get("hp", 0) + PASSIVES["grain"].step * lv("grain"))
        st.speed = BASE_SPEED * c.speed * (1 + NEST_BY_ID["speed"]["step"] * m.get("speed", 0) + PASSIVES["legs"].step * lv("legs"))
        st.magnet = BASE_MAGNET * (1 + NEST_BY_ID["magnet"]["step"] * m.get("magnet", 0) + PASSIVES["magnet"].step * lv("magnet"))
        st.might = c.might * (1 + NEST_BY_ID["dmg"]["step"] * m.get("dmg", 0) + PASSIVES["shell"].step * lv("shell"))
        st.might *= self.run.mod_dmg_mult
        st.area = 1 + PASSIVES["megaphone"].step * lv("megaphone")
        st.cooldown = c.cooldown * max(0.45, 1 + PASSIVES["clock"].step * lv("clock"))
        st.proj_speed = 1 + PASSIVES["glasses"].step * lv("glasses")
        st.pierce = (1 if lv("glasses") >= 2 else 0) + (1 if lv("glasses") >= 4 else 0)
        st.armor = PASSIVES["vest"].step * lv("vest")
        st.armor_pct = 0.05 * lv("vest")
        st.regen = PASSIVES["feed"].step * lv("feed")
        st.luck = 1 + PASSIVES["clover"].step * lv("clover")
        st.growth = (1 + NEST_BY_ID["xp"]["step"] * m.get("xp", 0) + PASSIVES["lucky_egg"].step * lv("lucky_egg")) * self.run.xp_mult
        st.crit_chance = c.crit_chance + 0.02 * lv("clover")
        st.crit_mult = c.crit_mult
        st.crow_mult = c.crow_mult
        st.xp_req = c.xp_req
        st.max_hp *= self.run.mod_hp_mult
        if first:
            self.hp = st.max_hp
        elif st.max_hp > old_max:
            self.hp += st.max_hp - old_max
        self.hp = min(self.hp, st.max_hp)

    # --- pohyb --------------------------------------------------------------------------
    def update(self, dt: float, mx: float, my: float) -> None:
        run = self.run
        st = self.stats
        if self.dead:
            return
        mag = math.hypot(mx, my)
        moving = mag > 0.05
        special = self.char.special
        zone_mult = self.zone_mult
        if special == "water" and (zone_mult < 1.0 or self.on_ice):
            zone_mult = 1.4
        speed = st.speed * zone_mult
        if moving:
            nx, ny = mx / mag, my / mag
            if special == "slide":
                dot = nx * self.dir_x + ny * self.dir_y
                if dot > 0.92:
                    self.slide = min(1.0, self.slide + dt * 0.55)
                else:
                    self.slide = max(0.0, self.slide - dt * 3.0 * (1.2 - dot))
                speed *= 1 + 0.6 * self.slide
            if not self.moving:
                self.sq_v -= 2.5     # začátek pohybu – stretch
            self.dir_x, self.dir_y = nx, ny
            tvx, tvy = nx * speed * min(1.0, mag), ny * speed * min(1.0, mag)
        else:
            tvx = tvy = 0.0
            if special == "slide":
                self.slide = max(0.0, self.slide - dt * 2.0)
        if special == "slide":
            accel = 520.0
        elif special != "water" and self.on_ice:
            accel = 260.0
        elif special != "water" and run.biome.slippery:
            accel = 900.0
        else:
            accel = 2400.0
        dvx, dvy = tvx - self.vx, tvy - self.vy
        dl = math.hypot(dvx, dvy)
        step = accel * dt
        if dl <= step:
            self.vx, self.vy = tvx, tvy
        else:
            self.vx += dvx / dl * step
            self.vy += dvy / dl * step
        px, py = self.zone_push
        self.x += (self.vx + px) * dt
        self.y += (self.vy + py) * dt
        run.map.collide_circle(self, self.r)
        run.clamp_to_arena(self)
        if self.vx > 8:
            self.face = 0
        elif self.vx < -8:
            self.face = 1
        sp = math.hypot(self.vx, self.vy)
        self.moving = sp > 20
        if self.moving:
            self.anim += dt * (6 + sp / 40)
        # squash & stretch pružina
        self.sq_v += (1.0 - self.sq) * 180 * dt
        self.sq_v *= math.exp(-dt * 12)
        self.sq += self.sq_v * dt
        # regenerace, nesmrtelnost
        if st.regen > 0 and self.hp < st.max_hp:
            self.hp = min(st.max_hp, self.hp + st.regen * dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt)
        self.no_hit_time += dt
        # občas kejhne
        if self.moving:
            self.cluck_t -= dt
            if self.cluck_t <= 0:
                self.cluck_t = run.rng.uniform(7, 14)
                run.sfx("cluck", 0.6)
        # Božena snáší zlatá vejce
        if special == "golden_egg":
            self.golden_t -= dt
            if self.golden_t <= 0:
                self.golden_t = 20.0
                run.lay_golden_egg(self.x - self.dir_x * 26, self.y - self.dir_y * 26 + 6)

    def take_damage(self, amount: float, sx: float | None = None, sy: float | None = None, src: str = "jiné") -> bool:
        run = self.run
        if self.dead or self.invuln > 0 or run.god:
            return False
        st = self.stats
        dmg = max(1.0, amount * (1 - min(0.5, st.armor_pct)) - st.armor)
        self.hp -= dmg
        self.invuln = 0.55
        self.flash = 0.18
        self.sq_v += 3.5      # squash
        self.hit_count += 1
        self.no_hit_time = 0.0
        run.stats_dmg_taken += dmg
        run.dmg_log[src] = run.dmg_log.get(src, 0.0) + dmg
        run.sfx("cluck_hurt", 0.8)
        run.particles.feathers(self.x, self.y - 10, 6, (250, 248, 240), 140)
        run.shake(0.28)
        if sx is not None:
            run.camera.kick(self.x - sx, self.y - sy, 7)
            dx, dy = self.x - sx, self.y - sy
            d = math.hypot(dx, dy) or 1
            self.vx += dx / d * 160
            self.vy += dy / d * 160
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            run.on_player_death()
        return True

    def heal(self, amount: float) -> None:
        self.hp = min(self.stats.max_hp, self.hp + amount)
