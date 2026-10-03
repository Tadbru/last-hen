"""Ikony (pixel mapy ~12×12) pro karty, HUD, sbírku a menu."""
from __future__ import annotations

import pygame

from . import pixelart as pa

ICONS: dict[str, tuple[str, dict]] = {
    # --- zbraně ---
    "egg": ("""
...www...
..wwwww..
.wwwwwww.
.wwwwwww.
wwwwwwwww
wwwwwwwWw
.wwwwwWW.
..WWWWW..
""", {}),
    "crow_wave": ("""
...oooooo...
.oo......oo.
o...oooo...o
o.oo....oo.o
.o..o..o..o.
.o.o.yy.o.o.
.o.o.yy.o.o.
.o..o..o..o.
o.oo....oo.o
o...oooo...o
.oo......oo.
...oooooo...
""", {}),
    "chick_army": ("""
...yy.......
..yyky......
..yyyyo.yy..
...yyy.yyky.
..y..y.yyyyo
....yy..yyy.
...yyky.y..y
...yyyyo....
....yyy.....
....y..y....
""", {}),
    "shuriken": ("""
.....w......
....wW......
....wW..wwww
.....w.wWW..
.wwwwwWw....
WWw..wW.....
....wW......
...wW.w.....
...w..w.....
..w...ww....
""", {}),
    "laser": ("""
..........rr
........rr..
......rrr...
....rrrr....
oooorrrr....
ooooorr.....
.ooooo......
..ooo.......
""", {}),
    "nest": ("""
....www.....
...wwwww.w..
..wwwwwwwww.
.jbwwwwwwbj.
jbjbjbjbjbjb
.bjbjbjbjbj.
..bjbjbjbj..
""", {}),
    "lightning": ("""
......yyyy
.....yyyy.
....yyyy..
...yyyy...
..yyyyyyy.
.....yyy..
....yyy...
...yy.....
..yy......
.y........
""", {}),
    "stink": ("""
...zz.......
..zzzz.zz...
.zzZzzzzzz..
zzzzzzZzzzz.
zzZzzzzzzzzz
.zzzzzzzZzz.
..zzZzzzzz..
...z..z..z..
..z..z..z...
""", {}),
    "wolf_howl": ("""
.........yy.
..O.O...yyay
..OOOO..yyyy
.OOeOOc..yy.
.OOOOcck....
.OOOOcc.....
OOOOOO......
OOOOOOO.....
""", {"O": (240, 140, 50), "c": (255, 240, 220), "e": (60, 120, 255)}),
    "sky_cake": ("""
.....r.....
....nnn....
..ccccccc..
..nnnnnnn..
.ccccccccc.
.nnnnnnnnn.
bbbbbbbbbbb
nnnnnnnnnnn
""", {}),
    "water_pistol": ("""
............
.uuuuuuuuq.q
uuuuuuuuuu..
uuuuuuuu..q.
.uuuu.......
..uuu.......
..uuu.......
...uu.......
""", {}),
    "beak_whip": ("""
.......ww...
.....ww..w..
...ww.....w.
.oo........w
ooooo......w
oooooo.....w
.ooo......w.
""", {}),
    "feather_shotgun": ("""
..........w.
.........w..
bbbbbbbbGGGw
BbbbbbbbGGG.
..bb.....w..
..bb......w.
..bb........
""", {}),
    "sound_waves": ("""
...kk...q..q
...kkk...q..
...k.kk...q.
...k......q.
...k......q.
.kkk.....q..
kkkk....q..q
.kk.........
""", {}),
    "fan_tail": ("""
..t..u..t...
...t.u.t....
.y..tut..y..
..tytutyt...
yy.ttuttyyy.
...tttttt...
.....u......
.....u......
""", {}),
    "fish": ("""
........l...
..lllll..l..
.lllkllllll.
lllllllll...
.lllllll.l..
........l...
""", {"l": (150, 210, 240)}),
    # --- pasivky ---
    "grain": ("""
.....y......
....yYy.....
.....y......
...y.y.y....
..yYyyyYy...
....yyy.....
..y..y..y...
.yYy.y.yYy..
.....y......
.....v......
""", {"v": (110, 160, 60)}),
    "legs": ("""
.......oo...
......oo....
.....oo.....
....oooo....
...oo.o.oo..
..oo..o..oo.
.oo...o...o.
ww..www..ww.
""", {}),
    "magnet": ("""
.rrr..rrr.
.rrr..rrr.
.rrr..rrr.
.rrr..rrr.
.rrr..rrr.
.rrrrrrrr.
..rrrrrr..
ss......ss
""", {}),
    "shell": ("""
...yyy....
..yaaay...
.yaayyyy..
.yyyyyyy..
yyyYyyyyy.
y.y.y.y.y.
.y.y.y.y..
""", {}),
    "clock": ("""
.k......k.
kkk....kkk
..wwwwww..
.wwwkwwww.
wwwwkwwwww
wwwwkkkwww
wwwwwwwwww
.wwwwwwww.
..wwwwww..
.k......k.
""", {}),
    "vest": ("""
..ww..ww..
.wwW..Www.
wwwW..Wwww
wwwwW.wwww
wWwwwwwwWw
wwwWwwWwww
wwwwwwwwww
.www..www.
""", {}),
    "lucky_egg": ("""
...www...
..wwzww..
.wwwwwzw.
.wzwwwww.
wwwwwzwww
wwzwwwwww
.wwwwwzw.
..wwwww..
""", {}),
    "megaphone": ("""
.........oo
.......oooo
..mmmoooooo
mmmmmoooooo
mmmmmoooooo
..mmmoooooo
...G...oooo
...G.....oo
""", {}),
    "feed": ("""
..bbbbbb..
...b..b...
..cccccc..
.cccccccc.
.ccyyyycc.
.ccyYyycc.
.ccyyYycc.
.cccccccc.
..cccccc..
""", {}),
    "clover": ("""
..zz..zz..
.zzzzzzzz.
.zzzzzzzz.
..zzzzzz..
..zzzzzz..
.zzzzzzzz.
.zzzzzzzz.
..zz.Zzz..
.....Z....
....Z.....
""", {}),
    "glasses": ("""
............
kkkkk..kkkkk
kqqlk..kqqlk
kqqqkkkkqqqk
kqqqk..kqqqk
.kkk....kkk.
""", {}),
    # --- měny a UI ---
    "cur_egg": ("""
..www..
.wwwww.
wwwwwww
wwwwwww
wwwwwWw
.wwwWW.
""", {}),
    "cur_gold": ("""
..yyy..
.yaayy.
yaayyyy
yyyyyyy
yyyyyYy
.yyyYY.
""", {}),
    "cur_token": ("""
.pppppppp.
pPyPyPyPPp
pPPPPPPPPp
pPyyPPyyPp
pPPPPPPPPp
.pppppppp.
""", {}),
    "coin": ("""
.yyy.
yaYYy
yYaYy
yYYay
.yyy.
""", {}),
    "pause": ("""
ww..ww
ww..ww
ww..ww
ww..ww
ww..ww
ww..ww
""", {}),
    "play": ("""
ww....
wwww..
wwwwww
wwww..
ww....
""", {}),
    "reroll": ("""
..www.w.
.w...ww.
w...www.
w.......
w......w
.www...w
.ww...w.
.w.www..
""", {}),
    "skip": ("""
w..w....
ww.ww...
wwwwww..
wwwwwww.
wwwwww..
ww.ww...
w..w....
""", {}),
    "banish": ("""
rr....rr
rrr..rrr
.rrrrrr.
..rrrr..
..rrrr..
.rrrrrr.
rrr..rrr
rr....rr
""", {}),
    "lock": ("""
..ggg..
.g...g.
.g...g.
yyyyyyy
yyyYyyy
yyykyyy
yyyYyyy
yyyyyyy
""", {}),
    "star": ("""
....y....
....y....
...yyy...
yyyyayyyy
.yyyyyyy.
..yyyyy..
..yy.yy..
.yy...yy.
""", {}),
    "trophy": ("""
yyyyyyyy
yaayyyyy
.yayyyy.
..yyyy..
...yy...
...yy...
..yyyy..
.bbbbbb.
""", {}),
    "note": ("""
...kkkkk
...k...k
...k...k
...k...k
.kkk.kkk
kkkkkkkk
.kk..kk.
""", {}),
    "speaker": ("""
...w..w.
..ww...w
wwww.w.w
wwww.w.w
wwww.w.w
..ww...w
...w..w.
""", {}),
    "gear": ("""
...gg...
.g.gg.g.
..gggg..
gggGGggg
gggGGggg
..gggg..
.g.gg.g.
...gg...
""", {}),
    "back": ("""
...w....
..ww....
.wwwwwww
wwwwwwww
.wwwwwww
..ww....
...w....
""", {}),
    "check": ("""
.......z
......zz
.....zz.
z...zz..
zz.zz...
.zzz....
..z.....
""", {}),
    "skull": ("""
..wwww..
.wwwwww.
wwkwwkww
wkkwwkkw
wwwwwwww
.ww..ww.
.w.ww.w.
""", {}),
    "heart": ("""
.rr.rr.
rrrrrrr
rrrrrrr
.rrrrr.
..rrr..
...r...
""", {}),
    "crow": ("""
....rr.r..
...rrrrr..
...wwwww..
..wwwkwwoo
..wwwwwooo
...wwwwr..
....wwwr..
""", {}),
    "calendar": ("""
.k....k.
rrrrrrrr
wwwwwwww
wkwkwkww
wwwwwwww
wkwkwrrw
wwwwwrrw
wwwwwwww
""", {}),
    "book": ("""
.bbbbbbb
bjjjjjjb
bjyyyyjb
bjjjjjjb
bjyyyjjb
bjjjjjjb
bjjjjjjb
bbbbbbbw
""", {}),
    "shop": ("""
.rwrwrwr.
rwrwrwrwr
.bbbbbbb.
.bwwbjjb.
.bwwbjjb.
.bbbbjjb.
.bbbbbbb.
""", {}),
    "chest": ("""
.bbbbbbbb.
bjjjjjjjjb
yyyyyyyyyy
bjjjyyjjjb
bjjjkkjjjb
bbbbbbbbbb
""", {}),
    "hp": ("""
.rr.rr.
rrrrrrr
rrwrrrr
.rrrrr.
..rrr..
...r...
""", {}),
    "dmg": ("""
......ww
.....wWw
....wWw.
.y.wWw..
.yywWw..
..yyw...
.yy.yy..
yy......
""", {}),
    "speed": ("""
....oooo
...oo...
oo.ooooo
...oo...
.oooooo.
...oo...
""", {}),
    "xp": ("""
..zz..
.yyzz.
yayyy.
yyayy.
.yyyY.
..YY..
""", {}),
    "daily": ("""
....yy....
.y..yy..y.
..yyyyyy..
..yyaayy..
yyyaaaayyy
..yyaayy..
..yyyyyy..
.y..yy..y.
....yy....
""", {}),
    "map": ("""
cccccccc
cvvccbbc
cvccbbcc
ccrcccvc
cccuucvc
cbbuuccc
cccccccc
""", {"v": (90, 150, 60)}),
    "question": ("""
.www.
w...w
....w
...w.
..w..
.....
..w..
""", {}),
}

EVO_TINT = (255, 220, 120)


class IconBank:
    def __init__(self) -> None:
        self.base: dict[str, pygame.Surface] = {}
        self.icons: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple, pygame.Surface] = {}
        for k, (spec, pal) in ICONS.items():
            self.base[k] = pa.build(pa.parse_map(spec), pal)
        self.base["forward"] = pa.flip(self.base["back"])     # „vpřed“ = zrcadlená šipka zpět (B-44)
        self.icons = self.base

    def get(self, name: str, scale: int = 3, evo: bool = False, gray: bool = False) -> pygame.Surface:
        key = (name, scale, evo, gray)
        s = self._scaled.get(key)
        if s is not None:
            return s
        base = self.base.get(name) or self.base["question"]
        if evo:
            w, h = base.get_size()
            glow = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
            sil = pa.silhouette(base, (255, 200, 60))
            for dx, dy in ((0, 0), (2, 0), (0, 2), (2, 2), (1, 0), (0, 1), (2, 1), (1, 2)):
                glow.blit(sil, (dx, dy))
            glow.blit(base, (2, 2))
            star = self.base["star"]
            glow.blit(pygame.transform.scale(star, (star.get_width() // 2 + 1, star.get_height() // 2 + 1)), (w - 2, 0))
            base = glow
        if gray:
            base = pa.silhouette(base, (40, 34, 48))
        s = pa.scale(base, scale)
        self._scaled[key] = s
        return s
