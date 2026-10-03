"""Procedurální dlaždice terénu (pixel art) a zóny podle biomu."""
from __future__ import annotations

import random

import pygame

from ..config import PX
from ..util import mul_color
from . import pixelart as pa

TILE_ART = 64                 # art pixelů
TILE = TILE_ART * PX          # logických pixelů (192)


def _px(s: pygame.Surface, x: int, y: int, c) -> None:
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), c)


def ground_tiles(biome) -> list[pygame.Surface]:
    """Tři varianty dlaždice. Vedle sebe se střídají náhodně, proto žádný motiv nesmí přesahovat okraj
    dlaždice (dřív se skvrny „zalamovaly“ na protější stranu a na švu s jinou variantou byly useknuté)."""
    out = []
    edge = 2
    for variant in range(3):
        rng = random.Random(f"{biome.id}-{variant}")
        s = pygame.Surface((TILE_ART, TILE_ART))
        s.fill(biome.ground)
        # skvrny – celé uvnitř dlaždice
        for _ in range(7):
            r = rng.randint(4, 11)
            cx = rng.randrange(r + edge, TILE_ART - r - edge)
            cy = rng.randrange(r + edge, TILE_ART - r - edge)
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r and rng.random() < 0.85:
                        _px(s, cx + dx, cy + dy, biome.ground2)
        bid = biome.id
        if bid in ("farm", "forest"):
            for _ in range(70 if bid == "farm" else 50):
                x, y = rng.randrange(1, TILE_ART - 2), rng.randrange(3, TILE_ART - 1)
                c = biome.detail if rng.random() < 0.7 else mul_color(biome.ground, 0.8)
                _px(s, x, y, c)
                _px(s, x, y - 1, c)
                if rng.random() < 0.5:
                    _px(s, x + 1, y - 2, c)
            if bid == "farm" and variant == 2:
                # vyšlapaná hlína – nepravidelná plocha uvnitř dlaždice (dřív pruh cesty, který končil na švu)
                cx, cy = 32, 34
                for x in range(10, 54):
                    for y in range(20, 48):
                        d = ((x - cx) / 21.0) ** 2 + ((y - cy) / 12.0) ** 2
                        if d < 1.0 - rng.random() * 0.25:
                            _px(s, x, y, (150, 116, 74) if rng.random() < 0.8 else (132, 100, 64))
            if bid == "forest":
                for _ in range(25):
                    x, y = rng.randrange(TILE_ART), rng.randrange(TILE_ART)
                    c = rng.choice([(120, 84, 40), (150, 100, 40), (90, 70, 40)])
                    _px(s, x, y, c)
                    _px(s, min(TILE_ART - 1, x + 1), y, c)
        elif bid == "city":
            side = (128, 128, 138)
            for x in range(TILE_ART):
                for y in range(TILE_ART):
                    if x < 8 or y < 8:
                        _px(s, x, y, side if (x + y) % 9 else mul_color(side, 0.85))
            for i in range(8, TILE_ART, 8):
                _px(s, i, 4, mul_color(side, 0.75))
                _px(s, 4, i, mul_color(side, 0.75))
            for x in range(14, TILE_ART, 10):
                for k in range(5):
                    _px(s, x + k, 36, (220, 210, 120))
            for _ in range(40):
                _px(s, rng.randrange(8, TILE_ART), rng.randrange(8, TILE_ART), mul_color(biome.ground, 1.12))
        elif bid == "mountain":
            for _ in range(60):
                x, y = rng.randrange(TILE_ART), rng.randrange(TILE_ART)
                _px(s, x, y, biome.detail if rng.random() < 0.6 else (250, 252, 255))
            for _ in range(6):
                x, y = rng.randrange(TILE_ART), rng.randrange(TILE_ART)
                _px(s, x, y, (130, 130, 145))
                _px(s, x + 1, y, (110, 110, 125))
        elif bid == "factory":
            plate = 32
            for px0 in range(0, TILE_ART, plate):
                for py0 in range(0, TILE_ART, plate):
                    for x in range(plate):
                        _px(s, px0 + x, py0, mul_color(biome.ground, 0.8))
                        _px(s, px0, py0 + x, mul_color(biome.ground, 0.8))
                    for (rx, ry) in ((3, 3), (plate - 4, 3), (3, plate - 4), (plate - 4, plate - 4)):
                        _px(s, px0 + rx, py0 + ry, mul_color(biome.ground, 1.3))
            if variant == 1:
                # výstražná deska uvnitř jednoho plátu (dřív pruh přes celou dlaždici, useknutý na švu)
                for x in range(36, 60):
                    for y in range(36, 60):
                        if x in (36, 59) or y in (36, 59):
                            _px(s, x, y, (40, 36, 40))
                        else:
                            _px(s, x, y, (230, 190, 40) if ((x + y) // 4) % 2 else (40, 36, 40))
            if variant == 2:
                for x in range(20, 44):
                    for y in range(20, 44):
                        if (x + y) % 3 == 0 or x in (20, 43) or y in (20, 43):
                            _px(s, x, y, (70, 72, 84))
        out.append(pa.scale(s, PX))
    return out


def zone_surface(kind: str, w: int, h: int, seed: int = 0) -> pygame.Surface:
    """Vizuál zóny (velikost v logických px)."""
    aw, ah = max(4, w // PX), max(4, h // PX)
    s = pygame.Surface((aw, ah), pygame.SRCALPHA)
    rng = random.Random(seed)
    if kind == "puddle":
        pygame.draw.ellipse(s, (60, 110, 170, 255), s.get_rect())
        pygame.draw.ellipse(s, (90, 150, 210, 255), s.get_rect().inflate(-4, -4))
        for _ in range(3):
            x = rng.randrange(aw // 4, max(aw // 4 + 1, aw * 3 // 4))
            y = rng.randrange(ah // 4, max(ah // 4 + 1, ah * 3 // 4))
            pygame.draw.line(s, (170, 210, 245, 255), (x, y), (x + 3, y))
    elif kind == "oil":
        pygame.draw.ellipse(s, (30, 26, 36, 255), s.get_rect())
        pygame.draw.ellipse(s, (60, 50, 80, 255), s.get_rect().inflate(-6, -6), 1)
        pygame.draw.line(s, (120, 80, 160, 255), (aw // 3, ah // 2), (aw // 3 + 4, ah // 2))
    elif kind == "ice":
        pygame.draw.ellipse(s, (170, 215, 245, 255), s.get_rect())
        pygame.draw.ellipse(s, (200, 235, 255, 255), s.get_rect().inflate(-6, -6))
        for _ in range(4):
            x = rng.randrange(4, max(5, aw - 6))
            y = rng.randrange(3, max(4, ah - 4))
            pygame.draw.line(s, (255, 255, 255, 255), (x, y), (x + 4, y - 2))
    elif kind == "snowdrift":
        pygame.draw.ellipse(s, (205, 215, 235, 255), s.get_rect())
        pygame.draw.ellipse(s, (250, 252, 255, 255), s.get_rect().inflate(-4, -6).move(0, -2))
    return pa.scale(s, PX)


def conveyor_frames(w: int, h: int, horizontal: bool) -> list[pygame.Surface]:
    aw, ah = max(4, w // PX), max(4, h // PX)
    frames = []
    for f in range(4):
        s = pygame.Surface((aw, ah))
        s.fill((52, 52, 60))
        if horizontal:
            for x in range(-4, aw + 4, 4):
                xx = x + f
                pygame.draw.line(s, (84, 84, 96), (xx, 2), (xx, ah - 3))
            pygame.draw.rect(s, (230, 190, 40), (0, 0, aw, 1))
            pygame.draw.rect(s, (230, 190, 40), (0, ah - 1, aw, 1))
        else:
            for y in range(-4, ah + 4, 4):
                yy = y + f
                pygame.draw.line(s, (84, 84, 96), (2, yy), (aw - 3, yy))
            pygame.draw.rect(s, (230, 190, 40), (0, 0, 1, ah))
            pygame.draw.rect(s, (230, 190, 40), (aw - 1, 0, 1, ah))
        frames.append(pa.scale(s, PX))
    return frames


def wall_surface(w: int, h: int, seed: int = 0) -> pygame.Surface:
    """Městská zeď / blok domů (pohled shora-zepředu)."""
    aw, ah = max(6, w // PX), max(6, h // PX)
    rng = random.Random(seed)
    s = pygame.Surface((aw, ah + 10), pygame.SRCALPHA)
    roof = rng.choice([(90, 70, 70), (70, 80, 100), (100, 90, 70)])
    brick = rng.choice([(150, 80, 64), (170, 150, 120), (120, 120, 130)])
    pygame.draw.rect(s, roof, (0, 0, aw, 10))
    pygame.draw.rect(s, mul_color(roof, 1.2), (0, 0, aw, 2))
    pygame.draw.rect(s, brick, (0, 10, aw, ah))
    for y in range(10, ah + 10, 3):
        off = 0 if (y // 3) % 2 else 3
        pygame.draw.line(s, mul_color(brick, 0.8), (0, y), (aw, y))
        for x in range(off, aw, 6):
            _px(s, x, y + 1, mul_color(brick, 0.8))
    for x in range(4, aw - 6, 10):
        pygame.draw.rect(s, (40, 40, 60), (x, 14, 5, 5))
        if rng.random() < 0.3:
            pygame.draw.rect(s, (230, 200, 100), (x + 1, 15, 3, 3))
    pygame.draw.rect(s, pa.OUTLINE, s.get_rect(), 1)
    return pa.scale(s, PX)
