"""RunRenderer – vykreslení světa runu: terén, zóny, telegrafy, y-sorted entity, efekty, osvětlení."""
from __future__ import annotations

import math
import time

import pygame

from .. import assets
from ..config import H, PX, W
from ..device import fblits
from ..gfx import pixelart as pa
from ..gfx.sprites import angle_index
from ..gfx.tiles import TILE
from ..util import clamp, lerp_color
from .entities import M_BOOMERANG, M_LOB, M_SPIRAL, M_WAVE, P_CHEST, P_COIN, P_GOLDEGG, P_MAGNET, P_WORM, P_XP

FAST_MULT = hasattr(pygame.Surface, "fblits")     # pygame-ce má SIMD blend; klasický pygame ne

# kotvy klobouků skinů (art px relativně k levému hornímu rohu spritu bez obrysu): (střed x, horní y)
HAT_ANCHOR = {"hen": (10.5, 1.5), "duck": (9.0, 2.0), "goose": (11.0, 0.5), "turkey": (11.5, 1.5),
              "rooster": (11.0, 0.5), "peacock": (13.0, 2.5), "penguin": (6.0, 0.5)}


class RunRenderer:
    def __init__(self, run) -> None:
        self.run = run
        self._circ: dict = {}
        self._overlay: dict = {}
        self._slide_rot: dict = {}
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
        self._ground(surf, ox, oy)
        self._zones(surf, ox, oy)
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
        self._telegraphs(surf, ox, oy, ground=False)
        run.particles.draw(surf, ox, oy)
        self._canopies(surf, ox, oy)
        if run.arena is not None:
            self._arena(surf, ox, oy, back=False)
        self._lighting(surf)
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
                if t.kind in ("circle", "stamper", "cake", "drop"):
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
                s = self.circle(r, a.color, int(70 * fade))
                surf.blit(s, (x - r - 1, y - r - 1))
                for i in range(3):
                    ang = self.t * 0.8 + i * 2.1 + a.x * 0.01
                    rr = r * 0.55
                    s2 = self.circle(rr, a.color, int(60 * fade))
                    surf.blit(s2, (x + math.cos(ang) * r * 0.35 - rr - 1, y + math.sin(ang) * r * 0.25 - rr - 1))
            elif a.kind == "cream":
                s = self.ellipse(r * 2, r * 1.3, (255, 245, 235), int(150 * fade))
                surf.blit(s, (x - r, y - r * 0.65))
            elif a.kind == "aura":
                s = self.circle(r, a.color, 40)
                surf.blit(s, (x - r - 1, y - r - 1))
                pygame.draw.circle(surf, a.color, (int(x), int(y)), int(r), 2)

    def _pickups(self, surf, ox, oy) -> None:
        sm = assets.sprites.small
        xp1, xp2, xp3 = sm["xp1"], sm["xp2"], sm["xp3"]
        blits = []
        t = self.t
        for pk in self.run.pickups:
            x, y = pk.x - ox, pk.y - oy
            if x < -20 or x > W + 20 or y < -30 or y > H + 20:
                continue
            k = pk.kind
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
            if k == P_CHEST and int(t * 4) % 2:
                blits.append((self.circle(20, (255, 230, 120), 50), (x - 21, y - 32)))
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
        player_drawn = p.dead and run.state == "dead"
        py = p.y
        for it in items:
            if not player_drawn and it[1] == 3 and it[0] > py:
                # hráč se kreslí nad všemi nepřáteli, ale pod překážkami, které stojí před ním
                if blits:
                    fblits(surf, blits)
                    blits = []
                self._player(surf, ox, oy)
                player_drawn = True
            blits.append((it[2], (it[3], it[4])))
            e = it[5]
            if e is not None:
                if e.freeze_t > 0 or e.hyp_t > 0 or e.elite:
                    extra.append(it)
        if blits:
            fblits(surf, blits)
        for it in extra:
            self._enemy_extra(surf, it, ox, oy)
        if not player_drawn:
            self._player(surf, ox, oy)

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
        if sl > 0.55 and (p.vx or p.vy):
            # klouzání po břiše: tělo leží ve směru jízdy, břichem dolů (úhel kvantovaný na 16 směrů)
            ang = math.atan2(p.vy, p.vx)
            right = math.cos(ang) >= 0
            face = 0 if right else 1
            q = int(round(ang / (math.tau / 16))) % 16
            key = (face, q, p.flash > 0)
            img = self._slide_rot.get(key)
            if img is None:
                base = anim.flash[face][0] if p.flash > 0 else anim.frames[face][0]
                a = q * 360 / 16
                rot = -90 - a if right else 90 - (a - 180)
                img = pygame.transform.rotate(base, rot)
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
        col = (90, 220, 90) if ratio > 0.5 else (240, 200, 60) if ratio > 0.25 else (240, 60, 60)
        pygame.draw.rect(surf, col, (bx, by, bw * ratio, 4))

    def _projs(self, surf, ox, oy) -> None:
        blits = []
        sm = assets.sprites.small
        for pr in self.run.projs:
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
            pygame.draw.circle(surf, r.color, (int(r.x - ox), int(r.y - oy)), int(rad), width)

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
            pygame.draw.rect(surf, (20, 12, 24), rect.inflate(4, 4))
            pygame.draw.rect(surf, (255, 250, 235), rect)
            pygame.draw.polygon(surf, (255, 250, 235), [(x - 6, rect.bottom), (x + 6, rect.bottom), (x, rect.bottom + 8)])
            yy = rect.y + 5
            for ln in lines:
                font.draw(surf, ln, (rect.centerx, yy), (40, 24, 40), 2, "midtop", shadow=False)
                yy += font.line_h(2)


def _sort_key(it):
    return it[0]
