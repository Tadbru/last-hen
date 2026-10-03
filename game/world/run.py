"""Run – kompletní simulace jednoho běhu hry (bez renderu → lze spouštět headless)."""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

from .. import assets
from ..config import DT, MAX_ENEMIES, MAX_PARTICLES, MAX_PICKUPS, MAX_PROJECTILES, MAX_TEXTS
from ..core.camera import Camera
from ..core.spatial import KMUL, OFF, SpatialGrid
from ..data import waves as WV
from ..data.biomes import BIOMES
from ..data.bosses import BOSSES
from ..data.characters import CHARACTERS
from ..data.enemies import ENEMIES
from ..data.meta import DIFFICULTIES
from ..data.passives import MAX_PASSIVE_LEVEL
from ..data.weapons import MAX_WEAPON_LEVEL, WEAPONS
from ..gfx import pixelart as pa
from ..gfx.particles import ParticleSystem
from ..gfx.sprites import Anim
from ..weapons.base import make_weapon
from .bosses import make_boss_ctrl, tinted_anim
from .director import Director
from .enemies import update_enemies
from .entities import (M_BOOMERANG, M_LOB, M_SPIRAL, M_STRAIGHT, M_WAVE, P_CHEST, P_COIN, P_GOLDEGG, P_MAGNET,
                       P_WORM, P_XP, Area, Beam, Enemy, FloatText, Pickup, Proj, Ring, Telegraph)
from .mapgen import WorldMap
from .player import Player

ARENA_R = 430.0
FLASH_GAP = 2.0            # min. rozestup běžných záblesků (s)
PLAYER_FX_CAP = 0.3        # strop třesu od vlastních zbraní (offset ≈ 1 px)
CROW_KILLS = 70


# Ladění délky módů (4. kolo reportu)
QUICK_XP = 1.6              # násobič XP v rychlém módu (dřív 1,8 → pauza každých ~6 s)
QUICK_CARD_LUCK = 1.3       # …a místo toho vzácnější karty
QUICK_FINAL_HP = 0.15       # HP finálního bosse v rychlém módu (dřív 0,1 → padl za 15 s)
XP_STEEP_FROM = 30          # od této úrovně roste potřeba XP rychleji
XP_STEEP = 0.12
RUSH_BOSS_LEVELS = 4        # kolik úrovní XP vysype boss v boss rushi
GIANT_K = 4 / 3             # zvětšení obrů
PAUSE_GAP = 8.0             # min. herní čas mezi dvěma přerušeními (level-upy se mezitím spojí do jedné obrazovky)

@dataclass
class RunConfig:
    character: str = "hen"
    biome: str = "farm"
    mode: str = "quick"              # quick | full | daily | bossrush
    difficulty: str = "normal"
    seed: int = 0
    modifiers: tuple = ()
    meta: dict = field(default_factory=dict)
    rerolls: int = 2
    banishes: int = 2
    bonus_levels: int = 0
    skin: str | None = None
    season: str | None = None
    headless: bool = False


class Wave:
    """Rozpínající se rázová vlna, která zraňuje nepřátele (a případně hráče) při průchodu."""
    __slots__ = ("x", "y", "r", "r0", "r1", "life", "maxlife", "dmg", "src", "kb", "slow", "stun", "color", "hit",
                 "follow", "alive", "hurt_player", "player_hit", "crit")

    def __init__(self, x, y, r0, r1, dur, dmg, src, kb, slow, stun, color, follow, hurt_player):
        self.x, self.y = x, y
        self.r = r0
        self.r0, self.r1 = r0, r1
        self.life = dur
        self.maxlife = dur
        self.dmg, self.src, self.kb, self.slow, self.stun = dmg, src, kb, slow, stun
        self.color = color
        self.hit: set = set()
        self.follow = follow
        self.alive = True
        self.hurt_player = hurt_player
        self.player_hit = False
        self.crit = True


class Run:
    def __init__(self, cfg: RunConfig) -> None:
        self.cfg = cfg
        self.headless = cfg.headless
        self.rng = random.Random(cfg.seed or random.randrange(1 << 30))
        self.char = CHARACTERS[cfg.character]
        self.biome = BIOMES[cfg.biome]
        self.diff = DIFFICULTIES[cfg.difficulty]
        mods = set(cfg.modifiers)
        self.mods = mods
        self.mod_hp_mult = 0.5 if "glass" in mods else 1.0
        self.mod_dmg_mult = 2.0 if "glass" in mods else 1.0
        self.mod_spawn_mult = 1.5 if "horde" in mods else 1.0
        self.mod_enemy_speed = 1.3 if "speedy" in mods else 1.0
        self.mod_enemy_hp = 1.5 if "giants" in mods else 1.0
        quick = cfg.mode in ("quick", "daily")
        # rychlý mód: méně level-upů (méně pauz), zato vzácnější karty (B-51)
        self.xp_mult = (QUICK_XP if quick else 1.0) * (1.25 if "horde" in mods else 1.0) \
            * (1.3 if "giants" in mods else 1.0)
        self.card_luck = QUICK_CARD_LUCK if quick else 1.0
        self.time = 0.0
        self.tick = 0
        self.state = "playing"
        self.state_t = 0.0
        self.god = False

        self.passives: dict[str, int] = {}
        self.weapons: list = []
        self.camera = Camera()
        self.player = Player(self, self.char, cfg.meta)
        self.map = WorldMap(self, self.biome, self.rng.randrange(1 << 30), cfg.season)
        self.grid = SpatialGrid(64)
        self.enemies: list[Enemy] = []
        self.props: list[Enemy] = []
        self.projs: list[Proj] = []
        self._proj_pool: list[Proj] = []
        self.eprojs: list = []
        self.areas: list[Area] = []
        self.waves: list[Wave] = []
        self.rings: list[Ring] = []
        self.beams: list[Beam] = []
        self.allies: list = []
        self.pickups: list[Pickup] = []
        self.telegraphs: list[Telegraph] = []
        self.texts: list[FloatText] = []
        self.bombs: list = []          # [x, y, t, r, dmg_player, dmg_enemy, src, color, warn]
        self.particles = ParticleSystem(MAX_PARTICLES)
        self.director = Director(self)

        # bonusové levelupy (boss rush, rubber-banding) zvednou úroveň hned – overlay pak ukazuje 2, 3, …
        self.level = 1 + max(0, cfg.bonus_levels)
        self.xp = 0.0
        self.xp_next = self.xp_needed(self.level)
        self.pending_levelups = cfg.bonus_levels
        self.pending_chests: list[str] = []
        self.pause_cd = 0.0             # odpočet do dalšího možného přerušení (B-51)
        self.offer = None
        self.chest_reward = None
        self.rerolls = cfg.rerolls
        self.banishes = cfg.banishes
        self.banished: set[str] = set()
        self.kills = 0
        self.coins = 0
        self.crow_charge = 0.0
        self.crows_used = 0
        self.crits = 0
        self.max_burst = 0
        self.stats_dmg_taken = 0.0
        self.dmg_log: dict[str, float] = {}
        self.bosses: list = []         # aktivní boss kontrolery
        self.final_boss = None
        self.bosses_killed: list[str] = []
        self.boss_log: dict[str, list] = {}     # boss -> [čas příchodu, délka souboje]
        self.arena = None
        self.timescale = 1.0
        self.slowmo_t = 0.0
        self.slowmo_cd = 0.0
        self._burst = deque([0] * 20, maxlen=20)
        self._kills_tick = 0
        self.corpses: deque = deque(maxlen=40)
        self.banners: list[list] = []
        self.speech: list[list] = []   # [entity, text, t, dead]
        self.flash_t = 0.0
        self.flash_col = (255, 255, 255)
        self.flash_cd = 0.0
        self.flash_count = 0
        self.flashes_on = True
        self.revived = False
        self.gave_up = False
        self.victory = False
        self.result = None
        self.show_damage = True
        self.discovered = {"enemies": set(), "weapons": set(), "evolutions": set(), "bosses": set(), "passives": set()}
        self.events_log: list[str] = []
        self.ever_passive = False
        self.max_weapons = 0
        self.chest_coins = (0, 0)       # (počet beden, mince) převedené po výhře
        self.best_no_hit = 0.0
        self.intensity = 0.0
        self._qbuf: list = []
        self._boss_sprites: dict = {}
        self._giant_sprites: dict = {}

        # startovní zbraň
        self.add_weapon(self.char.weapon)
        self.camera.snap(0, 0)
        self.map.ensure(0, 0)

    # =====================================================================================
    # POMOCNÉ
    # =====================================================================================
    def sfx(self, name: str, vol: float = 1.0) -> None:
        if not self.headless and assets.audio is not None:
            assets.audio.play(name, vol)

    def shake(self, amount: float, cap: float = 1.0) -> None:
        self.camera.shake(amount, cap)

    def flash(self, color, dur: float = 0.1, important: bool = False) -> None:
        """Záblesk přes obrazovku. Lze vypnout v Nastavení; běžné záblesky max. 1× za FLASH_GAP s."""
        if not self.flashes_on:
            return
        if not important and self.flash_cd > 0:
            return
        self.flash_cd = FLASH_GAP
        self.flash_count += 1
        self.flash_col = color
        self.flash_t = max(self.flash_t, dur)

    def banner(self, text: str, color=(255, 255, 255), dur: float = 1.8) -> None:
        self.banners.append([text, color, dur, dur])

    def say(self, e, text: str, dur: float = 2.5, dead: bool = False) -> None:
        self.speech = [s for s in self.speech if s[0] is not e]
        self.speech.append([e, text, dur, dead])

    def add_text(self, x, y, text, color=(255, 255, 255), scale=2, life=0.7) -> None:
        if len(self.texts) >= MAX_TEXTS:
            return
        self.texts.append(FloatText(x, y, text, color, life, scale))

    def xp_needed(self, level: int) -> float:
        req = 5 + 4.5 * level + 0.14 * level * level
        if level > XP_STEEP_FROM:
            # strmější konec: build se nedokončí minuty před koncem plného módu (B-55)
            req *= 1 + XP_STEEP * (level - XP_STEEP_FROM)
        return req * CHARACTERS[self.cfg.character].xp_req

    def enemy_dmg_mult(self) -> float:
        return WV.dmg_mult(self.director.eff_min()) * self.diff.dmg

    # =====================================================================================
    # ZBRANĚ A PASIVKY
    # =====================================================================================
    def weapon(self, wid: str):
        for w in self.weapons:
            if w.id == wid:
                return w
        return None

    def add_weapon(self, wid: str, level: int = 1):
        w = make_weapon(self, wid, level)
        self.weapons.append(w)
        d = WEAPONS[wid]
        self.discovered["evolutions" if d.evolution else "weapons"].add(wid)
        self.max_weapons = max(self.max_weapons, len(self.weapons))
        return w

    def level_weapon(self, wid: str, levels: int = 1) -> None:
        w = self.weapon(wid)
        if w is None:
            self.add_weapon(wid, min(MAX_WEAPON_LEVEL, levels))
            return
        w.set_level(min(MAX_WEAPON_LEVEL, w.level + levels))

    def add_passive(self, pid: str, levels: int = 1) -> None:
        self.passives[pid] = min(MAX_PASSIVE_LEVEL, self.passives.get(pid, 0) + levels)
        self.discovered["passives"].add(pid)
        self.ever_passive = True
        self.player.recompute()

    def evolve(self, wid: str) -> None:
        w = self.weapon(wid)
        if w is None or not w.d.evo_to:
            return
        idx = self.weapons.index(w)
        w.on_remove()
        nw = make_weapon(self, w.d.evo_to, 1)
        nw.damage_dealt = w.damage_dealt
        nw.kills = w.kills
        self.weapons[idx] = nw
        self.discovered["evolutions"].add(nw.id)
        self.banner(f"EVOLUCE: {nw.d.name}!", (255, 214, 70), 2.5)
        self.flash((255, 240, 180), 0.2, important=True)
        self.sfx("fanfare")
        self.camera.vibrate(10)

    def evolvable(self) -> list[str]:
        out = []
        for w in self.weapons:
            d = w.d
            if d.evo_to and w.level >= MAX_WEAPON_LEVEL and self.passives.get(d.evo_passive, 0) > 0:
                out.append(w.id)
        return out

    # =====================================================================================
    # NEPŘÁTELÉ
    # =====================================================================================
    def spawn_enemy(self, eid: str, x: float, y: float, summoned: bool = False):
        d = ENEMIES[eid]
        em = self.director.eff_min()
        hp = d.hp * WV.hp_mult(em) * self.diff.hp * self.biome.hp_mult * self.mod_enemy_hp
        if d.elite:
            hp *= 1 + em * 0.08
        speed = d.speed * self.rng.uniform(0.88, 1.12) * self.mod_enemy_speed
        dmg = d.dmg * WV.dmg_mult(em) * self.diff.dmg
        giant = "giants" in self.mods and not d.elite
        spr = self.giant_sprite(d.sprite) if giant else assets.sprites.enemies[d.sprite]
        e = Enemy(d, x, y, hp, speed, dmg, spr)
        e.anim = self.rng.random() * 2
        e.cd = self.rng.uniform(1.0, 3.0)
        e.summoned = summoned
        if giant:
            e.r *= GIANT_K
        self.enemies.append(e)
        if not self.headless and self.camera.on_screen(x, y, -10):
            # objevení přímo na obrazovce (okraj arény, vyvolání) – vylézt z hlíny, ne se „zhmotnit“
            self.particles.puff(x, y + 6, 4, (120, 96, 72), 50, 10)
            self.add_ring(x, y + 4, 4, e.r * 1.6, 0.35, (170, 120, 210), 3)
        return e

    def spawn_prop(self, x: float, y: float, ref):
        d = ENEMIES["barrel"]
        e = Enemy(d, x, y, d.hp, 0, 0, assets.sprites.enemies["barrel"])
        e.state = ref
        self.props.append(e)
        return e

    def despawn_prop(self, e) -> None:
        e.alive = False
        if e in self.props:
            self.props.remove(e)

    def boss_sprite(self, name: str, tint=None):
        key = (name, tint)
        a = self._boss_sprites.get(key)
        if a is None:
            base = assets.sprites.enemies[name]
            a = tinted_anim(base, tint) if tint else base
            self._boss_sprites[key] = a
        return a

    def giant_sprite(self, name: str) -> Anim:
        """Zvětšený sprite pro modifikátor Obři (B-58): 4/3 = 1 art pixel ze 3 na 4 px, čisté hrany."""
        a = self._giant_sprites.get(name)
        if a is None:
            base = assets.sprites.enemies[name]
            a = Anim([pa.scale(f, GIANT_K) for f in base.frames[0]])
            self._giant_sprites[name] = a
        return a

    def spawn_boss(self, bid: str) -> None:
        b = BOSSES[bid]
        p = self.player
        final = bid == "zombie_rooster"
        quick = self.director.quick
        hp = b.hp * self.diff.hp * self.biome.hp_mult
        bdmg = b.dmg * self.diff.dmg * (1 + 0.05 * self.director.eff_min())
        if final and quick:
            hp *= QUICK_FINAL_HP
            bdmg *= 0.8
        if self.cfg.mode == "bossrush":
            hp *= 0.75
        if final:
            # aréna kolem hráče
            self.arena = (p.x, p.y, ARENA_R)
            # bedny, zrní a odměny za plotem se stáhnou dovnitř arény (B-50)
            lim = ARENA_R - 70
            for pk in self.pickups:
                dx, dy = pk.x - p.x, pk.y - p.y
                d = math.hypot(dx, dy)
                if d > lim:
                    pk.x = p.x + dx / d * lim
                    pk.y = p.y + dy / d * lim
            for e in self.enemies:
                dx, dy = e.x - p.x, e.y - p.y
                d2 = dx * dx + dy * dy
                if d2 > (ARENA_R - 20) ** 2:
                    if e.boss:
                        # rozpracovaný mini-boss se přenese do arény (dřív zmizel a „visel“ v seznamu bossů)
                        d = math.sqrt(d2) or 1.0
                        e.x = p.x + dx / d * (ARENA_R - 90)
                        e.y = p.y + dy / d * (ARENA_R - 90)
                        e.alpha = 255
                    else:
                        e.alive = False
                        self.particles.puff(e.x, e.y, 2, (200, 200, 200))
            a = -math.pi / 2
            x, y = p.x, p.y - 300
        else:
            a = self.rng.uniform(0, math.tau)
            x, y = p.x + math.cos(a) * 420, p.y + math.sin(a) * 420
        tint = None
        sprite = b.sprite
        if final:
            from ..data.bosses import FINAL_VARIANTS
            tint = FINAL_VARIANTS.get(self.biome.id, {}).get("tint")
        d = ENEMIES["fox"]
        e = Enemy(d, x, y, hp, b.speed, bdmg, self.boss_sprite(sprite, tint))
        e.r = b.radius
        e.boss = True
        e.kb_res = 1.0
        e.xp = 0
        e.chest = False
        self.boss_log[bid] = [round(self.time, 1), None]
        ctrl = make_boss_ctrl(self, e, bid)
        e.ctrl = ctrl
        e.state = bid
        self.enemies.append(e)
        self.bosses.append(ctrl)
        self.particles.smoke(x, y, 12, (60, 50, 66), 30, 5, 50, 1.3)
        self.particles.pop_ring(x, y, 90, (255, 120, 90), 0.45)
        if final:
            self.final_boss = ctrl
            self.banner(ctrl.name, (255, 80, 80), 3.0)
            # finále začíná s plnými silami
            p.heal(p.stats.max_hp)
            self.crow_charge = 1.0
            self.add_text(p.x, p.y - 50, "Svítá! Plné síly!", (255, 230, 140), 2, 2.0)
            self.particles.stars(p.x, p.y - 20, 12, (255, 230, 120))
            if not self.headless and assets.audio:
                assets.audio.play_music("boss", 1.0)
        else:
            self.banner(f"BOSS: {b.name}", (255, 120, 80), 2.5)
        self.sfx("roar")
        self.shake(0.5)
        self.camera.vibrate(12)
        self.camera.haptic(80)

    def boss_killed(self, ctrl) -> None:
        e = ctrl.e
        bid = e.state
        self.bosses_killed.append(bid)
        if bid in self.boss_log:
            self.boss_log[bid][1] = round(self.time - self.boss_log[bid][0], 1)
        self.discovered["bosses"].add(bid)
        if ctrl in self.bosses:
            self.bosses.remove(ctrl)
        self.explosion(e.x, e.y, 120, 0, None, (255, 220, 120), big=True)
        self.particles.feathers(e.x, e.y, 40, (255, 240, 220), 300)
        self.particles.burst_ring(e.x, e.y - 20, 16, (255, 230, 140), 280)
        self.flash((255, 255, 255), 0.15, important=True)
        self.shake(0.8)
        self.camera.vibrate(16)
        self.camera.haptic(120)
        self.coins += 25 if bid != "zombie_rooster" else 100
        if ctrl is self.final_boss or (self.cfg.mode == "bossrush" and not self.director.rush and not self.bosses):
            self.final_boss = None
            self.arena = None
            self.state = "victory_anim"
            self.state_t = 3.0
            self.victory = True
            # dobíhající útoky po vítězství zrušit (dřív mohly hráče zabít během vítězné animace)
            self.telegraphs = []
            self.bombs = []
            self.eprojs = []
            self.waves = [w for w in self.waves if not w.hurt_player]
            self.player.invuln = 999.0
            self.sfx("victory")
            self.banner("SLUNCE VYCHÁZÍ!", (255, 220, 120), 3.0)
        else:
            self.pickups.append(Pickup(e.x, e.y, P_CHEST, 2))
            self.banner("Boss poražen!", (255, 214, 70), 2.0)
            if self.cfg.mode == "bossrush":
                self._boss_xp(e.x, e.y)
            self.sfx("fanfare")

    def recycle_enemy(self, e) -> None:
        """Vzdálené nepřátele přesunout před hráče (udržuje tlak a výkon)."""
        x, y = self.director.offscreen_pos()
        e.x, e.y = x, y
        e.kx = e.ky = 0.0

    def necro_raise(self, owl) -> None:
        raised = 0
        keep = deque(maxlen=40)
        for (x, y) in self.corpses:
            if raised < 5 and (x - owl.x) ** 2 + (y - owl.y) ** 2 < 300 * 300 and len(self.enemies) < MAX_ENEMIES:
                self.spawn_enemy("skeleton_fox", x, y, summoned=True)
                self.particles.puff(x, y, 4, (170, 100, 220))
                self.add_ring(x, y, 4, 30, 0.4, (170, 90, 220), 3)
                raised += 1
            else:
                keep.append((x, y))
        self.corpses = keep
        if raised == 0:
            for i in range(3):
                a = i * math.tau / 3
                self.spawn_enemy("skeleton_fox", owl.x + math.cos(a) * 40, owl.y + math.sin(a) * 40, summoned=True)
        self.add_ring(owl.x, owl.y, 10, 80, 0.5, (190, 100, 255), 4)
        self.say(owl, "Hú-hú! Vstávejte!", 1.4)
        self.sfx("teleport", 0.4)

    # =====================================================================================
    # POŠKOZENÍ
    # =====================================================================================
    def damage_enemy(self, e, dmg: float, src, kx: float = 0.0, ky: float = 0.0, kb: float = 0.0,
                     crit: bool = True, slow: float = 0.0, slow_t: float = 1.2, freeze: float = 0.0,
                     stun: float = 0.0, hyp: float = 0.0, flash: bool = True) -> float:
        """flash=False: plošné poškození v intervalech (mrak, šlehačka, aura) – jen vizuál: bez bílého
        bliknutí celého davu a bez záplavy čísel, místo toho drobná bublinka."""
        if not e.alive or dmg <= 0 and not kb:
            return 0.0
        st = self.player.stats
        is_crit = False
        if crit and self.rng.random() < st.crit_chance:
            dmg *= st.crit_mult
            is_crit = True
            self.crits += 1
        if e.hyp_t > 0:
            dmg *= 1.25
        if e.armor > 0:
            absorbed = min(e.armor, dmg * 0.7)
            e.armor -= absorbed
            dmg -= absorbed
            if e.armor <= 0:
                self.sfx("helmet", 0.5)
                self.particles.sparks(e.x, e.y - 12, 6, (220, 225, 240), 150)
                self.particles.glow(e.x, e.y - 12, 18, (200, 210, 240), 0.1)
                if e.d.id == "armored_fox":
                    e.spr = assets.sprites.enemies["armored_fox_broken"]
        if e.ctrl is not None:
            dmg = e.ctrl.modify_damage(dmg)
        if dmg > 0:
            e.hp -= dmg
            if not flash:
                if not self.headless and self.particles.rng.random() < 0.35:
                    self.particles.sparkle(e.x, e.y - e.r, src.d.color if src is not None else (200, 255, 150), 1)
            else:
                if e.flash <= 0 and not self.headless:
                    self.particles.hit(e.x, e.y - e.r * 0.6, kx, ky, (255, 230, 150) if is_crit else (255, 250, 225))
                e.flash = 0.09
            if src is not None:
                src.damage_dealt += dmg
            if self.show_damage and not self.headless:
                if is_crit:
                    self.add_text(e.x, e.y - e.r - 6, f"{int(dmg)}!", (255, 220, 60), 2, 0.8)
                elif dmg >= 1:
                    jx = self.rng.uniform(-6, 6)        # RNG se čerpá vždy stejně (tok herního RNG beze změny)
                    if flash:
                        self.add_text(e.x + jx, e.y - e.r - 4, str(int(dmg)), (255, 255, 255), 2, 0.55)
        if kb and not e.boss and e.kb_res < 1:
            d = math.hypot(kx, ky)
            if d > 0:
                k = kb * (1 - e.kb_res)
                e.kx += kx / d * k
                e.ky += ky / d * k
        if slow > 0:
            e.slow_f = max(e.slow_f, slow)
            e.slow_t = max(e.slow_t, slow_t)
        if not e.boss:
            if freeze > 0:
                if e.freeze_t <= 0:
                    self.sfx("freeze", 0.3)
                e.freeze_t = max(e.freeze_t, freeze * (0.4 if e.elite else 1.0))
            if stun > 0:
                e.stun_t = max(e.stun_t, stun * (0.4 if e.elite else 1.0))
            if not e.elite and (hyp > 0 or self.char.special == "hypnosis"):
                if self.rng.random() < 0.10 + hyp:
                    if e.hyp_t <= 0:
                        self.particles.stars(e.x, e.y - 20, 3, (220, 120, 255), 60)
                    e.hyp_t = 2.5
        if e.hp <= 0:
            self.kill_enemy(e, src)
        return dmg

    def kill_enemy(self, e, src) -> None:
        if not e.alive:
            return
        e.alive = False
        if e.prop:
            ref = e.state
            if isinstance(ref, list):
                ref[2] = True
                ref[3] = None
            if e in self.props:
                self.props.remove(e)
            self.explosion(e.x, e.y, e.d.explode, 120 * self.player.stats.might, None, (255, 120, 40),
                           kb=300, hurt_player=12)
            return
        if e.ctrl is not None:
            e.ctrl.on_death()
            return
        self.kills += 1
        self._kills_tick += 1
        self.crow_charge = min(1.0, self.crow_charge + self.player.stats.crow_mult / CROW_KILLS)
        self.discovered["enemies"].add(e.d.id)
        if src is not None:
            src.kills += 1
            s = src.s
            if s.get("lifesteal"):
                self.player.heal(1.0)
            if s.get("coin") and self.rng.random() < s["coin"]:
                self.pickups.append(Pickup(e.x, e.y, P_COIN, 1))
        if e.xp:
            self.drop_xp(e.x, e.y, e.xp)
        r = self.rng.random()
        if r < 0.006:
            self.pickups.append(Pickup(e.x + 8, e.y, P_WORM, 1))
        elif r < 0.0075:
            self.pickups.append(Pickup(e.x + 8, e.y, P_MAGNET, 1))
        if e.chest:
            self.pickups.append(Pickup(e.x, e.y, P_CHEST, 1))
            for _ in range(5):
                self.pickups.append(Pickup(e.x + self.rng.uniform(-20, 20), e.y + self.rng.uniform(-20, 20), P_COIN, 1))
            self.sfx("roar", 0.4)
        if e.d.explode or "explosive" in self.mods:
            rr = e.d.explode or 50
            self.bombs.append([e.x, e.y, 0.6, rr, e.dmg * 1.0, 30 * self.player.stats.might, None,
                               (255, 120, 40), True])
        if not e.summoned:
            self.corpses.append((e.x, e.y))
        self.particles.pop(e.x, e.y - 8, e.d.fluff, 4 if len(self.particles) < 450 else 1)
        if e.elite:
            self.particles.feathers(e.x, e.y, 20, e.d.fluff, 220)
            self.particles.glow(e.x, e.y - 10, 44, (255, 220, 160), 0.14)
            self.particles.smoke(e.x, e.y, 6, (70, 60, 66), 14, 4)
            self.particles.pop_ring(e.x, e.y - 8, 46, (255, 230, 170), 0.3)
            self.shake(0.3)
        self.sfx("plop", 0.5)
        if self.kills % 3 == 0:
            self.shake(0.035, 0.2)

    def area_damage(self, x: float, y: float, r: float, dmg: float, src, kb: float = 0.0, slow: float = 0.0,
                    slow_t: float = 1.2, stun: float = 0.0, freeze: float = 0.0, crit: bool = True,
                    exclude: set | None = None, flash: bool = True) -> int:
        hits = 0
        buf = self._qbuf
        buf.clear()
        for e in self.grid.query(x, y, r + 40, buf):
            if not e.alive:
                continue
            dx, dy = e.x - x, e.y - y
            rr = r + e.r
            if dx * dx + dy * dy < rr * rr:
                if exclude is not None:
                    if e.id in exclude:
                        continue
                    exclude.add(e.id)
                self.damage_enemy(e, dmg, src, dx, dy, kb, crit, slow, slow_t, 0.0 if not freeze else freeze, stun,
                                  flash=flash)
                hits += 1
        return hits

    def explosion(self, x, y, r, dmg, src, color=(255, 200, 80), kb: float = 200, big: bool = False,
                  hurt_player: float = 0.0, crit: bool = True, fx: str = "fire") -> None:
        if dmg > 0:
            self.area_damage(x, y, r, dmg, src, kb=kb, crit=crit)
        if hurt_player > 0:
            p = self.player
            if (p.x - x) ** 2 + (p.y - y) ** 2 < (r + p.r) ** 2:
                p.take_damage(hurt_player, x, y, "výbuch")
        if fx == "cream":
            self.add_ring(x, y, r * 0.5, r, 0.25, (255, 250, 240), 4 if not big else 6)
            self.particles.splat(x, y, r)
        else:
            self.add_ring(x, y, r * 0.3, r, 0.28 if not big else 0.5, color, 6 if not big else 12)
            self.particles.explosion(x, y, r, color, big)
        self.sfx("nuke" if big else "explode", 0.7 if not big else 1.0)
        if src is not None:
            # výbuch vlastní zbraně: jen jemné cuknutí, žádná vibrace
            self.shake(0.03 if not big else 0.08, PLAYER_FX_CAP)
        else:
            self.shake(0.12 if not big else 0.45, 0.7)
            if big:
                self.camera.vibrate(10)

    def enemies_on_segment(self, x1, y1, x2, y2, half_w: float) -> list:
        out = []
        dx, dy = x2 - x1, y2 - y1
        l2 = dx * dx + dy * dy or 1.0
        minx, maxx = min(x1, x2) - half_w - 40, max(x1, x2) + half_w + 40
        miny, maxy = min(y1, y2) - half_w - 40, max(y1, y2) + half_w + 40
        for e in self.enemies:
            if not e.alive:
                continue
            ex, ey = e.x, e.y
            if ex < minx or ex > maxx or ey < miny or ey > maxy:
                continue
            t = ((ex - x1) * dx + (ey - y1) * dy) / l2
            t = 0.0 if t < 0 else 1.0 if t > 1 else t
            px, py = x1 + dx * t - ex, y1 + dy * t - ey
            rr = half_w + e.r
            if px * px + py * py < rr * rr:
                out.append(e)
        for e in self.props:
            if e.alive:
                t = max(0.0, min(1.0, ((e.x - x1) * dx + (e.y - y1) * dy) / l2))
                if (x1 + dx * t - e.x) ** 2 + (y1 + dy * t - e.y) ** 2 < (half_w + e.r) ** 2:
                    out.append(e)
        return out

    def enemies_in_rect(self, l, t, r, b) -> list:
        return [e for e in self.enemies if e.alive and l < e.x < r and t < e.y < b]

    # --- cílení ------------------------------------------------------------------------------
    def nearest_enemy(self, x: float, y: float, max_d: float = 600.0, exclude: set | None = None):
        if exclude:
            return self.grid.nearest(x, y, max_d, lambda o: _targetable(o) and o.id not in exclude)
        return self.grid.nearest(x, y, max_d, _targetable)

    def targets(self, x: float, y: float, max_d: float, n: int) -> list:
        """n cílů; při menším počtu nepřátel se cíle opakují (vše dopadne i na osamoceného bosse)."""
        t = self.random_enemies(x, y, max_d, n)
        if t and len(t) < n:
            t = [t[i % len(t)] for i in range(n)]
        return t

    def random_enemies(self, x: float, y: float, max_d: float, n: int, nearest: bool = False) -> list:
        buf = self.grid.query(x, y, max_d)
        md2 = max_d * max_d
        cand = []
        for e in buf:
            if e.alive and not e.prop and e.alpha >= 128:
                d2 = (e.x - x) ** 2 + (e.y - y) ** 2
                if d2 < md2:
                    cand.append((d2, e))
        if not cand:
            return []
        if nearest or len(cand) <= n:
            cand.sort(key=lambda c: c[0])
            return [c[1] for c in cand[:n]]
        # preferovat bližší polovinu
        cand.sort(key=lambda c: c[0])
        pool = cand[: max(n * 3, len(cand) // 2)]
        picks = self.rng.sample(pool, min(n, len(pool)))
        return [c[1] for c in picks]

    # =====================================================================================
    # EFEKTY
    # =====================================================================================
    def add_proj(self, x, y, vx, vy, r, dmg, src, pierce=0, life=1.0, spr=None, kb=0.0) -> Proj:
        if self._proj_pool:
            p = self._proj_pool.pop()
            p.hits.clear()
        else:
            p = Proj()
        p.x, p.y, p.vx, p.vy, p.r, p.dmg, p.src = x, y, vx, vy, r, dmg, src
        p.pierce, p.life, p.spr, p.kb = pierce, life, spr, kb
        p.motion = M_STRAIGHT
        p.alive = True
        p.rot = None
        p.slow = p.freeze = p.stun = p.hyp = 0.0
        p.t = 0.0
        p.ret = False
        p.size = 1.0
        p.explode = 0.0
        p.z = 0.0
        p.ang = 0.0
        if len(self.projs) < MAX_PROJECTILES:
            self.projs.append(p)
        else:
            p.alive = False
        return p

    def add_area(self, x, y, r, dmg, tick, life, kind, src, slow=0.0, follow=False, color=(120, 220, 90)) -> Area:
        a = Area(x, y, r, dmg, tick, life, kind, src, slow, follow, color)
        self.areas.append(a)
        return a

    def add_wave(self, x, y, r0, r1, dur, dmg, src, kb=0.0, slow=0.0, stun=0.0, color=(255, 200, 120),
                 follow=False, hurt_player=0.0) -> Wave:
        w = Wave(x, y, r0, r1, dur, dmg, src, kb, slow, stun, color, follow, hurt_player)
        self.waves.append(w)
        return w

    def add_ring(self, x, y, r0, r1, life, color, width=6) -> None:
        if len(self.rings) < 60:
            self.rings.append(Ring(x, y, r0, r1, life, color, width))

    def add_beam(self, pts, width, life, color, kind="laser") -> None:
        if len(self.beams) < 80:
            self.beams.append(Beam(pts, width, life, color, kind))

    # =====================================================================================
    # PICKUPY, XP
    # =====================================================================================
    def drop_xp(self, x: float, y: float, value: float) -> None:
        if len(self.pickups) >= MAX_PICKUPS:
            # strop pickupů (B-49): XP nesmí zmizet do vzdáleného zrna mimo obrazovku
            near, nd = None, 160.0 * 160.0
            far, fd = None, -1.0
            px, py = self.player.x, self.player.y
            for pk in self.pickups:
                if pk.kind != P_XP or pk.attract:
                    continue
                d2 = (pk.x - x) ** 2 + (pk.y - y) ** 2
                if d2 < nd:
                    near, nd = pk, d2
                pd = (pk.x - px) ** 2 + (pk.y - py) ** 2
                if pd > fd:
                    far, fd = pk, pd
            if near is not None:
                near.value += value              # sloučit do zrna přímo u místa zabití
                return
            if far is not None:
                # nejvzdálenější staré zrno se „přestěhuje“ sem i se svou hodnotou – nic se neztratí
                far.alive = False
                self.pickups.remove(far)
                value += far.value
            else:
                return
        self.pickups.append(Pickup(x + self.rng.uniform(-4, 4), y + self.rng.uniform(-4, 4), P_XP, value))

    def _boss_xp(self, x: float, y: float) -> None:
        """Boss rush: poražený boss vysype zlatá vejce zhruba na RUSH_BOSS_LEVELS úrovní (B-53)."""
        need = sum(self.xp_needed(self.level + i) for i in range(RUSH_BOSS_LEVELS)) - self.xp
        need /= max(0.1, self.player.stats.growth)
        n = 6
        for i in range(n):
            a = i * math.tau / n + self.rng.uniform(-0.3, 0.3)
            pk = Pickup(x + math.cos(a) * 40, y + math.sin(a) * 40, P_GOLDEGG, need / n)
            pk.vz = 160
            pk.z = 1
            self.pickups.append(pk)

    def lay_golden_egg(self, x: float, y: float) -> None:
        pk = Pickup(x, y, P_GOLDEGG, max(10.0, self.xp_next * 0.35))
        pk.vz = 160
        pk.z = 1
        self.pickups.append(pk)
        self.sfx("cluck", 0.8)
        self.add_text(x, y - 30, "Zlaté vejce!", (255, 214, 70), 2, 1.0)

    def gain_xp(self, amount: float) -> None:
        self.xp += amount * self.player.stats.growth
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            self.pending_levelups += 1
            self.xp_next = self.xp_needed(self.level)

    def collect(self, pk: Pickup) -> None:
        k = pk.kind
        p = self.player
        if k == P_XP:
            self.gain_xp(pk.value)
            self.sfx("pickup", 0.5)
            if pk.value >= 3 or self.particles.rng.random() < 0.25:
                self.particles.sparkle(p.x, p.y - 12, (150, 230, 255), 1 if pk.value < 15 else 3)
        elif k == P_GOLDEGG:
            self.gain_xp(pk.value)
            self.sfx("gold", 0.7)
            self.particles.stars(pk.x, pk.y, 8, (255, 214, 70))
        elif k == P_WORM:
            p.heal(p.stats.max_hp * 0.3)
            self.add_text(p.x, p.y - 40, "+zdraví", (120, 255, 120), 2, 0.9)
            self.particles.sparkle(p.x, p.y - 12, (130, 255, 140), 6)
            self.particles.glow(p.x, p.y - 12, 30, (90, 200, 100), 0.2)
            self.sfx("heal")
        elif k == P_MAGNET:
            for q in self.pickups:
                if q.kind in (P_XP, P_GOLDEGG):
                    q.attract = True
            self.sfx("gold")
            self.add_text(p.x, p.y - 40, "MAGNET!", (255, 120, 120), 2, 1.0)
            self.particles.pop_ring(p.x, p.y - 10, 120, (255, 140, 140), 0.4)
        elif k == P_COIN:
            self.coins += int(pk.value)
            self.sfx("coin", 0.5)
            self.particles.sparkle(p.x, p.y - 14, (255, 220, 90), 2)
        elif k == P_CHEST:
            self.pending_chests.append("boss" if pk.value >= 2 else "elite")
            self.sfx("chest")
            self.particles.burst_ring(p.x, p.y - 14, 10, (255, 220, 110), 170)

    # =====================================================================================
    # KOKRHÁNÍ
    # =====================================================================================
    @property
    def crow_ready(self) -> bool:
        return self.crow_charge >= 1.0

    def crow(self, free: bool = False) -> bool:
        if self.state != "playing":
            return False
        if not free and not self.crow_ready:
            return False
        if not free:
            self.crow_charge = 0.0
            self.crows_used += 1
        p = self.player
        st = p.stats
        r = 290 * st.area
        self.add_wave(p.x, p.y, 20, r, 0.45, 40 * st.might, None, kb=560, stun=2.2, color=(255, 230, 120),
                      follow=True).crit = False
        self.add_ring(p.x, p.y, 10, r * 1.1, 0.6, (255, 255, 255), 10)
        for ep in self.eprojs:
            if (ep.x - p.x) ** 2 + (ep.y - p.y) ** 2 < r * r:
                ep.alive = False
                self.particles.sparks(ep.x, ep.y, 3, (255, 255, 200), 100)
        # bonus damage podle max HP běžných nepřátel
        for e in self.grid.query(p.x, p.y, r):
            if e.alive and not e.boss and (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < r * r:
                self.damage_enemy(e, e.max_hp * 0.25, None, crit=False)
        p.invuln = max(p.invuln, 1.0)
        self.flash((255, 250, 220), 0.15)
        self.shake(0.6)
        self.camera.vibrate(14)
        self.particles.stars(p.x, p.y - 20, 16, (255, 230, 90), 280)
        self.particles.glow(p.x, p.y - 14, 60, (255, 210, 110), 0.25)
        self.add_text(p.x, p.y - 60, "KIKIRIKÍ!", (255, 230, 90), 4, 1.2)
        self.sfx("crow", 1.0)
        if self.final_boss is not None and isinstance(getattr(self.final_boss, "wind", None), float):
            self.final_boss.wind = 0.0
            self.final_boss.inhale = 0.0
        return True

    # =====================================================================================
    # ARÉNA
    # =====================================================================================
    def clamp_to_arena(self, ent) -> None:
        if self.arena is None:
            return
        ax, ay, ar = self.arena
        dx, dy = ent.x - ax, ent.y - ay
        d = math.hypot(dx, dy)
        lim = ar - ent.r
        if d > lim:
            ent.x = ax + dx / d * lim
            ent.y = ay + dy / d * lim
            if ent is self.player:
                # odraz od plotu dovnitř arény
                ent.vx -= dx / d * 260
                ent.vy -= dy / d * 260
                if self.player.take_damage(6 * self.diff.dmg, ent.x + dx / d * 20, ent.y + dy / d * 20, "plot"):
                    self.particles.sparks(ent.x + dx / d * ent.r, ent.y + dy / d * ent.r, 10, (140, 220, 255), 200)
                    self.sfx("zap", 0.7)

    # =====================================================================================
    # HLAVNÍ UPDATE
    # =====================================================================================
    def update(self, dt: float, mx: float = 0.0, my: float = 0.0, crow: bool = False) -> None:
        if self.state in ("levelup", "chest", "dead", "victory", "paused"):
            return
        if self.state == "dying":
            self.state_t -= dt
            self.particles.update(dt)
            self._update_fx(dt * 0.3)
            self.camera.update(dt)
            if self.state_t <= 0:
                self.state = "dead"
            return
        if self.state == "victory_anim":
            self.state_t -= dt          # čas runu stojí – výsledný čas = okamžik porážky bosse (B-66)
            self._victory_tick(dt)
            if self.state_t <= 0:
                self._settle_chests()
                self.state = "victory"
            return

        # zpomalení času
        real_dt = dt
        if self.slowmo_t > 0:
            self.slowmo_t -= real_dt
            self.timescale = 0.25 if self.slowmo_t > 0 else 1.0
        self.slowmo_cd = max(0.0, self.slowmo_cd - real_dt)
        dt = dt * self.timescale

        self.tick += 1
        self.time += dt
        self.flash_t = max(0.0, self.flash_t - real_dt)
        self.flash_cd = max(0.0, self.flash_cd - real_dt)
        if crow:
            self.crow()

        p = self.player
        self.map.apply_zones(p)
        p.update(dt, mx, my)
        if p.no_hit_time > self.best_no_hit:
            self.best_no_hit = p.no_hit_time
        self.map.ensure(p.x, p.y)
        self.map.update_barrels(dt)
        self.map.update_hazards(dt)
        self.director.update(dt)

        # grid
        grid = self.grid
        grid.clear()
        cells = grid.cells
        inv = grid.inv
        for e in self.enemies:
            k = int((e.x + OFF) * inv) * KMUL + int((e.y + OFF) * inv)
            e.cell = k
            lst = cells.get(k)
            if lst is None:
                cells[k] = [e]
            else:
                lst.append(e)
        for e in self.props:
            grid.insert(e, e.x, e.y)

        for w in self.weapons:
            w.update(dt)
        for a in self.allies:
            if a.alive:
                a.update(dt)
        update_enemies(self, dt)
        self._update_projs(dt)
        self._update_eprojs(dt)
        self._update_areas(dt)
        self._update_waves(dt)
        self._update_bombs(dt)
        self._update_pickups(dt)
        self._update_fx(dt)
        self.particles.update(dt)

        # úklid
        self.enemies = [e for e in self.enemies if e.alive]
        if self.bosses and any(not c.e.alive for c in self.bosses):
            self.bosses = [c for c in self.bosses if c.e.alive]
        if self.tick % 30 == 0:
            self.allies = [a for a in self.allies if a.alive]

        # hustota efektů podle davu (jen vizuál): čitelnost a výkon v pozdní hře
        ne = len(self.enemies)
        self.particles.density = 1.0 if ne < 80 else max(0.4, 1.0 - (ne - 80) / 450)

        # masakr → zpomalení
        self._burst.append(self._kills_tick)
        self._kills_tick = 0
        burst = sum(self._burst)
        self.max_burst = max(self.max_burst, burst)
        if burst >= 50 and self.slowmo_cd <= 0:
            self.slowmo_t = 0.3
            self.slowmo_cd = 4.0
            self.banner("MASAKR!", (255, 80, 80), 1.2)
            self.sfx("slowmo")
            self.flash((255, 255, 255), 0.08)
            self.camera.vibrate(10)

        # kamera
        self.camera.follow(p.x, p.y, real_dt, p.vx * 0.12, p.vy * 0.12)
        self.camera.update(real_dt)

        # intenzita hudby
        self.intensity = min(1.0, len(self.enemies) / 260.0 + (0.5 if self.bosses else 0.0))

        # úrovně, bedny – nejvýš jedno přerušení za PAUSE_GAP s; čekající level-upy se pak ukážou za sebou (B-51)
        if self.pause_cd > 0:
            self.pause_cd -= dt
        if self.state == "playing" and not p.dead and self.pause_cd <= 0:
            if self.pending_levelups > 0:
                self._open_levelup()
            elif self.pending_chests:
                self._open_chest()

    def _open_levelup(self) -> None:
        from .. import progression
        if not progression.has_choices(self):
            # build je kompletní – levelup jen vyléčí a hru nepřeruší
            n = self.pending_levelups
            self.pending_levelups = 0
            p = self.player
            p.heal(p.stats.max_hp * progression.HEAL_FILL * n)
            self.add_text(p.x, p.y - 46, f"Úr. {self.level}  +zdraví", (120, 255, 140), 2, 1.2)
            self.particles.stars(p.x, p.y - 20, 6, (120, 255, 140), 90)
            self.particles.glow(p.x, p.y - 14, 34, (90, 200, 110), 0.2)
            self.sfx("heal", 0.6)
            return
        self.state = "levelup"
        self.offer = progression.make_offer(self)
        self.particles.burst_ring(self.player.x, self.player.y - 16, 14, (255, 220, 90), 210)
        self.particles.glow(self.player.x, self.player.y - 16, 54, (255, 210, 100), 0.3)
        self.sfx("levelup")
        self.camera.vibrate(6)

    def _open_chest(self) -> None:
        from .. import progression
        kind = self.pending_chests.pop(0)
        self.state = "chest"
        self.chest_reward = progression.open_chest(self, kind)

    def resume(self) -> None:
        """Po výběru karty / zavření bedny."""
        self.offer = None
        self.chest_reward = None
        self.state = "playing"
        if self.pending_levelups > 0:
            self._open_levelup()
        elif self.pending_chests:
            self._open_chest()
        if self.state == "playing":
            self.pause_cd = PAUSE_GAP

    def on_player_death(self) -> None:
        if self.victory:
            # smrt ve stejném ticku jako porážka finálního bosse – vítězství má přednost
            p = self.player
            p.dead = False
            p.hp = max(1.0, p.hp)
            return
        self.state = "dying"
        self.state_t = 1.4
        p = self.player
        self.particles.feathers(p.x, p.y, 40, (250, 248, 240), 260)
        self.particles.glow(p.x, p.y - 12, 70, (255, 240, 220), 0.3)
        self.particles.smoke(p.x, p.y, 8, (80, 72, 80), 14, 4, 40, 1.2)
        self.sfx("defeat")
        self.shake(0.7)
        self.camera.vibrate(16)
        self.timescale = 1.0

    def revive(self) -> None:
        p = self.player
        p.dead = False
        p.hp = p.stats.max_hp * 0.5
        p.invuln = 3.0
        self.revived = True
        self.state = "playing"
        self.crow(free=True)
        self.sfx("revive")
        self.banner("Oživena!" if self.char.female else "Oživen!", (120, 255, 120), 1.6)

    def _settle_chests(self) -> None:
        """Bedny sebrané během vítězné animace (nebo ležící na zemi) se po výhře převedou na mince (B-50)."""
        n = len(self.pending_chests)
        coins = sum(40 if k == "boss" else 25 for k in self.pending_chests)
        for pk in self.pickups:
            if pk.alive and pk.kind == P_CHEST:
                n += 1
                coins += 40 if pk.value >= 2 else 25
                pk.alive = False
        self.pending_chests = []
        if n:
            self.coins += coins
            self.chest_coins = (n, coins)

    def _victory_tick(self, dt: float) -> None:
        # nepřátelé se rozpadají ve slunečním světle
        n = 0
        for e in self.enemies:
            if e.alive and n < 8:
                e.alive = False
                self.particles.puff(e.x, e.y, 3, (255, 230, 180), 60)
                n += 1
        self.enemies = [e for e in self.enemies if e.alive]
        self.particles.update(dt)
        self._update_pickups(dt, magnet_all=True)
        self._update_fx(dt)
        self.camera.update(dt)

    # --- dílčí update -------------------------------------------------------------------------
    def _update_projs(self, dt: float) -> None:
        p = self.player
        px, py = p.x, p.y
        grid = self.grid
        cells = grid.cells
        inv = grid.inv
        pool = self._proj_pool
        keep = []
        sqrt = math.sqrt
        cos, sin = math.cos, math.sin
        for pr in self.projs:
            if not pr.alive:
                pool.append(pr)
                continue
            m = pr.motion
            if m == M_LOB:
                pr.t += dt
                k = pr.t / pr.dur
                if k >= 1.0:
                    pr.x, pr.y = pr.tx, pr.ty
                    pr.alive = False
                    if pr.src is not None:
                        pr.src.on_land(pr)
                    pool.append(pr)
                    continue
                pr.x = pr.sx + (pr.tx - pr.sx) * k
                pr.y = pr.sy + (pr.ty - pr.sy) * k
                pr.z = sin(k * math.pi) * pr.height
                keep.append(pr)
                continue
            if m == M_SPIRAL:
                pr.ang += pr.spin * dt
                pr.rad += pr.vx * dt
                pr.x = px + cos(pr.ang) * pr.rad
                pr.y = py - 8 + sin(pr.ang) * pr.rad
            elif m == M_BOOMERANG:
                pr.t += dt
                if not pr.ret:
                    pr.x += pr.vx * dt
                    pr.y += pr.vy * dt
                    pr.rad -= sqrt(pr.vx * pr.vx + pr.vy * pr.vy) * dt
                    if pr.rad <= 0:
                        pr.ret = True
                        pr.hits.clear()
                else:
                    dx, dy = px - pr.x, py - 10 - pr.y
                    d = sqrt(dx * dx + dy * dy) or 1
                    sp = sqrt(pr.vx * pr.vx + pr.vy * pr.vy) * 1.15 + pr.t * 60
                    if d < sp * dt + 14:
                        pr.alive = False
                        pool.append(pr)
                        continue
                    pr.x += dx / d * sp * dt
                    pr.y += dy / d * sp * dt
                pr.ang += dt * 14
            else:
                pr.x += pr.vx * dt
                pr.y += pr.vy * dt
                if m == M_WAVE:
                    pr.r = 16 * pr.size * (1 + pr.t * 1.4)
                    pr.t += dt
            pr.life -= dt
            if pr.life <= 0:
                pr.alive = False
                if pr.explode:
                    self.explosion(pr.x, pr.y, pr.explode, pr.dmg * 0.6, pr.src, (255, 200, 120), kb=100)
                pool.append(pr)
                continue
            # kolize
            r = pr.r
            x0 = int((pr.x - r - 24 + OFF) * inv)
            x1 = int((pr.x + r + 24 + OFF) * inv)
            y0 = int((pr.y - r - 24 + OFF) * inv)
            y1 = int((pr.y + r + 24 + OFF) * inv)
            dead = False
            for cx in range(x0, x1 + 1):
                base = cx * KMUL
                for cy in range(y0, y1 + 1):
                    lst = cells.get(base + cy)
                    if not lst:
                        continue
                    for e in lst:
                        if not e.alive or e.alpha < 128:
                            continue
                        ex = e.x - pr.x
                        ey = e.y - pr.y
                        rr = e.r + r
                        if ex * ex + ey * ey < rr * rr:
                            eid = e.id
                            if eid in pr.hits:
                                continue
                            pr.hits.add(eid)
                            self.damage_enemy(e, pr.dmg, pr.src, pr.vx or ex, pr.vy or ey, pr.kb, True, pr.slow,
                                              1.4, pr.freeze, pr.stun, pr.hyp)
                            if pr.explode:
                                self.explosion(pr.x, pr.y, pr.explode, pr.dmg * 0.6, pr.src, (255, 200, 120), kb=100)
                                pr.explode = 0.0
                            if pr.pierce <= 0:
                                dead = True
                                break
                            pr.pierce -= 1
                    if dead:
                        break
                if dead:
                    break
            if dead:
                pr.alive = False
                pool.append(pr)
                continue
            keep.append(pr)
        self.projs = keep

    def _update_eprojs(self, dt: float) -> None:
        p = self.player
        keep = []
        for ep in self.eprojs:
            if not ep.alive:
                continue
            ep.x += ep.vx * dt
            ep.y += ep.vy * dt
            ep.life -= dt
            ep.rot += dt * 10
            if ep.life <= 0:
                continue
            dx, dy = p.x - ep.x, p.y - 8 - ep.y
            rr = ep.r + p.r
            if dx * dx + dy * dy < rr * rr and not p.dead:
                p.take_damage(ep.dmg, ep.x, ep.y, "projektil")
                if ep.kind == 0:
                    self.particles.blobs(ep.x, ep.y, 5, (130, 240, 80))
                continue
            keep.append(ep)
        self.eprojs = keep

    def _update_areas(self, dt: float) -> None:
        p = self.player
        keep = []
        for a in self.areas:
            if not a.alive:
                continue
            a.life -= dt
            if a.life <= 0:
                continue
            if a.follow:
                a.x, a.y = p.x, p.y
            a.next -= dt
            if a.next <= 0:
                a.next = a.tick
                self.area_damage(a.x, a.y, a.r, a.dmg, a.src, slow=a.slow, slow_t=a.tick + 0.3, crit=False, flash=False)
                if a.kind == "cloud" and self.tick % 2 == 0:
                    self.particles.puff(a.x + self.rng.uniform(-a.r, a.r) * 0.6, a.y + self.rng.uniform(-a.r, a.r) * 0.4,
                                        1, a.color, 20, 10)
            keep.append(a)
        self.areas = keep

    def _update_waves(self, dt: float) -> None:
        p = self.player
        keep = []
        for w in self.waves:
            w.life -= dt
            k = 1.0 - max(0.0, w.life) / w.maxlife
            w.r = w.r0 + (w.r1 - w.r0) * k
            if w.follow:
                w.x, w.y = p.x, p.y
            if w.dmg > 0 or w.kb > 0:
                self.area_damage(w.x, w.y, w.r, w.dmg, w.src, kb=w.kb, slow=w.slow, slow_t=2.0, stun=w.stun,
                                 crit=w.crit, exclude=w.hit)
            if w.hurt_player and not w.player_hit:
                d2 = (p.x - w.x) ** 2 + (p.y - w.y) ** 2
                if d2 < (w.r + p.r) ** 2 and d2 > (w.r - 40) ** 2:
                    w.player_hit = True
                    p.take_damage(w.hurt_player, w.x, w.y, "vlna")
            if w.life > 0:
                keep.append(w)
        self.waves = keep

    def _update_bombs(self, dt: float) -> None:
        if not self.bombs:
            return
        keep = []
        for b in self.bombs:
            b[2] -= dt
            if b[2] <= 0:
                x, y, _, r, dmg_p, dmg_e, src, col, _w = b
                self.explosion(x, y, r, dmg_e, src, col, kb=220, hurt_player=dmg_p, crit=src is not None)
            else:
                keep.append(b)
        self.bombs = keep

    def _update_pickups(self, dt: float, magnet_all: bool = False) -> None:
        p = self.player
        px, py = p.x, p.y
        mag = p.stats.magnet
        mag2 = mag * mag
        keep = []
        sqrt = math.sqrt
        for pk in self.pickups:
            if not pk.alive:
                continue
            pk.t += dt
            if pk.vz or pk.z > 0:
                pk.z += pk.vz * dt
                pk.vz -= 700 * dt
                if pk.z <= 0:
                    pk.z = 0.0
                    pk.vz = 0.0
            dx = px - pk.x
            dy = py - pk.y
            d2 = dx * dx + dy * dy
            if not pk.attract:
                lim = mag2 if pk.kind != P_CHEST else 900
                if d2 < lim or magnet_all:
                    pk.attract = True
                else:
                    keep.append(pk)
                    continue
            d = sqrt(d2) or 1
            if d < p.r + 10:
                self.collect(pk)
                continue
            sp = 260 + pk.t * 120 if pk.kind != P_CHEST else 120
            sp = min(sp, 900)
            pk.x += dx / d * sp * dt
            pk.y += dy / d * sp * dt
            keep.append(pk)
        self.pickups = keep

    def _update_fx(self, dt: float) -> None:
        for lst_name in ("rings", "beams", "texts"):
            lst = getattr(self, lst_name)
            if not lst:
                continue
            keep = []
            for o in lst:
                o.life -= dt
                if lst_name == "texts":
                    o.y += o.vy * dt
                    o.vy *= 0.94
                if o.life > 0:
                    keep.append(o)
            setattr(self, lst_name, keep)
        if self.telegraphs:
            keep = []
            for t in self.telegraphs:
                t.t += dt
                if t.t >= t.dur:
                    if t.cb is not None:
                        t.cb(t)
                    continue
                keep.append(t)
            self.telegraphs = keep
        if self.banners:
            for b in self.banners:
                b[2] -= dt
            self.banners = [b for b in self.banners if b[2] > 0]
        if self.speech:
            for s in self.speech:
                s[2] -= dt
            self.speech = [s for s in self.speech if s[2] > 0]

    # =====================================================================================
    # VÝSLEDEK
    # =====================================================================================
    @property
    def final_time(self) -> float:
        return self.director.final_time

    def build_summary(self) -> list[tuple[str, int, float, bool]]:
        return [(w.id, w.level, w.damage_dealt, w.evolved) for w in self.weapons]


def _targetable(o) -> bool:
    """Cíl auto-aimu: živý nepřítel, ne sud, ne neviditelný boss (Pan Liška Špión v mlze)."""
    return not o.prop and o.alive and o.alpha >= 128
