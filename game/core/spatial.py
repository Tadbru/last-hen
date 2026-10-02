"""Spatial hash grid s int klíči. Přestavuje se každý logický tick (rychlejší než aktualizace)."""
from __future__ import annotations

OFF = 1_000_000.0       # posun, aby souřadnice buněk byly vždy kladné
KMUL = 100_000          # klíč = cx * KMUL + cy


class SpatialGrid:
    __slots__ = ("cell", "inv", "cells")

    def __init__(self, cell: int = 64) -> None:
        self.cell = cell
        self.inv = 1.0 / cell
        self.cells: dict[int, list] = {}

    def clear(self) -> None:
        self.cells = {}

    def key(self, x: float, y: float) -> int:
        inv = self.inv
        return int((x + OFF) * inv) * KMUL + int((y + OFF) * inv)

    def insert(self, obj, x: float, y: float) -> int:
        inv = self.inv
        k = int((x + OFF) * inv) * KMUL + int((y + OFF) * inv)
        lst = self.cells.get(k)
        if lst is None:
            self.cells[k] = [obj]
        else:
            lst.append(obj)
        return k

    def query(self, x: float, y: float, r: float, out: list | None = None) -> list:
        """Všechny objekty v buňkách, které protíná čtverec okolo (x, y) s poloměrem r."""
        inv = self.inv
        x0 = int((x - r + OFF) * inv)
        x1 = int((x + r + OFF) * inv)
        y0 = int((y - r + OFF) * inv)
        y1 = int((y + r + OFF) * inv)
        res = out if out is not None else []
        cells = self.cells
        for cx in range(x0, x1 + 1):
            base = cx * KMUL
            for cy in range(y0, y1 + 1):
                lst = cells.get(base + cy)
                if lst:
                    res.extend(lst)
        return res

    def nearest(self, x: float, y: float, max_r: float, pred=None):
        """Nejbližší objekt (podle .x/.y) do max_r, hledá v rozšiřujících se prstencích buněk."""
        inv = self.inv
        cx0 = int((x + OFF) * inv)
        cy0 = int((y + OFF) * inv)
        best = None
        best_d = max_r * max_r
        cells = self.cells
        max_ring = int(max_r * inv) + 1
        for ring in range(0, max_ring + 1):
            # pokud jsme už našli něco blíž, než může ležet další prstenec, končíme
            if best is not None and ((ring - 1) * self.cell) ** 2 > best_d:
                break
            for cx in range(cx0 - ring, cx0 + ring + 1):
                edge_x = cx == cx0 - ring or cx == cx0 + ring
                step = 1 if edge_x else ring * 2
                if step == 0:
                    step = 1
                cy = cy0 - ring
                while cy <= cy0 + ring:
                    lst = cells.get(cx * KMUL + cy)
                    if lst:
                        for o in lst:
                            if pred is not None and not pred(o):
                                continue
                            dx = o.x - x
                            dy = o.y - y
                            d = dx * dx + dy * dy
                            if d < best_d:
                                best_d = d
                                best = o
                    cy += step
        return best
