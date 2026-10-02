"""UI prvky: pixelová tlačítka, panely, posuvné seznamy. Všechna tlačítka ≥ 64 px na výšku pro prst."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_OUTLINE, C_PANEL, C_PANEL_HI, C_TEXT
from ..util import mul_color


def draw_panel(surf, rect, color=C_PANEL, border=C_OUTLINE, shadow: bool = True, hi: bool = True) -> None:
    r = pygame.Rect(rect)
    if shadow:
        pygame.draw.rect(surf, (12, 8, 16), r.move(0, 5))
    pygame.draw.rect(surf, border, r)
    inner = r.inflate(-6, -6)
    pygame.draw.rect(surf, color, inner)
    if hi:
        pygame.draw.rect(surf, mul_color(color, 1.25), (inner.x, inner.y, inner.w, 3))
        pygame.draw.rect(surf, mul_color(color, 0.75), (inner.x, inner.bottom - 3, inner.w, 3))


def draw_bar(surf, rect, ratio: float, color, back=(30, 22, 36), border=C_OUTLINE) -> None:
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, border, r.inflate(4, 4))
    pygame.draw.rect(surf, back, r)
    if ratio > 0:
        fill = r.copy()
        fill.w = int(r.w * max(0.0, min(1.0, ratio)))
        pygame.draw.rect(surf, color, fill)
        pygame.draw.rect(surf, mul_color(color, 1.3), (fill.x, fill.y, fill.w, max(1, r.h // 4)))


STYLES = {
    "primary": (234, 150, 40),
    "secondary": (78, 58, 86),
    "green": (84, 170, 70),
    "danger": (190, 56, 56),
    "blue": (60, 120, 200),
    "gold": (210, 170, 40),
    "dark": (44, 32, 50),
}


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
        if self.pulse and self.enabled:
            k = 0.5 + 0.5 * math.sin(t * 6)
            pygame.draw.rect(surf, (255, 230, 140), r.inflate(6 + 4 * k, 6 + 4 * k), 3)
        if self.pressed:
            r.y += 3
        draw_panel(surf, r, base, shadow=not self.pressed)
        tc = C_TEXT if self.enabled else (150, 140, 150)
        cx = r.centerx
        content_w = font.width(self.text, self.scale) if self.text else 0
        icon_img = None
        if self.icon:
            icon_img = assets.icons.get(self.icon, self.icon_scale, gray=not self.enabled)
            content_w += icon_img.get_width() + (8 if self.text else 0)
        x = cx - content_w // 2
        cy = r.centery - (6 if self.sub else 0)
        if icon_img is not None:
            surf.blit(icon_img, (x, cy - icon_img.get_height() // 2))
            x += icon_img.get_width() + 8
        if self.text:
            font.draw(surf, self.text, (x, cy), tc, self.scale, "midleft")
        if self.sub:
            font.draw(surf, self.sub, (cx, r.bottom - 8), (230, 220, 200) if self.enabled else (140, 130, 140), 1,
                      "midbottom")
        if self.badge:
            bw = font.width(self.badge, 1) + 10
            br = pygame.Rect(r.right - bw - 2, r.y - 8, bw, 16)
            pygame.draw.rect(surf, (220, 50, 50), br)
            font.draw(surf, self.badge, br.center, (255, 255, 255), 1, "center", shadow=False)


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
    pygame.draw.rect(surf, border, r)
    pygame.draw.rect(surf, (255, 200, 60) if evo else color, r.inflate(-4, -4))
    pygame.draw.rect(surf, color, r.inflate(-8, -8))
    img = assets.icons.get(icon, scale, evo=evo, gray=gray)
    surf.blit(img, img.get_rect(center=r.center))


def currency_row(surf, x: int, y: int, save, scale: int = 2, anchor_right: bool = False) -> None:
    font = assets.font
    items = [("cur_egg", save["eggs"]), ("cur_gold", save["gold"]), ("cur_token", save["tokens"])]
    from ..util import fmt_num
    widths = []
    for icon, val in items:
        widths.append(assets.icons.get(icon, 3).get_width() + 6 + font.width(fmt_num(val), scale) + 14)
    total = sum(widths)
    cx = x - total if anchor_right else x
    for (icon, val), w in zip(items, widths):
        img = assets.icons.get(icon, 3)
        surf.blit(img, (cx, y - img.get_height() // 2))
        font.draw(surf, fmt_num(val), (cx + img.get_width() + 6, y), C_TEXT, scale, "midleft")
        cx += w


def draw_title_bar(surf, title: str, y: int = 18) -> None:
    from ..config import W
    font = assets.font
    font.draw(surf, title, (W // 2, y), (255, 230, 150), 4, "midtop", outline=C_OUTLINE)


__all__ = ["Button", "ScrollArea", "draw_panel", "draw_bar", "draw_icon_frame", "currency_row", "draw_title_bar",
           "C_PANEL_HI"]
