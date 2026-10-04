"""Pool částic s pevným stropem – žádné alokace během hry.

Částice se kreslí jako předrenderované pixel-art sprity (mřížka 3 px jako zbytek hry): kulaté chuchvalce
kouře, ohnivé koule s barevnou rampou, jiskry s ocáskem, peříčka, úlomky a aditivní záře.
Vše jde jednou dávkou přes fblits. Pozadí (spáleniště po výbuchu) se kreslí zvlášť pod entity.
"""
from __future__ import annotations

import math
import random

import pygame

FEATHER, SPARK, PUFF, BLOB, STAR, ZZZ, FIRE, SMOKE, GLOW, DEBRIS, POP = range(11)
HEART, FLAKE, NOTE, DROP, SHARD = range(11, 16)      # ultimátky: srdíčko, vločka, nota, kapka, střep ledu

# pixel mapy malých částic ultimátek (# = barva, + = světlejší odlesk, - = tmavší spodek)
_SHAPES = {
    HEART: [".#.#.", "#+###", "#####", ".---.", "..-.."],
    -HEART: [".#.#.", "#+.##", "##.##", ".-.-.", "..-.."],      # zlomené srdce (konec okouzlení)
    FLAKE: ["..#..", "#.#.#", ".#+#.", "#.#.#", "..#.."],
    NOTE: ["..##.", "..#.#", "..#..", "-##..", "--#.."],
    DROP: [".#.", "+##", "###", ".-."],
    SHARD: [".+.", "++#", "###", "#-#", ".-."],
}

G = 3                       # pixelová mřížka efektů (= PX, 1 art pixel)
_ALPHA_STEPS = 6
MAX_DECALS = 24
_HAS_FBLITS = hasattr(pygame.Surface, "fblits")


def _mul(c, f: float):
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


def _mix(a, b, t: float):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def _disc_cells(r: int):
    """Buňky pixelového kruhu o poloměru r (v art pixelech) – mírně „kulatější“ než přesný kruh."""
    lim = r * r + r * 0.8
    return [(i, j) for j in range(-r, r + 1) for i in range(-r, r + 1) if i * i + j * j <= lim]


def _blit_add(surf, seq) -> None:
    if not seq:
        return
    if _HAS_FBLITS:
        surf.fblits(seq, pygame.BLEND_RGB_ADD)
    else:
        surf.blits([(s, p, None, pygame.BLEND_RGB_ADD) for s, p in seq], False)


class _SpriteCache:
    """Malé sprity částic podle (druh, barva, velikost, průhlednost). Omezená velikost."""

    def __init__(self) -> None:
        self.d: dict = {}

    def _put(self, key, s):
        if len(self.d) > 1800:
            self.d.clear()
        self.d[key] = s
        return s

    def disc(self, r: int, col, a: int, shade: bool = True) -> pygame.Surface:
        """Plný pixelový kruh (r v art px) s jemným objemem: světlejší vlevo nahoře, tmavší vpravo dole."""
        key = ("d", r, col, a, shade)
        s = self.d.get(key)
        if s is not None:
            return s
        n = r * 2 + 1
        low = pygame.Surface((n, n), pygame.SRCALPHA)
        hi, lo = _mul(col, 1.18), _mul(col, 0.8)
        for i, j in _disc_cells(r):
            c = col
            if shade and r >= 1:
                if i + j <= -r * 0.9:
                    c = hi
                elif i + j >= r * 0.9:
                    c = lo
            low.set_at((i + r, j + r), (*c, a))
        s = pygame.transform.scale(low, (n * G, n * G))
        return self._put(key, s)

    def glow(self, r: int, col, k: float) -> pygame.Surface:
        """Aditivní záře: soustředné pixelové kruhy, intenzita zapečená do RGB (černá = nic)."""
        key = ("g", r, col, int(k * 8))
        s = self.d.get(key)
        if s is not None:
            return s
        n = r * 2 + 1
        low = pygame.Surface((n, n))
        low.fill((0, 0, 0))
        kk = int(k * 8) / 8
        for rr, f in ((r, 0.22), (max(1, int(r * 0.66)), 0.45), (max(0, int(r * 0.33)), 0.8)):
            c = _mul(col, f * kk)
            for i, j in _disc_cells(rr):
                low.set_at((i + r, j + r), c)
        s = pygame.transform.scale(low, (n * G, n * G))
        return self._put(key, s)

    def spark(self, col, size: int, dx: int, dy: int) -> pygame.Surface:
        """Jiskra s ocáskem ve směru pohybu (dx, dy ∈ {-1, 0, 1})."""
        key = ("s", col, size, dx, dy)
        s = self.d.get(key)
        if s is not None:
            return s
        w = size * 3
        s = pygame.Surface((w, w), pygame.SRCALPHA)
        c = w // 2 - size // 2
        tail = _mul(col, 0.7)
        s.fill((*tail, 200), (c - dx * size, c - dy * size, size, size))
        s.fill((*_mix(col, (255, 255, 255), 0.55), 255), (c, c, size, size))
        return self._put(key, s)

    def feather(self, col, flip: int) -> pygame.Surface:
        key = ("f", col, flip)
        s = self.d.get(key)
        if s is not None:
            return s
        rows = [".##", "##."] if flip else ["##.", ".##"]
        low = pygame.Surface((3, 2), pygame.SRCALPHA)
        dark = _mul(col, 0.72)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    low.set_at((x, y), (*(col if y == 0 else dark), 255))
        s = pygame.transform.scale(low, (6, 4))
        return self._put(key, s)

    def star(self, col, big: bool) -> pygame.Surface:
        key = ("t", col, big)
        s = self.d.get(key)
        if s is not None:
            return s
        u = 3 if big else 2
        s = pygame.Surface((u * 3, u * 3), pygame.SRCALPHA)
        s.fill((*col, 255), (u, 0, u, u * 3))
        s.fill((*col, 255), (0, u, u * 3, u))
        s.fill((255, 255, 240, 255), (u, u, u, u))
        return self._put(key, s)

    def shape(self, kind: int, col, g: int) -> pygame.Surface:
        """Malá pixelová částice podle mapy v _SHAPES (g = velikost art pixelu)."""
        key = ("sh", kind, col, g)
        s = self.d.get(key)
        if s is not None:
            return s
        rows = _SHAPES[kind]
        low = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
        hi, lo = _mix(col, (255, 255, 255), 0.55), _mul(col, 0.7)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    low.set_at((x, y), (*(hi if ch == "+" else lo if ch == "-" else col), 255))
        s = pygame.transform.scale(low, (low.get_width() * g, low.get_height() * g))
        return self._put(key, s)

    def chunk(self, col, w: int, h: int) -> pygame.Surface:
        key = ("c", col, w, h)
        s = self.d.get(key)
        if s is not None:
            return s
        s = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        s.fill((26, 16, 30, 255))
        s.fill((*col, 255), (1, 1, w, h))
        s.fill((*_mul(col, 1.2), 255), (1, 1, w, 1))
        return self._put(key, s)

    def ring(self, r: int, col, width: int) -> pygame.Surface:
        key = ("r", r, col, width)
        s = self.d.get(key)
        if s is not None:
            return s
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*col, 255), (r + 1, r + 1), r, width)
        return self._put(key, s)

    def gas(self, r: int, col, a: int) -> pygame.Surface:
        """Chuchvalec plynu: tmavší okraj, ditherovaný vnitřek, světlejší vršek (pixel art, r v art px)."""
        key = ("gas", r, col, a)
        s = self.d.get(key)
        if s is not None:
            return s
        n = r * 2 + 1
        low = pygame.Surface((n, n), pygame.SRCALPHA)
        rim, dark, light = _mul(col, 0.62), _mul(col, 0.84), _mix(col, (255, 255, 230), 0.3)
        lim = r * r + r * 0.8
        inner = (r - 1) * (r - 1) + (r - 1) * 0.8
        for i, j in _disc_cells(r):
            d = i * i + j * j
            if d > inner and r >= 2:
                c, aa = rim, a
            elif j < -r * 0.35 and i < r * 0.3 and d < lim * 0.45:
                c, aa = light, a
            else:
                c, aa = (col if (i + j) & 1 else dark), a
            low.set_at((i + r, j + r), (*c, aa))
        s = pygame.transform.scale(low, (n * G, n * G))
        return self._put(key, s)

    def cream(self, r: int, seed: int) -> pygame.Surface:
        """Kaňka šlehačky: nepravidelný obrys z několika kruhů, stín dole, obrys a růžový posyp."""
        key = ("cr", r, seed)
        s = self.d.get(key)
        if s is not None:
            return s
        rng = random.Random(seed * 7919 + r)
        ry = max(2, int(r * 0.62))
        w, h = r * 2 + 5, ry * 2 + 5
        grid = [[False] * w for _ in range(h)]
        blobs = [(0.0, 0.0, 1.0)] + [(rng.uniform(-0.55, 0.55), rng.uniform(-0.45, 0.45), rng.uniform(0.35, 0.55))
                                      for _ in range(5)]
        for bx, by, br in blobs:
            cx, cy, rr = w / 2 + bx * r, h / 2 + by * ry, br
            for y in range(h):
                for x in range(w):
                    if ((x + 0.5 - cx) / (r * rr + 0.5)) ** 2 + ((y + 0.5 - cy) / (ry * rr + 0.5)) ** 2 <= 0.62:
                        grid[y][x] = True
        low = pygame.Surface((w, h), pygame.SRCALPHA)
        base, shade, hi, edge = (252, 244, 230), (226, 206, 194), (255, 255, 250), (176, 136, 128)
        for y in range(h):
            for x in range(w):
                if not grid[y][x]:
                    if any(0 <= y + dy < h and 0 <= x + dx < w and grid[y + dy][x + dx]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        low.set_at((x, y), (*edge, 255))
                    continue
                below = y + 1 >= h or not grid[y + 1][x]
                above = y - 1 < 0 or not grid[y - 1][x]
                c = shade if below else hi if above else base
                low.set_at((x, y), (*c, 255))
        sprinkles = [(255, 120, 160), (120, 200, 255), (255, 214, 70), (150, 230, 120)]
        for _ in range(max(2, r)):
            x, y = rng.randrange(w), rng.randrange(h)
            if grid[y][x] and (y + 1 < h and grid[y + 1][x]):
                low.set_at((x, y), (*rng.choice(sprinkles), 255))
        s = pygame.transform.scale(low, (w * G, h * G))
        return self._put(key, s)

    def stink_line(self, col, a: int) -> pygame.Surface:
        """Komiksová „smradlavá čárka“ – klikatá svislá linka (3×9 art px)."""
        key = ("sl", col, a)
        s = self.d.get(key)
        if s is not None:
            return s
        rows = ["#..", ".#.", "..#", ".#.", "#..", ".#.", "..#", ".#.", "#.."]
        low = pygame.Surface((3, len(rows)), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    low.set_at((x, y), (*col, a))
        s = pygame.transform.scale(low, (3 * G, len(rows) * G))
        return self._put(key, s)

    def scorch(self, r: int, a: int) -> pygame.Surface:
        key = ("x", r, a)
        s = self.d.get(key)
        if s is not None:
            return s
        rx, ry = r, max(1, int(r * 0.6))
        low = pygame.Surface((rx * 2 + 1, ry * 2 + 1), pygame.SRCALPHA)
        for j in range(-ry, ry + 1):
            for i in range(-rx, rx + 1):
                d = (i / (rx + 0.5)) ** 2 + (j / (ry + 0.5)) ** 2
                if d <= 1.0:
                    # tmavý střed, světlejší okraj s „roztřepeným“ ditheringem
                    if d > 0.7 and (i + j) & 1:
                        continue
                    k = 1.0 if d < 0.45 else 0.6
                    low.set_at((i + rx, j + ry), (30, 22, 20, int(a * k)))
        s = pygame.transform.scale(low, (low.get_width() * G, low.get_height() * G))
        return self._put(key, s)


_cache = _SpriteCache()

# ohnivá rampa: bílá → žlutá → oranžová → tmavě červená
FIRE_RAMP = [(255, 248, 210), (255, 220, 96), (255, 156, 46), (226, 92, 38), (92, 72, 74)]


class ParticleSystem:
    def __init__(self, cap: int = 700) -> None:
        self.cap = cap
        n = cap
        self.x = [0.0] * n
        self.y = [0.0] * n
        self.vx = [0.0] * n
        self.vy = [0.0] * n
        self.life = [0.0] * n
        self.maxl = [1.0] * n
        self.kind = [0] * n
        self.col = [(255, 255, 255)] * n
        self.size = [3] * n
        self.alive: list[int] = []
        self.free = list(range(n - 1, -1, -1))
        self.rng = random.Random(7)
        self.density = 1.0          # 1 = plné efekty; při davu nepřátel Run snižuje (čitelnost + výkon)
        self.decals: list[list] = []   # [x, y, r, life, maxlife, druh] – spáleniště / šlehačka pod entitami

    def clear(self) -> None:
        self.alive.clear()
        self.free = list(range(self.cap - 1, -1, -1))
        self.decals.clear()

    def emit(self, x: float, y: float, vx: float, vy: float, life: float, kind: int, col, size: int = 3) -> None:
        if not self.free:
            return
        i = self.free.pop()
        self.x[i] = x
        self.y[i] = y
        self.vx[i] = vx
        self.vy[i] = vy
        self.life[i] = life
        self.maxl[i] = life
        self.kind[i] = kind
        self.col[i] = col
        self.size[i] = size
        self.alive.append(i)

    def _n(self, n: int) -> int:
        """Počet částic podle hustoty (náhodné zaokrouhlení, aby i 1 částice občas prošla)."""
        v = n * self.density
        k = int(v)
        if self.rng.random() < v - k:
            k += 1
        return k

    # --- základní presety (původní API) --------------------------------------------------------
    def feathers(self, x: float, y: float, n: int, col=(250, 248, 240), speed: float = 120) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s - 40, r.uniform(0.5, 1.1), FEATHER, col, 3)

    def sparks(self, x: float, y: float, n: int, col=(255, 220, 120), speed: float = 220, life: float = 0.35) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.5, 1.0) * life, SPARK, col, 3)

    def puff(self, x: float, y: float, n: int, col=(230, 230, 230), speed: float = 50, size: int = 8) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.2, 1.0) * speed
            self.emit(x + r.uniform(-6, 6), y + r.uniform(-6, 6), math.cos(a) * s, math.sin(a) * s - 15,
                      r.uniform(0.35, 0.7), PUFF, col, size)

    def blobs(self, x: float, y: float, n: int, col=(130, 240, 80), speed: float = 140) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s - 60, r.uniform(0.3, 0.6), BLOB, col, 4)

    def stars(self, x: float, y: float, n: int, col=(255, 230, 90), speed: float = 160) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.4, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.4, 0.9), STAR, col, 3)

    # --- složené efekty --------------------------------------------------------------------------
    def glow(self, x: float, y: float, r: float, col=(255, 220, 140), life: float = 0.12) -> None:
        self.emit(x, y, 0.0, 0.0, life, GLOW, col, max(2, int(r / G)))

    def pop_ring(self, x: float, y: float, r: float, col=(255, 255, 255), life: float = 0.22) -> None:
        self.emit(x, y, 0.0, 0.0, life, POP, col, max(4, int(r)))

    def smoke(self, x: float, y: float, n: int, col=(70, 62, 66), spread: float = 10, size: int = 4,
              speed: float = 30, life: float = 1.0) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.2, 1.0) * speed
            self.emit(x + r.uniform(-spread, spread), y + r.uniform(-spread, spread) * 0.7,
                      math.cos(a) * s, math.sin(a) * s * 0.6 - 18, r.uniform(0.7, 1.2) * life, SMOKE, col,
                      max(1, int(size * r.uniform(0.7, 1.3))))

    def explosion(self, x: float, y: float, rad: float, col=(255, 200, 80), big: bool = False,
                  scorch: bool = True) -> None:
        """Vrstvený výbuch: záblesk, ohnivé koule, jiskry, kouř, úlomky, spáleniště.
        Kruh poškození (přesný poloměr) kreslí volající přes Run.add_ring."""
        r = self.rng
        rad = max(16.0, rad)
        k = rad / 60.0
        self.glow(x, y, rad * (0.6 if big else 0.5), _mix(col, (255, 200, 120), 0.4), 0.14 if big else 0.09)
        # kouř první (kreslí se pod ohněm)
        self.smoke(x, y, self._n(int((5 if not big else 10) * min(2.0, k))), (64, 56, 60),
                   rad * 0.35, int(3 + 2 * min(2.0, k)), 40, 1.1 if big else 0.85)
        nf = self._n(int((5 if not big else 12) * min(2.2, k)) + 2)
        for _ in range(nf):
            a = r.uniform(0, math.tau)
            d = r.uniform(0, rad * 0.35)
            s = r.uniform(20, 70) * min(2.0, k)
            self.emit(x + math.cos(a) * d, y + math.sin(a) * d * 0.8, math.cos(a) * s, math.sin(a) * s - 10,
                      r.uniform(0.26, 0.42) * (1.3 if big else 1.0), FIRE, col,
                      max(1, int(r.uniform(2, 4) * min(1.8, max(0.7, k)))))
        ns = self._n(10 if not big else 22)
        sp = 260 if not big else 420
        for _ in range(ns):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.35, 1.0) * sp
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s - 60, r.uniform(0.25, 0.55), SPARK,
                      _mix(col, (255, 240, 180), 0.3), 3)
        for _ in range(self._n(3 if not big else 7)):
            a = r.uniform(math.pi * 1.05, math.pi * 1.95)
            s = r.uniform(120, 260)
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.5, 0.8), DEBRIS, (92, 70, 58), 3)
        if scorch:
            self.scorch(x, y, rad * 0.45)

    def hit(self, x: float, y: float, dx: float, dy: float, col=(255, 250, 220)) -> None:
        """Drobný zásah: 2–3 jiskry odlétající ve směru úderu."""
        n = self._n(3)
        if n <= 0:
            return
        r = self.rng
        base = math.atan2(dy, dx) if (dx or dy) else r.uniform(0, math.tau)
        for _ in range(n):
            a = base + r.uniform(-0.7, 0.7)
            s = r.uniform(120, 240)
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.12, 0.22), SPARK, col, 3)

    def pop(self, x: float, y: float, fluff, n_feathers: int = 4) -> None:
        """Smrt běžného nepřítele: chuchvalec chlupů, peříčka a malý kruh. Málo částic – děje se často."""
        r = self.rng
        if self._n(1):
            self.emit(x, y, 0.0, 0.0, 0.16, POP, _mix(fluff, (255, 255, 255), 0.5), 14)
        for _ in range(self._n(2)):
            self.emit(x + r.uniform(-5, 5), y + r.uniform(-4, 4), r.uniform(-30, 30), r.uniform(-50, -10),
                      r.uniform(0.3, 0.45), PUFF, _mix(fluff, (235, 230, 225), 0.35), 4)
        self.feathers(x, y, max(1, self._n(n_feathers)), fluff, 110)

    def sparkle(self, x: float, y: float, col=(255, 240, 160), n: int = 3) -> None:
        r = self.rng
        for _ in range(self._n(n)):
            self.emit(x + r.uniform(-8, 8), y + r.uniform(-10, 4), r.uniform(-20, 20), r.uniform(-70, -30),
                      r.uniform(0.25, 0.45), STAR, col, 2)

    def dust(self, x: float, y: float, col=(150, 126, 96), n: int = 1) -> None:
        r = self.rng
        for _ in range(n):
            self.emit(x + r.uniform(-4, 4), y + r.uniform(-2, 2), r.uniform(-18, 18), r.uniform(-22, -8),
                      r.uniform(0.3, 0.45), PUFF, col, 3)

    def burst_ring(self, x: float, y: float, n: int, col, speed: float = 200) -> None:
        """Pravidelný věnec hvězdiček (level-up, odměny)."""
        for i in range(n):
            a = i * math.tau / n
            self.emit(x, y, math.cos(a) * speed, math.sin(a) * speed * 0.8 - 40, 0.55, STAR, col, 3)

    # --- ultimátky ------------------------------------------------------------------------------
    def hearts(self, x: float, y: float, n: int, speed: float = 90, broken: bool = False) -> None:
        r = self.rng
        col = (176, 150, 190) if broken else (255, 110, 180)
        for _ in range(n):
            a = r.uniform(math.pi * 1.15, math.pi * 1.85)
            s = r.uniform(0.4, 1.0) * speed
            self.emit(x + r.uniform(-6, 6), y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.6, 1.0),
                      HEART, col, -1 if broken else 1)

    def flakes(self, x: float, y: float, n: int, speed: float = 120, spread: float = 8.0) -> None:
        r = self.rng
        for _ in range(self._n(n)):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x + r.uniform(-spread, spread), y + r.uniform(-spread, spread) * 0.7,
                      math.cos(a) * s, math.sin(a) * s, r.uniform(0.6, 1.1), FLAKE,
                      r.choice(((235, 248, 255), (190, 230, 255), (255, 255, 255))), 2 if r.random() < 0.6 else 3)

    def notes(self, x: float, y: float, n: int, col=(255, 230, 120), speed: float = 110) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(math.pi * 1.1, math.pi * 1.9)
            s = r.uniform(0.5, 1.0) * speed
            self.emit(x + r.uniform(-14, 14), y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.7, 1.1), NOTE, col, 3)

    def drops(self, x: float, y: float, n: int, col=(150, 220, 255), speed: float = 160, up: float = 120) -> None:
        r = self.rng
        for _ in range(self._n(n)):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x + r.uniform(-6, 6), y, math.cos(a) * s, math.sin(a) * s * 0.7 - up, r.uniform(0.35, 0.6),
                      DROP, col, 3 if r.random() < 0.5 else 2)

    def shards(self, x: float, y: float, n: int, spread: float = 60.0) -> None:
        """Roztříštěný led: střepy rozlétající se do kruhu."""
        r = self.rng
        for i in range(self._n(n)):
            a = i * math.tau / max(1, n) + r.uniform(-0.2, 0.2)
            s = r.uniform(0.6, 1.0) * spread * 3.2
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s * 0.8 - 90, r.uniform(0.45, 0.7), SHARD,
                      r.choice(((210, 240, 255), (160, 215, 250))), 3)

    def scorch(self, x: float, y: float, r: float, life: float = 4.0, kind: int = 0) -> None:
        if len(self.decals) >= MAX_DECALS:
            self.decals.pop(0)
        self.decals.append([x, y, max(2, min(9 if kind == 0 else 14, int(r / G))), life, life, kind])

    def splat(self, x: float, y: float, rad: float) -> None:
        """Dopad dortu: šlehačkové cákance, posyp, bílý kruh a kaňka na zemi – žádný oheň ani kouř."""
        r = self.rng
        self.pop_ring(x, y, rad * 0.9, (255, 250, 240), 0.22)
        for _ in range(self._n(10)):
            a = r.uniform(0, math.tau)
            sp = r.uniform(80, 220) * min(1.6, rad / 70)
            self.emit(x, y - 6, math.cos(a) * sp, math.sin(a) * sp * 0.7 - 120, r.uniform(0.35, 0.6), BLOB,
                      r.choice(((252, 244, 230), (255, 255, 250), (250, 200, 210))), 4)
        for _ in range(self._n(8)):
            a = r.uniform(0, math.tau)
            sp = r.uniform(60, 200)
            self.emit(x, y - 6, math.cos(a) * sp, math.sin(a) * sp - 140, r.uniform(0.4, 0.7), DEBRIS,
                      r.choice(((255, 120, 160), (120, 200, 255), (255, 214, 70), (150, 230, 120))), 3)
        self.scorch(x, y, min(rad * 0.3, 18), 2.5, 1)

    # --- update/draw --------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        X, Y, VX, VY, L, K = self.x, self.y, self.vx, self.vy, self.life, self.kind
        alive = self.alive
        keep = []
        free = self.free
        drag_f = 1.0 - min(0.9, 4.0 * dt)
        drag_s = 1.0 - min(0.9, 6.0 * dt)
        drag_h = 1.0 - min(0.9, 3.0 * dt)
        sin = math.sin
        for i in alive:
            l = L[i] - dt
            if l <= 0:
                free.append(i)
                continue
            L[i] = l
            k = K[i]
            if k == FEATHER or k == FLAKE:
                VX[i] *= drag_f
                VY[i] = VY[i] * drag_f + 60 * dt
                X[i] += (VX[i] + sin(l * 9.0) * 25) * dt
            elif k == BLOB or k == DEBRIS or k == DROP or k == SHARD:
                VY[i] += 520 * dt
                X[i] += VX[i] * dt
            elif k == SPARK:
                VX[i] *= drag_s
                VY[i] = VY[i] * drag_s + 220 * dt
                X[i] += VX[i] * dt
            elif k == SMOKE:
                VX[i] *= drag_h
                VY[i] = VY[i] * drag_h - 14 * dt
                X[i] += VX[i] * dt
            elif k == GLOW or k == POP:
                keep.append(i)          # stojí na místě, ale žijí do konce life (jinak slot vypadl z poolu, B-67)
                continue
            else:
                VX[i] *= drag_s
                VY[i] *= drag_s
                X[i] += VX[i] * dt
            Y[i] += VY[i] * dt
            keep.append(i)
        self.alive = keep
        if self.decals:
            for d in self.decals:
                d[3] -= dt
            if self.decals[0][3] <= 0:
                self.decals = [d for d in self.decals if d[3] > 0]

    def draw_decals(self, surf: pygame.Surface, ox: float, oy: float) -> None:
        """Spáleniště – kreslit pod entity."""
        if not self.decals:
            return
        w, h = surf.get_size()
        seq = []
        for x, y, r, life, maxl, kind in self.decals:
            k = min(1.0, life / (maxl * 0.5))
            if kind == 1:
                if k < 1.0 and int(life * 12) & 1:      # šlehačka mizí „poblikáváním“ (pixel styl, bez alfy)
                    continue
                s = _cache.cream(r, int(x + y) & 3)
            else:
                s = _cache.scorch(r, int(110 * k) // 10 * 10)
            sx = x - ox - s.get_width() / 2
            sy = y - oy - s.get_height() / 2
            if -60 < sx < w + 10 and -40 < sy < h + 10:
                seq.append((s, (sx, sy)))
        if seq:
            if _HAS_FBLITS:
                surf.fblits(seq)
            else:
                surf.blits(seq, False)

    def draw(self, surf: pygame.Surface, ox: float, oy: float) -> None:
        X, Y, L, M, K, C, S = self.x, self.y, self.life, self.maxl, self.kind, self.col, self.size
        VX, VY = self.vx, self.vy
        w, h = surf.get_size()
        cache = _cache
        seq = []
        add = []
        ap = seq.append
        steps = _ALPHA_STEPS
        for i in self.alive:
            x = int(X[i] - ox)
            y = int(Y[i] - oy)
            if x < -40 or y < -40 or x > w + 40 or y > h + 40:
                continue
            k = K[i]
            t = L[i] / M[i]                 # 1 → 0 během života
            if k == FEATHER:
                img = cache.feather(C[i], int(L[i] * 10) & 1)
                ap((img, (x - 3, y - 2)))
            elif k == SPARK:
                vx, vy = VX[i], VY[i]
                ddx = 1 if vx > 40 else -1 if vx < -40 else 0
                ddy = 1 if vy > 40 else -1 if vy < -40 else 0
                sz = 3 if t > 0.45 and S[i] >= 3 else 2
                img = cache.spark(C[i], sz, ddx, ddy)
                ap((img, (x - img.get_width() // 2, y - img.get_height() // 2)))
            elif k == PUFF:
                r = max(1, int((S[i] / 6.0) * (0.8 + (1 - t) * 0.8) + 0.5))
                a = 255 if t > 0.5 else int(255 * (t / 0.5) ** 0.8)
                img = cache.disc(r, C[i], max(40, a * steps // 255 * 255 // steps))
                hw = img.get_width() // 2
                ap((img, (x - hw, y - hw)))
            elif k == SMOKE:
                r = max(1, int(S[i] * (0.6 + (1 - t) * 0.9) + 0.5))
                a = int(190 * min(1.0, t * 1.6))
                if a < 24:
                    continue
                img = cache.disc(r, C[i], a * steps // 255 * 255 // steps)
                hw = img.get_width() // 2
                ap((img, (x - hw, y - hw)))
            elif k == FIRE:
                u = 1 - t
                idx = min(len(FIRE_RAMP) - 1, int(u ** 0.7 * len(FIRE_RAMP)))
                col = FIRE_RAMP[idx]
                if 1 <= idx <= 2:
                    col = _mix(col, C[i], 0.3)
                grow = min(1.0, u * 5)
                r = max(1, int(S[i] * (0.6 + 0.4 * grow) * (0.55 + 0.45 * t) + 0.5))
                img = cache.disc(r, col, 255 if idx < 4 else 170)
                hw = img.get_width() // 2
                ap((img, (x - hw, y - hw)))
            elif k == BLOB:
                img = cache.chunk(C[i], 4, 4)
                ap((img, (x - 3, y - 3)))
            elif k == DEBRIS:
                img = cache.chunk(C[i], 3 + (i & 1) * 3, 3)
                ap((img, (x - 3, y - 2)))
            elif k == STAR:
                img = cache.star(C[i], t > 0.5 and S[i] >= 3)
                hw = img.get_width() // 2
                ap((img, (x - hw, y - hw)))
            elif k == GLOW:
                img = cache.glow(S[i], C[i], t)
                hw = img.get_width() // 2
                add.append((img, (x - hw, y - hw)))
            elif k >= HEART:
                sz = S[i]
                if k == HEART and sz < 0:
                    img = cache.shape(-HEART, C[i], 2)
                else:
                    img = cache.shape(k, C[i], abs(sz) if k != HEART else 2 + (t > 0.5))
                hw = img.get_width() // 2
                ap((img, (x - hw, y - img.get_height() // 2)))
            elif k == POP:
                rr = int(S[i] * (1.15 - t * 0.75)) // 2 * 2
                if rr >= 2:
                    img = cache.ring(rr, C[i], 3 if t > 0.4 else 2)
                    ap((img, (x - rr - 1, y - rr - 1)))
            else:
                img = cache.chunk(C[i], 3, 3)
                ap((img, (x - 2, y - 2)))
        if seq:
            if _HAS_FBLITS:
                surf.fblits(seq)
            else:
                surf.blits(seq, False)
        _blit_add(surf, add)

    def __len__(self) -> int:
        return len(self.alive)


# --- veřejné pomocníky pro renderer (záře pod projektily, ambientní částice) -------------------------
def glow_sprite(r: int, col, k: float = 1.0) -> pygame.Surface:
    """Aditivní pixelová záře (r v art px); kreslit přes blit_add."""
    return _cache.glow(r, col, k)


def disc_sprite(r: int, col, a: int = 255, shade: bool = True) -> pygame.Surface:
    return _cache.disc(r, col, a, shade)


def gas_sprite(r: int, col, a: int) -> pygame.Surface:
    return _cache.gas(r, col, a)


def stink_line_sprite(col, a: int) -> pygame.Surface:
    return _cache.stink_line(col, a)


def cream_sprite(r: int, seed: int) -> pygame.Surface:
    return _cache.cream(r, seed)


def blit_add(surf, seq) -> None:
    _blit_add(surf, seq)


def shape_sprite(kind: int, col, g: int = 3) -> pygame.Surface:
    """Malý pixelový tvar částice (srdíčko, vločka, nota, kapka, střep) – pro renderer ultimátek."""
    return _cache.shape(kind, col, g)
