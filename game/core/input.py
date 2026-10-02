"""Ovládání: plovoucí virtuální joystick (dotyk / myš) + klávesnice."""
from __future__ import annotations

import math

import pygame

from ..config import H


class Joystick:
    RADIUS = 64
    DEAD = 0.14

    def __init__(self) -> None:
        self.active = False
        self.ox = self.oy = 0.0
        self.px = self.py = 0.0
        self.vx = self.vy = 0.0
        self.alpha = 0.0     # pro jemné zobrazení/skrytí

    def allowed_start(self, x: float, y: float) -> bool:
        """Joystick se objeví jen ve spodních ~2/3 obrazovky."""
        return y > H / 3

    def press(self, x: float, y: float) -> None:
        self.active = True
        self.ox, self.oy = x, y
        self.px, self.py = x, y
        self.vx = self.vy = 0.0

    def move(self, x: float, y: float) -> None:
        if not self.active:
            return
        dx, dy = x - self.ox, y - self.oy
        d = math.hypot(dx, dy)
        r = self.RADIUS
        if d > r:
            # plovoucí: základna se táhne za prstem
            k = (d - r) / d
            self.ox += dx * k
            self.oy += dy * k
            dx, dy = x - self.ox, y - self.oy
            d = r
        self.px, self.py = x, y
        m = d / r
        if m < self.DEAD:
            self.vx = self.vy = 0.0
        else:
            mm = (m - self.DEAD) / (1 - self.DEAD)
            self.vx = dx / (d or 1) * mm
            self.vy = dy / (d or 1) * mm

    def release(self) -> None:
        self.active = False
        self.vx = self.vy = 0.0

    def update(self, dt: float) -> None:
        target = 1.0 if self.active else 0.0
        self.alpha += (target - self.alpha) * min(1.0, dt * 12)


KEYS_LEFT = (pygame.K_a, pygame.K_LEFT)
KEYS_RIGHT = (pygame.K_d, pygame.K_RIGHT)
KEYS_UP = (pygame.K_w, pygame.K_UP)
KEYS_DOWN = (pygame.K_s, pygame.K_DOWN)


def keyboard_vector() -> tuple[float, float]:
    try:
        k = pygame.key.get_pressed()
    except pygame.error:
        return 0.0, 0.0
    x = (any(k[c] for c in KEYS_RIGHT)) - (any(k[c] for c in KEYS_LEFT))
    y = (any(k[c] for c in KEYS_DOWN)) - (any(k[c] for c in KEYS_UP))
    if x and y:
        return x * 0.7071, y * 0.7071
    return float(x), float(y)
