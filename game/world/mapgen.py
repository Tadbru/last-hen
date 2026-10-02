"""Nekonečná mapa z chunků: deterministické překážky, zóny, výbušné sudy a biomové hazardy."""
from __future__ import annotations

import math
import random

import pygame

from .. import assets
from ..gfx import tiles as T
from ..util import weighted_choice
from .entities import Telegraph

CHUNK = 480
CELL = 64          # stejná buňka jako grid nepřátel → sdílené klíče
OFF = 1_000_000.0
KMUL = 100_000
PAD = 26           # rozšíření bboxu překážky o max. poloměr entity

# Specifikace dekorací: sprite, tvar kolize (rect: šířka/výška u paty, circle: r), vrstva
DECOR_SPECS = {
    "haybale": dict(spr="haybale", shape="rect", cw=44, ch=18),
    "fence_h": dict(spr="fence_h", shape="rect", cw=48, ch=10),
    "fence_v": dict(spr="fence_v", shape="rect", cw=10, ch=34),
    "scarecrow": dict(spr="scarecrow", shape="circle", r=8),
    "rock": dict(spr="rock", shape="circle", r=16),
    "snowrock": dict(spr="snowrock", shape="circle", r=16),
    "barn": dict(spr="barn", misc=True, shape="rect", cw=110, ch=54),
    "coop": dict(spr="coop", misc=True, shape="rect", cw=72, ch=34),
    "bush": dict(spr="bush", shape=None),
    "tree": dict(spr="trunk", shape="circle", r=11, canopy="canopy"),
    "log": dict(spr="log", shape="rect", cw=50, ch=12),
    "pine": dict(spr="pine", shape="circle", r=11),
    "car": dict(spr="car", shape="rect", cw=58, ch=18),
    "bin": dict(spr="bin", shape="circle", r=11),
    "lamp": dict(spr="lamp", shape="circle", r=6),
    "hydrant": dict(spr="hydrant", shape="circle", r=7),
    "crate": dict(spr="crate", shape="rect", cw=30, ch=22),
    "machine": dict(spr="machine", shape="rect", cw=48, ch=24),
    "pipe": dict(spr="pipe", shape="rect", cw=46, ch=8),
    "wall": dict(spr=None, shape="rect"),
}
DECALS = {"flowers": ["flower_y", "flower_r", "flower_p"], "mushroom": ["mushroom"]}


class Obstacle:
    __slots__ = ("kind", "x", "y", "spr", "shape", "r", "l", "t", "rr", "b", "canopy", "canopy_a", "cx", "cy")

    def __init__(self, kind, x, y, spr, shape, r=0.0, l=0.0, t=0.0, rr=0.0, b=0.0):
        self.kind, self.x, self.y, self.spr, self.shape = kind, x, y, spr, shape
        self.r, self.l, self.t, self.rr, self.b = r, l, t, rr, b
        self.canopy = None
        self.canopy_a = None
        self.cx = x
        self.cy = y - r * 0.5 if shape == "circle" else y


class Zone:
    __slots__ = ("kind", "x", "y", "w", "h", "surf", "frames", "dx", "dy", "slow", "ice")

    def __init__(self, kind, x, y, w, h):
        self.kind, self.x, self.y, self.w, self.h = kind, x, y, w, h
        self.surf = None
        self.frames = None
        self.dx = self.dy = 0.0
        self.slow = 1.0
        self.ice = False

    def contains(self, px: float, py: float) -> bool:
        if self.kind == "conveyor":
            return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h
        rx, ry = self.w / 2, self.h / 2
        dx = (px - (self.x + rx)) / rx
        dy = (py - (self.y + ry)) / ry
        return dx * dx + dy * dy <= 1.0


class Chunk:
    __slots__ = ("obstacles", "zones", "decals", "barrels")

    def __init__(self):
        self.obstacles: list[Obstacle] = []
        self.zones: list[Zone] = []
        self.decals: list = []
        self.barrels: list = []     # [x, y, destroyed, enemy]


class WorldMap:
    def __init__(self, run, biome, seed: int, season: str | None = None) -> None:
        self.run = run
        self.biome = biome
        self.seed = seed & 0x7FFFFFFF
        self.season = season
        self.chunks: dict[tuple, Chunk] = {}
        self.ogrid: dict[int, list] = {}
        self.tiles = _tile_cache(biome)
        self._wall_cache: dict = {}
        self._barrel_t = 0.0
        self.hazard_t = 30.0
        self.conv_anim = 0.0
        self.headless = run.headless

    # --- generování ----------------------------------------------------------------
    def _rng(self, cx: int, cy: int) -> random.Random:
        return random.Random((self.seed * 2654435761 ^ (cx * 73856093) ^ (cy * 19349663)) & 0xFFFFFFFFFFFF)

    def ensure(self, x: float, y: float, rx: float = 520, ry: float = 760) -> None:
        cx0 = math.floor((x - rx) / CHUNK)
        cx1 = math.floor((x + rx) / CHUNK)
        cy0 = math.floor((y - ry) / CHUNK)
        cy1 = math.floor((y + ry) / CHUNK)
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                if (cx, cy) not in self.chunks:
                    self._gen(cx, cy)

    def _gen(self, cx: int, cy: int) -> None:
        ch = Chunk()
        self.chunks[(cx, cy)] = ch
        rng = self._rng(cx, cy)
        b = self.biome
        x0, y0 = cx * CHUNK, cy * CHUNK
        kinds = [k for k, _ in b.decor]
        weights = [w for _, w in b.decor]
        n = max(0, int(b.density + rng.uniform(-2.5, 2.5)))
        placed: list[tuple] = []
        for _ in range(n):
            kind = weighted_choice(rng, kinds, weights)
            x = x0 + rng.uniform(30, CHUNK - 30)
            y = y0 + rng.uniform(30, CHUNK - 30)
            if x * x + y * y < 190 * 190:
                continue
            big = kind in ("barn", "wall", "coop")
            min_d = 140 if big else 64
            if any((x - px) ** 2 + (y - py) ** 2 < (min_d + pr) ** 2 for px, py, pr in placed):
                continue
            if kind == "barrel":
                ch.barrels.append([x, y, False, None])
                placed.append((x, y, 20))
                continue
            if kind in DECALS:
                for _ in range(rng.randint(2, 5)):
                    name = rng.choice(DECALS[kind])
                    ch.decals.append((name, x + rng.uniform(-40, 40), y + rng.uniform(-30, 30)))
                continue
            ob = self._make_obstacle(kind, x, y, rng)
            if ob is not None:
                ch.obstacles.append(ob)
                self._register(ob)
                placed.append((x, y, 60 if big else 20))
        # zóny
        if b.zones:
            zk = [k for k, _ in b.zones]
            zw = [w for _, w in b.zones]
            nz = int(b.zone_density + rng.random() * 1.2)
            for _ in range(nz):
                kind = weighted_choice(rng, zk, zw)
                ch.zones.append(self._make_zone(kind, x0 + rng.uniform(20, CHUNK - 220), y0 + rng.uniform(20, CHUNK - 220), rng))
        # sezónní dekorace
        if self.season and rng.random() < 0.8:
            from ..data.meta import SEASONS
            name = SEASONS[self.season]["decor"]
            for _ in range(rng.randint(1, 3)):
                ch.decals.append((name, x0 + rng.uniform(20, CHUNK - 20), y0 + rng.uniform(20, CHUNK - 20)))

    def _make_obstacle(self, kind: str, x: float, y: float, rng) -> Obstacle | None:
        spec = DECOR_SPECS.get(kind)
        if spec is None:
            return None
        if kind == "car" and rng.random() < 0.5:
            spr_name = "car_red"
        else:
            spr_name = spec["spr"]
        if kind == "wall":
            w = rng.choice([96, 120, 150, 180])
            h = rng.choice([42, 54, 66])
            seed = rng.randrange(1 << 20)
            spr = None if self.headless else self._wall(w, h, seed)
            return Obstacle(kind, x, y, spr, "rect", l=x - w / 2, t=y - h, rr=x + w / 2, b=y)
        if self.headless:
            spr = None
        elif spec.get("misc"):
            spr = assets.sprites.misc[spr_name]
        else:
            spr = assets.sprites.decor[spr_name]
        if spec["shape"] == "circle":
            ob = Obstacle(kind, x, y, spr, "circle", r=spec["r"])
        elif spec["shape"] == "rect":
            cw, chh = spec["cw"], spec["ch"]
            ob = Obstacle(kind, x, y, spr, "rect", l=x - cw / 2, t=y - chh, rr=x + cw / 2, b=y)
        else:
            ob = Obstacle(kind, x, y, spr, None)
        if spec.get("canopy") and not self.headless:
            name = "canopy_dark" if self.biome.id == "forest" and rng.random() < 0.5 else spec["canopy"]
            ob.canopy = assets.sprites.misc[name]
            ob.canopy_a = _alpha_copy(ob.canopy, 110)
        return ob

    def _wall(self, w, h, seed):
        key = (w, h, seed % 8)
        s = self._wall_cache.get(key)
        if s is None:
            s = T.wall_surface(w, h, seed % 8)
            self._wall_cache[key] = s
        return s

    def _make_zone(self, kind: str, x: float, y: float, rng) -> Zone:
        if kind == "conveyor":
            horiz = rng.random() < 0.5
            w, h = (rng.choice([192, 240, 288]), 48) if horiz else (48, rng.choice([192, 240, 288]))
            z = Zone(kind, x, y, w, h)
            sgn = rng.choice([-1, 1])
            z.dx, z.dy = (110 * sgn, 0.0) if horiz else (0.0, 110 * sgn)
            if not self.headless:
                fr = T.conveyor_frames(w, h, horiz)
                if sgn < 0:
                    fr = fr[::-1]
                z.frames = fr
            return z
        sizes = {"puddle": ((72, 150), (42, 78)), "ice": ((130, 240), (80, 140)), "snowdrift": ((80, 150), (48, 80)),
                 "oil": ((70, 130), (40, 70))}
        (w0, w1), (h0, h1) = sizes.get(kind, ((80, 120), (50, 70)))
        w = int(rng.uniform(w0, w1)) // 3 * 3
        h = int(rng.uniform(h0, h1)) // 3 * 3
        z = Zone(kind, x, y, w, h)
        if kind == "puddle":
            z.slow = 0.6
        elif kind == "snowdrift":
            z.slow = 0.65
        elif kind in ("ice", "oil"):
            z.ice = True
            z.slow = 1.0 if kind == "ice" else 0.85
        if not self.headless:
            z.surf = T.zone_surface(kind, w, h, rng.randrange(1000))
        return z

    def _register(self, ob: Obstacle) -> None:
        if ob.shape is None:
            return
        if ob.shape == "circle":
            l, t, r, b = ob.cx - ob.r, ob.cy - ob.r, ob.cx + ob.r, ob.cy + ob.r
        else:
            l, t, r, b = ob.l, ob.t, ob.rr, ob.b
        inv = 1.0 / CELL
        x0 = int((l - PAD + OFF) * inv)
        x1 = int((r + PAD + OFF) * inv)
        y0 = int((t - PAD + OFF) * inv)
        y1 = int((b + PAD + OFF) * inv)
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                self.ogrid.setdefault(cx * KMUL + cy, []).append(ob)

    # --- kolize -------------------------------------------------------------------------
    def obstacles_at_key(self, key: int):
        return self.ogrid.get(key)

    def collide_circle(self, ent, r: float) -> bool:
        inv = 1.0 / CELL
        key = int((ent.x + OFF) * inv) * KMUL + int((ent.y + OFF) * inv)
        lst = self.ogrid.get(key)
        if not lst:
            return False
        return push_out(ent, r, lst)

    def blocked(self, x: float, y: float, r: float = 14) -> bool:
        inv = 1.0 / CELL
        lst = self.ogrid.get(int((x + OFF) * inv) * KMUL + int((y + OFF) * inv))
        if not lst:
            return False
        for ob in lst:
            if ob.shape == "circle":
                dx, dy = x - ob.cx, y - ob.cy
                if dx * dx + dy * dy < (r + ob.r) ** 2:
                    return True
            elif ob.l - r < x < ob.rr + r and ob.t - r < y < ob.b + r:
                return True
        return False

    def zones_near(self, x: float, y: float):
        cx, cy = math.floor(x / CHUNK), math.floor(y / CHUNK)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ch = self.chunks.get((cx + dx, cy + dy))
                if ch and ch.zones:
                    yield from ch.zones

    def apply_zones(self, player) -> None:
        slow, ice, px, py = 1.0, False, 0.0, 0.0
        for z in self.zones_near(player.x, player.y):
            if z.contains(player.x, player.y):
                if z.kind == "conveyor":
                    px += z.dx
                    py += z.dy
                else:
                    slow = min(slow, z.slow)
                    ice = ice or z.ice
        player.zone_mult = slow
        player.on_ice = ice
        player.zone_push = (px, py)

    # --- sudy ---------------------------------------------------------------------------------
    def update_barrels(self, dt: float) -> None:
        self._barrel_t -= dt
        if self._barrel_t > 0:
            return
        self._barrel_t = 0.4
        run = self.run
        px, py = run.player.x, run.player.y
        lim2 = 900 * 900
        for (cx, cy), ch in self.chunks.items():
            if not ch.barrels:
                continue
            for bar in ch.barrels:
                if bar[2]:
                    continue
                d2 = (bar[0] - px) ** 2 + (bar[1] - py) ** 2
                if d2 < lim2 and bar[3] is None:
                    bar[3] = run.spawn_prop(bar[0], bar[1], bar)
                elif d2 >= lim2 and bar[3] is not None:
                    run.despawn_prop(bar[3])
                    bar[3] = None

    # --- hazardy --------------------------------------------------------------------------------
    def update_hazards(self, dt: float) -> None:
        self.conv_anim += dt
        hz = self.biome.hazards
        if not hz:
            return
        run = self.run
        if run.state != "playing" or run.time < 20:
            return
        self.hazard_t -= dt
        if self.hazard_t > 0:
            return
        px, py = run.player.x, run.player.y
        if "avalanche" in hz:
            self.hazard_t = run.rng.uniform(32, 48)
            band_h = 150
            y = py + run.rng.uniform(-200, 200)
            run.banner("LAVINA!", (220, 240, 255), 1.6)
            run.sfx("warning")

            def hit(tel, y=y):
                run.sfx("avalanche")
                run.shake(0.5)
                p = run.player
                if abs(p.y - y) < band_h / 2:
                    p.take_damage(22 * run.enemy_dmg_mult(), p.x - 80, p.y, "lavina")
                for e in run.enemies_in_rect(run.camera.ox - 60, y - band_h / 2, run.camera.ox + 600, y + band_h / 2):
                    run.damage_enemy(e, 200, None, 1, 0, 300, crit=False)
                for i in range(40):
                    run.particles.puff(run.camera.ox + i * 14, y + run.rng.uniform(-band_h / 2, band_h / 2), 1,
                                       (250, 252, 255), 120, 12)
                run.add_beam([(run.camera.ox - 50, y), (run.camera.ox + 600, y)], band_h, 0.5, (240, 248, 255), "band")
            run.telegraphs.append(Telegraph("band", px, y, band_h, 1.6, hit, color=(200, 230, 255)))
        if "stamper" in hz:
            self.hazard_t = run.rng.uniform(5.5, 8.5)
            for _ in range(run.rng.randint(2, 4)):
                a = run.rng.uniform(0, math.tau)
                d = run.rng.uniform(0, 230)
                x, y = px + math.cos(a) * d, py + math.sin(a) * d

                def stamp(tel):
                    run.sfx("stamp")
                    run.shake(0.35)
                    p = run.player
                    if (p.x - tel.x) ** 2 + (p.y - tel.y) ** 2 < (tel.r + p.r) ** 2:
                        p.take_damage(20 * run.enemy_dmg_mult(), tel.x, tel.y, "lis")
                    run.area_damage(tel.x, tel.y, tel.r, 250, None, kb=0, crit=False)
                    run.particles.sparks(tel.x, tel.y, 12, (255, 200, 80), 200)
                    run.add_ring(tel.x, tel.y, tel.r * 0.5, tel.r * 1.2, 0.3, (255, 210, 120), 5)
                run.telegraphs.append(Telegraph("stamper", x, y, 52, 1.3, stamp, color=(255, 170, 40)))

    # --- render helpery ------------------------------------------------------------------------------
    def visible_chunks(self, ox: float, oy: float, w: int, h: int):
        cx0 = math.floor((ox - 140) / CHUNK)
        cx1 = math.floor((ox + w + 140) / CHUNK)
        cy0 = math.floor((oy - 140) / CHUNK)
        cy1 = math.floor((oy + h + 200) / CHUNK)
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                ch = self.chunks.get((cx, cy))
                if ch:
                    yield ch


def push_out(ent, r: float, lst) -> bool:
    hit = False
    for ob in lst:
        if ob.shape == "circle":
            dx = ent.x - ob.cx
            dy = ent.y - ob.cy
            rr = r + ob.r
            d2 = dx * dx + dy * dy
            if d2 < rr * rr:
                d = math.sqrt(d2) or 0.01
                push = rr - d
                ent.x += dx / d * push
                ent.y += dy / d * push
                hit = True
        elif ob.shape == "rect":
            x, y = ent.x, ent.y
            if ob.l - r < x < ob.rr + r and ob.t - r < y < ob.b + r:
                # nejmenší průnik
                left = x - (ob.l - r)
                right = (ob.rr + r) - x
                top = y - (ob.t - r)
                bot = (ob.b + r) - y
                m = min(left, right, top, bot)
                if m == left:
                    ent.x -= left
                elif m == right:
                    ent.x += right
                elif m == top:
                    ent.y -= top
                else:
                    ent.y += bot
                hit = True
    return hit


_TILE_CACHE: dict = {}


def _tile_cache(biome):
    if assets.headless:
        return []
    t = _TILE_CACHE.get(biome.id)
    if t is None:
        t = T.ground_tiles(biome)
        _TILE_CACHE[biome.id] = t
    return t


def _alpha_copy(s: pygame.Surface, a: int) -> pygame.Surface:
    c = s.copy()
    c.set_alpha(a)
    return c
