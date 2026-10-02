"""Pool částic (peří, jiskry, sliz, kouř) s pevným stropem – žádné alokace během hry."""
from __future__ import annotations

import math
import random

import pygame

FEATHER, SPARK, PUFF, BLOB, STAR, ZZZ = range(6)


class ParticleSystem:
    def __init__(self, cap: int = 700) -> None:
        self.cap = cap
        n = cap
        self.x = [0.0] * n
        self.y = [0.0] * n
        self.vx = [0.0] * n
        self.vy = [0.0] * n
        self.life = [0.0] * n
        self.maxl = [1.0] * n
        self.kind = [0] * n
        self.col = [(255, 255, 255)] * n
        self.size = [3] * n
        self.alive: list[int] = []
        self.free = list(range(n - 1, -1, -1))
        self.rng = random.Random(7)

    def clear(self) -> None:
        self.alive.clear()
        self.free = list(range(self.cap - 1, -1, -1))

    def emit(self, x: float, y: float, vx: float, vy: float, life: float, kind: int, col, size: int = 3) -> None:
        if not self.free:
            return
        i = self.free.pop()
        self.x[i] = x
        self.y[i] = y
        self.vx[i] = vx
        self.vy[i] = vy
        self.life[i] = life
        self.maxl[i] = life
        self.kind[i] = kind
        self.col[i] = col
        self.size[i] = size
        self.alive.append(i)

    # --- presety ---------------------------------------------------------------------
    def feathers(self, x: float, y: float, n: int, col=(250, 248, 240), speed: float = 120) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s - 40, r.uniform(0.5, 1.1), FEATHER, col, 3)

    def sparks(self, x: float, y: float, n: int, col=(255, 220, 120), speed: float = 220, life: float = 0.35) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.5, 1.0) * life, SPARK, col, 3)

    def puff(self, x: float, y: float, n: int, col=(230, 230, 230), speed: float = 50, size: int = 8) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.2, 1.0) * speed
            self.emit(x + r.uniform(-6, 6), y + r.uniform(-6, 6), math.cos(a) * s, math.sin(a) * s - 15,
                      r.uniform(0.35, 0.7), PUFF, col, size)

    def blobs(self, x: float, y: float, n: int, col=(130, 240, 80), speed: float = 140) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.3, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s - 60, r.uniform(0.3, 0.6), BLOB, col, 4)

    def stars(self, x: float, y: float, n: int, col=(255, 230, 90), speed: float = 160) -> None:
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(0.4, 1.0) * speed
            self.emit(x, y, math.cos(a) * s, math.sin(a) * s, r.uniform(0.4, 0.9), STAR, col, 3)

    # --- update/draw --------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        X, Y, VX, VY, L, K = self.x, self.y, self.vx, self.vy, self.life, self.kind
        alive = self.alive
        keep = []
        free = self.free
        drag_f = 1.0 - min(0.9, 4.0 * dt)
        drag_s = 1.0 - min(0.9, 6.0 * dt)
        for i in alive:
            l = L[i] - dt
            if l <= 0:
                free.append(i)
                continue
            L[i] = l
            k = K[i]
            if k == FEATHER:
                VX[i] *= drag_f
                VY[i] = VY[i] * drag_f + 60 * dt
                X[i] += (VX[i] + math.sin(l * 9.0) * 25) * dt
            elif k == BLOB:
                VY[i] += 420 * dt
                X[i] += VX[i] * dt
            else:
                VX[i] *= drag_s
                VY[i] *= drag_s
                X[i] += VX[i] * dt
            Y[i] += VY[i] * dt
            keep.append(i)
        self.alive = keep

    def draw(self, surf: pygame.Surface, ox: float, oy: float) -> None:
        X, Y, L, M, K, C, S = self.x, self.y, self.life, self.maxl, self.kind, self.col, self.size
        fill = surf.fill
        w, h = surf.get_size()
        for i in self.alive:
            x = int(X[i] - ox)
            y = int(Y[i] - oy)
            if x < -10 or y < -10 or x > w + 10 or y > h + 10:
                continue
            k = K[i]
            t = L[i] / M[i]
            if k == FEATHER:
                if int(L[i] * 10) & 1:
                    fill(C[i], (x - 3, y - 1, 6, 3))
                else:
                    fill(C[i], (x - 1, y - 3, 3, 6))
            elif k == SPARK:
                s = max(1, int(S[i] * t + 1))
                fill(C[i], (x, y, s, s))
            elif k == PUFF:
                s = int(S[i] * (1.4 - t * 0.6))
                fill(C[i], (x - s // 2, y - s // 2, s, s))
            elif k == BLOB:
                fill(C[i], (x - 2, y - 2, 4, 4))
            elif k == STAR:
                fill(C[i], (x - 1, y - 3, 3, 7))
                fill(C[i], (x - 3, y - 1, 7, 3))
            else:
                fill(C[i], (x, y, 3, 3))

    def __len__(self) -> int:
        return len(self.alive)
