"""Pixel mapy všech postav, nepřátel, bossů, projektilů a dekorací + SpriteBank.

Mapy obsahují jen barevné plochy směřující doprava; obrys, stínování, zrcadlení
a bílé „flash“ verze se generují při startu.
"""
from __future__ import annotations

import math

import pygame

from ..config import PX
from . import pixelart as pa

# ---------------------------------------------------------------------------
# HRÁČSKÁ ZVÍŘATA (body + 2 sady nohou pro walk cycle)
# ---------------------------------------------------------------------------
HEN = dict(body="""
..........rr...
.........rrrr..
.........wwww..
........wwwkwo.
........wwwwwoo
..ww....wwwwr..
.wWWw..wwwwwr..
.wWWWwwwwwwww..
.wWWwwWWWwwwww.
..wwwWWWWWwwww.
..wwwwWWWwwwww.
...wwwwwwwwww..
.....wwwwwww...
""", legs=("""
......o..o.....
.....oo.oo.....
""", """
.....o....o....
....oo...oo....
"""))

DUCK = dict(body="""
........uuu....
.......uuuuu...
......uuuuuuu..
.......yyyyy...
.......yykyyoo.
.......yyyyyooo
........yyyy...
...y....yyy....
..yyy..yyyyy...
..yYyyyyyyyyy..
.yyYYYyyyyyyyy.
.yyyYYYYyyyyyy.
..yyyyyyyyyyy..
....yyyyyyyy...
""", legs=("""
......o..o.....
.....ooooooo...
""", """
.....o....o....
....ooo..ooo...
"""))

GOOSE = dict(body="""
........nnwww..
........nwwwkw.
.........wwwwoo
.........wwwooo
..........ww...
..........ww...
..........ww...
...ww....www...
..wWWw..wwww...
..wWWWwwwwwww..
.wWWWWWwwwwwww.
.wwWWWWWwwwwww.
..wwwwwwwwwwww.
...wwwwwwwwww..
.....wwwwwww...
""", legs=("""
......o..o.....
.....oo.oo.....
""", """
.....o....o....
....oo...oo....
"""))

TURKEY = dict(body="""
..OcO..........
.ObcbO....RRR..
OcbcbcO..RRRRR.
cbcbcbc.RRllkl.
ObcbcbO...lllyy
.cbcbc....lrr..
..bbbb...bll...
.bBbbbbbbbbb...
.bBBbbbbbbbbbb.
.bBBBbbbbbbbbb.
..bBBBbbbbbbb..
...bbbbbbbbbb..
.....bbbbbb....
""", legs=("""
......y..y.....
.....yy.yy.....
""", """
.....y....y....
....yy...yy....
"""))

ROOSTER = dict(body="""
.........hhhh..
........hhhhhh.
.........hhh...
........fffkkk.
........ffffyy.
..ZZ....fffr...
.ZvvZ..ffffr...
ZvZZvZffffff...
Z.ZvZffffffff..
..ZZfFFFffffff.
...fFFFFFfffff.
...ffFFFfffff..
.....fffffff...
""", legs=("""
......y..y.....
.....yy.yy.....
""", """
.....y....y....
....yy...yy....
"""))

PEACOCK = dict(body="""
..ttt.......p.p.
.tytyt.......p..
tyUtUyt.....uuu.
tUttttUt...uuuky
tyttttyt...uuuyy
tUtyytUt...uuu..
.tyttyt...uuu...
..ttttuuuuuuu...
...tUuuuuuuuu...
....uuUUUuuuu...
.....uuUUuuu....
......uuuuu.....
""", legs=("""
.......g..g.....
......gg.gg.....
""", """
......g....g....
.....gg...gg....
"""))

PENGUIN = dict(body="""
....UUUU.....
...UUUUUU....
...UUUwkwoo..
...UUUwwwoo..
...rrrrrrr...
..rUUUUwwwr..
.UUUUUwwwww..
UU.UUUwwwwww.
...UUUwwwwww.
...UUUwwwwww.
...UUUwwwwww.
....UUwwwww..
.....UUUUU...
""", legs=("""
....oo.oo....
""", """
...oo...oo...
"""))

MAGPIE = dict(body="""
...........kkk..
..........kkkkk.
..........kkxkmm
..........kkkk..
tt.......kkkk...
.ttt....kkwwk...
..tttkkkkwwwwk..
...tkkkqqwwwwk..
....kkqqqwwwwk..
.....kkqqwwwk...
......kkwwwk....
.......kkkk.....
""", legs=("""
........m..m....
.......mm.mm....
""", """
.......m....m...
......mm...mm...
"""), palette={"k": (52, 50, 72), "x": (255, 255, 255)})

PLAYER_MAPS = {
    "hen": HEN, "duck": DUCK, "goose": GOOSE, "turkey": TURKEY,
    "rooster": ROOSTER, "peacock": PEACOCK, "penguin": PENGUIN, "magpie": MAGPIE,
}

# Špička zobáku v mapě těla (art px, sloupec / řádek, postava hledí doprava) – odtud střílí Zobák-laser
PLAYER_BEAK = {
    "hen": (14, 4), "duck": (14, 4.5), "goose": (14, 2.5), "turkey": (14, 4),
    "rooster": (13, 4), "peacock": (15, 3.5), "penguin": (10, 2.5), "magpie": (15, 2),
}
_beak_cache: dict = {}


def beak_offset(cid: str, face: int, lying: bool = False) -> tuple[float, float]:
    """Posun špičky zobáku od pozice hráče (px) přesně podle toho, jak RunRenderer kreslí sprite:
    obraz (w × h) s levým horním rohem v (x − w/2, y − h + 9). face 1 = zrcadleně, lying = klouzající tučňák
    (sprite otočený o 90° hlavou ve směru jízdy). Počítá se z map, bez Surface – funguje i headless."""
    key = (cid, face, lying)
    v = _beak_cache.get(key)
    if v is not None:
        return v
    spec = PLAYER_MAPS.get(cid, HEN)
    body = pa.parse_map(spec["body"])
    legs = pa.parse_map(spec["legs"][0]) if spec.get("legs") else []
    rows = body + legs
    w = (max(len(r) for r in rows) + 2) * PX           # +2 = automatický obrys
    h = (len(rows) + 2) * PX
    tx, ty = PLAYER_BEAK.get(cid, (len(body[0]) - 1, 3))
    px, py = (tx + 1.5) * PX, (ty + 1.5) * PX            # střed pixelu v obrazu (včetně obrysu)
    sign = 1.0 if face == 0 else -1.0
    if lying:
        v = (sign * (h / 2 - py), -w + 9 + px)
    else:
        v = (sign * (px - w / 2), -h + 9 + py)
    _beak_cache[key] = v
    return v

# Skiny – doplňky přes hlavu (souřadnice relativně k hlavě postavy)
SKIN_HATS = {
    "pirate": ("""
..kkkk..
.kkwkkk.
yyyyyyyy
""", {}),      # zlatý lem – černý klobouk na tmavé hlavě Straky splýval (B-108)
    "cowboy": ("""
...bbb...
..bbbbb..
bbbbbbbbb
""", {}),
    "astronaut": ("""
.lllll.
l.....l
l.....l
""", {}),
    "ninja": ("""
kkkkkkk
rrrrrrr
""", {}),
    "pumpkin": ("""
...v...
.ooooo.
ookoook
ooooooo
""", {}),
    "santa": ("""
....w
..rrr.
.rrrrr
wwwwwww
""", {}),
    "bunny": ("""
.w...w.
.n...n.
.w...w.
""", {}),
    # tajné skiny za kompletní kategorie sbírky
    "ushanka": ("""
..OOOOO..
.OoooooO.
OoooooooO
wwwwwwwww
Oo.....oO
""", {}),
    "crown": ("""
y..y..y
yy.y.yy
yyyyyyy
yryyyry
YYYYYYY
""", {}),
    "helmet": ("""
...ZZZ...
.ZZzzzZZ.
ZzzzzzzzZ
ZZZZZZZZZ
""", {}),
    "halo": ("""
..yyyyy..
.y.....y.
..yyyyy..
.........
.........
""", {}),
    "wizard": ("""
.....p...
....pp...
...ppp...
...pyp...
..ppppp..
.ppppppp.
PPPPPPPPP
""", {}),
}

# ---------------------------------------------------------------------------
# NEPŘÁTELÉ
# ---------------------------------------------------------------------------
FOX = dict(body="""
...........O.O..
..........OOOO..
..........OeOOc.
..........OOOcck
.c.......OOOcc..
cOc..OOOOOOO....
cOOOOOOZOOOO....
.cOOOOZZOOOO....
..OOOOOOOOOO....
...cccOOOccc....
""", legs=("""
...O.O..O.O.....
...O.O..O.O.....
""", """
..O...O.O...O...
..O...O.O...O...
"""), palette={"O": (196, 108, 52), "c": (222, 206, 172), "Z": (96, 160, 80), "e": (190, 255, 110)})

FAST_FOX = dict(body="""
.........O.O..
........OOOO..
........OrOOc.
........OOOcck
cc.....OOOc...
.cOOOOOOOO....
..OOOOOOOO....
...cccOOcc....
""", legs=("""
..O..O.O..O...
.O...O.O...O..
""", """
...OO...OO....
...O.....O....
"""), palette={"O": (236, 168, 70), "c": (250, 232, 196), "r": (255, 60, 60)})

ARMOR_HELMET = """
..........sss...
.........ssmss..
.........smmmms.
"""

SPITTER = dict(body="""
...........O.O..
..........OOOO..
..........OeOOc.
..........OOOOcc
.c.......OOOOzz.
cOc..OOOOOOO.z..
cOOOOOOZOOOO....
.cOOOOZZOOOO....
..OOOOOOOOOO....
...cccOOOccc....
""", legs=FOX["legs"], palette={"O": (150, 172, 64), "c": (210, 220, 150), "Z": (110, 60, 150),
                                 "e": (255, 120, 255), "z": (130, 240, 80)})

EXPLODER_BOMB = """
.......y....
......y.....
.....GG.....
....GGGG....
....GGGG....
"""

WOLF = dict(body="""
..............G..G..
.............GgggG..
.............gegggw.
.............ggggwwk
..g.........gggwww..
.gGg...gggggggg.....
gGggggggZggggggg....
.gGggggZZggggggg....
..gggggggggggggg....
..ggggggggggggg.....
...wwwgggggwwww.....
""", legs=("""
...gg.gg...gg.gg....
...gg.gg...gg.gg....
""", """
..gg...gg.gg...gg...
..gg...gg.gg...gg...
"""), palette={"g": (138, 138, 150), "G": (90, 90, 106), "Z": (96, 160, 80), "e": (190, 255, 110)})

BAT_A = """
p.............p
pp...........pp
ppp...PPP...ppp
.pppppPePPppppp
..ppppPPPpppp..
......p.p......
"""
BAT_B = """
......PPP......
......PeP......
...ppPPPPPpp...
.ppppppppppppp.
pp..pp...pp..pp
p.............p
"""
BAT_PAL = {"p": (120, 62, 150), "P": (80, 40, 104), "e": (190, 255, 110)}

OWL = dict(body="""
...pp....pp.....
..pPPp..pPPp....
..pPPPppPPPp....
..pbbbbbbbbp..e.
.pbyykbbkyybp.B.
.pbyyybbyyybp.B.
.pbbbbYYbbbbp.B.
.ppbbbbbbbbppBB.
pPPpbcbbcbpPPpB.
pPPPbccccbPPPpB.
pPPPbccccbPPPpB.
.pPPbbccbbPPp.B.
..pPPPPPPPPp..B.
...pPPPPPPp...B.
""", legs=("""
....YY..YY......
""", """
...YY....YY.....
"""), palette={"b": (150, 110, 70), "c": (220, 200, 160), "e": (150, 255, 120)})

BEAR = dict(body="""
..............BB....
.............BbbB...
............BbbbbB..
............bbrbbb..
............bbbbbbcc
.BB........bbbbbbck.
BbbbbbbbbbbbbbbbB...
BbbbZbbbbbbbbbbbB...
bbbZZZbbbbbbbbbbb...
bbbbZbbbbbbbbbbbb...
.bbbbbbbbbbbbbbb....
.bbbbbbbbbbbbbbb....
..bbbbbbbbbbbbb.....
""", legs=("""
..bbb.bbb...bbb.bbb.
..bbb.bbb...bbb.bbb.
""", """
.bbb...bbbbbb...bbb.
.bbb...bbb.bbb..bbb.
"""), palette={"b": (120, 80, 50), "B": (80, 52, 34), "Z": (96, 160, 80), "r": (255, 50, 50)})

BARREL = dict(body="""
.RRRRRR.
RrrrrrrR
RrryyrrR
GGGGGGGG
RrykkyrR
RrryyrrR
GGGGGGGG
RrrrrrrR
.RRRRRR.
""", legs=None)

# ---------------------------------------------------------------------------
# BOSSOVÉ
# ---------------------------------------------------------------------------
SPY_FOX = dict(body="""
.....hhhhhh.....
....hhhhhhhh....
..hhhhhhhhhhhh..
.....OOOOOO.....
....OkkOkkkO....
....OOOOOOOcc...
.....OOOccccck..
......OOOO......
....jjjjjjjj....
...jjjjcjjjjj...
..jjjjjccjjjjj..
..jOjjjccjjjjOj.
..jOjjjccjjjjOj.
OO.jjjjccjjjj...
.OOjjjjjjjjjj...
....jjjjjjjj....
""", legs=("""
....kk....kk....
""", """
.....kk..kk.....
"""), palette={"O": (214, 112, 48), "c": (240, 222, 190), "j": (150, 112, 66), "h": (40, 34, 44)})

RABBIT = dict(body="""
...ww....ww...
..wnw....wnw..
..wnw....wnw..
..wnw....wnw..
..wnww..wwnw..
...wwwwwwww...
..wwwwwwwwww..
.wwrrwwwwrrww.
.wwrRwwwwRrww.
.wwwwwnnwwwww.
.wwwwkxxkwwww.
..wwwxkkxwww..
...wwwwwwwr...
..wwwwwwwwrw..
.wwwWwwwwWwww.
.wrwWwwwwWwww.
..wwwwwwwwww..
""", legs=("""
...ww....ww...
..www....www..
""", """
..ww......ww..
.www......www.
"""), palette={"x": (255, 255, 255)})

ROOSTER_BOSS = dict(body="""
...........rRr.rRr......
..........rRRrRRRr......
...........rRRRRr.......
..........zzzzzzz.......
.........zzzzzzeez......
.........zzzzzzeezyy....
.........zzzzzzzzyyyy...
..PP......zzzzzzzyy.....
.PvvP.....zzzzzRR.......
PvPPvP....zzzzzRR.......
P.PPvP...zzzzzzR........
..PvPPzzzzzzzzzz........
...PPzzzGzGzGzzzz.......
....zzzzGzGzGzzzzz......
....zzzzzzzzzzzzzz......
....zzzzzzzzzzzzz.......
.....zzzzzzzzzzz........
.......zzzzzzz..........
""", legs=("""
.........yy..yy.........
.........yy..yy.........
........yyy.yyy.........
""", """
........yy....yy........
........yy....yy........
.......yyy...yyy........
"""), palette={"z": (150, 176, 128), "G": (230, 220, 200), "P": (90, 50, 120), "v": (130, 200, 90),
               "e": (220, 255, 90), "r": (180, 40, 120), "R": (120, 20, 80)})

CROWN = """
y.y.y
yyyyy
"""

# ---------------------------------------------------------------------------
# PROJEKTILY, PICKUPY, SPOJENCI
# ---------------------------------------------------------------------------
SMALL = {
    "egg": ("""
.ww.
wwww
wwww
wWWw
.WW.
""", {}),
    "egg_gold": ("""
.yy.
yaay
yyyy
yYYy
.YY.
""", {}),
    "water": ("""
.q.
qlq
qqq
.U.
""", {"U": (40, 120, 200)}),
    "feather": ("""
.....ww
...wwW.
.wwWW..
wWW....
""", {}),
    "feather_c": ("""
.....uu
...ttp.
.yyrr..
rrr....
""", {}),
    "trinket": ("""
..ss.
.ssss
..ss.
.s...
s....
""", {}),
    "feather_t": ("""
.....yy
...rrR.
.rrRR..
bRR....
""", {}),
    "sound": ("""
.q.
..q
..q
..q
.q.
""", {}),
    "slime": ("""
.zz.
zezz
zzzZ
.ZZ.
""", {}),
    "carrot": ("""
.......zz
oooooozz.
.ooooo.z.
""", {}),
    "fish": ("""
.......l.
..lllll.l
.lllklllll
..lllll.l
.......l.
""", {"l": (150, 210, 240)}),
    "cake": ("""
.....r.....
....nnn....
...nnnnn...
..cccccccc.
..nnnnnnnn.
.ccccccccc.
.bbbbbbbbbb
.nnnnnnnnnn
""", {}),
    "chick": ("""
..yy..
.yyky.
yyyyyo
yyyyy.
.y..y.
""", {}),
    "rooster_chick": ("""
..rr..
.ffkf.
ffffyy
fffff.
.y..y.
""", {}),
    "nest": ("""
...wwww....
.jbwwwwbj..
jbjbjbjbjb.
.bjbjbjbj..
""", {}),
    "fortress": ("""
.r.......r.
RRR.....RRR
RwR.yyy.RwR
RRRRRRRRRRR
RwRRRkRRRwR
RRRRRkRRRRR
""", {}),
    "xp1": ("""
.y.
yay
.Y.
""", {}),
    "xp2": ("""
.yy.
yaay
yyyY
.YY.
""", {}),
    "xp3": ("""
..zz..
.yyzz.
yayyy.
yyayy.
.yyyY.
..YY..
""", {}),
    "worm": ("""
.nn..nn.
n..nn..n
.......k
""", {}),
    "magnet": ("""
rr..rr
rr..rr
rr..rr
.rrrr.
""", {}),
    "coin": ("""
.yyy.
yaYYy
yYaYy
yYYay
.yyy.
""", {}),
    "chest": ("""
.bbbbbbbbbb.
bjjjjjjjjjjb
bjjjjjjjjjjb
yyyyyyyyyyyy
bjjjjyyjjjjb
bjjjjkkjjjjb
bjjjjjjjjjjb
bbbbbbbbbbbb
""", {}),
    "skull": ("""
.www.
wkwkw
wwwww
.w.w.
""", {}),
    "bone": ("""
w....w
.wwww.
w....w
""", {}),
}

# ---------------------------------------------------------------------------
# DEKORACE
# ---------------------------------------------------------------------------
DECOR = {
    "haybale": ("""
.yyyyyyyyyyyy.
yYyyyyYyyyyyYy
yyyyYyyyyYyyyy
bbbbbbbbbbbbbb
yyYyyyyyYyyyYy
yyyyyYyyyyyyyy
.yyyyyyyyyyyy.
""", {}),
    "fence_h": ("""
.b.....b.....b.
jbjjjjjbjjjjjbj
.b.....b.....b.
jbjjjjjbjjjjjbj
.b.....b.....b.
""", {}),
    "fence_v": ("""
jbj
.b.
.b.
jbj
.b.
.b.
jbj
.b.
.b.
jbj
.b.
.b.
""", {}),
    "rock": ("""
...gggg....
..gggWgg...
.gggggggg..
ggGgggggggg
gGGGgggGggg
.GGGGGGGGG.
""", {}),
    "snowrock": ("""
...wwww....
..wwwWww...
.gwwwwwwg..
ggGgggggggg
gGGGgggGggg
.GGGGGGGGG.
""", {}),
    "bush": ("""
...vvv.vv...
.vvzvvvvzvv.
vvvvvzvvvvvv
vzvvvvvvzvvv
.vvvvvvvvvv.
""", {"v": (60, 120, 60), "z": (90, 160, 70)}),
    "mushroom": ("""
.rrr.
rwrwr
..w..
..w..
""", {}),
    "log": ("""
.bbbbbbbbbbbbbbb.
bjjjjjjjjjjjjjjcb
bbbbbbbbbbbbbbbcb
.jjjjjjjjjjjjjj..
""", {}),
    "trunk": ("""
.BB.
BbbB
BbbB
BbbB
BbbB
bbbbb
""", {}),
    "pine": ("""
.....v.....
....vvv....
...vvwvv...
..vvvvvvv..
....vvv....
...vvvvv...
..vvwvvvvv.
.vvvvvvvvv.
...vvvvv...
..vvvvvwvv.
.vvvvvvvvvv
vvvwvvvvvvv
.....B.....
.....B.....
""", {"v": (40, 100, 70)}),
    "scarecrow": ("""
...bbb...
..bbbbb..
...ccc...
...ckc...
.uuuuuuu.
u..uuu..u
...uuu...
....b....
....b....
....b....
""", {}),
    "car": ("""
.....uuuuuuuuu......
....ulllulllllu.....
.uuuuuuuuuuuuuuuuu..
uuuuuuuuuuuuuuuuuuuy
uuuuuuuuuuuuuuuuuuuu
.uukkuuuuuuuuukkuu..
...kk.........kk....
""", {}),
    "car_red": ("""
.....rrrrrrrrr......
....rlllrlllllr.....
.rrrrrrrrrrrrrrrrr..
rrrrrrrrrrrrrrrrrrry
rrrrrrrrrrrrrrrrrrrr
.rrkkrrrrrrrrrkkrr..
...kk.........kk....
""", {}),
    "bin": ("""
.mmmmmm.
mGGGGGGm
.mgmgmm.
.mgmgmm.
.mgmgmm.
.mmmmmm.
""", {}),
    "crate": ("""
bbbbbbbbbb
bjjjjjjjjb
bjbjjjjbjb
bjjbjjbjjb
bjjjbbjjjb
bjjjbbjjjb
bjjbjjbjjb
bjbjjjjbjb
bjjjjjjjjb
bbbbbbbbbb
""", {}),
    "machine": ("""
GGGGGGGGGGGGGGGG
GmmmmmmmmmmmmmmG
GmrmzmmmmmmGGGmG
GmmmmmmmmmmGqGmG
GmmmmmmmmmmGGGmG
GGGGGGGGGGGGGGGG
GmmmmmmmmmmmmmmG
GmGGGGGGGGGGGGmG
GmmmmmmmmmmmmmmG
GGGGGGGGGGGGGGGG
""", {}),
    "lamp": ("""
.yyy.
yaaay
.GGG.
..G..
..G..
..G..
..G..
..G..
.GGG.
""", {}),
    "hydrant": ("""
.rr.
rrrr
rRRr
rrrr
.rr.
""", {}),
    "flower_y": ("""
.y.
yay
.v.
""", {"v": (60, 120, 60)}),
    "flower_r": ("""
.r.
ryr
.v.
""", {"v": (60, 120, 60)}),
    "flower_p": ("""
.p.
pyp
.v.
""", {"v": (60, 120, 60)}),
    "pipe": ("""
GmmmmmmmmmmmmmG
mssssssssssssssm
GmmmmmmmmmmmmmG
""", {}),
    "pumpkin": ("""
...v...
.ooooo.
ooOoOoo
oOkoOko
ooOkOoo
.ooooo.
""", {}),
    "gift": ("""
..y.y..
...y...
rrryrrr
rrryrrr
yyyyyyy
rrryrrr
rrryrrr
""", {}),
    "easter_egg": ("""
.nn.
nyyn
qqqq
nnnn
.pp.
""", {}),
}


# ---------------------------------------------------------------------------
# STAVBA
# ---------------------------------------------------------------------------
class Anim:
    """Sada snímků entity: frames[face][i], flash[face][i]. face 0 = doprava, 1 = doleva."""
    __slots__ = ("frames", "flash", "w", "h", "shadow")

    def __init__(self, frames_right: list[pygame.Surface], shadow_w: int | None = None):
        self.frames = [frames_right, [pa.flip(f) for f in frames_right]]
        self.flash = [[pa.flash(f) for f in frames_right], []]
        self.flash[1] = [pa.flip(f) for f in self.flash[0]]
        self.w, self.h = frames_right[0].get_size()
        sw = shadow_w or int(self.w * 0.75)
        self.shadow = pa.make_shadow(sw, max(6, sw // 3))


def creature_frames(spec: dict, palette: dict | None = None, k: float = PX,
                    extra_over: tuple[str, int, int] | None = None, recol: dict | None = None) -> list[pygame.Surface]:
    pal = dict(spec.get("palette") or {})
    if palette:
        pal.update(palette)
    body = pa.parse_map(spec["body"])
    if recol:
        body = pa.recolor(body, recol)
    if extra_over:
        body = pa.overlay(body, pa.parse_map(extra_over[0]), extra_over[1], extra_over[2])
    legs = spec.get("legs")
    out = []
    if legs:
        for lg in legs:
            lrows = pa.parse_map(lg)
            if recol:
                lrows = pa.recolor(lrows, recol)
            rows = body + lrows
            out.append(pa.scale(pa.build(rows, pal), k))
    else:
        out.append(pa.scale(pa.build(body, pal), k))
    return out


def simple(spec: str, palette: dict | None = None, k: float = PX, shade: bool = True) -> pygame.Surface:
    return pa.scale(pa.build(pa.parse_map(spec), palette, shade=shade), k)


class SpriteBank:
    def __init__(self) -> None:
        self.players: dict[str, Anim] = {}
        self.enemies: dict[str, Anim] = {}
        self.small: dict[str, pygame.Surface] = {}
        self.decor: dict[str, pygame.Surface] = {}
        self.hats: dict[str, pygame.Surface] = {}
        self.misc: dict[str, pygame.Surface] = {}
        self._build()

    def rot(self, name: str, steps: int = 16) -> list[pygame.Surface]:
        r = self._rot.get(name)
        if r is None:
            r = rotate_cache(self.small[name], steps)
            self._rot[name] = r
        return r

    def _build(self) -> None:
        self._rot: dict[str, list] = {}
        for pid, spec in PLAYER_MAPS.items():
            self.players[pid] = Anim(creature_frames(spec))
        for hid, (spec, pal) in SKIN_HATS.items():
            self.hats[hid] = simple(spec, pal)

        E = self.enemies
        E["fox"] = Anim(creature_frames(FOX))
        E["fast_fox"] = Anim(creature_frames(FAST_FOX))
        E["armored_fox"] = Anim(creature_frames(FOX, extra_over=(ARMOR_HELMET, 0, -1)))
        E["armored_fox_broken"] = E["fox"]
        E["spitter"] = Anim(creature_frames(SPITTER))
        E["exploder"] = Anim(creature_frames(FOX, palette={"O": (222, 78, 48), "c": (250, 200, 160)},
                                             extra_over=(EXPLODER_BOMB, 3, 0)))
        E["wolf"] = Anim(creature_frames(WOLF))
        E["bat"] = Anim([simple(BAT_A, BAT_PAL), simple(BAT_B, BAT_PAL)])
        E["giant_fox"] = Anim(creature_frames(FOX, palette={"O": (178, 70, 40), "c": (230, 190, 150)},
                                              extra_over=(CROWN, 10, -2), k=PX * 2))
        E["owl"] = Anim(creature_frames(OWL))
        E["bear"] = Anim(creature_frames(BEAR, k=PX + 1))
        E["bear_rage"] = Anim(creature_frames(BEAR, palette={"b": (176, 62, 48), "B": (120, 36, 30),
                                                             "r": (255, 230, 60)}, k=PX + 1))
        E["skeleton_fox"] = Anim(creature_frames(FOX, palette={"O": (190, 205, 200), "c": (240, 250, 245),
                                                                "Z": (130, 90, 170), "e": (210, 120, 255)}))
        E["zchick"] = Anim(creature_frames(HEN, palette={"w": (170, 205, 150), "W": (120, 160, 110),
                                                          "k": (255, 60, 60), "r": (140, 40, 100)}, k=2))
        E["barrel"] = Anim(creature_frames(BARREL), shadow_w=24)
        # biomové varianty
        E["snow_fox"] = Anim(creature_frames(FOX, palette={"O": (232, 236, 245), "c": (190, 210, 235),
                                                            "Z": (140, 170, 210), "e": (90, 200, 255)}))
        E["robo_fox"] = Anim(creature_frames(FOX, palette={"O": (150, 156, 172), "c": (205, 212, 225),
                                                            "Z": (230, 80, 60), "e": (255, 70, 60)},
                                             extra_over=(ARMOR_HELMET, 0, -1)))
        E["rat"] = Anim(creature_frames(FAST_FOX, palette={"O": (120, 112, 120), "c": (200, 160, 170),
                                                            "r": (255, 60, 60)}, k=2))
        E["mist_wolf"] = Anim(creature_frames(WOLF, palette={"g": (170, 190, 215), "G": (120, 140, 170),
                                                              "w": (220, 230, 245), "Z": (110, 120, 200)}))
        # bossové
        E["spy_fox"] = Anim(creature_frames(SPY_FOX, k=4))
        E["rabbit"] = Anim(creature_frames(RABBIT, k=4))
        E["zombie_bear"] = Anim(creature_frames(BEAR, palette={"b": (112, 126, 84), "B": (72, 84, 54),
                                                                "Z": (200, 120, 140), "r": (230, 255, 90)}, k=6))
        E["wolf_alpha"] = Anim(creature_frames(WOLF, palette={"g": (76, 76, 96), "G": (44, 44, 62),
                                                               "w": (180, 180, 200), "e": (255, 60, 60)},
                                               extra_over=(CROWN, 14, -2), k=5))
        E["zombie_rooster"] = Anim(creature_frames(ROOSTER_BOSS, k=4))
        E["zombie_rooster_big"] = Anim(creature_frames(ROOSTER_BOSS, palette={"z": (170, 130, 150)}, k=6))
        # spojenci
        E["ally_fox"] = Anim(creature_frames(FOX, palette={"O": (250, 140, 40), "c": (255, 245, 220),
                                                            "Z": (250, 140, 40), "e": (60, 140, 255)}))
        E["ally_alpha"] = Anim(creature_frames(FOX, palette={"O": (255, 190, 60), "c": (255, 245, 220),
                                                              "Z": (255, 190, 60), "e": (60, 140, 255)},
                                               extra_over=(CROWN, 10, -2), k=4))

        for sid, (spec, pal) in SMALL.items():
            self.small[sid] = simple(spec, pal)
        self.small["xp1"] = simple(SMALL["xp1"][0], k=2)
        for did, (spec, pal) in DECOR.items():
            self.decor[did] = simple(spec, pal)
        self._build_misc()

    def _build_misc(self) -> None:
        M = self.misc
        # stromy (koruna zvlášť, kreslí se nad entitami)
        for name, col, col2 in (("canopy", (52, 110, 58), (72, 140, 70)), ("canopy_dark", (30, 70, 52), (44, 96, 64)),
                                ("canopy_snow", (40, 96, 72), (235, 240, 250))):
            s = pygame.Surface((30, 26), pygame.SRCALPHA)
            for cx, cy, r in ((15, 14, 11), (8, 15, 7), (22, 15, 7), (11, 8, 7), (19, 8, 7), (15, 18, 8)):
                pygame.draw.circle(s, (*col, 255), (cx, cy), r)
            for cx, cy, r in ((12, 8, 3), (19, 7, 3), (8, 13, 2), (22, 12, 2), (15, 12, 3)):
                pygame.draw.circle(s, (*col2, 255), (cx, cy), r)
            # obrys
            m = pygame.mask.from_surface(s)
            ol = m.outline()
            if ol:
                pygame.draw.lines(s, (*pa.OUTLINE, 255), True, ol, 1)
            M[name] = pa.scale(s, PX)
        # hnízdo-hrad, stodola, kurník – procedurálně
        M["barn"] = self._barn()
        M["coop"] = self._coop()

    def _barn(self) -> pygame.Surface:
        s = pygame.Surface((40, 36), pygame.SRCALPHA)
        red, dred, white, roof = (178, 46, 44), (130, 30, 34), (240, 236, 226), (90, 60, 50)
        pygame.draw.polygon(s, roof, [(0, 14), (20, 1), (39, 14)])
        pygame.draw.rect(s, red, (2, 13, 36, 22))
        for x in range(2, 38, 3):
            pygame.draw.line(s, dred, (x, 14), (x, 34))
        pygame.draw.rect(s, white, (13, 18, 14, 17))
        pygame.draw.rect(s, dred, (14, 19, 12, 16))
        pygame.draw.line(s, white, (14, 19), (25, 34))
        pygame.draw.line(s, white, (25, 19), (14, 34))
        pygame.draw.rect(s, white, (17, 7, 6, 5))
        pygame.draw.rect(s, (40, 30, 30), (18, 8, 4, 3))
        m = pygame.mask.from_surface(s)
        pygame.draw.lines(s, pa.OUTLINE, True, m.outline(), 1)
        return pa.scale(s, PX)

    def _coop(self) -> pygame.Surface:
        s = pygame.Surface((26, 22), pygame.SRCALPHA)
        wood, dwood, roof = (190, 140, 80), (140, 96, 56), (160, 60, 50)
        pygame.draw.rect(s, wood, (2, 8, 22, 12))
        for y in range(9, 20, 3):
            pygame.draw.line(s, dwood, (2, y), (23, y))
        pygame.draw.polygon(s, roof, [(0, 9), (13, 1), (25, 9)])
        pygame.draw.rect(s, (40, 26, 20), (10, 12, 6, 8))
        m = pygame.mask.from_surface(s)
        pygame.draw.lines(s, pa.OUTLINE, True, m.outline(), 1)
        return pa.scale(s, PX)


def rotate_cache(surf: pygame.Surface, steps: int = 16) -> list[pygame.Surface]:
    """Předrenderované rotace (pro projektily)."""
    out = []
    for i in range(steps):
        ang = -i * 360 / steps
        out.append(pygame.transform.rotate(surf, ang))
    return out


def angle_index(angle: float, steps: int = 16) -> int:
    return int(round(angle / (math.tau / steps))) % steps
