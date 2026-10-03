"""UI prvky: pixelová tlačítka, panely, posuvné seznamy. Všechna tlačítka ≥ 64 px na výšku pro prst."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_OUTLINE, C_PANEL, C_PANEL_HI, C_TEXT
from ..util import mul_color


NOTCH = 3            # zkosené rohy panelů = 1 art pixel (pixel-art „bevel“)


def notched_rect(surf, color, rect, n: int = NOTCH) -> None:
    """Obdélník s useknutými rohy (n px) – pixelový vzhled místo ostrých pravých úhlů."""
    r = pygame.Rect(rect)
    if r.w <= 2 * n or r.h <= 2 * n:
        pygame.draw.rect(surf, color, r)
        return
    pygame.draw.rect(surf, color, (r.x + n, r.y, r.w - 2 * n, r.h))
    pygame.draw.rect(surf, color, (r.x, r.y + n, r.w, r.h - 2 * n))


def draw_panel(surf, rect, color=C_PANEL, border=C_OUTLINE, shadow: bool = True, hi: bool = True) -> None:
    r = pygame.Rect(rect)
    if shadow:
        notched_rect(surf, (12, 8, 16), r.move(0, 5))
    notched_rect(surf, border, r)
    inner = r.inflate(-6, -6)
    notched_rect(surf, color, inner)
    if hi and inner.w > 12:
        # světlo shora: světlá horní hrana + světlý levý okraj, tmavá spodní hrana
        light = mul_color(color, 1.25)
        pygame.draw.rect(surf, light, (inner.x + NOTCH, inner.y, inner.w - 2 * NOTCH, 3))
        pygame.draw.rect(surf, mul_color(color, 1.1), (inner.x, inner.y + NOTCH, 3, inner.h - 2 * NOTCH - 3))
        pygame.draw.rect(surf, mul_color(color, 0.75), (inner.x + NOTCH, inner.bottom - 3, inner.w - 2 * NOTCH, 3))


def draw_bar(surf, rect, ratio: float, color, back=(30, 22, 36), border=C_OUTLINE, ghost: float | None = None) -> None:
    """Pruh s rámečkem, leskem a volitelnou „ghost“ stopou (světlý zbytek po ztrátě, který pomalu dobíhá)."""
    r = pygame.Rect(rect)
    notched_rect(surf, border, r.inflate(4, 4), 2)
    pygame.draw.rect(surf, back, r)
    pygame.draw.rect(surf, mul_color(back, 0.7), (r.x, r.y, r.w, max(1, r.h // 4)))
    ratio = max(0.0, min(1.0, ratio))
    if ghost is not None and ghost > ratio:
        gw = int(r.w * min(1.0, ghost))
        pygame.draw.rect(surf, (255, 240, 220), (r.x, r.y, gw, r.h))
    if ratio > 0:
        fill = r.copy()
        fill.w = int(r.w * ratio)
        pygame.draw.rect(surf, color, fill)
        pygame.draw.rect(surf, mul_color(color, 1.3), (fill.x, fill.y, fill.w, max(1, r.h // 4)))
        if r.h >= 8:
            pygame.draw.rect(surf, mul_color(color, 0.72), (fill.x, fill.bottom - max(1, r.h // 5), fill.w,
                                                           max(1, r.h // 5)))


class Ghost:
    """Stav pro ghost stopu pruhu: drží se chvíli na staré hodnotě, pak plynule dobíhá."""
    __slots__ = ("v", "hold")

    def __init__(self, v: float = 1.0) -> None:
        self.v = v
        self.hold = 0.0

    def update(self, target: float, dt: float) -> float:
        if target >= self.v:
            self.v = target
            self.hold = 0.0
        else:
            if self.hold <= 0 and self.v - target > 0.002:
                self.hold = 0.35
            self.hold -= dt
            if self.hold <= 0:
                self.v = max(target, self.v - dt * 0.6)
        return self.v


# Výplně dost tmavé pro bílý text (kontrast ≥ 3:1 podle WCAG), text navíc s tmavým obrysem.
# Oranžová „primary“ je vyhrazená pro hlavní akce; vybraná možnost se značí rámečkem (Button.selected).
STYLES = {
    "primary": (204, 108, 24),
    "secondary": (78, 58, 86),
    "green": (52, 132, 48),
    "danger": (184, 50, 50),
    "blue": (52, 106, 188),
    "gold": (164, 118, 20),
    "dark": (44, 32, 50),
}
SELECT_COLOR = (255, 214, 70)
MARGIN = 16          # jednotný okraj obrazovek (B-44)
TITLE_SCALE = 5


def draw_frame(surf, rect, color, width: int = 3, grow: int = 6) -> None:
    """Rámeček zvýraznění kolem prvku – kreslí se AŽ PO panelu (jinak ho přepíše jeho stín)."""
    g = grow + (grow & 1)            # sudé nafouknutí → rámeček souměrně
    pygame.draw.rect(surf, color, pygame.Rect(rect).inflate(g, g), width)


class Button:
    def __init__(self, rect, text: str = "", on_click=None, icon: str | None = None, style: str = "secondary",
                 enabled: bool = True, scale: int = 2, sub: str = "", icon_scale: int = 3, sound: str = "click",
                 key=None) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.icon = icon
        self.style = style
        self.enabled = enabled
        self.scale = scale
        self.sub = sub
        self.icon_scale = icon_scale
        self.pressed = False
        self.hover = False
        self.visible = True
        self.sound = sound
        self.key = key
        self.pulse = False
        self.badge = ""
        self.color = None
        self.selected = False          # zvolená možnost (rámeček + fajfka), ne akce
        self.sel_color = SELECT_COLOR

    def contains(self, x: float, y: float) -> bool:
        return self.visible and self.rect.collidepoint(x, y)

    def click(self) -> None:
        if self.enabled and self.on_click:
            if assets.audio:
                assets.audio.play(self.sound)
            self.on_click()

    def draw(self, surf, t: float = 0.0) -> None:
        if not self.visible:
            return
        font = assets.font
        base = self.color or STYLES.get(self.style, STYLES["secondary"])
        if not self.enabled:
            base = (70, 62, 74)
        elif self.hover:
            base = mul_color(base, 1.12)
        r = self.rect.copy()
        if self.pressed:
            r.y += 3
        draw_panel(surf, r, base, shadow=not self.pressed)
        if self.style == "primary" and self.enabled and not self.pressed:
            _shine(surf, r, base, t + (self.rect.x + self.rect.y) * 0.003)
        # zvýraznění až nad panelem (B-29: stín panelu dřív mazal spodní hranu)
        if self.selected:
            draw_frame(surf, r, self.sel_color, 3, 6)
            if r.w >= 130:                      # fajfka jen tam, kde nepřekryje text
                ck = assets.icons.get("check", 2)
                surf.blit(ck, (r.right - ck.get_width() - 6, r.y + 6))
        if self.pulse and self.enabled:
            k = 0.5 + 0.5 * math.sin(t * 6)
            draw_frame(surf, r, (255, 230, 140), 3, 6 + 2 * int(k * 2))
        tc = C_TEXT if self.enabled else (150, 140, 150)
        cx = r.centerx
        content_w = font.width(self.text, self.scale) if self.text else 0
        icon_img = None
        if self.icon:
            icon_img = assets.icons.get(self.icon, self.icon_scale, gray=not self.enabled)
            content_w += icon_img.get_width() + (8 if self.text else 0)
        x = cx - content_w // 2
        cy = r.centery - (11 if self.sub else 0)
        if icon_img is not None:
            surf.blit(icon_img, (x, cy - icon_img.get_height() // 2))
            x += icon_img.get_width() + 8
        if self.text:
            font.draw(surf, self.text, (x, cy), tc, self.scale, "midleft", outline=C_OUTLINE)
        if self.sub:
            # podtitul čitelně (měřítko 2), menší jen když se opravdu nevejde
            ss = 2 if font.width(self.sub, 2) <= r.w - 14 else 1
            font.draw(surf, self.sub, (cx, r.bottom - 6), (240, 232, 214) if self.enabled else (150, 140, 150), ss,
                      "midbottom", outline=C_OUTLINE)
        if self.badge:
            bw = font.width(self.badge, 1) + 10
            br = pygame.Rect(r.right - bw - 2, r.y - 8, bw, 16)
            pygame.draw.rect(surf, (220, 50, 50), br)
            font.draw(surf, self.badge, br.center, (255, 255, 255), 1, "center", shadow=False)


def _shine(surf, r: pygame.Rect, base, t: float) -> None:
    """Šikmý lesk, který jednou za ~4 s přejede přes hlavní tlačítko (jemný „živý“ pohyb menu)."""
    period, dur = 4.0, 0.7
    ph = t % period
    if ph > dur:
        return
    inner = r.inflate(-12, -12)
    k = ph / dur
    x = inner.x - 40 + (inner.w + 80) * k
    old = surf.get_clip()
    surf.set_clip(inner.clip(old) if old else inner)
    col = mul_color(base, 1.28)
    for off, w in ((0, 15), (24, 6)):
        xx = x + off
        pygame.draw.polygon(surf, col, [(xx, inner.bottom), (xx + w, inner.bottom), (xx + w + 24, inner.y),
                                        (xx + 24, inner.y)])
    surf.set_clip(old)


class ScrollArea:
    """Svislý posuvný obsah (táhnutí prstem / kolečko)."""

    def __init__(self, rect, content_h: int = 0) -> None:
        self.rect = pygame.Rect(rect)
        self.content_h = content_h
        self.offset = 0.0
        self.vel = 0.0
        self.drag = None
        self.moved = 0.0

    @property
    def max_off(self) -> float:
        return max(0.0, self.content_h - self.rect.h)

    def down(self, x, y) -> bool:
        if self.rect.collidepoint(x, y):
            self.drag = y
            self.moved = 0.0
            self.vel = 0.0
            return True
        return False

    def move(self, x, y) -> None:
        if self.drag is not None:
            dy = y - self.drag
            self.drag = y
            self.offset = max(0.0, min(self.max_off, self.offset - dy))
            self.moved += abs(dy)
            self.vel = -dy * 30

    def up(self) -> bool:
        """Vrací True, pokud šlo o klepnutí (ne táhnutí)."""
        was = self.drag is not None and self.moved < 10
        self.drag = None
        return was

    def wheel(self, dy: float) -> None:
        self.offset = max(0.0, min(self.max_off, self.offset - dy * 50))

    def update(self, dt: float) -> None:
        if self.drag is None and abs(self.vel) > 5:
            self.offset = max(0.0, min(self.max_off, self.offset + self.vel * dt))
            self.vel *= math.exp(-dt * 5)

    def draw_scrollbar(self, surf) -> None:
        if self.max_off <= 0:
            return
        r = self.rect
        h = max(30, r.h * r.h / self.content_h)
        y = r.y + (r.h - h) * (self.offset / self.max_off)
        pygame.draw.rect(surf, (255, 255, 255, 60), (r.right - 6, y, 4, h))


def draw_icon_frame(surf, rect, icon: str, evo: bool = False, gray: bool = False, scale: int = 3,
                    color=(60, 46, 66), border=C_OUTLINE) -> None:
    r = pygame.Rect(rect)
    notched_rect(surf, border, r, 2)
    notched_rect(surf, (255, 200, 60) if evo else color, r.inflate(-4, -4), 2)
    pygame.draw.rect(surf, color, r.inflate(-8, -8))
    pygame.draw.rect(surf, mul_color(color, 0.78), (r.x + 4, r.y + 4, r.w - 8, 3))
    img = assets.icons.get(icon, scale, evo=evo, gray=gray)
    surf.blit(img, img.get_rect(center=r.center))


def currency_row(surf, x: int, y: int, save, scale: int = 2, anchor_right: bool = False,
                 center: bool = False) -> None:
    font = assets.font
    items = [("cur_egg", save["eggs"]), ("cur_gold", save["gold"]), ("cur_token", save["tokens"])]
    from ..util import fmt_num
    widths = []
    for icon, val in items:
        widths.append(assets.icons.get(icon, 3).get_width() + 6 + font.width(fmt_num(val), scale) + 14)
    total = sum(widths) - 14
    cx = x - total // 2 if center else (x - total if anchor_right else x)
    for (icon, val), w in zip(items, widths):
        img = assets.icons.get(icon, 3)
        surf.blit(img, (cx, y - img.get_height() // 2))
        font.draw(surf, fmt_num(val), (cx + img.get_width() + 6, y), C_TEXT, scale, "midleft")
        cx += w


def draw_title_bar(surf, title: str, y: int = 18) -> None:
    """Nadpis obrazovky – stejná velikost na všech obrazovkách (B-44)."""
    from ..config import W
    font = assets.font
    sc = TITLE_SCALE if font.width(title, TITLE_SCALE) <= W - 2 * (MARGIN + 72) else 4
    font.draw(surf, title, (W // 2, y), (255, 230, 150), sc, "midtop", outline=C_OUTLINE)


__all__ = ["Button", "Ghost", "ScrollArea", "draw_panel", "draw_bar", "notched_rect", "draw_icon_frame", "currency_row", "draw_title_bar",
           "C_PANEL_HI"]
