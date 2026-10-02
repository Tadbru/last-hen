"""Overlaye herní scény: levelup karty, otevírání bedny, pauza."""
from __future__ import annotations

import math

import pygame

from .. import assets, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, RARITY_COLORS, RARITY_NAMES, W
from ..data.passives import PASSIVES
from ..data.weapons import WEAPONS
from ..util import ease_out_back, fmt_num
from .widgets import Button, draw_icon_frame, draw_panel


def _dim(surf, a: int = 170) -> None:
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    s.fill((12, 6, 18, a))
    surf.blit(s, (0, 0))


class Overlay:
    def __init__(self, scene) -> None:
        self.scene = scene
        self.run = scene.run
        self.t = 0.0
        self.buttons: list[Button] = []
        self._pressed = None
        self.done = False

    def handle(self, ev) -> None:
        if ev.type == "down":
            for b in self.buttons:
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
                if b.key is not None and b.key == ev.key and b.enabled and b.visible:
                    b.click()
                    return
            self.on_key(ev.key)

    def on_down(self, ev) -> None:
        pass

    def on_up(self, ev) -> None:
        pass

    def on_move(self, ev) -> None:
        pass

    def on_key(self, key) -> None:
        pass

    def update(self, dt: float) -> None:
        self.t += dt

    def draw(self, surf) -> None:
        for b in self.buttons:
            b.draw(surf, self.t)


# ---------------------------------------------------------------------------------------------
class LevelUpOverlay(Overlay):
    CARD_H = 176

    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.banish_mode = False
        self.offer_id = None
        self.hover = -1
        self.pressed_card = -1
        y = H - 104
        self.b_reroll = Button((20, y, 160, 76), "Rerol", self._reroll, icon="reroll", style="blue", key=pygame.K_r)
        self.b_skip = Button((190, y, 160, 76), "Skip", self._skip, icon="skip", style="secondary", key=pygame.K_s)
        self.b_banish = Button((360, y, 160, 76), "Vyřadit", self._banish, icon="banish", style="danger",
                               key=pygame.K_b)
        self.buttons = [self.b_reroll, self.b_skip, self.b_banish]
        self._sync()

    def _sync(self) -> None:
        r = self.run
        self.b_reroll.sub = f"zbývá {r.rerolls}"
        self.b_reroll.enabled = r.rerolls > 0
        self.b_skip.sub = f"+{5 + r.level // 2} mincí"
        self.b_banish.sub = f"zbývá {r.banishes}"
        self.b_banish.enabled = r.banishes > 0
        self.b_banish.pulse = self.banish_mode
        if id(r.offer) != self.offer_id:
            self.offer_id = id(r.offer)
            self.t = 0.0

    def _reroll(self) -> None:
        if progression.reroll(self.run):
            self.banish_mode = False
            assets.audio.play("teleport", 0.4)

    def _skip(self) -> None:
        progression.skip(self.run)
        assets.audio.play("coin")

    def _banish(self) -> None:
        self.banish_mode = not self.banish_mode

    def card_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(26, 196 + i * (self.CARD_H + 14), W - 52, self.CARD_H)

    def _pick(self, i: int) -> None:
        offer = self.run.offer
        if not offer or i >= len(offer):
            return
        card = offer[i]
        if self.banish_mode:
            if progression.banish(self.run, card):
                assets.audio.play("back")
                self.banish_mode = False
            return
        assets.audio.play("click")
        progression.apply_card(self.run, card)
        self.scene.run.camera.vibrate(5)

    def on_down(self, ev) -> None:
        if self.t < 0.25:
            return
        for i in range(len(self.run.offer or [])):
            if self.card_rect(i).collidepoint(ev.x, ev.y):
                self.pressed_card = i

    def on_up(self, ev) -> None:
        i = self.pressed_card
        self.pressed_card = -1
        if i >= 0 and self.card_rect(i).collidepoint(ev.x, ev.y):
            self._pick(i)

    def on_move(self, ev) -> None:
        self.hover = -1
        for i in range(len(self.run.offer or [])):
            if self.card_rect(i).collidepoint(ev.x, ev.y):
                self.hover = i

    def on_key(self, key) -> None:
        if key in (pygame.K_1, pygame.K_KP1):
            self._pick(0)
        elif key in (pygame.K_2, pygame.K_KP2):
            self._pick(1)
        elif key in (pygame.K_3, pygame.K_KP3):
            self._pick(2)

    def update(self, dt: float) -> None:
        super().update(dt)
        self._sync()

    def draw(self, surf) -> None:
        run = self.run
        font = assets.font
        _dim(surf)
        k = ease_out_back(min(1.0, self.t * 3))
        font.draw(surf, "LEVEL UP!", (W // 2, 62 - (1 - k) * 40), (255, 220, 90), 6, "midtop", outline=C_OUTLINE)
        font.draw(surf, f"Úroveň {run.level - run.pending_levelups + 1}", (W // 2, 140), C_TEXT, 3, "midtop",
                  outline=C_OUTLINE)
        if self.banish_mode:
            font.draw(surf, "Klepni na kartu, kterou chceš vyřadit", (W // 2, 176), (255, 120, 120), 2, "midtop",
                      outline=C_OUTLINE)
        for i, card in enumerate(run.offer or []):
            self._card(surf, i, card)
        super().draw(surf)

    def _card(self, surf, i: int, card) -> None:
        font = assets.font
        appear = ease_out_back(max(0.0, min(1.0, (self.t - i * 0.08) * 4)))
        if appear <= 0:
            return
        r = self.card_rect(i)
        r.x += int((1 - appear) * W)
        pulse = 0.5 + 0.5 * math.sin(self.t * 4 + i)
        rc = RARITY_COLORS[card.rarity]
        if self.hover == i or card.rarity > 0:
            g = 4 + int(pulse * 4) + (4 if self.hover == i else 0)
            pygame.draw.rect(surf, rc, r.inflate(g, g), 3)
        if self.pressed_card == i:
            r.y += 3
        bg = (64, 48, 74) if not self.banish_mode else (90, 40, 50)
        draw_panel(surf, r, bg, border=rc if card.rarity else C_OUTLINE)
        # ikona
        evo = False
        draw_icon_frame(surf, (r.x + 14, r.y + 16, 84, 84), card.icon, evo=evo, scale=5)
        # rarita
        font.draw(surf, RARITY_NAMES[card.rarity], (r.right - 14, r.y + 12), rc, 1, "topright", outline=C_OUTLINE)
        # název a úroveň
        tx = r.x + 112
        font.draw(surf, card.title, (tx, r.y + 14), (255, 240, 200), 3, "topleft", outline=C_OUTLINE)
        if card.kind in ("weapon", "passive"):
            if card.new:
                tag = "NOVÉ!" if card.to <= 1 else f"NOVÉ! Úr. {card.to}"
                col = (120, 255, 140)
            else:
                tag = f"Úr. {card.cur} → {card.to}"
                col = (150, 210, 255)
            font.draw(surf, tag, (tx, r.y + 52), col, 2, "topleft", outline=C_OUTLINE)
            if card.kind == "weapon":
                d = WEAPONS[card.id]
                if d.evo_passive:
                    font.draw(surf, f"Evoluce s: {PASSIVES[d.evo_passive].name}", (tx, r.y + 78), (200, 170, 230), 1,
                              "topleft", outline=C_OUTLINE)
            elif card.kind == "passive":
                evos = [WEAPONS[w.id].name for w in self.run.weapons if WEAPONS[w.id].evo_passive == card.id
                        and not w.evolved]
                if evos:
                    font.draw(surf, f"Evoluce: {evos[0]}", (tx, r.y + 78), (255, 210, 120), 1, "topleft",
                              outline=C_OUTLINE)
        lines = font.wrap(card.desc, r.w - 128, 2)[:3]
        y = r.y + 96
        for ln in lines:
            font.draw(surf, ln, (tx, y), (230, 225, 235), 2, "topleft")
            y += 22
        if self.banish_mode and card.kind in ("weapon", "passive"):
            img = assets.icons.get("banish", 4)
            surf.blit(img, (r.right - 50, r.bottom - 50))


# ---------------------------------------------------------------------------------------------
class ChestOverlay(Overlay):
    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.reward = self.run.chest_reward
        self.opened = False
        self.b_ok = Button((W // 2 - 140, H - 160, 280, 80), "Pokračovat", self._close, style="primary",
                           key=pygame.K_RETURN)
        self.b_ok.visible = False
        self.buttons = [self.b_ok]
        assets.audio.play("chest")

    def _close(self) -> None:
        self.done = True
        self.run.resume()

    def on_down(self, ev) -> None:
        if not self.opened:
            self.t = max(self.t, 1.0)

    def on_key(self, key) -> None:
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if not self.opened:
                self.t = max(self.t, 1.0)
            elif self.b_ok.visible:
                self._close()

    def update(self, dt: float) -> None:
        super().update(dt)
        if not self.opened and self.t >= 1.0:
            self.opened = True
            assets.audio.play("gold")
            if self.reward and self.reward.get("evolution"):
                assets.audio.play("fanfare")
            self.scene.run.camera.vibrate(8)
        n = len(self.reward["items"]) if self.reward else 0
        if self.opened and self.t > 1.2 + n * 0.25:
            self.b_ok.visible = True

    def draw(self, surf) -> None:
        font = assets.font
        _dim(surf, 190)
        cx, cy = W // 2, 300
        evo = bool(self.reward and self.reward.get("evolution"))
        if not self.opened:
            sh = math.sin(self.t * 40) * 6 * self.t
            img = assets.icons.get("chest", 10)
            surf.blit(img, img.get_rect(center=(cx + sh, cy)))
            font.draw(surf, "BEDNA!", (cx, cy - 130), C_GOLD, 5, "midtop", outline=C_OUTLINE)
            font.draw(surf, "klepni pro otevření", (cx, cy + 90), C_TEXT, 2, "midtop", outline=C_OUTLINE)
            return
        # paprsky
        rays = pygame.Surface((W, 560), pygame.SRCALPHA)
        col = (255, 220, 90, 60) if not evo else (255, 120, 255, 70)
        for i in range(12):
            a = self.t * 0.8 + i * math.tau / 12
            pts = [(cx, 280), (cx + math.cos(a) * 600, 280 + math.sin(a) * 600),
                   (cx + math.cos(a + 0.15) * 600, 280 + math.sin(a + 0.15) * 600)]
            pygame.draw.polygon(rays, col, pts)
        surf.blit(rays, (0, 20))
        img = assets.icons.get("chest", 8)
        surf.blit(img, img.get_rect(center=(cx, 200)))
        font.draw(surf, "EVOLUCE!" if evo else "Poklad!", (cx, 90), (255, 140, 255) if evo else C_GOLD, 5, "midtop",
                  outline=C_OUTLINE)
        y = 290
        for i, (icon, name, sub, is_evo) in enumerate(self.reward["items"] if self.reward else []):
            k = ease_out_back(max(0.0, min(1.0, (self.t - 1.1 - i * 0.25) * 4)))
            if k <= 0:
                continue
            r = pygame.Rect(40, y, W - 80, 96)
            r.x += int((1 - k) * 200)
            draw_panel(surf, r, (90, 60, 30) if is_evo else (64, 48, 74), border=(255, 200, 60) if is_evo else C_OUTLINE)
            draw_icon_frame(surf, (r.x + 12, r.y + 10, 76, 76), icon, evo=is_evo, scale=5)
            font.draw(surf, name, (r.x + 100, r.y + 14), (255, 240, 200), 3, "topleft", outline=C_OUTLINE)
            lines = font.wrap(sub, r.w - 112, 2)[:2]
            for j, ln in enumerate(lines):
                font.draw(surf, ln, (r.x + 100, r.y + 50 + j * 22), (230, 220, 240), 2, "topleft")
            y += 108
        if self.reward:
            font.draw(surf, f"+{self.reward['coins']} mincí", (cx, y + 10), C_GOLD, 3, "midtop", outline=C_OUTLINE)
        super().draw(surf)


# ---------------------------------------------------------------------------------------------
class PauseOverlay(Overlay):
    def __init__(self, scene) -> None:
        super().__init__(scene)
        cx = W // 2
        self.buttons = [
            Button((cx - 170, H - 330, 340, 76), "Pokračovat", self._resume, icon="play", style="primary",
                   key=pygame.K_ESCAPE),
            Button((cx - 170, H - 240, 165, 70), "Hudba", self._music, icon="note", style="secondary"),
            Button((cx + 5, H - 240, 165, 70), "Zvuky", self._sfx, icon="speaker", style="secondary"),
            Button((cx - 170, H - 156, 165, 70), "Vzdát se", self._quit, icon="skull", style="danger"),
            Button((cx + 5, H - 156, 165, 70), "Restart", self._restart, icon="reroll", style="secondary"),
        ]
        self._sync()

    def _sync(self) -> None:
        st = self.scene.app.save.settings
        self.buttons[1].sub = "zapnuto" if st["music_on"] else "vypnuto"
        self.buttons[2].sub = "zapnuto" if st["sfx_on"] else "vypnuto"

    def _resume(self) -> None:
        self.done = True

    def _music(self) -> None:
        st = self.scene.app.save.settings
        st["music_on"] = not st["music_on"]
        self.scene.app.apply_settings()
        self._sync()

    def _sfx(self) -> None:
        st = self.scene.app.save.settings
        st["sfx_on"] = not st["sfx_on"]
        self.scene.app.apply_settings()
        self._sync()

    def _quit(self) -> None:
        self.done = True
        self.scene.give_up()

    def _restart(self) -> None:
        self.done = True
        self.scene.restart()

    def on_key(self, key) -> None:
        if key == pygame.K_p:
            self.done = True

    def draw(self, surf) -> None:
        font = assets.font
        run = self.run
        _dim(surf, 200)
        font.draw(surf, "PAUZA", (W // 2, 50), (255, 220, 90), 6, "midtop", outline=C_OUTLINE)
        r = pygame.Rect(30, 140, W - 60, 440)
        draw_panel(surf, r, (52, 38, 60))
        font.draw(surf, f"{run.char.name} · {run.biome.name} · {run.diff.name}", (r.centerx, r.y + 16), C_TEXT, 2,
                  "midtop")
        y = r.y + 50
        for w in run.weapons:
            draw_icon_frame(surf, (r.x + 16, y, 40, 40), w.d.icon, evo=w.evolved, scale=3)
            lvl = "EVO" if w.evolved else f"Úr. {w.level}"
            font.draw(surf, f"{w.d.name}", (r.x + 66, y + 4), (255, 240, 200), 2, "topleft")
            font.draw(surf, f"{lvl} · {fmt_num(w.damage_dealt)} dmg", (r.x + 66, y + 24), (190, 180, 200), 1, "topleft")
            y += 46
        y2 = r.y + 50
        for pid, lv in run.passives.items():
            d = PASSIVES[pid]
            draw_icon_frame(surf, (r.centerx + 20, y2, 40, 40), d.icon, scale=3)
            font.draw(surf, d.name, (r.centerx + 70, y2 + 4), (255, 240, 200), 1, "topleft")
            font.draw(surf, f"Úr. {lv}/5", (r.centerx + 70, y2 + 22), (190, 180, 200), 1, "topleft")
            y2 += 46
        st = run.player.stats
        stats = [f"Zdraví {int(run.player.hp)}/{int(st.max_hp)}", f"Síla ×{st.might:.2f}",
                 f"Rychlost {int(st.speed)}", f"Krit. {int(st.crit_chance * 100)} % ×{st.crit_mult:g}",
                 f"Zabití {fmt_num(run.kills)}", f"Mince {run.coins}"]
        y = r.bottom - 74
        for i, s in enumerate(stats):
            font.draw(surf, s, (r.x + 20 + (i % 2) * 250, y + (i // 2) * 22), (210, 200, 220), 1, "topleft")
        super().draw(surf)
