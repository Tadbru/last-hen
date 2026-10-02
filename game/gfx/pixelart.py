"""Převod pixel map (řetězce + paleta) na pygame Surface.

Mapy obsahují jen barevné plochy – obrys a jednoduché stínování se dopočítají automaticky.
"""
from __future__ import annotations

import pygame

from ..util import mul_color

OUTLINE = (26, 16, 30)

# Sdílená základní paleta; jednotlivé sprity si mohou znaky přepsat.
BASE_PALETTE: dict[str, tuple[int, int, int]] = {
    "w": (250, 248, 240), "W": (214, 210, 218), "g": (150, 148, 160), "G": (96, 94, 112),
    "k": (34, 24, 38), "r": (226, 48, 52), "R": (158, 26, 42), "o": (246, 152, 42),
    "O": (204, 102, 34), "y": (252, 216, 64), "Y": (222, 170, 40), "b": (146, 92, 52),
    "B": (98, 62, 36), "c": (246, 226, 188), "p": (168, 82, 204), "P": (112, 50, 152),
    "z": (124, 220, 92), "Z": (72, 150, 62), "e": (196, 255, 120), "u": (82, 142, 232),
    "U": (42, 80, 170), "n": (255, 168, 190), "t": (44, 172, 160), "s": (206, 214, 232),
    "q": (70, 205, 235), "m": (124, 128, 142), "x": (255, 255, 255), "h": (60, 40, 30),
    "v": (60, 110, 60), "l": (190, 240, 255), "i": (255, 120, 40), "j": (120, 70, 40),
    "a": (255, 236, 150), "d": (60, 50, 80), "f": (230, 120, 60), "F": (170, 80, 40),
}


def parse_map(spec: str) -> list[str]:
    rows = [r.rstrip() for r in spec.strip("\n").split("\n")]
    # odstranit společné odsazení
    ind = min((len(r) - len(r.lstrip(" ")) for r in rows if r.strip()), default=0)
    return [r[ind:] for r in rows]


def build(rows: list[str], palette: dict | None = None, outline=OUTLINE, shade: bool = True,
          outline_on: bool = True) -> pygame.Surface:
    pal = dict(BASE_PALETTE)
    if palette:
        pal.update(palette)
    h = len(rows)
    w = max(len(r) for r in rows) if rows else 1
    m = 1 if outline_on else 0
    grid: list[list] = [[None] * w for _ in range(h)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in (".", " "):
                col = pal.get(ch)
                if col is not None:
                    grid[y][x] = col
    surf = pygame.Surface((w + 2 * m, h + 2 * m), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            c = grid[y][x]
            if c is None:
                continue
            if shade:
                below = grid[y + 1][x] if y + 1 < h else None
                above = grid[y - 1][x] if y > 0 else None
                if below is None:
                    c = mul_color(c, 0.78)
                elif above is None:
                    c = mul_color(c, 1.12)
            surf.set_at((x + m, y + m), (*c, 255))
    if outline_on:
        ol = (*outline, 255)
        for y in range(h + 2):
            for x in range(w + 2):
                gx, gy = x - 1, y - 1
                if 0 <= gx < w and 0 <= gy < h and grid[gy][gx] is not None:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] is not None:
                        surf.set_at((x, y), ol)
                        break
    return surf


def scale(surf: pygame.Surface, k: float) -> pygame.Surface:
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (max(1, round(w * k)), max(1, round(h * k))))


def flip(surf: pygame.Surface) -> pygame.Surface:
    return pygame.transform.flip(surf, True, False)


def flash(surf: pygame.Surface) -> pygame.Surface:
    s = surf.copy()
    s.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return s


def tint(surf: pygame.Surface, color, strength: float = 1.0) -> pygame.Surface:
    """Multiplikativní tónování (strength 1 = plné)."""
    s = surf.copy()
    c = tuple(int(255 - (255 - v) * strength) for v in color[:3])
    s.fill((*c, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def silhouette(surf: pygame.Surface, color, alpha: int = 255) -> pygame.Surface:
    s = surf.copy()
    s.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.fill((*color[:3], 0), special_flags=pygame.BLEND_RGBA_ADD)
    if alpha < 255:
        s.set_alpha(alpha)
    return s


def recolor(rows: list[str], mapping: dict[str, str]) -> list[str]:
    tbl = str.maketrans(mapping)
    return [r.translate(tbl) for r in rows]


def overlay(rows: list[str], over: list[str], ox: int = 0, oy: int = 0) -> list[str]:
    """Překreslí znaky z `over` (kromě '.') přes mapu."""
    out = [list(r) for r in rows]
    for y, row in enumerate(over):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            yy, xx = y + oy, x + ox
            if yy < 0:
                continue
            while yy >= len(out):
                out.append([])
            while xx >= len(out[yy]):
                out[yy].append(".")
            out[yy][xx] = ch
    return ["".join(r) for r in out]


def shift_up(rows: list[str], n: int = 1) -> list[str]:
    return rows[n:] + ["." * len(rows[0])] * n


def make_shadow(w: int, h: int, alpha: int = 80) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (10, 6, 16, alpha), s.get_rect())
    return s


def circle_surf(r: int, color, alpha: int = 255, width: int = 0) -> pygame.Surface:
    s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*color[:3], alpha), (r + 1, r + 1), r, width)
    return s


def radial_glow(r: int, color, max_alpha: int = 160, steps: int = 8) -> pygame.Surface:
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(steps, 0, -1):
        rr = int(r * i / steps)
        a = int(max_alpha * (1 - i / steps) ** 0.8) + 8
        pygame.draw.circle(s, (*color[:3], min(255, a)), (r, r), rr)
    return s
