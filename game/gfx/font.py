"""Vlastní bitmapový pixel font 5×7 s plnou podporou české diakritiky.

Buňka znaku má 11 řádků: 2 řádky rezerva na akcenty velkých písmen, 7 řádků tělo,
2 řádky dotahy (g, j, p, q, y, čárka). Akcenty se skládají automaticky (čárka, háček, kroužek).
"""
from __future__ import annotations

import re

import pygame

TOP = 2          # řádky nad tělem (akcenty verzálek)
CELL_H = 11      # celková výška buňky
LINE_H = 12      # výška řádku včetně mezery

# Řádky odděleny '|'. 7 řádků = bez dotahu, 9 řádků = s dotahem.
GLYPHS: dict[str, str] = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "###|.#.|.#.|.#.|.#.|.#.|###",
    "J": "..###|...#.|...#.|...#.|#..#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "a": ".....|.....|.###.|....#|.####|#...#|.####",
    "b": "#....|#....|####.|#...#|#...#|#...#|####.",
    "c": "....|....|.###|#...|#...|#...|.###",
    "d": "....#|....#|.####|#...#|#...#|#...#|.####",
    "e": ".....|.....|.###.|#...#|#####|#....|.###.",
    "f": "..##|.#..|####|.#..|.#..|.#..|.#..",
    "g": ".....|.....|.####|#...#|#...#|#...#|.####|....#|.###.",
    "h": "#....|#....|####.|#...#|#...#|#...#|#...#",
    "i": "#|.|#|#|#|#|#",
    "j": "..#|...|..#|..#|..#|..#|..#|#.#|.#.",
    "k": "#...|#...|#..#|#.#.|##..|#.#.|#..#",
    "l": "#.|#.|#.|#.|#.|#.|.#",
    "m": ".....|.....|##.#.|#.#.#|#.#.#|#.#.#|#...#",
    "n": "....|....|###.|#..#|#..#|#..#|#..#",
    "o": ".....|.....|.###.|#...#|#...#|#...#|.###.",
    "p": ".....|.....|####.|#...#|#...#|#...#|####.|#....|#....",
    "q": ".....|.....|.####|#...#|#...#|#...#|.####|....#|....#",
    "r": "....|....|#.##|##..|#...|#...|#...",
    "s": "....|....|.###|#...|.##.|...#|###.",
    "t": ".#..|.#..|####|.#..|.#..|.#..|..##",
    "u": ".....|.....|#...#|#...#|#...#|#...#|.####",
    "v": ".....|.....|#...#|#...#|#...#|.#.#.|..#..",
    "w": ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.",
    "x": "....|....|#..#|#..#|.##.|#..#|#..#",
    "y": "....|....|#..#|#..#|#..#|#..#|.###|...#|###.",
    "z": "....|....|####|...#|.##.|#...|####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": ".#.|##.|.#.|.#.|.#.|.#.|###",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": ".###.|#....|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|..#..|..#..|..#..",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|....#|.###.",
    ".": ".|.|.|.|.|.|#",
    ",": "..|..|..|..|..|..|.#|#.",
    "!": "#|#|#|#|#|.|#",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    ":": ".|.|#|.|.|.|#",
    ";": "..|..|.#|..|..|..|.#|#.",
    "-": "...|...|...|###|...|...|...",
    "–": "....|....|....|####|....|....|....",
    "+": "...|...|.#.|###|.#.|...|...",
    "=": "...|...|###|...|###|...|...",
    "/": "....#|...#.|...#.|..#..|.#...|.#...|#....",
    "(": ".#|#.|#.|#.|#.|#.|.#",
    ")": "#.|.#|.#|.#|.#|.#|#.",
    "[": "##|#.|#.|#.|#.|#.|##",
    "]": "##|.#|.#|.#|.#|.#|##",
    "'": "#|#|.|.|.|.|.",
    '"': "#.#|#.#|...|...|...|...|...",
    "„": "...|...|...|...|...|#.#|#.#|#.#",
    "“": "#.#|#.#|...|...|...|...|...",
    "%": "##..#|##.#.|...#.|..#..|.#...|.#.##|#..##",
    "×": "...|...|#.#|.#.|#.#|...|...",
    "#": ".#.#.|#####|.#.#.|.#.#.|#####|.#.#.|.....",
    "*": "...|#.#|.#.|#.#|...|...|...",
    "<": "...#|..#.|.#..|#...|.#..|..#.|...#",
    ">": "#...|.#..|..#.|...#|..#.|.#..|#...",
    "_": ".....|.....|.....|.....|.....|.....|.....|#####",
    "&": ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#",
    "|": "#|#|#|#|#|#|#",
    "^": ".#.|#.#|...|...|...|...|...",
    "°": "###|#.#|###|...|...|...|...",
    "·": ".|.|.|#|.|.|.",
    "~": ".....|.....|.#...|#.#.#|...#.|.....|.....",
    "♥": ".#.#.|#####|#####|#####|.###.|..#..|.....",
    "★": "..#..|..#..|#####|.###.|.###.|##.##|#...#",
    "→": ".....|..#..|...#.|#####|...#.|..#..|.....",
    "←": ".....|..#..|.#...|#####|.#...|..#..|.....",
    "↑": "..#..|.###.|#.#.#|..#..|..#..|..#..|.....",
    "↓": "..#..|..#..|..#..|#.#.#|.###.|..#..|.....",
    "✓": ".....|....#|...#.|#.#..|.#...|.....|.....",
    "…": ".....|.....|.....|.....|.....|.....|#.#.#",
}

ACUTE = ["..#", ".#."]
CARON = ["#.#", ".#."]
RING_UP = [".#.", "#.#"]
RING_LOW = [".#.", "#.#", ".#."]

# náhrady znaků, které font nemá
FALLBACK = {"−": "-", "—": "–", "™": "", "’": "'", "‘": "'", "”": '"', "	": " "}

# znak -> (základ, akcent, styl) ; styl 'cap' = akcent v horní rezervě, 'low' = v řádcích 0-1 těla
COMPOSED = {
    "Á": ("A", ACUTE, "cap"), "É": ("E", ACUTE, "cap"), "Í": ("I", ACUTE, "cap"),
    "Ó": ("O", ACUTE, "cap"), "Ú": ("U", ACUTE, "cap"), "Ý": ("Y", ACUTE, "cap"),
    "Č": ("C", CARON, "cap"), "Ď": ("D", CARON, "cap"), "Ě": ("E", CARON, "cap"),
    "Ň": ("N", CARON, "cap"), "Ř": ("R", CARON, "cap"), "Š": ("S", CARON, "cap"),
    "Ť": ("T", CARON, "cap"), "Ž": ("Z", CARON, "cap"), "Ů": ("U", RING_UP, "cap"),
    "á": ("a", ACUTE, "low"), "é": ("e", ACUTE, "low"), "ó": ("o", ACUTE, "low"),
    "ú": ("u", ACUTE, "low"), "ý": ("y", ACUTE, "low"), "ů": ("u", RING_LOW, "ring"),
    "č": ("c", CARON, "low"), "ě": ("e", CARON, "low"), "ň": ("n", CARON, "low"),
    "ř": ("r", CARON, "low"), "š": ("s", CARON, "low"), "ž": ("z", CARON, "low"),
    "Ä": ("A", ["#.#", "..."], "cap"), "Ö": ("O", ["#.#", "..."], "cap"), "Ü": ("U", ["#.#", "..."], "cap"),
    "ä": ("a", ["#.#", "..."], "low"), "ö": ("o", ["#.#", "..."], "low"), "ü": ("u", ["#.#", "..."], "low"),
}
# Speciální ručně kreslené
SPECIAL = {
    "í": ".#|#.|#.|#.|#.|#.|#.",
    "ď": "....#.#|....#.#|.####..|#...#..|#...#..|#...#..|.####..",
    "ť": ".#..#|.#..#|####.|.#...|.#...|.#...|..##.",
}

SPACE_W = 3
LETTER_SP = 1


def _rows(spec: str) -> list[str]:
    return spec.split("|")


_NUM = re.compile(r"^[+\-−]?\d{1,3}$")
_GROUP = re.compile(r"^\d{3}([.,!?):;]*)$")
_UNITS = {"s", "s.", "s,", "min", "min.", "px", "HP", "×"}
NBSP = " "


def _glue(words: list[str]) -> list[str]:
    """Slepí slova, která se nesmí rozdělit na konci řádku (B-43): „40 %“, „1 500“, „20 s“.
    Spojují se nezlomitelnou mezerou (vykreslí se jako běžná mezera)."""
    out: list[str] = []
    for w in words:
        if out and w and (w.startswith("%") or (_NUM.match(out[-1].split(NBSP)[-1]) and
                                                 (_GROUP.match(w) or w in _UNITS))):
            out[-1] = out[-1] + NBSP + w
        else:
            out.append(w)
    return out


class BitmapFont:
    def __init__(self) -> None:
        self.glyphs: dict[str, pygame.Surface] = {}
        self.widths: dict[str, int] = {}
        self._cache: dict[tuple, pygame.Surface] = {}
        self._build()

    # --- stavba glyfů ------------------------------------------------------
    def _make(self, rows: list[str], accent: list[str] | None = None, style: str = "cap") -> pygame.Surface:
        w = max(len(r) for r in rows)
        if accent:
            w = max(w, len(accent[0]))
        surf = pygame.Surface((w, CELL_H), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    surf.set_at((x, TOP + y), (255, 255, 255, 255))
        if accent:
            aw = len(accent[0])
            ox = (w - aw + 1) // 2 if w > aw else 0
            oy = 0 if style == "cap" else (TOP - 1 if style == "ring" else TOP)
            for y, row in enumerate(accent):
                for x, ch in enumerate(row):
                    if ch == "#":
                        surf.set_at((ox + x, oy + y), (255, 255, 255, 255))
            if style == "low":
                # vyčistit případnou tečku/ascender v řádcích akcentu je zbytečné – základní znaky nemají
                pass
        return surf

    def _build(self) -> None:
        for ch, spec in GLYPHS.items():
            self._add(ch, self._make(_rows(spec)))
        for ch, spec in SPECIAL.items():
            self._add(ch, self._make(_rows(spec)))
        for ch, (base, acc, style) in COMPOSED.items():
            self._add(ch, self._make(_rows(GLYPHS[base]), acc, style))
        sp = pygame.Surface((SPACE_W, CELL_H), pygame.SRCALPHA)
        self._add(" ", sp)
        self._add(" ", sp)
        self._add("?unknown", self._make(_rows(GLYPHS["?"])))

    def _add(self, ch: str, surf: pygame.Surface) -> None:
        self.glyphs[ch] = surf
        self.widths[ch] = surf.get_width()

    # --- měření ---------------------------------------------------------------
    def _glyph(self, ch: str) -> pygame.Surface:
        g = self.glyphs.get(ch)
        if g is None:
            # fallback: zkusit bez diakritiky / velké písmeno
            g = self.glyphs.get(ch.upper()) or self.glyphs["?unknown"]
        return g

    @staticmethod
    def _clean(text: str) -> str:
        if any(c in FALLBACK for c in text):
            text = "".join(FALLBACK.get(c, c) for c in text)
        return text

    def width(self, text: str, scale: int = 2) -> int:
        if not text:
            return 0
        text = self._clean(text)
        w = 0
        for ch in text:
            w += self._glyph(ch).get_width() + LETTER_SP
        return (w - LETTER_SP) * scale

    def height(self, scale: int = 2) -> int:
        return CELL_H * scale

    def line_h(self, scale: int = 2) -> int:
        return LINE_H * scale

    # --- render ---------------------------------------------------------------
    def _mask(self, text: str) -> pygame.Surface:
        text = self._clean(text)
        w = max(1, self.width(text, 1))
        surf = pygame.Surface((w, CELL_H), pygame.SRCALPHA)
        x = 0
        for ch in text:
            g = self._glyph(ch)
            surf.blit(g, (x, 0))
            x += g.get_width() + LETTER_SP
        return surf

    def render(self, text: str, color=(255, 255, 255), scale: int = 2, shadow: bool = True,
               outline: tuple | None = None, shadow_color=(20, 12, 24)) -> pygame.Surface:
        key = (text, color, scale, shadow, outline)
        s = self._cache.get(key)
        if s is not None:
            return s
        if len(self._cache) > 3000:
            self._cache.clear()
        mask = self._mask(text)
        mw, mh = mask.get_size()
        pad = 1 if (outline or shadow) else 0
        base = pygame.Surface((mw + pad * 2, mh + pad * 2), pygame.SRCALPHA)
        if outline:
            ol = mask.copy()
            ol.fill((*outline[:3], 255), special_flags=pygame.BLEND_RGBA_MIN)
            ol.fill((*outline[:3], 0), special_flags=pygame.BLEND_RGBA_MAX)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                base.blit(ol, (pad + dx, pad + dy))
        elif shadow:
            sh = mask.copy()
            sh.fill((*shadow_color, 255), special_flags=pygame.BLEND_RGBA_MIN)
            sh.fill((*shadow_color, 0), special_flags=pygame.BLEND_RGBA_MAX)
            base.blit(sh, (pad + 1, pad + 1))
        col = mask.copy()
        col.fill((*color[:3], 255), special_flags=pygame.BLEND_RGBA_MIN)
        col.fill((*color[:3], 0), special_flags=pygame.BLEND_RGBA_MAX)
        base.blit(col, (pad, pad))
        if scale != 1:
            base = pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
        self._cache[key] = base
        return base

    def draw(self, surf: pygame.Surface, text: str, pos, color=(255, 255, 255), scale: int = 2,
             anchor: str = "topleft", shadow: bool = True, outline: tuple | None = None, alpha: int = 255) -> pygame.Rect:
        img = self.render(text, color, scale, shadow, outline)
        r = img.get_rect()
        setattr(r, anchor, pos)
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        surf.blit(img, r)
        return r

    def fit(self, text: str, max_w: int, scale: int = 2) -> str:
        """Zkrátí text s „…“, aby se vešel do max_w."""
        if self.width(text, scale) <= max_w:
            return text
        while text and self.width(text + "…", scale) > max_w:
            text = text[:-1]
        return text.rstrip() + "…"

    def wrap(self, text: str, max_w: int, scale: int = 2) -> list[str]:
        lines: list[str] = []
        for para in text.split("\n"):
            words = _glue(para.split(" "))
            cur = ""
            for w in words:
                test = w if not cur else cur + " " + w
                if self.width(test, scale) <= max_w:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            lines.append(cur)
        return lines

    def draw_wrapped(self, surf, text: str, rect: pygame.Rect, color=(255, 255, 255), scale: int = 2,
                     align: str = "left", shadow: bool = True, outline=None, line_gap: int = 0) -> int:
        y = rect.y
        lh = self.line_h(scale) + line_gap
        for line in self.wrap(text, rect.w, scale):
            if align == "center":
                self.draw(surf, line, (rect.centerx, y), color, scale, "midtop", shadow, outline)
            else:
                self.draw(surf, line, (rect.x, y), color, scale, "topleft", shadow, outline)
            y += lh
        return y - rect.y
