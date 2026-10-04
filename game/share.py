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
# po prohře – vítězné hlášky („Kurník je zase v bezpečí.“) by tam lhaly (B-78)
FUNNY_LOSS = [
    "Lišky slaví. Zatím.", "Příště to vyjde!", "Kurník čeká na odplatu.", "Slepice se nevzdává.",
    "Babička už chystá obvazy.", "Odveta bude za svítání.",
]
# nový rekord Nekonečné noci – dřív sdílení po rekordu hlásilo „PADLA JSEM…“ s vtipem o prohře (B-85)
FUNNY_RECORD = [
    "Noc nekončí. Slepice taky ne.", "Slunce nevyšlo, rekord ano.", "Lišky už nevědí, co s ní.",
    "Kohout zírá s otevřeným zobákem.",
]


def share_text(run) -> str:
    f = run.char.female
    verb1 = "Přežila jsem" if f else "Přežil jsem"
    verb2 = "zabila" if f else "zabil"
    k = run.kills
    where = " v Nekonečné noci" if getattr(run, "endless", False) else ""
    return f"{verb1} {fmt_time(run.time)}{where} a {verb2} {fmt_num(k)} {plural(k, 'lišku', 'lišky', 'lišek')}!"


def make_share_image(run, victory: bool, record: bool = False) -> str:
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
    if victory:
        head, hcol, jokes = "VÍTĚZSTVÍ!", (255, 240, 200), FUNNY
    elif record:
        head, hcol, jokes = "NOVÝ REKORD!", (255, 214, 70), FUNNY_RECORD
    else:
        head, hcol, jokes = ("PADLA JSEM…" if run.char.female else "PADL JSEM…"), (255, 140, 140), FUNNY_LOSS
    font.draw(s, head, (W // 2, 110), hcol, 4, "midtop", outline=C_OUTLINE)
    lines = font.wrap(share_text(run), W - 60, 3)
    y = 280
    for ln in lines:
        font.draw(s, ln, (W // 2, y), (255, 255, 255), 3, "midtop", outline=C_OUTLINE)
        y += 38
    import random
    font.draw(s, random.choice(jokes), (W // 2, y + 4), (255, 230, 160), 2, "midtop", outline=C_OUTLINE)
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
