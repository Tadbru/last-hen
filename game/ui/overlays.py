"""Overlaye herní scény: levelup karty, otevírání bedny, pauza."""
from __future__ import annotations

import math

import pygame

from .. import assets, device, progression
from ..config import C_GOLD, C_OUTLINE, C_TEXT, H, RARITY_COLORS, RARITY_NAMES, W
from ..data.passives import PASSIVES
from ..data.weapons import WEAPONS
from ..util import ease_out_back, ease_out_cubic, fmt_num
from ..gfx.particles import ParticleSystem
from .widgets import Button, draw_frame, draw_icon_frame, draw_panel


def _compact(v: float) -> str:
    v = int(v)
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 10_000:
        return f"{v // 1000}k"
    return fmt_num(v)


def _dim(surf, a: int = 170) -> None:
    from ..scenes.base import dim_layer
    surf.blit(dim_layer(a, (12, 6, 18)), (0, 0))


class Overlay:
    def __init__(self, scene) -> None:
        self.scene = scene
        self.run = scene.run
        self.t = 0.0
        self.buttons: list[Button] = []
        self._pressed = None
        self.done = False

    lock = 0.0       # s po otevření, kdy se ignorují dotyky (ochrana proti náhodnému klepnutí)

    def handle(self, ev) -> None:
        if ev.type in ("down", "up") and self.t < self.lock:
            if self._pressed is not None:
                self._pressed.pressed = False
                self._pressed = None
            return
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
    lock = 0.6       # palec často zrovna drží joystick ve spodní části obrazovky
    SKIP_CONFIRM = 2.5

    def __init__(self, scene) -> None:
        super().__init__(scene)
        self.skip_arm = 0.0
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
        self.b_banish.enabled = r.banishes > 0 and any(c.kind in ("weapon", "passive") for c in (r.offer or []))
        if not self.b_banish.enabled:
            self.banish_mode = False
        self.b_banish.pulse = self.banish_mode
        if id(r.offer) != self.offer_id:
            self.offer_id = id(r.offer)
            self.t = 0.0
            self.skip_arm = 0.0
            self.hover = -1             # nová nabídka nesmí mít „předvybranou“ kartu (B-33)
            self.pressed_card = -1
        if self.skip_arm > 0:
            self.b_skip.text = "Opravdu?"
            self.b_skip.sub = "klepni znovu"
            self.b_skip.pulse = True
        else:
            self.b_skip.text = "Skip"
            self.b_skip.pulse = False

    def _reroll(self) -> None:
        if progression.reroll(self.run):
            self.banish_mode = False
            assets.audio.play("teleport", 0.4)

    def _skip(self) -> None:
        # Skip zahodí celý levelup – musí se potvrdit druhým klepnutím
        if self.skip_arm <= 0:
            self.skip_arm = self.SKIP_CONFIRM
            self._sync()
            return
        self.skip_arm = 0.0
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
            if card.kind not in ("weapon", "passive"):
                self.scene.toast("Tuhle kartu nejde vyřadit", (255, 160, 140), 1.8)
                assets.audio.play("back")
                return
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
        if device.MOBILE:
            return                      # na dotyku se zvýrazňuje jen držená karta
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
        if self.skip_arm > 0:
            self.skip_arm = max(0.0, self.skip_arm - dt)
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
        # přílet zprava bez přestřelení za levý okraj (B-37)
        appear = ease_out_cubic(max(0.0, min(1.0, (self.t - i * 0.08) * 4)))
        if appear <= 0:
            return
        r = self.card_rect(i)
        r.x += int((1 - appear) * W)
        pulse = 0.5 + 0.5 * math.sin(self.t * 4 + i)
        rc = RARITY_COLORS[card.rarity]
        if self.pressed_card == i:
            r.y += 3
        bg = (64, 48, 74) if not self.banish_mode else (90, 40, 50)
        draw_panel(surf, r, bg, border=rc if card.rarity else C_OUTLINE)
        # zvýraznění AŽ po panelu – stín panelu dřív mazal spodní hranu rámečku (B-29)
        if self.hover == i or self.pressed_card == i:
            draw_frame(surf, r, (255, 250, 230), 3, 8)
        elif card.rarity > 0:
            draw_frame(surf, r, rc, 3, 6 + 2 * int(pulse * 2))
        draw_icon_frame(surf, (r.x + 14, r.y + 16, 84, 84), card.icon, evo=False, scale=5)
        # název, úroveň a rarita (vše čitelné – měřítko 2+)
        tx = r.x + 112
        font.draw(surf, card.title, (tx, r.y + 12), (255, 240, 200), 3, "topleft", outline=C_OUTLINE)
        if card.kind in ("weapon", "passive"):
            if card.new:
                tag = "NOVÉ!" if card.to <= 1 else f"NOVÉ! Úr. {card.to}"
                col = (120, 255, 140)
            else:
                tag = f"Úr. {card.cur} → {card.to}"
                col = (150, 210, 255)
            font.draw(surf, tag, (tx, r.y + 50), col, 2, "topleft", outline=C_OUTLINE)
            if card.rarity:
                font.draw(surf, RARITY_NAMES[card.rarity], (r.right - 14, r.y + 50), rc, 2, "topright",
                          outline=C_OUTLINE)
        hint = ""
        if card.kind == "weapon":
            d = WEAPONS[card.id]
            if d.evo_passive:
                hint = f"Evoluce s: {PASSIVES[d.evo_passive].name}"
        elif card.kind == "passive":
            evos = [WEAPONS[w.id].name for w in self.run.weapons if WEAPONS[w.id].evo_passive == card.id
                    and not w.evolved]
            if evos:
                hint = f"Evoluce: {evos[0]}"
        y = r.y + 76
        if hint:
            font.draw(surf, hint, (tx, y), (255, 210, 120), 2, "topleft", outline=C_OUTLINE)
            y += 26
        cap = (r.bottom - 6 - y) // 22
        for ln in font.wrap(card.desc, r.w - 128, 2)[:cap]:
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
        self.b_ok = Button((W // 2 - 140, H - 104, 280, 80), "Pokračovat", self._close, style="primary",
                           key=pygame.K_RETURN)
        self.b_ok.visible = False
        self.buttons = [self.b_ok]
        self.fx = ParticleSystem(60)
        self.open_t = 0.0
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
        self.fx.update(dt)
        if not self.opened and self.t >= 1.0:
            self.opened = True
            self.open_t = self.t
            self.fx.burst_ring(W // 2, 168, 16, (255, 236, 150), 260)
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
        # paprsky jednou „vystřelí“ z truhly a vyblednou (kreslené v art pixelech, zvětšené ×3)
        rays = _chest_rays(self.t - self.open_t, self.t, evo)
        if rays is not None:
            surf.blit(rays, (0, 0))
        self.fx.draw(surf, 0, 0)
        img = assets.icons.get("chest", 6)
        surf.blit(img, img.get_rect(center=(cx, 168)))
        font.draw(surf, "EVOLUCE!" if evo else "Poklad!", (cx, 56), (255, 140, 255) if evo else C_GOLD, 5, "midtop",
                  outline=C_OUTLINE)
        if self.reward:
            font.draw(surf, f"+{self.reward['coins']} mincí", (cx, 206), C_GOLD, 3, "midtop", outline=C_OUTLINE)
        items = self.reward["items"] if self.reward else []
        n = max(1, len(items))
        y0, y1, gap = 252, self.b_ok.rect.y - 14, 10
        fs = 76
        tw = (W - 60) - (fs + 22) - 12
        # výška řádku podle obsahu (B-38): text svisle na střed k ikoně, žádná prázdná půlka panelu
        layouts = []
        for icon, name, sub, is_evo in items:
            name_sc = 3 if font.width(name, 3) <= tw else 2
            lines = font.wrap(sub, tw, 2)
            text_h = font.line_h(name_sc) + 2 + len(lines) * font.line_h(2)
            layouts.append((name_sc, lines, text_h, max(fs + 16, text_h + 18)))
        total = sum(lay[3] for lay in layouts) + gap * (len(layouts) - 1)
        if total > y1 - y0:
            # nouzově (5 položek s dlouhým popisem) – popis jen 1 řádek
            layouts = [(2, lay[1][:1], font.line_h(2) * 2 + 2, fs + 6) for lay in layouts]
        y = y0
        for i, ((icon, name, sub, is_evo), (name_sc, lines, text_h, row_h)) in enumerate(zip(items, layouts)):
            k = ease_out_back(max(0.0, min(1.0, (self.t - 1.1 - i * 0.25) * 4)))
            if k <= 0:
                y += row_h + gap
                continue
            r = pygame.Rect(30, y, W - 60, row_h)
            r.x += int((1 - k) * 200)
            draw_panel(surf, r, (90, 60, 30) if is_evo else (64, 48, 74), border=(255, 200, 60) if is_evo else C_OUTLINE)
            ifs = min(fs, row_h - 12)
            draw_icon_frame(surf, (r.x + 10, r.y + (row_h - ifs) // 2, ifs, ifs), icon, evo=is_evo,
                            scale=5 if ifs >= 70 else 4)
            tx = r.x + fs + 22
            ty = r.y + (row_h - text_h) // 2
            font.draw(surf, name, (tx, ty), (255, 240, 200), name_sc, "topleft", outline=C_OUTLINE)
            ty += font.line_h(name_sc) + 2
            for ln in lines:
                font.draw(surf, ln, (tx, ty), (230, 220, 240), 2, "topleft")
                ty += font.line_h(2)
            y += row_h + gap
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
        from ..scenes.base import Dialog

        def do():
            self.done = True
            self.scene.give_up()
        self.scene.modal = Dialog("Vzdát se?", "Run skončí a dostaneš odměnu za dosavadní výkon.",
                                  [("Vzdát se", do, "danger"), ("Hrát dál", None, "primary")], icon="skull")

    def _restart(self) -> None:
        from ..scenes.base import Dialog

        def do():
            self.done = True
            self.scene.restart()
        self.scene.modal = Dialog("Začít znovu?", "Rozehraný run se zahodí bez odměny.",
                                  [("Restart", do, "danger"), ("Hrát dál", None, "primary")], icon="reroll")

    def on_key(self, key) -> None:
        if key == pygame.K_p:
            self.done = True

    def draw(self, surf) -> None:
        font = assets.font
        run = self.run
        _dim(surf, 120)
        font.draw(surf, "PAUZA", (W // 2, 36), (255, 220, 90), 6, "midtop", outline=C_OUTLINE)
        font.draw(surf, f"{run.char.name} · {run.biome.short or run.biome.name} · {run.diff.name}", (W // 2, 108),
                  C_TEXT, 2, "midtop", outline=C_OUTLINE)
        r = pygame.Rect(24, 140, W - 48, 480)
        draw_panel(surf, r, (52, 38, 60))
        cw = r.w // 2 - 18
        cols = (r.x + 12, r.centerx + 6)
        font.draw(surf, "Zbraně", (cols[0], r.y + 12), (255, 214, 120), 2, "topleft", outline=C_OUTLINE)
        font.draw(surf, "Pasivky", (cols[1], r.y + 12), (255, 214, 120), 2, "topleft", outline=C_OUTLINE)
        tw = cw - 48
        y = r.y + 44
        for w in run.weapons:
            draw_icon_frame(surf, (cols[0], y, 40, 40), w.d.icon, evo=w.evolved, scale=3)
            lvl = "EVO" if w.evolved else f"Úr. {w.level}"
            font.draw(surf, font.fit(w.d.name, tw, 2), (cols[0] + 48, y - 2), (255, 240, 200), 2, "topleft")
            font.draw(surf, f"{lvl} · {_compact(w.damage_dealt)}", (cols[0] + 48, y + 20), (200, 190, 210), 2,
                      "topleft")
            y += 48
        y = r.y + 44
        for pid, lv in run.passives.items():
            d = PASSIVES[pid]
            draw_icon_frame(surf, (cols[1], y, 40, 40), d.icon, scale=3)
            font.draw(surf, font.fit(d.name, tw, 2), (cols[1] + 48, y - 2), (255, 240, 200), 2, "topleft")
            font.draw(surf, f"Úr. {lv}/5", (cols[1] + 48, y + 20), (200, 190, 210), 2, "topleft")
            y += 48
        st = run.player.stats
        stats = [f"Zdraví {int(run.player.hp)}/{int(st.max_hp)}", f"Síla ×{st.might:.2f}",
                 f"Rychlost {int(st.speed)}", f"Krit. {int(st.crit_chance * 100)} % ×{st.crit_mult:g}",
                 f"Zabití {fmt_num(run.kills)}", f"Mince {run.coins}"]
        y = r.y + 352
        pygame.draw.line(surf, (90, 70, 100), (r.x + 12, y - 10), (r.right - 12, y - 10), 2)
        for i, s_ in enumerate(stats):
            font.draw(surf, s_, (cols[i % 2], y + (i // 2) * 28), (215, 205, 225), 2, "topleft")
        super().draw(surf)


_RAYS: dict = {}


def _chest_rays(age: float, t: float, evo: bool):
    """Paprsky z truhly: při otevření vystřelí (rychle se prodlouží), chvíli svítí a vyblednou. None = už nejsou."""
    fade = 1.0 - max(0.0, (age - 0.5) / 0.9)
    if fade <= 0:
        return None
    low = _RAYS.get("low")
    if low is None:
        low = _RAYS["low"] = pygame.Surface((W // 3, H // 3), pygame.SRCALPHA)
        _RAYS["big"] = pygame.Surface((W, H), pygame.SRCALPHA)
    low.fill((0, 0, 0, 0))
    cx, cy = W // 6, 56
    reach = 400 * ease_out_cubic(min(1.0, age / 0.3))
    a0 = 70 if evo else 60
    col = (255, 120, 255, int(a0 * fade)) if evo else (255, 220, 90, int(a0 * fade))
    for i in range(12):
        a = t * 0.8 + i * math.tau / 12
        pygame.draw.polygon(low, col, [(cx, cy), (cx + math.cos(a) * reach, cy + math.sin(a) * reach),
                                       (cx + math.cos(a + 0.15) * reach, cy + math.sin(a + 0.15) * reach)])
    big = _RAYS["big"]
    pygame.transform.scale(low, (W, H), big)
    return big
