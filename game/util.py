"""Drobné pomocné funkce: matematika, tweening, formátování."""
from __future__ import annotations

import math
import random

TAU = math.tau


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def approach(v: float, target: float, step: float) -> float:
    if v < target:
        return min(v + step, target)
    return max(v - step, target)


def norm(dx: float, dy: float) -> tuple[float, float]:
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return 0.0, 0.0
    return dx / d, dy / d


def dist2(ax: float, ay: float, bx: float, by: float) -> float:
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def angle_to(ax: float, ay: float, bx: float, by: float) -> float:
    return math.atan2(by - ay, bx - ax)


def lerp_color(a, b, t: float):
    t = clamp(t, 0.0, 1.0)
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def mul_color(c, f: float):
    return (int(clamp(c[0] * f, 0, 255)), int(clamp(c[1] * f, 0, 255)), int(clamp(c[2] * f, 0, 255)))


# --- easing -----------------------------------------------------------------

def ease_out_cubic(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_out_back(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ease_out_elastic(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (TAU / 3)) + 1


# --- formátování -------------------------------------------------------------

def fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"


def fmt_num(n: int | float) -> str:
    """1284 -> '1 284' (česká mezera tisíců)."""
    s = f"{int(n):,}"
    return s.replace(",", " ")


def plural(n: int, one: str, few: str, many: str) -> str:
    """Česká množná čísla: 1 liška, 2 lišky, 5 lišek."""
    n = abs(int(n))
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def weighted_choice(rng: random.Random, items, weights):
    total = sum(weights)
    if total <= 0:
        return rng.choice(items)
    r = rng.random() * total
    acc = 0.0
    for it, w in zip(items, weights):
        acc += w
        if r <= acc:
            return it
    return items[-1]


class Tween:
    """Jednoduchý časový tween 0→1."""
    __slots__ = ("t", "dur", "ease")

    def __init__(self, dur: float, ease=ease_out_cubic):
        self.t = 0.0
        self.dur = max(1e-6, dur)
        self.ease = ease

    def update(self, dt: float) -> None:
        self.t = min(self.dur, self.t + dt)

    @property
    def done(self) -> bool:
        return self.t >= self.dur

    @property
    def value(self) -> float:
        return self.ease(self.t / self.dur)
