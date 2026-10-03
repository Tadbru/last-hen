"""RunRenderer – vykreslení světa runu: terén, zóny, telegrafy, y-sorted entity, efekty, osvětlení."""
from __future__ import annotations

import math
import time

import pygame

from .. import assets
from ..config import H, PX, W
from ..device import fblits
from ..gfx import pixelart as pa
from ..gfx.particles import blit_add, cream_sprite, disc_sprite, glow_sprite, stink_line_sprite
from ..gfx.sprites import angle_index
from ..gfx.tiles import TILE
from ..ui.widgets import notched_rect
from ..util import clamp, lerp_color, mul_color
from .entities import M_BOOMERANG, M_LOB, M_SPIRAL, M_WAVE, P_CHEST, P_COIN, P_GOLDEGG, P_MAGNET, P_WORM, P_XP

FAST_MULT = hasattr(pygame.Surface, "fblits")     # pygame-ce má SIMD blend; klasický pygame ne

# prach pod nohama podle biomu
DUST_COL = {"farm": (138, 116, 84), "forest": (92, 78, 60), "city": (150, 150, 158), "mountain": (240, 244, 252),
            "factory": (120, 118, 126)}
# záře nepřátelských projektilů (čitelnost v davu): sliz, peří kohouta, mrkev
EPROJ_GLOW = {0: (110, 255, 60), 1: (255, 240, 220), 2: (255, 140, 40)}
PICKUP_GLOW = {P_GOLDEGG: (255, 200, 60), P_CHEST: (255, 210, 110), P_MAGNET: (255, 90, 90), P_WORM: (120, 240, 120)}

# kotvy klobouků skinů (art px relativně k levému hornímu rohu spritu bez obrysu): (střed x, horní y)
HAT_ANCHOR = {"hen": (10.5, 1.5), "duck": (9.0, 2.0), "goose": (11.0, 0.5), "turkey": (11.5, 1.5),
              "rooster": (11.0, 0.5), "peacock": (13.0, 2.5), "penguin": (6.0, 0.5)}


class RunRenderer:
    def __init__(self, run) -> None:
        self.run = run
        self._circ: dict = {}
        self._overlay: dict = {}
        self._slide_rot: dict = {}
        self._ghosts: dict = {}
        self.fog = None
        self.vignette_red = None
        self.t = 0.0
        b = run.biome
        if b.fog:
            self.fog = self._make_fog()
        self.vignette_red = self._make_vignette((200, 20, 30))
        self.shadow_small = pa.make_shadow(30, 10, 70)
        self._light_ov = pygame.Surface((W, H))
        self.hat = None
        skin = run.cfg.skin
        if skin and skin in assets.sprites.hats:
            self.hat = assets.sprites.hats[skin]
        self.season_tint = None
        if run.cfg.season:
            from ..data.meta import SEASONS
            self.season_tint = SEASONS[run.cfg.season]["tint"]
        self.edges = self._make_edges()
        self.hp_ghost = 1.0
        self._dust_t = 0.0
        self._amb = _Ambient(run.biome.id)

    # --- pomocné povrchy -----------------------------------------------------------------------
    def _make_fog(self) -> pygame.Surface:
        s = pygame.Surface((W * 2, H * 2), pygame.SRCALPHA)
        s.fill((10, 16, 22, 210))
        cx, cy = W, H
        for i in range(30, 0, -1):
            r = int(160 + i * 12)
            a = int(210 * (i / 30) ** 1.6)
            pygame.draw.circle(s, (10, 16, 22, a), (cx, cy), r)
        pygame.draw.circle(s, (0, 0, 0, 0), (cx, cy), 150)
        return s

    def _make_edges(self) -> list:
        """Jemná trvalá vinětace jen v okrajových pruzích (levnější než celoplošná vrstva – Android).
        Pixelové pásy po 3 px, ať sedí k pixel artu."""
        col = (14, 8, 20)
        out = []
        th, sw = 72, 54
        top = pygame.Surface((W, th), pygame.SRCALPHA)
        for y in range(0, th, 3):
            a = int(110 * (1 - y / th) ** 2)
            top.fill((*col, a), (0, y, W, 3))
        out.append((top, (0, 0)))
        out.append((pygame.transform.flip(top, False, True), (0, H - th)))
        side = pygame.Surface((sw, H), pygame.SRCALPHA)
        for x in range(0, sw, 3):
            a = int(80 * (1 - x / sw) ** 2)
            side.fill((*col, a), (x, 0, 3, H))
        out.append((side, (0, 0)))
        out.append((pygame.transform.flip(side, True, False), (W - sw, 0)))
        return out

    def _make_vignette(self, col) -> pygame.Surface:
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(24):
            a = int(120 * (1 - i / 24) ** 2)
            pygame.draw.rect(s, (*col, a), (i * 6, i * 8, W - i * 12, H - i * 16), 8)
        return s

    def circle(self, r: int, color, alpha: int, width: int = 0) -> pygame.Surface:
        r = max(2, int(r) // 2 * 2)
        key = (r, color, alpha, width)
        s = self._circ.get(key)
        if s is None:
            if len(self._circ) > 400:
                self._circ.clear()
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color[:3], alpha), (r + 1, r + 1), r, width)
            self._circ[key] = s
        return s

    def ellipse(self, w: int, h: int, color, alpha: int, width: int = 0) -> pygame.Surface:
        w = max(4, int(w) // 2 * 2)
        h = max(2, int(h) // 2 * 2)
        key = ("e", w, h, color, alpha, width)
        s = self._circ.get(key)
        if s is None:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*color[:3], alpha), s.get_rect(), width)
            self._circ[key] = s
        return s

    def overlay(self, anim, face: int, f: int, kind: str) -> pygame.Surface:
        key = (id(anim), face, f, kind)
        s = self._overlay.get(key)
        if s is None:
            base = anim.frames[face][f]
            if kind == "ice":
                s = pa.silhouette(base, (150, 220, 255), 150)
            else:
                s = pa.silhouette(base, (200, 120, 255), 110)
            self._overlay[key] = s
        return s

    # --- hlavní kreslení --------------------------------------------------------------------------
    def draw(self, surf: pygame.Surface, dt: float | None = None) -> None:
        run = self.run
        # animace podle skutečného času, ne podle počtu vykreslení
        now = time.perf_counter()
        last = getattr(self, "_last_draw", None)
        self._last_draw = now
        self.t += min(0.1, now - last) if last is not None else 0.0
        cam = run.camera
        ox, oy = cam.ox, cam.oy
        dt_real = self.t - getattr(self, "_t_prev", self.t)
        self._t_prev = self.t
        self._dt = dt_real
        self._ground(surf, ox, oy)
        self._zones(surf, ox, oy)
        run.particles.draw_decals(surf, ox, oy)
        if run.arena is not None:
            self._arena(surf, ox, oy, back=True)
        self._telegraphs(surf, ox, oy, ground=True)
        self._areas(surf, ox, oy)
        self._pickups(surf, ox, oy)
        self._entities(surf, ox, oy)
        self._projs(surf, ox, oy)
        self._eprojs(surf, ox, oy)
        self._waves_rings(surf, ox, oy)
        self._beams(surf, ox, oy)
        self._bombs(surf, ox, oy)
        self._gas(surf, ox, oy)
        self._telegraphs(surf, ox, oy, ground=False)
        run.particles.draw(surf, ox, oy)
        self._canopies(surf, ox, oy)
        if run.arena is not None:
            self._arena(surf, ox, oy, back=False)
        self._footsteps(dt_real)
        self._amb.update(dt_real, run)
        self._amb.draw(surf, ox, oy, run, lit=False)
        self._lighting(surf)
        self._amb.draw(surf, ox, oy, run, lit=True)
        for img, pos in self.edges:
            surf.blit(img, pos)
        self._texts(surf, ox, oy)
        self._speech(surf, ox, oy)
        if run.flash_t > 0:
            a = int(clamp(run.flash_t / 0.15, 0, 1) * 110)
            fl = pygame.Surface((W, H))
            fl.fill(run.flash_col)
            fl.set_alpha(a)
            surf.blit(fl, (0, 0))
        p = run.player
        if p.hp < p.stats.max_hp * 0.3 and not p.dead:
            v = self.vignette_red
            v.set_alpha(int(150 + 100 * math.sin(self.t * 6)))
            surf.blit(v, (0, 0))

    def _ground(self, surf, ox, oy) -> None:
        tiles = self.run.map.tiles
        if not tiles:
            surf.fill(self.run.biome.ground)
            return
        tx0 = math.floor(ox / TILE)
        ty0 = math.floor(oy / TILE)
        blits = []
        n = len(tiles)
        for tx in range(tx0, tx0 + W // TILE + 2):
            for ty in range(ty0, ty0 + H // TILE + 2):
                v = ((tx * 7919) ^ (ty * 104729)) % 11
                idx = 0 if v < 6 else 1 if v < 9 or n < 3 else 2
                blits.append((tiles[idx], (tx * TILE - ox, ty * TILE - oy)))
        fblits(surf, blits)

    def _zones(self, surf, ox, oy) -> None:
        run = self.run
        m = run.map
        blits = []
        conv_f = int(m.conv_anim * 10) % 4
        decor = assets.sprites.decor
        for ch in m.visible_chunks(ox, oy, W, H):
            for z in ch.zones:
                if z.frames:
                    blits.append((z.frames[conv_f], (z.x - ox, z.y - oy)))
                elif z.surf is not None:
                    blits.append((z.surf, (z.x - ox, z.y - oy)))
            for name, x, y in ch.decals:
                s = decor.get(name)
                if s is not None:
                    blits.append((s, (x - ox - s.get_width() / 2, y - oy - s.get_height())))
        if blits:
            fblits(surf, blits)

    def _arena(self, surf, ox, oy, back: bool) -> None:
        ax, ay, ar = self.run.arena
        cx, cy = ax - ox, ay - oy
        flick = (int(self.t * 20) % 3) != 0
        if back:
            col = (90, 200, 255) if flick else (200, 240, 255)
            pygame.draw.circle(surf, (40, 60, 90), (cx, cy + 4), ar, 6)
            pygame.draw.circle(surf, col, (cx, cy), ar, 3)
            return
        for i in range(36):
            a = i * math.tau / 36
            x = cx + math.cos(a) * ar
            y = cy + math.sin(a) * ar
            if -20 < x < W + 20 and -40 < y < H + 20:
                pygame.draw.rect(surf, (60, 50, 60), (x - 3, y - 22, 6, 24))
                pygame.draw.rect(surf, (160, 150, 160), (x - 3, y - 22, 6, 3))
                if flick and i % 3 == int(self.t * 12) % 3:
                    pygame.draw.circle(surf, (180, 240, 255), (int(x), int(y - 22)), 3)

    def _telegraphs(self, surf, ox, oy, ground: bool) -> None:
        for t in self.run.telegraphs:
            k = t.t / t.dur
            x, y = t.x - ox, t.y - oy
            if ground:
                pulse = 0.5 + 0.5 * math.sin(self.t * 18)
                if t.kind == "cake":
                    self._cake_tel(surf, t, x, y, k)
                elif t.kind in ("circle", "stamper", "drop"):
                    r = t.r
                    a = int(60 + 60 * k)
                    s = self.circle(r, t.color, a)
                    surf.blit(s, (x - r - 1, y - r - 1))
                    rr = max(2, int(r * k))
                    pygame.draw.circle(surf, t.color, (int(x), int(y)), int(r), 2 if pulse > 0.5 else 1)
                    if t.kind != "drop":
                        s2 = self.circle(rr, t.color, 110)
                        surf.blit(s2, (x - rr - 1, y - rr - 1))
                elif t.kind == "line":
                    self._line_tel(surf, t, ox, oy, k)
                elif t.kind == "band":
                    a = int(70 + 70 * (0.5 + 0.5 * math.sin(self.t * 16)))
                    band = pygame.Surface((W, int(t.r)), pygame.SRCALPHA)
                    band.fill((*t.color, a))
                    surf.blit(band, (0, y - t.r / 2))
            else:
                if t.kind == "cake":
                    spr = assets.sprites.small["cake"]
                    big = 2 if t.r > 100 else 1
                    if big > 1:
                        spr = pygame.transform.scale(spr, (spr.get_width() * 2, spr.get_height() * 2))
                    h = (1 - k) ** 1.5 * 520
                    surf.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() - h))
                elif t.kind == "drop":
                    from ..data.enemies import ENEMIES
                    d = ENEMIES.get(t.data or "zchick", ENEMIES["zchick"])
                    spr = assets.sprites.enemies[d.sprite].frames[0][0]
                    h = (1 - k) * 420
                    surf.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() - h))
                elif t.kind == "stamper":
                    h = (1 - k) * 60 + 20
                    pygame.draw.rect(surf, (90, 90, 100), (x - t.r * 0.8, y - h - 70, t.r * 1.6, 60))
                    pygame.draw.rect(surf, (60, 60, 70), (x - t.r * 0.8, y - h - 70, t.r * 1.6, 60), 3)
                    pygame.draw.rect(surf, (230, 190, 40), (x - t.r * 0.8, y - h - 18, t.r * 1.6, 8))

    def _cake_tel(self, surf, t, x, y, k) -> None:
        """Vlastní zbraň hráče – nenápadně: rostoucí stín padajícího dortu a tečkovaný kroužek dopadu."""
        r = t.r
        sw = r * (0.3 + 0.45 * k)
        sh = self.ellipse(sw * 2, sw, (20, 10, 24), int(30 + 60 * k) // 10 * 10)
        surf.blit(sh, (x - sh.get_width() / 2, y - sh.get_height() / 2))
        n = 16
        col = t.color
        rot = self.t * 0.9
        for i in range(n):
            a = rot + i * math.tau / n
            surf.fill(col, (int(x + math.cos(a) * r) // 3 * 3 - 3, int(y + math.sin(a) * r * 0.8) // 3 * 3 - 1, 6, 3))

    def _line_tel(self, surf, t, ox, oy, k) -> None:
        x1, y1, x2, y2 = t.x - ox, t.y - oy, t.x2 - ox, t.y2 - oy
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln * t.w / 2, dx / ln * t.w / 2
        pts = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
        minx = min(p[0] for p in pts)
        miny = min(p[1] for p in pts)
        maxx = max(p[0] for p in pts)
        maxy = max(p[1] for p in pts)
        w, h = int(maxx - minx) + 2, int(maxy - miny) + 2
        if w <= 0 or h <= 0 or w > 2000 or h > 2000:
            return
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(s, (*t.color, int(50 + 90 * k)), [(px - minx, py - miny) for px, py in pts])
        surf.blit(s, (minx, miny))
        pygame.draw.line(surf, t.color, (x1, y1), (x1 + dx * k, y1 + dy * k), 2)

    def _areas(self, surf, ox, oy) -> None:
        for a in self.run.areas:
            x, y = a.x - ox, a.y - oy
            r = a.r
            if x < -r or x > W + r or y < -r or y > H + r:
                continue
            fade = min(1.0, a.life / 0.4)
            if a.kind == "cloud":
                self._gas_cloud(surf, a, x, y, r, fade)
            elif a.kind == "cream":
                if a.life < 0.6 and int(a.life * 12) & 1:
                    continue                        # mizí „poblikáváním“ (pixel styl)
                self._cream(surf, a, x, y, r)

    def _gas(self, surf, ox, oy) -> None:
        """Plyn (mrak smradu, toxická aura) je ve vzduchu – kreslí se nad entitami."""
        for a in self.run.areas:
            if a.kind != "cloud" and a.kind != "aura":
                continue
            x, y = a.x - ox, a.y - oy
            r = a.r
            if x < -r or x > W + r or y < -r - 40 or y > H + r:
                continue
            if a.kind == "cloud":
                self._gas_air(surf, a, x, y, r, min(1.0, a.life / 0.4))
            else:
                self._gas_aura(surf, a, x, y, r)

    def _gas_puffs(self, surf, x, y, rx, ry, n, rmax, cols, al, seed, ring: bool = False) -> None:
        """Vzdouvající se plyn: chuchvalce se rodí na náhodném místě, nafouknou se, stoupají a zmizí
        (stejný princip jako kouř výbuchů). Deterministické z času – žádný stav ani alokace."""
        t = self.t
        out = []
        for i in range(n):
            h0 = (seed * 2654435761 + i * 40503) & 0xFFFFFFFF
            period = 1.3 + (h0 & 255) / 255 * 1.1
            u = t / period + ((h0 >> 8) & 255) / 255
            cyc = int(u)
            k = u - cyc
            h = (h0 ^ (cyc * 2246822519)) * 3266489917 & 0xFFFFFFFF
            ang = (h & 0xFFFF) / 65536 * math.tau
            d = 0.86 + ((h >> 16) & 0xFF) / 255 * 0.18 if ring else math.sqrt(((h >> 16) & 0xFF) / 255) * 0.8
            px = x + math.cos(ang) * d * rx
            py = y + math.sin(ang) * d * ry - k * 10
            life = math.sin(math.pi * k)
            a = int(al * min(1.0, life * 2.0)) // 30 * 30
            if a < 30:
                continue
            rc = max(1, int(rmax * (0.5 + 0.5 * life) * (0.7 + ((h >> 24) & 3) * 0.12) / 3))
            out.append((py, disc_sprite(rc, cols[(h >> 26) % len(cols)], a), px))
        out.sort(key=lambda o: o[0])
        fblits(surf, [(img, (int(px) // 3 * 3 - img.get_width() // 2, int(py) // 3 * 3 - img.get_height() // 2))
                      for py, img, px in out])

    def _gas_cloud(self, surf, a, x, y, r, fade) -> None:
        """Mrak smradu: oblak z mnoha menších vzdouvajících se chuchvalců (pod entitami)."""
        fade *= min(1.0, (a.maxlife - a.life) / 0.25)
        al = int(170 * fade)
        if al < 30:
            return
        col = a.color
        cols = (col, mul_color(col, 0.84), mul_color(col, 0.7), lerp_color(col, (230, 255, 150), 0.3))
        seed = (int(a.x * 0.37) ^ int(a.y * 0.11)) & 0xFFFF
        self._gas_puffs(surf, x, y, r * 0.95, r * 0.7, max(10, int(r / 6)), r * 0.42, cols, al, seed)

    def _gas_air(self, surf, a, x, y, r, fade) -> None:
        """Nad entitami: bubliny a komiksové smradlavé čárky (lišky v mraku zůstávají vidět)."""
        fade *= min(1.0, (a.maxlife - a.life) / 0.25)
        if fade < 0.2:
            return
        col = a.color
        seed = (int(a.x * 0.37) ^ int(a.y * 0.11)) % 97
        light = mul_color(col, 1.25)
        for i in range(4):
            ph = (self.t * 0.55 + i / 4 + seed * 0.13) % 1.0
            if ph > 0.85:
                continue
            bx = x + math.sin(seed + i * 2.3) * r * 0.5
            by = y + r * 0.3 - ph * r * 0.9
            sz = 3 if i & 1 else 6
            surf.fill(light, (int(bx) // 3 * 3, int(by) // 3 * 3, sz, sz))
        # stoupající smradlavé čárky (čitelné na první pohled: tady to smrdí)
        for i in range(3):
            ph = (self.t * 0.7 + i / 3 + seed * 0.07) % 1.0
            la = int(230 * min(1.0, (1 - ph) * 2.5) * fade) // 46 * 46
            if la <= 0:
                continue
            lx = int(x + (i - 1) * r * 0.42 + math.sin(self.t * 2 + i) * 4) // 3 * 3 - 4
            ly = int(y - r * 0.35 - ph * r * 0.8) // 3 * 3 - 13
            surf.blit(stink_line_sprite((40, 60, 20), la), (lx + 3, ly + 3))
            surf.blit(stink_line_sprite((214, 250, 120), la), (lx, ly))

    def _cream(self, surf, a, x, y, r) -> None:
        """Šlehačka: rozprsklé kopečky šlehačky s posypem po ploše zásahu (žádná jedna velká kaňka)."""
        seed = (int(a.x * 0.53) ^ int(a.y * 0.29)) & 0xFFFF
        n = max(5, int(r / 11))
        seq = []
        for i in range(n):
            h = (seed * 2654435761 + i * 40503) & 0xFFFFFFFF
            ang = (h & 0xFFFF) / 65536 * math.tau
            d = math.sqrt(((h >> 16) & 0xFF) / 255) * r * 0.85
            cs = cream_sprite(3 + (h >> 24) % 3, (h >> 8) & 3)
            seq.append((cs, (int(x + math.cos(ang) * d - cs.get_width() / 2) // 3 * 3,
                             int(y + math.sin(ang) * d * 0.7 - cs.get_height() / 2) // 3 * 3)))
        fblits(surf, seq)

    def _gas_aura(self, surf, a, x, y, r) -> None:
        """Aura Biologické zbraně: prstenec vzdouvajícího se toxického plynu kolem slepice."""
        col = a.color
        cols = (mul_color(col, 0.7), mul_color(col, 0.58), mul_color(col, 0.82))
        self._gas_puffs(surf, x, y, r, r * 0.8, max(18, int(r / 6)), 22, cols, 160, 7, ring=True)

    def _pickups(self, surf, ox, oy) -> None:
        sm = assets.sprites.small
        xp1, xp2, xp3 = sm["xp1"], sm["xp2"], sm["xp3"]
        blits = []
        glows = []
        t = self.t
        for pk in self.run.pickups:
            x, y = pk.x - ox, pk.y - oy
            if x < -20 or x > W + 20 or y < -30 or y > H + 20:
                continue
            k = pk.kind
            gc = PICKUP_GLOW.get(k)
            if gc is not None:
                g = glow_sprite(5, gc, 0.55 + 0.25 * math.sin(t * 4 + pk.x * 0.05))
                glows.append((g, (x - g.get_width() / 2, y - 12 - pk.z - g.get_height() / 2)))
            if k == P_XP:
                v = pk.value
                img = xp1 if v < 3 else xp2 if v < 15 else xp3
            elif k == P_GOLDEGG:
                img = sm["egg_gold"]
            elif k == P_WORM:
                img = sm["worm"]
            elif k == P_MAGNET:
                img = sm["magnet"]
            elif k == P_COIN:
                img = sm["coin"]
            else:
                img = sm["chest"]
                blits.append((self.shadow_small, (x - 15, y - 3)))
            bob = math.sin(t * 5 + pk.x * 0.1) * 2 if k != P_XP else 0
            blits.append((img, (x - img.get_width() / 2, y - img.get_height() - pk.z + bob)))
        blit_add(surf, glows)
        if blits:
            fblits(surf, blits)

    def _entities(self, surf, ox, oy) -> None:
        run = self.run
        items = []
        add = items.append
        lo_x, hi_x = ox - 120, ox + W + 120
        lo_y, hi_y = oy - 60, oy + H + 160
        shadows = []
        for e in run.enemies:
            ex, ey = e.x, e.y
            if ex < lo_x or ex > hi_x or ey < lo_y or ey > hi_y:
                continue
            a = e.spr
            frames = a.frames[e.face]
            f = int(e.anim) % len(frames)
            img = a.flash[e.face][f] if e.flash > 0 else frames[f]
            if e.alpha < 255:
                if e.alpha <= 0:
                    continue
                img = img.copy()
                img.set_alpha(e.alpha)
            w, h = a.w, a.h
            sx = ex - ox - w * 0.5
            sy = ey - oy - h + e.r * 0.6 - e.bob
            shadows.append((a.shadow, (ex - ox - a.shadow.get_width() * 0.5, ey - oy + e.r * 0.6 - a.shadow.get_height() * 0.6)))
            add((ey, 0, img, sx, sy, e))
        for e in run.props:
            if lo_x < e.x < hi_x and lo_y < e.y < hi_y:
                a = e.spr
                img = a.flash[0][0] if e.flash > 0 else a.frames[0][0]
                add((e.y, 1, img, e.x - ox - a.w / 2, e.y - oy - a.h + 8, None))
        for al in run.allies:
            if not al.alive:
                continue
            if lo_x < al.x < hi_x and lo_y < al.y < hi_y:
                if al.kind == "fox":
                    a = al.anim_spr
                    fr = a.frames[al.face]
                    img = fr[int(al.anim) % len(fr)]
                    shadows.append((a.shadow, (al.x - ox - a.shadow.get_width() / 2, al.y - oy + 4)))
                    add((al.y, 2, img, al.x - ox - a.w / 2, al.y - oy - a.h + 8, None))
                else:
                    img = al.spr
                    if al.kind == "chick" and al.face == 1:
                        img = pygame.transform.flip(img, True, False)
                    bob = -abs(math.sin(al.anim)) * 3 if al.kind == "chick" else 0
                    if al.kind == "nest" and getattr(al, "pulse", 0) > 0:
                        bob = -al.pulse * 3
                    shadows.append((self.shadow_small, (al.x - ox - 15, al.y - oy - 2)))
                    add((al.y, 2, img, al.x - ox - img.get_width() / 2, al.y - oy - img.get_height() + 4 + bob, None))
        for ch in run.map.visible_chunks(ox, oy, W, H):
            for ob in ch.obstacles:
                if ob.spr is None:
                    continue
                if lo_x - 100 < ob.x < hi_x + 100 and lo_y < ob.y < hi_y + 120:
                    s = ob.spr
                    add((ob.y, 3, s, ob.x - ox - s.get_width() / 2, ob.y - oy - s.get_height() + 3, None))
        p = run.player
        if shadows:
            fblits(surf, shadows)
        items.sort(key=_sort_key)
        blits = []
        extra = []
        hide_player = p.dead and run.state == "dead"
        for it in items:
            blits.append((it[2], (it[3], it[4])))
            e = it[5]
            if e is not None:
                if e.freeze_t > 0 or e.hyp_t > 0 or e.elite:
                    extra.append(it)
        if blits:
            fblits(surf, blits)
        for it in extra:
            self._enemy_extra(surf, it, ox, oy)
        if hide_player:
            return
        # hráč VŽDY nad nepřáteli (B-32) …
        self._player(surf, ox, oy)
        # … a překážky stojící před ním (níž na obrazovce) se přes něj dokreslí poloprůhledně
        pr = pygame.Rect(0, 0, 40, 48)
        pr.midbottom = (p.x - ox, p.y - oy + 9)
        for it in items:
            if it[1] == 3 and it[0] > p.y:
                img = it[2]
                if pr.colliderect(pygame.Rect(it[3], it[4], img.get_width(), img.get_height())):
                    surf.blit(self._ghost(img), (it[3], it[4]))

    def _ghost(self, img: pygame.Surface) -> pygame.Surface:
        g = self._ghosts.get(id(img))
        if g is None:
            g = img.copy()
            g.set_alpha(120)
            if len(self._ghosts) > 200:
                self._ghosts.clear()
            self._ghosts[id(img)] = g
        return g

    def _enemy_extra(self, surf, it, ox, oy) -> None:
        e = it[5]
        a = e.spr
        frames = a.frames[e.face]
        f = int(e.anim) % len(frames)
        if e.freeze_t > 0:
            surf.blit(self.overlay(a, e.face, f, "ice"), (it[3], it[4]))
        elif e.hyp_t > 0:
            surf.blit(self.overlay(a, e.face, f, "hyp"), (it[3], it[4]))
            for i in range(3):
                ang = self.t * 5 + i * 2.1
                pygame.draw.circle(surf, (230, 140, 255), (int(e.x - ox + math.cos(ang) * 10),
                                                           int(it[4] - 6 + math.sin(ang) * 4)), 2)
        if e.elite and not e.boss:
            hpw = 40
            x, y = e.x - ox - hpw / 2, it[4] - 10
            pygame.draw.rect(surf, (30, 20, 30), (x - 1, y - 1, hpw + 2, 6))
            pygame.draw.rect(surf, (255, 160, 60), (x, y, hpw * max(0, e.hp / e.max_hp), 4))

    def _player(self, surf, ox, oy) -> None:
        run = self.run
        p = run.player
        anim = assets.sprites.players[run.char.id]
        f = (int(p.anim) % 2) if p.moving else 0
        face = p.face
        x, y = p.x - ox, p.y - oy
        if p.dead:
            return
        sl = p.slide if run.char.special == "slide" else 0.0
        if sl > 0.55:
            # klouzání po břiše: vždy ležící tučňák (rotace přesně o 90° = čistý pixel art), hlavou
            # vlevo/vpravo podle posledního vodorovného směru – i při jízdě nahoru/dolů (B-31)
            key = (face, p.flash > 0)
            img = self._slide_rot.get(key)
            if img is None:
                base = anim.flash[face][0] if p.flash > 0 else anim.frames[face][0]
                img = pygame.transform.rotate(base, -90 if face == 0 else 90)
                self._slide_rot[key] = img
        else:
            img = anim.flash[face][f] if p.flash > 0 else anim.frames[face][f]
        if p.invuln > 0 and p.flash <= 0 and int(self.t * 16) % 2 == 0 and run.state == "playing":
            # průhlednost až na hotový (případně otočený) snímek – nikdy ne do cache
            img = img.copy()
            img.set_alpha(120)
        sq = clamp(p.sq, 0.75, 1.25)
        w0, h0 = img.get_size()
        if abs(sq - 1) > 0.02:
            img = pygame.transform.scale(img, (int(w0 * (2 - sq)), int(h0 * sq)))
        w, h = img.get_size()
        bob = -abs(math.sin(p.anim * 0.5 * math.pi)) * 3 if p.moving else 0
        sh = anim.shadow
        surf.blit(sh, (x - sh.get_width() / 2, y + 6 - sh.get_height() / 2))
        sx, sy = x - w / 2, y - h + 9 + bob
        surf.blit(img, (sx, sy))
        if self.hat is not None and sl <= 0.55:
            hx, hy = HAT_ANCHOR.get(run.char.id, (7, 0))
            if face == 1:
                hx = w0 / PX - 2 - hx
            hat = self.hat if face == 0 else pygame.transform.flip(self.hat, True, False)
            surf.blit(hat, (sx + (hx + 1) * PX * (w / w0) - hat.get_width() / 2,
                            sy + (hy + 1) * PX * (h / h0) - hat.get_height() + 3))
        # HP bar pod hráčem
        st = p.stats
        bw = 44
        ratio = max(0.0, p.hp / st.max_hp)
        bx, by = x - bw / 2, y + 16
        pygame.draw.rect(surf, (24, 16, 28), (bx - 2, by - 2, bw + 4, 8))
        # bílá stopa ztraceného zdraví pomalu dobíhá (jen vizuál)
        self.hp_ghost = ratio if ratio >= self.hp_ghost else max(ratio, self.hp_ghost - 0.7 * getattr(self, "_dt", 0.016))
        if self.hp_ghost > ratio:
            pygame.draw.rect(surf, (255, 240, 220), (bx, by, bw * self.hp_ghost, 4))
        col = (90, 220, 90) if ratio > 0.5 else (240, 200, 60) if ratio > 0.25 else (240, 60, 60)
        pygame.draw.rect(surf, col, (bx, by, bw * ratio, 4))
        pygame.draw.rect(surf, mul_color(col, 1.25), (bx, by, bw * ratio, 1))

    def _projs(self, surf, ox, oy) -> None:
        blits = []
        sm = assets.sprites.small
        projs = self.run.projs
        if len(projs) < 160:
            glows = []
            for pr in projs:
                if pr.motion in (M_LOB, M_WAVE) or pr.src is None:
                    continue
                x, y = pr.x - ox, pr.y - oy
                if -20 < x < W + 20 and -20 < y < H + 20:
                    g = glow_sprite(3, pr.src.d.color, 0.45)
                    glows.append((g, (x - 10, y - 10)))
            blit_add(surf, glows)
        for pr in projs:
            x, y = pr.x - ox, pr.y - oy
            if x < -40 or x > W + 40 or y < -60 or y > H + 40:
                continue
            m = pr.motion
            if m == M_WAVE:
                r = pr.r
                a0 = pr.ang
                rect = (x - r, y - r, r * 2, r * 2)
                fade = min(1.0, pr.life * 3)
                col = lerp_color((255, 255, 255), pr.color, 1 - fade * 0.3)
                pygame.draw.arc(surf, col, rect, -a0 - 0.9, -a0 + 0.9, max(2, int(4 * pr.size)))
                continue
            if m == M_LOB:
                sh = self.shadow_small
                blits.append((sh, (x - 15, y - 5)))
                img = pr.spr
                if pr.size != 1.0:
                    img = pygame.transform.scale(img, (int(img.get_width() * pr.size), int(img.get_height() * pr.size)))
                blits.append((img, (x - img.get_width() / 2, y - pr.z - img.get_height() / 2)))
                continue
            if pr.rot is not None:
                if m == M_SPIRAL:
                    ang = pr.ang + math.pi / 2
                elif m == M_BOOMERANG:
                    ang = pr.ang
                else:
                    ang = math.atan2(pr.vy, pr.vx)
                img = pr.rot[angle_index(ang)]
            elif pr.spr is not None:
                img = pr.spr
            else:
                img = sm["egg"]
            blits.append((img, (x - img.get_width() / 2, y - img.get_height() / 2)))
        if blits:
            fblits(surf, blits)

    def _eprojs(self, surf, ox, oy) -> None:
        glows = []
        pulse = 0.75 + 0.25 * math.sin(self.t * 14)
        for ep in self.run.eprojs:
            x, y = ep.x - ox, ep.y - oy
            if x < -30 or x > W + 30 or y < -30 or y > H + 30:
                continue
            g = glow_sprite(4, EPROJ_GLOW.get(ep.kind, (255, 120, 120)), pulse)
            glows.append((g, (x - g.get_width() / 2, y - g.get_height() / 2)))
        blit_add(surf, glows)
        for ep in self.run.eprojs:
            x, y = ep.x - ox, ep.y - oy
            if x < -30 or x > W + 30 or y < -30 or y > H + 30:
                continue
            img = ep.spr
            if ep.kind in (1, 2):
                rot = assets.sprites.rot("carrot" if ep.kind == 2 else "feather")
                img = rot[angle_index(math.atan2(ep.vy, ep.vx))]
            surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))

    def _waves_rings(self, surf, ox, oy) -> None:
        for w in self.run.waves:
            k = 1 - max(0.0, w.life) / w.maxlife
            width = max(2, int(10 * (1 - k)))
            pygame.draw.circle(surf, w.color, (int(w.x - ox), int(w.y - oy)), int(w.r), width)
            if w.r > 30:
                pygame.draw.circle(surf, (255, 255, 255), (int(w.x - ox), int(w.y - oy)), int(w.r - width), 1)
        for r in self.run.rings:
            k = 1 - r.life / r.maxlife
            rad = r.r0 + (r.r1 - r.r0) * (1 - (1 - k) ** 2)
            width = max(1, int(r.width * (1 - k)))
            c = (int(r.x - ox), int(r.y - oy))
            pygame.draw.circle(surf, r.color, c, int(rad), width)
            if k < 0.35 and rad > 8:
                pygame.draw.circle(surf, (255, 255, 240), c, int(rad - width / 2), max(1, width // 3))

    def _beams(self, surf, ox, oy) -> None:
        for b in self.run.beams:
            k = b.life / b.maxlife
            if b.kind == "laser":
                (x1, y1), (x2, y2) = b.pts
                w = max(2, int(b.width * k))
                pygame.draw.line(surf, b.color, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), w)
                pygame.draw.line(surf, (255, 255, 255), (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), max(1, w // 3))
                pygame.draw.circle(surf, (255, 255, 255), (int(x1 - ox), int(y1 - oy)), max(3, w // 2 + 2))
            elif b.kind == "bolt":
                pts = [(x - ox, y - oy) for x, y in b.pts]
                pygame.draw.lines(surf, b.color, False, pts, max(1, int(b.width * k) + 1))
                pygame.draw.lines(surf, (255, 255, 255), False, pts, 1)
            elif b.kind == "slash":
                (cx, cy), (ang, arc) = b.pts
                r = b.width
                x, y = cx - ox, cy - oy
                rect = (x - r, y - r, r * 2, r * 2)
                start = -ang - arc / 2
                for i, wdt in enumerate((7, 4, 2)):
                    rr = r - i * 6
                    pygame.draw.arc(surf, b.color if i < 2 else (255, 255, 255), (x - rr, y - rr, rr * 2, rr * 2),
                                    start, start + arc, max(1, int(wdt * k)))
            elif b.kind == "band":
                (x1, y1), (x2, y2) = b.pts
                s = pygame.Surface((W, int(b.width)), pygame.SRCALPHA)
                s.fill((*b.color, int(200 * k)))
                surf.blit(s, (0, y1 - oy - b.width / 2))
            elif b.kind == "crack":
                (x1, y1), (x2, y2) = b.pts
                pygame.draw.line(surf, b.color, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), max(2, int(b.width * k)))

    def _bombs(self, surf, ox, oy) -> None:
        for b in self.run.bombs:
            if not b[8]:
                continue
            x, y = b[0] - ox, b[1] - oy
            col = (255, 60, 40) if int(b[2] * 16) % 2 else (255, 230, 120)
            pygame.draw.circle(surf, (30, 20, 30), (int(x), int(y)), 9)
            pygame.draw.circle(surf, col, (int(x), int(y)), 7)
            s = self.circle(b[3], (255, 80, 40), 40)
            surf.blit(s, (x - b[3] - 1, y - b[3] - 1))

    def _canopies(self, surf, ox, oy) -> None:
        run = self.run
        p = run.player
        for ch in run.map.visible_chunks(ox, oy, W, H):
            for ob in ch.obstacles:
                if ob.canopy is None:
                    continue
                c = ob.canopy
                cw, chh = c.get_size()
                x = ob.x - ox - cw / 2
                y = ob.y - oy - chh - 12
                if x < -cw or x > W or y < -chh or y > H:
                    continue
                near = abs(p.x - ob.x) < cw * 0.6 and -chh - 30 < p.y - ob.y < 20
                surf.blit(ob.canopy_a if near else c, (x, y))

    def _lighting(self, surf) -> None:
        run = self.run
        ft = run.final_time or 600
        if run.victory:
            k = 1.0
        else:
            k = clamp(run.time / ft, 0, 1)
        night = run.biome.night
        night_mul = (150 + night[0] // 2, 150 + night[1] // 2, 190 + night[2] // 3)
        dawn = (255, 225, 205)
        day = (255, 255, 255)
        if run.victory:
            col = day
        elif k < 0.85:
            col = lerp_color(night_mul, (215, 195, 215), k / 0.85)
        else:
            col = lerp_color((215, 195, 215), dawn, (k - 0.85) / 0.15)
        if self.season_tint:
            col = lerp_color(col, (col[0] * self.season_tint[0] // 255, col[1] * self.season_tint[1] // 255,
                                   col[2] * self.season_tint[2] // 255), 0.25)
        if col != (255, 255, 255):
            if FAST_MULT:
                surf.fill(col, special_flags=pygame.BLEND_MULT)
            else:
                # klasický pygame (Android) má pomalé BLEND_MULT – průhledná tmavá vrstva je ~10× levnější
                dark = 1.0 - (col[0] + col[1] + col[2]) / 765.0
                ov = self._light_ov
                ov.fill((col[0] // 6, col[1] // 6, col[2] // 5))
                ov.set_alpha(min(255, int(dark * 300)))
                surf.blit(ov, (0, 0))
        if self.fog is not None:
            p = run.player
            x = p.x - run.camera.ox - W
            y = p.y - run.camera.oy - H
            surf.blit(self.fog, (x, y))

    def _footsteps(self, dt: float) -> None:
        """Prach pod nohama při chůzi (jen vizuál, vlastní RNG částic)."""
        run = self.run
        p = run.player
        if run.state != "playing" or p.dead or not p.moving:
            return
        self._dust_t -= dt
        if self._dust_t <= 0:
            self._dust_t = 0.16
            run.particles.dust(p.x - p.vx * 0.04, p.y + 7, DUST_COL.get(run.biome.id, (140, 120, 90)))

    def _texts(self, surf, ox, oy) -> None:
        font = assets.font
        for t in self.run.texts:
            x, y = t.x - ox, t.y - oy
            if -40 < x < W + 40 and -20 < y < H:
                a = 255 if t.life > 0.25 else int(255 * t.life / 0.25)
                font.draw(surf, t.text, (x, y), t.color, t.scale, "center", outline=(20, 10, 20), alpha=a)

    def _speech(self, surf, ox, oy) -> None:
        font = assets.font
        for e, text, life, dead in self.run.speech:
            x, y = e.x - ox, e.y - oy - (e.spr.h if hasattr(e, "spr") and e.spr else 40) * 0.8 - 20
            lines = font.wrap(text, 230, 2)
            tw = max(font.width(ln, 2) for ln in lines) + 16
            th = len(lines) * font.line_h(2) + 10
            x = clamp(x, tw / 2 + 6, W - tw / 2 - 6)
            y = clamp(y, th + 60, H - 40)
            rect = pygame.Rect(0, 0, tw, th)
            rect.midbottom = (x, y)
            notched_rect(surf, (20, 12, 24), rect.inflate(6, 6))
            notched_rect(surf, (255, 250, 235), rect)
            pygame.draw.rect(surf, (226, 214, 196), (rect.x + 3, rect.bottom - 3, rect.w - 6, 3))
            pygame.draw.polygon(surf, (255, 250, 235), [(x - 6, rect.bottom), (x + 6, rect.bottom), (x, rect.bottom + 8)])
            yy = rect.y + 5
            for ln in lines:
                font.draw(surf, ln, (rect.centerx, yy), (40, 24, 40), 2, "midtop", shadow=False)
                yy += font.line_h(2)


def _sort_key(it):
    return it[0]


class _Ambient:
    """Ambientní život biomu: listí (les), prach (město), sníh (hory), jiskry (továrna). Světlušky byly rušivé.
    Souřadnice ve světě zabalené kolem kamery – při pohybu se posouvají s mapou (žádná „špína na čočce“)."""
    SPAN_X, SPAN_Y = W + 60, H + 60

    def __init__(self, biome: str) -> None:
        import random as _r
        rng = _r.Random(11)
        self.biome = biome
        spec = {"farm": [], "forest": [("leaf", 16)], "city": [("mote", 18)],
                "mountain": [("snow", 34)], "factory": [("ember", 16), ("mote", 8)]}.get(biome, [("mote", 10)])
        self.items = []
        for kind, n in spec:
            for _ in range(n):
                self.items.append([rng.uniform(0, self.SPAN_X), rng.uniform(0, self.SPAN_Y),
                                   rng.uniform(0, math.tau), kind, rng.uniform(0.6, 1.3)])
        self.t = 0.0
        self.leaf_cols = [(214, 140, 50), (186, 92, 40), (120, 160, 60)]

    def update(self, dt: float, run) -> None:
        if run.state not in ("playing", "victory_anim", "dying"):
            return
        self.t += dt
        for it in self.items:
            kind, sp = it[3], it[4]
            if kind == "snow":
                it[1] += 46 * sp * dt
                it[0] += math.sin(self.t * 1.3 + it[2]) * 18 * dt
            elif kind == "leaf":
                it[1] += 30 * sp * dt
                it[0] += (math.sin(self.t * 1.7 + it[2]) * 40 + 12) * dt
            elif kind == "ember":
                it[1] -= 34 * sp * dt
                it[0] += math.sin(self.t * 2 + it[2]) * 14 * dt
            else:
                it[0] += 8 * sp * dt
                it[1] += math.sin(self.t * 0.5 + it[2]) * 5 * dt

    def draw(self, surf, ox: float, oy: float, run, lit: bool) -> None:
        sx_span, sy_span = self.SPAN_X, self.SPAN_Y
        adds = []
        for x, y, ph, kind, sp in self.items:
            glowy = kind in ("ember", "snow")     # sníh až po nočním přítmí – jinak splyne se zemí
            if glowy != lit:
                continue
            par = 1.0 + (sp - 1.0) * 0.4
            px = int((x - ox * par) % sx_span) - 30
            py = int((y - oy * par) % sy_span) - 30
            if kind == "snow":
                s = 6 if sp > 1.1 else 3
                gx, gy = px // 3 * 3, py // 3 * 3
                surf.fill((140, 160, 200), (gx + 3, gy + 3, s, s))     # stín – vločka čitelná i na sněhu
                surf.fill((250, 252, 255), (gx, gy, s, s))
            elif kind == "leaf":
                c = self.leaf_cols[int(ph * 3) % 3]
                flip = int(self.t * 3 + ph * 5) & 1
                surf.fill(c, (px, py, 6 if flip else 3, 3 if flip else 6))
                surf.fill(mul_color(c, 0.7), (px, py + 3, 3, 3))
            elif kind == "mote":
                surf.fill((200, 200, 205), (px // 3 * 3, py // 3 * 3, 3, 3))
            elif kind == "ember":
                k = 0.5 + 0.5 * math.sin(self.t * 5 + ph * 3)
                g = glow_sprite(2, (255, 150, 50), 0.4 + 0.6 * k)
                adds.append((g, (px - 7, py - 7)))
        blit_add(surf, adds)
