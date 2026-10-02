"""Kamera: plynulé sledování, trauma screen-shake a „kick“ (simulace vibrace)."""
from __future__ import annotations

import math
import random

from ..config import W, H


class Camera:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.trauma = 0.0
        self.kick_x = 0.0
        self.kick_y = 0.0
        self.ox = 0.0       # levý horní roh (svět) po započtení shake
        self.oy = 0.0
        self.shake_on = True
        self._t = 0.0
        self.zoom_punch = 0.0
        self.haptics = False      # zapíná GameScene (headless simulace nevibrují)

    def snap(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self._apply(0, 0)

    def follow(self, tx: float, ty: float, dt: float, lead_x: float = 0.0, lead_y: float = 0.0) -> None:
        k = min(1.0, dt * 7.0)
        self.x += (tx + lead_x - self.x) * k
        self.y += (ty + lead_y - self.y) * k

    def shake(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def kick(self, dx: float, dy: float, power: float = 10.0) -> None:
        d = math.hypot(dx, dy) or 1.0
        self.kick_x += dx / d * power
        self.kick_y += dy / d * power

    def vibrate(self, power: float = 8.0) -> None:
        """Krátké trhnutí kamerou + haptika telefonu (Android)."""
        if self.haptics:
            from ..device import vibrate
            vibrate(int(10 + power * 2.5))
        a = random.uniform(0, math.tau)
        self.kick(math.cos(a), math.sin(a), power)
        self.shake(0.25)

    def update(self, dt: float) -> None:
        self._t += dt
        self.trauma = max(0.0, self.trauma - dt * 1.6)
        decay = math.exp(-dt * 14)
        self.kick_x *= decay
        self.kick_y *= decay
        sx = sy = 0.0
        if self.shake_on and self.trauma > 0:
            s = self.trauma * self.trauma * 14
            sx = (random.random() * 2 - 1) * s
            sy = (random.random() * 2 - 1) * s
        kx, ky = (self.kick_x, self.kick_y) if self.shake_on else (0.0, 0.0)
        self._apply(sx + kx, sy + ky)

    def _apply(self, sx: float, sy: float) -> None:
        self.ox = self.x - W / 2 + sx
        self.oy = self.y - H / 2 + sy

    def on_screen(self, x: float, y: float, margin: float = 64) -> bool:
        return (self.ox - margin < x < self.ox + W + margin) and (self.oy - margin < y < self.oy + H + margin)
