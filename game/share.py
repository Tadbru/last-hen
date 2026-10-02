"""Sdílení výsledku – vygeneruje PNG kartičku do složky shares/."""
from __future__ import annotations

import os
import time

import pygame

from . import assets
from .config import C_OUTLINE, SHARES_DIR
from .gfx import pixelart as pa
from .util import fmt_num, fmt_time, plural

FUNNY = [
    "Lišky jsou v šoku.", "Farmář by byl hrdý.", "Kurník je zase v bezpečí.", "Omeleta z lišek se podává.",
    "Kokrhání se neslo až do vesnice.", "Babička peče oslavný koláč.",
]


def share_text(run) -> str:
    f = run.char.female
    verb1 = "Přežila jsem" if f else "Přežil jsem"
    verb2 = "zabila" if f else "zabil"
    k = run.kills
    return f"{verb1} {fmt_time(run.time)} a {verb2} {fmt_num(k)} {plural(k, 'lišku', 'lišky', 'lišek')}!"


def make_share_image(run, victory: bool) -> str:
    os.makedirs(SHARES_DIR, exist_ok=True)
    font = assets.font
    W, H = 540, 540
    s = pygame.Surface((W, H))
    b = run.biome
    s.fill(b.ground)
    for i in range(0, W, 24):
        pygame.draw.line(s, b.ground2, (i, 0), (i - 200, H), 6)
    pygame.draw.rect(s, (30, 20, 34), (0, 0, W, 90))
    font.draw(s, "LAST CHICKEN", (W // 2, 18), (255, 214, 70), 5, "midtop", outline=C_OUTLINE)
    # postava
    img = assets.sprites.players[run.char.id].frames[0][0]
    big = pa.scale(img, 2)
    s.blit(pa.make_shadow(big.get_width(), 24, 90), (W // 2 - big.get_width() // 2, 248))
    s.blit(big, big.get_rect(midbottom=(W // 2, 262)))
    head = "VÍTĚZSTVÍ!" if victory else "PADLA JSEM…" if run.char.female else "PADL JSEM…"
    font.draw(s, head, (W // 2, 110), (255, 240, 200) if victory else (255, 140, 140), 4, "midtop", outline=C_OUTLINE)
    lines = font.wrap(share_text(run), W - 60, 3)
    y = 280
    for ln in lines:
        font.draw(s, ln, (W // 2, y), (255, 255, 255), 3, "midtop", outline=C_OUTLINE)
        y += 38
    import random
    font.draw(s, random.choice(FUNNY), (W // 2, y + 4), (255, 230, 160), 2, "midtop", outline=C_OUTLINE)
    # build
    x = W // 2 - len(run.weapons) * 30
    for w in run.weapons:
        ic = assets.icons.get(w.d.icon, 4, evo=w.evolved)
        s.blit(ic, ic.get_rect(center=(x + 30, H - 70)))
        x += 60
    font.draw(s, f"{run.char.name} · {b.name} · Úroveň {run.level}", (W // 2, H - 26), (230, 230, 230), 2, "midtop",
              outline=C_OUTLINE)
    pygame.draw.rect(s, C_OUTLINE, s.get_rect(), 6)
    name = time.strftime("lastchicken_%Y%m%d_%H%M%S.png")
    path = os.path.join(SHARES_DIR, name)
    pygame.image.save(s, path)
    return path
