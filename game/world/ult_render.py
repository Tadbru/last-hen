"""Vykreslení běžících ultimátek (vrstvy pod entitami a nad nimi). Logika je ve world/ultimates.py.

Vše v pixelové mřížce 3 px jako zbytek hry; povrchy se cachují (žádné velké alokace za snímek).
"""
from __future__ import annotations

import math

import pygame

from ..config import H, W
from ..gfx.particles import FLAKE, HEART, blit_add, disc_sprite, glow_sprite, shape_sprite
from ..device import fblits

_frost: dict = {}
GOLD = (255, 206, 64)
WATER_DARK = (40, 104, 196)
WATER = (82, 160, 245)
FOAM = (226, 244, 255)
RAINBOW = ((255, 96, 170), (214, 120, 255), (120, 170, 255), (120, 230, 200))


def draw(surf, ren, run, ox: float, oy: float, ground: bool) -> None:
    if not run.ult_fx:
        return
    t = ren.t
    for f in run.ult_fx:
        k = f.kind
        if k == "egg_rain":
            if ground:
                _egg_marks(surf, ren, f, ox, oy, t)
        elif k == "flood":
            _flood(surf, f, ox, oy, t, ground)
        elif k == "goose_fury":
            _goose(surf, run, f, ox, oy, t, ground)
        elif k == "hypno":
            if not ground:
                _hypno(surf, f, ox, oy)
        elif k == "ice_age":
            _ice(surf, f, ox, oy, t, ground)


def _snap(v: float) -> int:
    return int(v) // 3 * 3


# --- slepice: zlaté značky dopadu ------------------------------------------------------------
def _egg_marks(surf, ren, f, ox, oy, t) -> None:
    r0 = f.s["radius"] * f.src.run.player.stats.area
    for pr in f.eggs:
        k = min(1.0, pr.t / max(0.01, pr.dur))
        x, y = pr.tx - ox, pr.ty - oy
        if x < -80 or x > W + 80 or y < -60 or y > H + 60:
            continue
        # poloměr a průhlednost po krocích – jinak by cache elips rostla do stovek povrchů (B-88)
        step = int(k * 5) / 5
        r = int(r0 * (0.35 + 0.65 * step)) // 6 * 6 + 6
        a = 40 + int(90 * step) // 30 * 30
        fill = ren.ellipse(r * 2, r * 1.3, GOLD, a // 2)
        surf.blit(fill, (x - fill.get_width() / 2, y - fill.get_height() / 2))
        ring = ren.ellipse(r * 2, r * 1.3, GOLD, min(255, a + 80), 3)
        surf.blit(ring, (x - ring.get_width() / 2, y - ring.get_height() / 2))
        # zaměřovací křížek pulzuje rychleji, čím blíž je dopad
        c = int(6 + 4 * math.sin(t * (8 + 14 * k)))
        col = (255, 240, 170)
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x1, y1 = x + sx * (r * 0.45), y + sy * (r * 0.3)
            pygame.draw.line(surf, col, (x1, y1), (x1 + sx * c, y1 + sy * c), 3)


# --- kachna: vlna ----------------------------------------------------------------------------
def _flood(surf, f, ox, oy, t, ground: bool) -> None:
    dx, dy = f.dx, f.dy
    nx, ny = -dy, dx
    hw = f.hw
    fx, fy = f.front
    fade = min(1.0, (f.len - f.dist) / 60.0 + 0.35)
    step = 27
    n = int(hw * 2 / step) + 1
    seq = []
    if ground:
        # mokrá stopa za vlnou: řady vodních chuchvalců, čím dál od čela, tím průhlednější
        for row in range(4):
            back = 36 + row * 30
            if f.dist - back < -20:
                break
            a = int((150 - row * 34) * fade) // 30 * 30
            if a < 30:
                continue
            for i in range(n):
                off = -hw + i * step + (row % 2) * step * 0.5
                w = math.sin(t * 6 + i * 1.7 + row) * 6
                px = fx - ox - dx * (back + w) + nx * off
                py = fy - oy - dy * (back + w) + ny * off
                if px < -40 or px > W + 40 or py < -40 or py > H + 40:
                    continue
                img = disc_sprite(5 - row // 2, WATER_DARK if row else WATER, a)
                seq.append((img, (_snap(px - img.get_width() / 2), _snap(py - img.get_height() / 2))))
        fblits(surf, seq)
        return
    # hřbet vlny (nad liškami): tmavá základna, světlé tělo, pěna na hraně
    for layer, (back, rad, col, al) in enumerate(((18, 7, WATER_DARK, 235), (8, 6, WATER, 245), (-2, 3, FOAM, 255))):
        for i in range(n + (1 if layer == 2 else 0)):
            off = -hw + i * step + (layer == 2) * step * 0.5
            if off > hw + 2:
                continue
            w = math.sin(t * 9 + i * 1.3 + layer * 0.8) * 5
            px = fx - dx * (back + w) + nx * off
            py = fy - dy * (back + w) + ny * off - (layer * 3)
            if -40 < px - ox < W + 40 and -40 < py - oy < H + 40:
                img = disc_sprite(rad if (i + layer) % 3 else rad + 1, col, int(al * fade) // 30 * 30)
                seq.append((img, (_snap(px - ox - img.get_width() / 2), _snap(py - oy - img.get_height() / 2))))
    fblits(surf, seq)
    # sprška z hřebene (vizuální RNG částic)
    run_p = f.src.run.particles
    if run_p.rng.random() < 0.7:
        off = run_p.rng.uniform(-hw, hw)
        run_p.drops(fx + nx * off, fy + ny * off - 10, 1, FOAM, 90, 160)


# --- husa: aura řádění -----------------------------------------------------------------------
def _goose(surf, run, f, ox, oy, t, ground: bool) -> None:
    p = run.player
    k = p.ult_aura
    if k <= 0 or p.dead:
        return
    x, y = p.x - ox, p.y - oy
    if ground:
        # pod husou: rudá záře, pulzující kruh a zbývající čas jako oblouk kolem nohou
        g = glow_sprite(10, (255, 70, 100), 0.4 + 0.2 * math.sin(t * 14))
        blit_add(surf, [(g, (x - g.get_width() / 2, y - 4 - g.get_height() / 2))])
        pulse = (t * 2.2) % 1.0
        r = int(22 + 26 * pulse)
        col = (255, int(120 + 100 * (1 - pulse)), 140)
        pygame.draw.ellipse(surf, col, (x - r, y + 4 - r * 0.6, r * 2, r * 1.2), 3 if pulse < 0.6 else 2)
        rect = pygame.Rect(0, 0, 54, 32)
        rect.center = (int(x), int(y + 6))
        pygame.draw.arc(surf, (255, 230, 120), rect, math.pi / 2, math.pi / 2 + math.tau * k, 4)
        return
    # nad husou: vzteklé obláčky páry
    if run.particles.rng.random() < 0.25:
        run.particles.puff(p.x + run.particles.rng.uniform(-10, 10), p.y - 34, 1, (255, 235, 235), 40, 6)


# --- páv: duhová vlna okouzlení --------------------------------------------------------------
def _hypno(surf, f, ox, oy) -> None:
    gr = f.s["grow"]
    if f.t > gr + 0.15:
        return
    a = 1.0 if f.t < gr else max(0.0, 1 - (f.t - gr) / 0.15)
    c = (int(f.x - ox), int(f.y - oy))
    rings = len(RAINBOW) if a >= 1.0 else max(1, int(len(RAINBOW) * a))     # dozní: vnitřní pruhy mizí
    for i, col in enumerate(RAINBOW[:rings]):
        r = int(f.r - i * 7)
        if r > 8:
            pygame.draw.circle(surf, col, c, r, 4 if i == 0 else 3)
    # srdíčka obíhající po okraji vlny
    seq = []
    for i in range(10):
        ang = i * math.tau / 10 + f.t * 3
        img = shape_sprite(HEART, (255, 110, 180), 3)
        seq.append((img, (_snap(c[0] + math.cos(ang) * f.r - 7), _snap(c[1] + math.sin(ang) * f.r - 6))))
    fblits(surf, seq)


# --- tučňák: ledová bouře --------------------------------------------------------------------
def _frost_disc(R: int) -> pygame.Surface:
    """Namrzlá zem: světle modrý kruh se světlejším středem, okrajem a jiskřičkami (pixel art, mřížka 3 px).
    Jeden povrch na poloměr, průhlednost náběhu se řeší při kreslení – dřív se stavěl pixel po pixelu pro každý
    krok průhlednosti a první bouře trhala snímky (B-87)."""
    key = R // 9
    s = _frost.get(key)
    if s is not None:
        return s
    if len(_frost) > 8:
        _frost.clear()
    r = max(4, R // 3)
    n = r * 2 + 1
    low = pygame.Surface((n, n), pygame.SRCALPHA)
    pygame.draw.circle(low, (150, 210, 250, 70), (r, r), r)
    pygame.draw.circle(low, (175, 225, 252, 90), (r, r), max(2, r * 2 // 3))
    pygame.draw.circle(low, (220, 244, 255, 160), (r, r), r, 2)
    for i in range(r * 2):                         # ledové jiskřičky (deterministicky)
        ang = i * 2.39996
        d = r * 0.9 * ((i * 0.618034) % 1.0) ** 0.5
        low.set_at((int(r + math.cos(ang) * d), int(r + math.sin(ang) * d)), (240, 252, 255, 170))
    s = pygame.transform.scale(low, (n * 3, n * 3))
    _frost[key] = s
    return s


def _ice(surf, f, ox, oy, t, ground: bool) -> None:
    R = f.R
    k = min(1.0, f.t / 0.3, max(0.0, (f.dur - f.t) / 0.3))
    x, y = f.x - ox, f.y - oy
    if ground:
        img = _frost_disc(int(R))
        img.set_alpha(int(255 * k) // 32 * 32 + 31)
        surf.blit(img, (_snap(x - img.get_width() / 2), _snap(y - img.get_height() / 2)))
        return
    spin = f.spin
    # větrné oblouky točící se kolem tučňáka
    for i in range(3):
        rr = int(R * (0.45 + 0.22 * i))
        a0 = -(t * 3.2 * spin + i * 2.1)
        rect = pygame.Rect(0, 0, rr * 2, rr * 2)
        rect.center = (int(x), int(y))
        pygame.draw.arc(surf, (210, 240, 255) if i != 1 else (255, 255, 255), rect, a0, a0 + 1.1, 3)
    pygame.draw.circle(surf, (190, 230, 255), (int(x), int(y)), int(R), 2)
    # vločky ve víru
    seq = []
    n = 30
    for i in range(n):
        u = (i * 0.618034) % 1.0
        rad = R * (0.2 + 0.8 * u) + math.sin(t * 3 + i) * 8
        ang = spin * t * (2.6 - 1.4 * u) + i * 2.39996
        img = shape_sprite(FLAKE, (235, 248, 255) if i % 3 else (170, 220, 255), 2 if i % 4 else 3)
        px, py = x + math.cos(ang) * rad, y + math.sin(ang) * rad * 0.85 - 10
        if k < 1 and (i / n) > k:
            continue
        seq.append((img, (_snap(px - img.get_width() / 2), _snap(py - img.get_height() / 2))))
    fblits(surf, seq)
