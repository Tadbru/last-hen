"""Základ scén, modální dialogy (vč. falešné reklamy) a jednoduché události vstupu."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_OUTLINE, C_TEXT, H, W
from ..ui.widgets import Button, draw_panel


class Ev:
    """Událost v logických souřadnicích: down / up / move / key / wheel."""
    __slots__ = ("type", "x", "y", "key", "dy")

    def __init__(self, type_: str, x: float = 0.0, y: float = 0.0, key: int = 0, dy: float = 0.0) -> None:
        self.type = type_
        self.x, self.y = x, y
        self.key = key
        self.dy = dy


class Dialog:
    """Modální okno s tlačítky. timer > 0 → odpočet (falešná reklama), pak se zavolá on_done."""

    def __init__(self, title: str, text: str, buttons: list[tuple] | None = None, timer: float = 0.0,
                 on_done=None, ad: bool = False, icon: str | None = None) -> None:
        self.title = title
        self.text = text
        self.timer = timer
        self.on_done = on_done
        self.ad = ad
        self.icon = icon
        self.t = 0.0
        self.closed = False
        self.buttons: list[Button] = []
        self.rect = pygame.Rect(40, H // 2 - 220, W - 80, 440)
        bs = buttons or []
        n = len(bs)
        bw = (self.rect.w - 40 - (n - 1) * 12) // max(1, n)
        for i, b in enumerate(bs):
            label, cb = b[0], b[1]
            style = b[2] if len(b) > 2 else "secondary"

            def make(cb=cb):
                def f():
                    self.closed = True
                    if cb:
                        cb()
                return f
            self.buttons.append(Button((self.rect.x + 20 + i * (bw + 12), self.rect.bottom - 90, bw, 70), label,
                                       make(), style=style))
        self._pressed = None

    def handle(self, ev: Ev) -> None:
        if self.timer > 0:
            return
        if ev.type == "down":
            for b in self.buttons:
                if b.contains(ev.x, ev.y) and b.enabled:
                    b.pressed = True
                    self._pressed = b
        elif ev.type == "up":
            b = self._pressed
            self._pressed = None
            if b is not None:
                b.pressed = False
                if b.contains(ev.x, ev.y):
                    b.click()
        elif ev.type == "key" and ev.key in (pygame.K_RETURN, pygame.K_SPACE) and self.buttons:
            self.buttons[0].click()
        elif ev.type == "key" and ev.key == pygame.K_ESCAPE and self.buttons:
            self.buttons[-1].click()

    def update(self, dt: float) -> None:
        self.t += dt
        if self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.closed = True
                if self.on_done:
                    self.on_done()

    def draw(self, surf) -> None:
        font = assets.font
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((10, 6, 14, 170))
        surf.blit(dim, (0, 0))
        k = min(1.0, self.t * 6)
        r = self.rect.inflate(-(1 - k) * 60, -(1 - k) * 60)
        if self.ad:
            draw_panel(surf, r, (250, 236, 200))
            font.draw(surf, "REKLAMA", (r.right - 14, r.y + 12), (160, 120, 80), 1, "topright", shadow=False)
            font.draw(surf, self.title, (r.centerx, r.y + 40), (120, 60, 20), 3, "midtop", shadow=False)
            # „produkt“
            cx, cy = r.centerx, r.centery - 10
            bounce = math.sin(self.t * 8) * 6
            pygame.draw.rect(surf, (230, 190, 40), (cx - 50, cy - 60 + bounce, 100, 120))
            pygame.draw.rect(surf, (140, 90, 20), (cx - 50, cy - 60 + bounce, 100, 120), 4)
            font.draw(surf, "KUKUŘICE", (cx, cy - 10 + bounce), (120, 60, 20), 2, "center", shadow=False)
            font.draw(surf, "™", (cx + 46, cy - 50 + bounce), (120, 60, 20), 1, "center", shadow=False)
            font.draw_wrapped(surf, self.text, pygame.Rect(r.x + 30, cy + 80, r.w - 60, 80), (90, 60, 40), 2,
                              "center", shadow=False)
            font.draw(surf, f"Reklama skončí za {max(0, math.ceil(self.timer))} s", (r.centerx, r.bottom - 30),
                      (160, 110, 60), 2, "midbottom", shadow=False)
            return
        draw_panel(surf, r, (62, 46, 70))
        y = r.y + 24
        if self.icon:
            img = assets.icons.get(self.icon, 5)
            surf.blit(img, img.get_rect(midtop=(r.centerx, y)))
            y += img.get_height() + 12
        font.draw(surf, self.title, (r.centerx, y), (255, 220, 140), 3, "midtop", outline=C_OUTLINE)
        y += 46
        font.draw_wrapped(surf, self.text, pygame.Rect(r.x + 24, y, r.w - 48, r.h - 200), C_TEXT, 2, "center")
        if k >= 1:
            for b in self.buttons:
                b.draw(surf, self.t)


class Scene:
    music = "menu"

    def __init__(self, app) -> None:
        self.app = app
        self.buttons: list[Button] = []
        self.t = 0.0
        self._pressed: Button | None = None
        self.modal: Dialog | None = None
        self.toasts: list[list] = []

    @property
    def save(self):
        return self.app.save

    def enter(self) -> None:
        if self.music and assets.audio:
            assets.audio.play_music(self.music, 0.3)

    def exit(self) -> None:
        pass

    def add(self, b: Button) -> Button:
        self.buttons.append(b)
        return b

    def toast(self, text: str, color=(255, 230, 150), dur: float = 2.5) -> None:
        self.toasts.append([text, color, dur])

    # --- vstup ---------------------------------------------------------------------------------
    def handle(self, ev: Ev) -> None:
        if self.modal is not None:
            self.modal.handle(ev)
            if self.modal is not None and self.modal.closed:
                self.modal = None
            return
        if ev.type == "down":
            for b in reversed(self.buttons):
                if b.contains(ev.x, ev.y) and b.enabled:
                    b.pressed = True
                    self._pressed = b
                    return
            self.on_down(ev)
        elif ev.type == "up":
            b = self._pressed
            self._pressed = None
            if b is not None:
                b.pressed = False
                if b.contains(ev.x, ev.y):
                    b.click()
                return
            self.on_up(ev)
        elif ev.type == "move":
            for b in self.buttons:
                b.hover = b.contains(ev.x, ev.y)
            self.on_move(ev)
        elif ev.type == "key":
            for b in self.buttons:
                if b.key is not None and ev.key == b.key and b.enabled and b.visible:
                    b.click()
                    return
            self.on_key(ev.key)
        elif ev.type == "wheel":
            self.on_wheel(ev)

    def on_down(self, ev: Ev) -> None:
        pass

    def on_up(self, ev: Ev) -> None:
        pass

    def on_move(self, ev: Ev) -> None:
        pass

    def on_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.back()

    def on_wheel(self, ev: Ev) -> None:
        pass

    def back(self) -> None:
        from .menu import MenuScene
        self.app.switch(MenuScene(self.app))

    # --- update/draw --------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.t += dt
        if self.modal is not None:
            self.modal.update(dt)
            if self.modal.closed:
                self.modal = None
        for tt in self.toasts:
            tt[2] -= dt
        self.toasts = [tt for tt in self.toasts if tt[2] > 0]

    def draw(self, surf) -> None:
        pass

    def draw_buttons(self, surf) -> None:
        for b in self.buttons:
            b.draw(surf, self.t)

    def draw_overlays(self, surf) -> None:
        font = assets.font
        y = H - 150
        for text, col, life in self.toasts[-4:]:
            a = 255 if life > 0.4 else int(255 * life / 0.4)
            w = min(W - 30, font.width(text, 2) + 30)
            r = pygame.Rect(0, 0, w, 40)
            r.center = (W // 2, y)
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            s.fill((20, 12, 24, int(a * 0.85)))
            surf.blit(s, r)
            font.draw(surf, text, r.center, col, 2, "center", alpha=a)
            y -= 46
        if self.modal is not None:
            self.modal.draw(surf)


def draw_bg(surf, t: float, color=(40, 28, 48), stripes=(48, 34, 58)) -> None:
    surf.fill(color)
    off = int(t * 20) % 64
    for i in range(-2, H // 32 + 3):
        y = i * 64 + off
        pygame.draw.polygon(surf, stripes, [(0, y), (W, y - 120), (W, y - 90), (0, y + 30)])
