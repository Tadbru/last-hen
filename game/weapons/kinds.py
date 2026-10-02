"""Chování všech druhů zbraní. Evoluce používají stejné třídy s jinými parametry."""
from __future__ import annotations

import math

from .. import assets
from ..world.allies import AllyFox, Chick, Nest
from ..world.entities import M_BOOMERANG, M_LOB, M_SPIRAL, M_WAVE, Telegraph
from .base import Weapon

TAU = math.tau


def _rot(name: str):
    return assets.sprites.rot(name)


class LobWeapon(Weapon):
    """Vejce granát / Zlatá bomba – hod obloukem, výbuch při dopadu."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        rng_ = s["range"] * p.stats.area ** 0.5
        targets = run.targets(p.x, p.y, rng_, int(s["count"]))
        if not targets:
            return False
        nuke = s.get("nuke")
        for i, e in enumerate(targets):
            tx = e.x + run.rng.uniform(-14, 14)
            ty = e.y + run.rng.uniform(-14, 14)
            pr = run.add_proj(p.x, p.y - 10, 0, 0, 8, self.dmg(), self, life=99,
                              spr=assets.sprites.small["egg_gold" if nuke else "egg"])
            pr.motion = M_LOB
            pr.sx, pr.sy = p.x, p.y - 10
            pr.tx, pr.ty = tx, ty
            d = math.hypot(tx - p.x, ty - p.y)
            pr.dur = 0.42 + d / 700 + i * 0.05
            pr.height = 50 + d * 0.25
            pr.size = 1.6 if nuke else 1.0
        run.sfx("throw", 0.6)
        return True

    def on_land(self, pr) -> None:
        run = self.run
        s = self.s
        nuke = s.get("nuke")
        r = self.area(s["area"])
        dmg = pr.dmg
        if nuke:
            run.explosion(pr.x, pr.y, r, dmg, self, (255, 214, 70), kb=s["kb"], big=True)
            run.flash((255, 240, 180), 0.12)
        else:
            run.explosion(pr.x, pr.y, r, dmg, self, (255, 240, 200), kb=s["kb"])
            run.particles.blobs(pr.x, pr.y, 6, (255, 220, 60), 120)
        n = int(s.get("cluster", 0))
        for i in range(n):
            a = i * TAU / n + run.rng.uniform(-0.3, 0.3)
            d = r * run.rng.uniform(0.7, 1.1)
            run.bombs.append([pr.x + math.cos(a) * d, pr.y + math.sin(a) * d, 0.12 + i * 0.05, r * 0.55,
                              0.0, dmg * 0.5, self, (255, 230, 120) if not nuke else (255, 200, 60), False])


class PulseWeapon(Weapon):
    """Kokrhací vlna / Apokalypsa – rozpínající se kruhové vlny."""

    def __init__(self, *a, **k) -> None:
        self.queue: list[float] = []
        super().__init__(*a, **k)

    def fire(self) -> bool:
        run = self.run
        p = run.player
        r = self.area(self.s["area"])
        if run.nearest_enemy(p.x, p.y, r * 1.1) is None:
            return False
        waves = int(self.s.get("waves", 1))
        self.queue = [i * 0.32 for i in range(waves)]
        return True

    def update(self, dt: float) -> None:
        super().update(dt)
        if not self.queue:
            return
        self.queue = [q - dt for q in self.queue]
        while self.queue and self.queue[0] <= 0:
            self.queue.pop(0)
            run = self.run
            p = run.player
            s = self.s
            r = self.area(s["area"])
            evo = self.evolved
            col = (255, 110, 50) if evo else (255, 190, 90)
            run.add_wave(p.x, p.y, 12, r, 0.38, self.dmg(), self, kb=s["kb"], slow=s.get("slow", 0),
                         stun=s.get("stun", 0), color=col, follow=True)
            run.sfx("wave", 0.7)
            if evo:
                run.shake(0.12)


class ChicksWeapon(Weapon):
    """Kuřecí armáda / Kohoutí legie."""

    def __init__(self, *a, **k) -> None:
        self.chicks: list[Chick] = []
        super().__init__(*a, **k)

    def on_refresh(self) -> None:
        n = int(self.s["count"])
        for c in self.chicks:
            c.alive = False
        self.chicks = []
        for i in range(n):
            c = Chick(self.run, self, i)
            self.chicks.append(c)
            self.run.allies.append(c)

    def update(self, dt: float) -> None:
        pass   # kuřata se aktualizují jako spojenci

    def on_remove(self) -> None:
        for c in self.chicks:
            c.alive = False


class SpiralWeapon(Weapon):
    """Peří-shuriken / Peřinová vichřice."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        n = int(s["count"])
        base = run.rng.uniform(0, TAU)
        rot = _rot("feather")
        for i in range(n):
            pr = run.add_proj(p.x, p.y, 0, 0, 9, self.dmg(), self, pierce=self.pierce(),
                              life=s["dur"] * p.stats.duration, spr=None, kb=50)
            pr.motion = M_SPIRAL
            pr.ang = base + i * TAU / n
            pr.rad = 18
            pr.spin = s["spin"]
            pr.vx = self.pspeed(s["speed"]) * p.stats.area ** 0.5   # radiální rychlost
            pr.rot = rot
        run.sfx("whip", 0.4)
        return True


class LaserWeapon(Weapon):
    """Zobák-laser / Oči sokola."""

    def __init__(self, *a, **k) -> None:
        self.charging = 0.0
        self.active = 0.0
        self.angles: list[float] = []
        self.tick = 0.0
        super().__init__(*a, **k)

    def fire(self) -> bool:
        run = self.run
        p = run.player
        if run.nearest_enemy(p.x, p.y, self.s["range"]) is None:
            return False
        self.charging = self.s["charge"]
        run.sfx("laser_charge", 0.5)
        return True

    def _dirs(self) -> list[float]:
        run = self.run
        p = run.player
        beams = int(self.s["beams"])
        dx, dy, _ = self.aim(self.s["range"])
        base = math.atan2(dy, dx)
        spread = 0.16 if not self.s.get("sweep") else 0.35
        return [base + (i - (beams - 1) / 2) * spread for i in range(beams)]

    def update(self, dt: float) -> None:
        run = self.run
        p = run.player
        s = self.s
        if self.charging > 0:
            self.charging -= dt
            if run.tick % 3 == 0:
                run.particles.sparks(p.x + p.dir_x * 14, p.y - 14, 1, self.d.color, 60, 0.2)
            if self.charging <= 0:
                self.angles = self._dirs()
                if s.get("sweep"):
                    self.active = s["dur"]
                    self.tick = 0.0
                else:
                    self._shoot(1.0)
                run.sfx("laser", 0.7)
            return
        if self.active > 0:
            self.active -= dt
            # Oči sokola: paprsky sledují nejbližší cíl a kmitají kolem něj
            dx, dy, tgt = self.aim(s["range"])
            base = math.atan2(dy, dx)
            n = len(self.angles)
            wob = math.sin(self.active * 6) * 0.3
            self.angles = [base + wob + (i - (n - 1) / 2) * 0.35 for i in range(n)]
            self.tick -= dt
            if self.tick <= 0:
                self.tick = 0.1
                self._shoot(0.33, 0.12)
            if self.active <= 0:
                self.timer = self.cd()
            return
        super().update(dt)

    def _shoot(self, mult: float, life: float = 0.22) -> None:
        run = self.run
        p = run.player
        s = self.s
        ln = self.area(s["range"])
        w = self.area(s["width"])
        sx, sy = p.x + p.dir_x * 8, p.y - 14
        for a in self.angles:
            ex, ey = sx + math.cos(a) * ln, sy + math.sin(a) * ln
            for e in run.enemies_on_segment(sx, sy, ex, ey, w / 2):
                run.damage_enemy(e, self.dmg() * mult, self, math.cos(a), math.sin(a), 40)
            run.add_beam([(sx, sy), (ex, ey)], w, life, self.d.color, "laser")
        run.shake(0.06)


class NestWeapon(Weapon):
    """Hnízdo / Pevnost Kurník."""

    def __init__(self, *a, **k) -> None:
        self.nests: list[Nest] = []
        super().__init__(*a, **k)

    def fire(self) -> bool:
        run = self.run
        p = run.player
        self.nests = [n for n in self.nests if n.alive]
        while len(self.nests) >= int(self.s["count"]):
            old = self.nests.pop(0)
            old.alive = False
        n = Nest(run, self, p.x + run.rng.uniform(-10, 10), p.y + 10)
        self.nests.append(n)
        run.allies.append(n)
        run.particles.puff(n.x, n.y, 5, (200, 160, 100))
        run.sfx("throw", 0.5)
        return True

    def on_refresh(self) -> None:
        for n in getattr(self, "nests", []):
            pass

    def on_remove(self) -> None:
        for n in self.nests:
            n.alive = False


class LightningWeapon(Weapon):
    """Kvaltík / Bouřková křídla."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        targets = run.targets(p.x, p.y, s["range"], int(s["count"]))
        if not targets:
            return False
        dmg = self.dmg()
        area = self.area(s["area"])
        chain = int(s.get("chain", 0))
        stun = s.get("stun", 0.0)
        for e in targets:
            pts = _bolt(run, e.x, e.y - 340, e.x, e.y)
            run.add_beam(pts, 4, 0.18, (255, 250, 180), "bolt")
            run.area_damage(e.x, e.y, area, dmg, self, kb=40, stun=stun)
            run.particles.sparks(e.x, e.y, 5, (255, 250, 160), 160)
            last = e
            hit = {e.id}
            for _ in range(chain):
                nxt = run.nearest_enemy(last.x, last.y, 140, exclude=hit)
                if nxt is None:
                    break
                hit.add(nxt.id)
                run.add_beam(_bolt(run, last.x, last.y, nxt.x, nxt.y, 4), 3, 0.15, (200, 230, 255), "bolt")
                run.damage_enemy(nxt, dmg * 0.7, self, 0, 0, 0, stun=stun)
                last = nxt
        run.sfx("zap", 0.6)
        return True


def _bolt(run, x1, y1, x2, y2, segs: int = 7):
    pts = [(x1, y1)]
    for i in range(1, segs):
        t = i / segs
        pts.append((x1 + (x2 - x1) * t + run.rng.uniform(-14, 14), y1 + (y2 - y1) * t + run.rng.uniform(-8, 8)))
    pts.append((x2, y2))
    return pts


class StinkWeapon(Weapon):
    """Slepičí smrad / Biologická zbraň."""

    def __init__(self, *a, **k) -> None:
        self.aura = None
        super().__init__(*a, **k)

    def on_refresh(self) -> None:
        aura_r = self.s.get("aura", 0)
        if aura_r and self.aura is None:
            self.aura = self.run.add_area(0, 0, aura_r, self.s["dmg"], 0.4, 1e9, "aura", self,
                                          slow=self.s["slow"], follow=True, color=(150, 255, 80))

    def update(self, dt: float) -> None:
        if self.aura is not None:
            self.aura.r = self.area(self.s["aura"])
            self.aura.dmg = self.dmg()
        super().update(dt)

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        n = int(s["count"])
        targets = run.random_enemies(p.x, p.y, 260, n)
        r = self.area(s["area"])
        for i in range(n):
            if i < len(targets):
                x, y = targets[i].x, targets[i].y
            else:
                a = run.rng.uniform(0, TAU)
                x, y = p.x + math.cos(a) * 60, p.y + math.sin(a) * 60
            run.add_area(x, y, r, self.dmg(), 0.4, s["dur"] * p.stats.duration, "cloud", self, slow=s["slow"],
                         color=(130, 230, 90))
        run.sfx("cloud", 0.5)
        return True

    def on_remove(self) -> None:
        if self.aura is not None:
            self.aura.alive = False


class FoxesWeapon(Weapon):
    """Vlčí vytí / Liščí kmotr."""

    def __init__(self, *a, **k) -> None:
        self.foxes: list[AllyFox] = []
        super().__init__(*a, **k)

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        self.foxes = [f for f in self.foxes if f.alive]
        if s.get("permanent"):
            want = int(s["count"]) + (1 if s.get("alpha") else 0)
            if len(self.foxes) >= want:
                return True
            has_alpha = any(f.alpha_fox for f in self.foxes)
            while len(self.foxes) < want:
                alpha = s.get("alpha") and not has_alpha
                has_alpha = has_alpha or alpha
                self._summon(1e9, alpha)
            run.sfx("howl", 0.6)
            return True
        if run.nearest_enemy(p.x, p.y, 420) is None:
            return False
        for _ in range(int(s["count"])):
            self._summon(s["dur"] * p.stats.duration, False)
        run.sfx("howl", 0.7)
        run.add_text(p.x, p.y - 40, "Au-uuu!", (255, 200, 120), 2, 0.9)
        return True

    def _summon(self, life: float, alpha: bool) -> None:
        run = self.run
        p = run.player
        a = run.rng.uniform(0, TAU)
        f = AllyFox(run, self, p.x + math.cos(a) * 40, p.y + math.sin(a) * 40, life, alpha)
        self.foxes.append(f)
        run.allies.append(f)
        run.particles.puff(f.x, f.y, 4, (255, 210, 140))

    def on_remove(self) -> None:
        for f in self.foxes:
            f.alive = False


class CakeWeapon(Weapon):
    """Koláč z vajec / Svatební dort."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        targets = run.targets(p.x, p.y, 380, int(s["count"]))
        if not targets:
            return False
        r = self.area(s["area"])
        dmg = self.dmg()
        big = self.evolved
        seen = set()
        for i, e in enumerate(targets):
            tx, ty = e.x, e.y
            if e.id in seen:
                tx += run.rng.uniform(-r * 0.4, r * 0.4)
                ty += run.rng.uniform(-r * 0.4, r * 0.4)
            seen.add(e.id)

            def land(tel, r=r, dmg=dmg, big=big):
                run.explosion(tel.x, tel.y, r, dmg, self, (255, 200, 220), kb=240, big=big)
                run.particles.blobs(tel.x, tel.y, 10, (255, 240, 245), 200)
                run.particles.blobs(tel.x, tel.y, 6, (255, 160, 190), 180)
                if s.get("cream"):
                    run.add_area(tel.x, tel.y, r * 0.8, dmg * 0.08, 0.5, 3.0, "cream", self, slow=0.5,
                                 color=(255, 245, 230))
                if s.get("xp_drop"):
                    for _ in range(3):
                        run.drop_xp(tel.x + run.rng.uniform(-r / 2, r / 2), tel.y + run.rng.uniform(-r / 2, r / 2), 2)
            run.telegraphs.append(Telegraph("cake", tx, ty, r, 0.75 + i * 0.12, land, color=(255, 170, 200)))
        run.sfx("whistle", 0.5)
        return True


class GunWeapon(Weapon):
    """Vodní pistole / Hasičská hadice."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        dx, dy, tgt = self.aim(460)
        if tgt is None and not p.moving:
            return False
        base = math.atan2(dy, dx)
        n = int(s["count"])
        spread = math.radians(s["spread"])
        sp = self.pspeed(s["speed"])
        spr = assets.sprites.small["water"]
        for i in range(n):
            a = base + (i - (n - 1) / 2) * spread + run.rng.uniform(-0.04, 0.04)
            pr = run.add_proj(p.x + math.cos(a) * 14, p.y - 10 + math.sin(a) * 14, math.cos(a) * sp, math.sin(a) * sp,
                              7, self.dmg(), self, pierce=self.pierce(), life=s["life"], spr=spr, kb=s.get("kb", 30))
            pr.slow = s.get("slow", 0.0)
        run.sfx("water", 0.35)
        return True


class WhipWeapon(Weapon):
    """Zobák-šleh / Husí hněv."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        r = self.area(s["area"])
        if run.nearest_enemy(p.x, p.y, r + 30) is None:
            return False
        arc = math.radians(s["arc"])
        dx, dy, _ = self.aim(r + 40)
        base = math.atan2(dy, dx)
        dirs = [base] + ([base + math.pi] if s.get("sides", 1) >= 2 and s["arc"] < 360 else [])
        dmg = self.dmg()
        hit = set()
        for d in dirs:
            for e in run.grid.query(p.x, p.y, r + 30):
                if not e.alive or e.id in hit:
                    continue
                ex, ey = e.x - p.x, e.y - p.y
                dist = math.hypot(ex, ey)
                if dist > r + e.r:
                    continue
                if arc < TAU - 0.01:
                    da = (math.atan2(ey, ex) - d + math.pi) % TAU - math.pi
                    if abs(da) > arc / 2 + 0.2:
                        continue
                hit.add(e.id)
                run.damage_enemy(e, dmg, self, ex, ey, s["kb"])
            run.add_beam([(p.x, p.y - 8), (d, min(arc, TAU))], r, 0.16, self.d.color, "slash")
        run.sfx("whip", 0.6)
        return True


class ShotgunWeapon(Weapon):
    """Brokovnice z peří / Peří Gatling."""

    def __init__(self, *a, **k) -> None:
        self.burst_q: list[float] = []
        super().__init__(*a, **k)

    def fire(self) -> bool:
        p = self.run.player
        dx, dy, tgt = self.aim(400)
        if tgt is None and not p.moving:
            return False
        self._blast(math.atan2(dy, dx))
        self.burst_q = [0.16 * (i + 1) for i in range(int(self.s.get("bursts", 1)) - 1)]
        return True

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.burst_q:
            self.burst_q = [q - dt for q in self.burst_q]
            while self.burst_q and self.burst_q[0] <= 0:
                self.burst_q.pop(0)
                dx, dy, _ = self.aim(400)
                self._blast(math.atan2(dy, dx))

    def _blast(self, base: float) -> None:
        run = self.run
        p = run.player
        s = self.s
        n = int(s["count"])
        spread = math.radians(s["spread"])
        sp = self.pspeed(s["speed"])
        rot = _rot("feather")
        for i in range(n):
            a = base + (i / max(1, n - 1) - 0.5) * spread if n > 1 else base
            a += run.rng.uniform(-0.05, 0.05)
            v = sp * run.rng.uniform(0.85, 1.1)
            pr = run.add_proj(p.x, p.y - 10, math.cos(a) * v, math.sin(a) * v, 7, self.dmg(), self,
                              pierce=self.pierce(), life=s["life"], kb=70)
            pr.rot = rot
        run.sfx("shotgun", 0.45)
        if not self.evolved:
            run.camera.kick(-math.cos(base), -math.sin(base), 3)


class WavesWeapon(Weapon):
    """Zvukové vlny / Rockový koncert."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        dirs = int(s["dirs"])
        dx, dy, tgt = self.aim(380)
        if tgt is None and not p.moving:
            return False
        base = math.atan2(dy, dx)
        if dirs == 1:
            angs = [base]
        elif dirs == 2:
            angs = [base, base + math.pi]
        else:
            angs = [base + i * TAU / dirs for i in range(dirs)]
        sp = self.pspeed(s["speed"])
        size = s["size"] * p.stats.area
        for a in angs:
            pr = run.add_proj(p.x, p.y - 10, math.cos(a) * sp, math.sin(a) * sp, 16 * size, self.dmg(), self,
                              pierce=999, life=s["life"], kb=s["kb"])
            pr.motion = M_WAVE
            pr.size = size
            pr.ang = a
            pr.stun = s.get("stun", 0.0)
            pr.color = self.d.color
        run.sfx("wave", 0.45)
        return True


class FanWeapon(Weapon):
    """Ocas-vějíř / Duhová show."""

    COLORS = [(44, 172, 160), (82, 142, 232), (252, 216, 64), (168, 82, 204), (226, 48, 52)]

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        dx, dy, tgt = self.aim(420)
        if tgt is None and not p.moving:
            return False
        base = math.atan2(dy, dx)
        n = int(s["count"])
        spread = math.radians(min(360, s["spread"]))
        sp = self.pspeed(s["speed"])
        rot = _rot("feather_c")
        full = s["spread"] >= 360
        for i in range(n):
            if full:
                a = base + i * TAU / n
            else:
                a = base + (i / max(1, n - 1) - 0.5) * spread if n > 1 else base
            pr = run.add_proj(p.x, p.y - 12, math.cos(a) * sp, math.sin(a) * sp, 7, self.dmg(), self,
                              pierce=self.pierce(), life=s["life"], kb=40)
            pr.rot = rot
            pr.hyp = s.get("hyp", 0.0)
        run.sfx("whip", 0.4)
        return True


class BoomerangWeapon(Weapon):
    """Mražená ryba / Ledová tsunami."""

    def fire(self) -> bool:
        run = self.run
        p = run.player
        s = self.s
        n = int(s["count"])
        if s.get("radial"):
            base = run.rng.uniform(0, TAU)
            angs = [base + i * TAU / n for i in range(n)]
            for i, t in enumerate(run.random_enemies(p.x, p.y, s["range"] + 80, 3, nearest=True)):
                angs[i] = math.atan2(t.y - p.y, t.x - p.x) + (i - 1) * 0.12
        else:
            targets = run.random_enemies(p.x, p.y, s["range"] + 80, n, nearest=True)
            if not targets and not p.moving:
                return False
            angs = []
            for i in range(n):
                if i < len(targets):
                    angs.append(math.atan2(targets[i].y - p.y, targets[i].x - p.x))
                else:
                    angs.append(math.atan2(p.dir_y, p.dir_x) + (i - n / 2) * 0.5)
        sp = self.pspeed(s["speed"])
        rot = _rot("fish")
        for a in angs:
            pr = run.add_proj(p.x, p.y - 10, math.cos(a) * sp, math.sin(a) * sp, 10 * s["size"], self.dmg(), self,
                              pierce=999, life=6.0, kb=50)
            pr.motion = M_BOOMERANG
            pr.rad = self.area(s["range"])
            pr.slow = s.get("slow", 0.0)
            pr.freeze = s.get("freeze", 0.0)
            pr.rot = rot
            pr.size = s["size"]
        run.sfx("whip", 0.4)
        return True


KINDS = {
    "lob": LobWeapon, "pulse": PulseWeapon, "chicks": ChicksWeapon, "spiral": SpiralWeapon, "laser": LaserWeapon,
    "nest": NestWeapon, "lightning": LightningWeapon, "stink": StinkWeapon, "foxes": FoxesWeapon, "cake": CakeWeapon,
    "gun": GunWeapon, "whip": WhipWeapon, "shotgun": ShotgunWeapon, "waves": WavesWeapon, "fan": FanWeapon,
    "boomerang": BoomerangWeapon,
}
