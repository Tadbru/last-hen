"""Lehké entity se __slots__ (nepřátelé, projektily, efekty, pickupy)."""
from __future__ import annotations

# --- pohyb projektilů ---
M_STRAIGHT, M_SPIRAL, M_BOOMERANG, M_LOB, M_WAVE = range(5)

# --- pickupy ---
P_XP, P_GOLDEGG, P_WORM, P_MAGNET, P_COIN, P_CHEST = range(6)

_ids = [0]


def next_id() -> int:
    _ids[0] += 1
    return _ids[0]


class Enemy:
    __slots__ = ("d", "id", "x", "y", "kx", "ky", "hp", "max_hp", "speed", "dmg", "r", "xp", "alive",
                 "flash", "flash_cd", "slow_t", "slow_f", "stun_t", "hyp_t", "freeze_t", "anim", "face", "armor",
                 "ctrl", "elite", "boss", "prop", "flyer", "touch_cd", "t", "cd", "state", "spr", "kb_res",
                 "ai", "tint", "alpha", "cell", "bob", "summoned", "fuse", "hx", "hy", "rage", "chest",
                 "charm_t", "foe")

    def __init__(self, d, x: float, y: float, hp: float, speed: float, dmg: float, spr) -> None:
        self.d = d
        self.id = next_id()
        self.x = x
        self.y = y
        self.kx = 0.0
        self.ky = 0.0
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.dmg = dmg
        self.r = d.radius
        self.xp = d.xp
        self.alive = True
        self.flash = 0.0
        self.flash_cd = 0.0     # rozestup bílých bliknutí bosse/elity (B-69)
        self.slow_t = 0.0
        self.slow_f = 0.0
        self.stun_t = 0.0
        self.hyp_t = 0.0
        self.freeze_t = 0.0
        self.anim = 0.0
        self.face = 1
        self.armor = d.armor_hp
        self.ctrl = None
        self.elite = d.elite
        self.boss = False
        self.prop = d.prop
        self.flyer = d.flyer
        self.touch_cd = 0.0
        self.t = 0.0
        self.cd = 0.0
        self.state = 0
        self.spr = spr
        self.kb_res = d.kb_res
        self.ai = d.ai
        self.tint = None
        self.alpha = 255
        self.cell = 0
        self.bob = 0.0
        self.summoned = False
        self.fuse = 0.0
        self.hx = 0.0
        self.hy = 0.0
        self.rage = False
        self.chest = d.elite
        self.charm_t = 0.0      # okouzlení Divou (ultimátka Božská krása) – bojuje za hráče
        self.foe = None         # cíl okouzlené lišky


class Proj:
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "pierce", "life", "spr", "hits", "kb", "motion",
                 "ang", "rad", "spin", "t", "src", "slow", "freeze", "stun", "hyp", "alive", "rot",
                 "sx", "sy", "tx", "ty", "dur", "height", "z", "ret", "size", "color", "explode", "data")

    def __init__(self) -> None:
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.r = 6.0
        self.dmg = 1.0
        self.pierce = 0
        self.life = 1.0
        self.spr = None
        self.hits: set = set()
        self.kb = 0.0
        self.motion = M_STRAIGHT
        self.ang = 0.0
        self.rad = 0.0
        self.spin = 0.0
        self.t = 0.0
        self.src = None
        self.slow = 0.0
        self.freeze = 0.0
        self.stun = 0.0
        self.hyp = 0.0
        self.alive = True
        self.rot = None          # seznam rotací spritu
        self.sx = self.sy = 0.0  # start (lob)
        self.tx = self.ty = 0.0  # cíl (lob)
        self.dur = 1.0
        self.height = 60.0
        self.z = 0.0
        self.ret = False
        self.size = 1.0
        self.color = (255, 255, 255)
        self.explode = 0.0
        self.data = None


class EProj:
    """Nepřátelský projektil (sliz, mrkev, peří…)."""
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "life", "spr", "alive", "kind", "rot")

    def __init__(self, x, y, vx, vy, r, dmg, life, spr, kind=0) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.r, self.dmg, self.life, self.spr = r, dmg, life, spr
        self.alive = True
        self.kind = kind
        self.rot = 0.0


class Area:
    """Plošný efekt s periodickým poškozením (mrak, šlehačka, aura)."""
    __slots__ = ("x", "y", "r", "dmg", "tick", "next", "life", "maxlife", "slow", "kind", "follow", "src",
                 "alive", "color", "stun", "hurt_player")

    def __init__(self, x, y, r, dmg, tick, life, kind, src=None, slow=0.0, follow=False, color=(120, 220, 90)):
        self.x, self.y, self.r, self.dmg = x, y, r, dmg
        self.tick = tick
        self.next = 0.0
        self.life = life
        self.maxlife = life
        self.slow = slow
        self.kind = kind
        self.follow = follow
        self.src = src
        self.alive = True
        self.color = color
        self.stun = 0.0
        self.hurt_player = 0.0


class Beam:
    __slots__ = ("pts", "width", "life", "maxlife", "color", "kind", "alive")

    def __init__(self, pts, width, life, color, kind="laser"):
        self.pts = pts
        self.width = width
        self.life = life
        self.maxlife = life
        self.color = color
        self.kind = kind
        self.alive = True


class Ring:
    """Rozpínající se kruh (vizuál rázové vlny / výbuchu)."""
    __slots__ = ("x", "y", "r0", "r1", "life", "maxlife", "color", "width", "alive", "follow")

    def __init__(self, x, y, r0, r1, life, color, width=6, follow=False):
        self.x, self.y, self.r0, self.r1 = x, y, r0, r1
        self.life = life
        self.maxlife = life
        self.color = color
        self.width = width
        self.alive = True
        self.follow = follow


class Telegraph:
    """Varovná značka na zemi. Po vypršení zavolá callback (např. dopad útoku)."""
    __slots__ = ("kind", "x", "y", "r", "x2", "y2", "w", "t", "dur", "color", "cb", "alive", "data")

    def __init__(self, kind, x, y, r, dur, cb=None, x2=0.0, y2=0.0, w=0.0, color=(255, 60, 60), data=None):
        self.kind = kind
        self.x, self.y, self.r = x, y, r
        self.x2, self.y2, self.w = x2, y2, w
        self.t = 0.0
        self.dur = dur
        self.color = color
        self.cb = cb
        self.alive = True
        self.data = data       # např. id nepřítele, který padá z nebe


class FloatText:
    __slots__ = ("x", "y", "text", "color", "life", "maxlife", "scale", "vy", "alive")

    def __init__(self, x, y, text, color, life=0.7, scale=2, vy=-40):
        self.x, self.y, self.text, self.color = x, y, text, color
        self.life = life
        self.maxlife = life
        self.scale = scale
        self.vy = vy
        self.alive = True


class Pickup:
    __slots__ = ("x", "y", "kind", "value", "attract", "vx", "vy", "t", "alive", "z", "vz")

    def __init__(self, x, y, kind, value=1):
        self.x, self.y = x, y
        self.kind = kind
        self.value = value
        self.attract = False
        self.vx = 0.0
        self.vy = 0.0
        self.t = 0.0
        self.alive = True
        self.z = 0.0
        self.vz = 0.0
