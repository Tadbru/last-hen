"""HUD během runu: XP bar, časovač do svítání, zabití, mince, zbraně, boss bar, kokrhání, joystick, bannery."""
from __future__ import annotations

import math

import pygame

from .. import assets
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, W
from ..data.passives import PASSIVES
from ..util import clamp, fmt_num, fmt_time
from .widgets import draw_bar

CROW_POS = (W - 74, H - 84)
CROW_R = 50
PAUSE_RECT = pygame.Rect(W - 70, 22, 62, 58)


def draw_hud(surf, run, joy, t: float, debug: dict | None = None) -> None:
    font = assets.font
    icons = assets.icons
    # XP bar
    ratio = run.xp / run.xp_next if run.xp_next else 0
    draw_bar(surf, (4, 4, W - 8, 12), ratio, (80, 200, 255), back=(20, 30, 50))
    font.draw(surf, f"Úr. {run.level}", (8, 22), C_TEXT, 2, "topleft", outline=C_OUTLINE)
    # časovač
    if run.final_boss is not None:
        font.draw(surf, "BOSS!", (W // 2, 22), (255, 90, 80), 4, "midtop", outline=C_OUTLINE)
    elif run.cfg.mode == "bossrush":
        font.draw(surf, fmt_time(run.time), (W // 2, 22), C_TEXT, 4, "midtop", outline=C_OUTLINE)
    else:
        remain = max(0.0, run.final_time - run.time)
        col = C_TEXT if remain > 20 else (255, 200, 90)
        font.draw(surf, fmt_time(remain), (W // 2, 22), col, 4, "midtop", outline=C_OUTLINE)
        # slunce – postup k úsvitu
        k = clamp(run.time / max(1, run.final_time), 0, 1)
        bx, bw = W // 2 - 70, 140
        pygame.draw.rect(surf, (30, 20, 40), (bx, 66, bw, 6))
        pygame.draw.rect(surf, (255, 170, 60), (bx, 66, int(bw * k), 6))
        sx = bx + int(bw * k)
        pygame.draw.circle(surf, (255, 220, 90), (sx, 69), 6)
        pygame.draw.circle(surf, C_OUTLINE, (sx, 69), 6, 1)
    # zabití a mince
    sk = icons.get("skull", 2)
    kx = W - 82
    font.draw(surf, fmt_num(run.kills), (kx, 30), C_TEXT, 2, "topright", outline=C_OUTLINE)
    surf.blit(sk, (kx - font.width(fmt_num(run.kills), 2) - sk.get_width() - 8, 30))
    ci = icons.get("coin", 2)
    surf.blit(ci, (8, 52))
    font.draw(surf, str(run.coins), (8 + ci.get_width() + 4, 50), C_GOLD, 2, "topleft", outline=C_OUTLINE)
    # pauza
    pr = PAUSE_RECT
    pygame.draw.rect(surf, (20, 12, 24), pr.move(0, 3))
    pygame.draw.rect(surf, (60, 44, 68), pr)
    pygame.draw.rect(surf, C_OUTLINE, pr, 3)
    pi = icons.get("pause", 4)
    surf.blit(pi, pi.get_rect(center=pr.center))
    # zbraně a pasivky
    x0, y0 = 8, 82
    for i, w in enumerate(run.weapons):
        _slot(surf, x0 + i * 38, y0, w.d.icon, w.level, w.evolved)
    for i, (pid, lv) in enumerate(run.passives.items()):
        _slot(surf, x0 + i * 38, y0 + 40, PASSIVES[pid].icon, lv, False, maxlv=5)
    # boss bar
    yb = 182
    for ctrl in run.bosses:
        e = ctrl.e
        if not e.alive:
            continue
        bw = W - 60
        draw_bar(surf, (30, yb, bw, 14), e.hp / e.max_hp, (220, 50, 60), back=(50, 20, 30))
        if ctrl.enraged:
            pygame.draw.rect(surf, (255, 80, 60), (28, yb - 2, bw + 4, 18), 2)
        font.draw(surf, ctrl.name, (W // 2, yb - 4), (255, 220, 200), 2, "midbottom", outline=C_OUTLINE)
        if getattr(ctrl, "phase", 0):
            font.draw(surf, f"Fáze {ctrl.phase}/3", (W - 32, yb + 18), (255, 200, 180), 2, "topright", outline=C_OUTLINE)
        yb += 42
    # bannery
    by = H * 0.3
    for text, col, life, maxl in run.banners[-3:]:
        k = 1 - life / maxl
        sc = 4 if len(text) < 16 else 3
        a = 255 if life > 0.3 else int(255 * life / 0.3)
        pop = 1.0 + max(0.0, 0.25 - k) * 2
        font.draw(surf, text, (W // 2, by - (pop - 1) * 20), col, sc, "center", outline=C_OUTLINE, alpha=a)
        by += 46
    # ukazatele bossů mimo obrazovku
    _boss_arrows(surf, run, t)
    # kokrhání
    _crow_button(surf, run, t)
    # joystick
    if joy.alpha > 0.02:
        a = int(joy.alpha * 90)
        base = pygame.Surface((joy.RADIUS * 2 + 8, joy.RADIUS * 2 + 8), pygame.SRCALPHA)
        c = joy.RADIUS + 4
        pygame.draw.circle(base, (255, 255, 255, a), (c, c), joy.RADIUS, 3)
        pygame.draw.circle(base, (255, 255, 255, a // 3), (c, c), joy.RADIUS)
        surf.blit(base, (joy.ox - c, joy.oy - c))
        kx = joy.ox + joy.vx * joy.RADIUS
        ky = joy.oy + joy.vy * joy.RADIUS
        knob = pygame.Surface((56, 56), pygame.SRCALPHA)
        pygame.draw.circle(knob, (255, 255, 255, int(joy.alpha * 170)), (28, 28), 24)
        pygame.draw.circle(knob, (40, 30, 50, int(joy.alpha * 170)), (28, 28), 24, 3)
        surf.blit(knob, (kx - 28, ky - 28))
    if debug:
        y = 210
        for k, v in debug.items():
            font.draw(surf, f"{k}: {v}", (8, y), (180, 255, 180), 1, "topleft", outline=C_OUTLINE)
            y += 14


def _boss_arrows(surf, run, t: float) -> None:
    cam = run.camera
    for ctrl in run.bosses:
        e = ctrl.e
        if not e.alive or e.alpha < 128:
            continue
        sx, sy = e.x - cam.ox, e.y - cam.oy - 20
        if -10 < sx < W + 10 and -10 < sy < H + 10:
            continue
        cx, cy = W / 2, H / 2
        dx, dy = sx - cx, sy - cy
        m = 34
        k = min((W / 2 - m) / abs(dx) if dx else 1e9, (H / 2 - m - 60) / abs(dy) if dy else 1e9)
        ax, ay = cx + dx * k, cy + dy * k
        ang = math.atan2(dy, dx)
        pulse = 4 + 3 * math.sin(t * 8)
        tip = (ax + math.cos(ang) * (18 + pulse), ay + math.sin(ang) * (18 + pulse))
        l = (ax + math.cos(ang + 2.5) * 16, ay + math.sin(ang + 2.5) * 16)
        r = (ax + math.cos(ang - 2.5) * 16, ay + math.sin(ang - 2.5) * 16)
        pygame.draw.polygon(surf, C_OUTLINE, [tip, l, r])
        pygame.draw.polygon(surf, (255, 70, 60), [tip, l, r], 0)
        pygame.draw.polygon(surf, C_OUTLINE, [tip, l, r], 2)
        sk = assets.icons.get("skull", 3)
        surf.blit(sk, sk.get_rect(center=(ax - math.cos(ang) * 12, ay - math.sin(ang) * 12)))


def _slot(surf, x, y, icon, lv, evo, maxlv=8) -> None:
    pygame.draw.rect(surf, C_OUTLINE, (x, y, 36, 36))
    pygame.draw.rect(surf, (255, 200, 60) if evo else (60, 46, 66), (x + 2, y + 2, 32, 32))
    img = assets.icons.get(icon, 2, evo=False)
    surf.blit(img, img.get_rect(center=(x + 15, y + 15)))
    if not evo:
        assets.font.draw(surf, str(lv), (x + 37, y + 39), (255, 255, 255), 2, "bottomright", outline=C_OUTLINE)


def _crow_button(surf, run, t: float) -> None:
    cx, cy = CROW_POS
    r = CROW_R
    ready = run.crow_ready
    pygame.draw.circle(surf, (14, 8, 18), (cx, cy + 5), r + 3)
    col = (234, 150, 40) if ready else (70, 52, 76)
    if ready:
        k = 0.5 + 0.5 * math.sin(t * 7)
        pygame.draw.circle(surf, (255, 230, 120), (cx, cy), int(r + 6 + 4 * k), 3)
    pygame.draw.circle(surf, C_OUTLINE, (cx, cy), r + 3)
    pygame.draw.circle(surf, col, (cx, cy), r)
    # nabití
    ch = run.crow_charge
    if ch > 0 and not ready:
        rect = pygame.Rect(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2)
        pygame.draw.arc(surf, (255, 200, 80), rect, math.pi / 2, math.pi / 2 + math.tau * ch, 6)
    icon = assets.icons.get("crow", 5 if ready else 4, gray=not ready)
    surf.blit(icon, icon.get_rect(center=(cx, cy - 2)))
    if ready:
        assets.font.draw(surf, "KOKRHEJ!", (cx, cy + r + 2), (255, 230, 120), 2, "midtop", outline=C_OUTLINE)


def crow_hit(x: float, y: float) -> bool:
    return (x - CROW_POS[0]) ** 2 + (y - CROW_POS[1]) ** 2 <= (CROW_R + 10) ** 2
