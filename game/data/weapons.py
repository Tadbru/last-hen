"""Zbraně – datově řízené. Statistika na úrovni L = base + součet změn úrovní 2..L.

kind určuje třídu chování (game/weapons/kinds.py). Evoluce jsou samostatné definice (1 úroveň).
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_WEAPON_LEVEL = 8


@dataclass
class WeaponDef:
    id: str
    name: str
    kind: str
    icon: str
    desc: str
    base: dict
    levels: list = field(default_factory=list)     # [(změny, popis)] pro úrovně 2..8
    evo_passive: str = ""
    evo_to: str = ""
    evolution: bool = False
    evolved_from: str = ""
    owner: str = ""            # startovní zbraň zvířete (exkluzivní)
    sound: str = "throw"
    color: tuple = (255, 255, 255)

    def stats_at(self, level: int) -> dict:
        s = dict(self.base)
        for i in range(min(level, len(self.levels) + 1) - 1):
            for k, v in self.levels[i][0].items():
                s[k] = s.get(k, 0) + v
        return s

    def level_text(self, level: int) -> str:
        """Popis toho, co přinese úroveň `level` (2..8)."""
        if level <= 1 or self.evolution:
            return self.desc
        return self.levels[level - 2][1]


def _w(**kw) -> WeaponDef:
    return WeaponDef(**kw)


WEAPONS: dict[str, WeaponDef] = {}


def _reg(*defs: WeaponDef) -> None:
    for d in defs:
        WEAPONS[d.id] = d


# --- 10 základních zbraní -------------------------------------------------------------
_reg(
    _w(id="egg", name="Vaječný granát", kind="lob", icon="egg", sound="throw", color=(250, 248, 240),
       desc="Hází vejce obloukem. Při dopadu vybuchne. Omeleta z lišek.",
       base=dict(dmg=22, cd=1.5, count=1, area=46, range=260, kb=140, cluster=0),
       levels=[({"count": 1}, "+1 vejce na hod."),
               ({"area": 12}, "Výbuch je o čtvrtinu větší."),
               ({"dmg": 10, "cd": -0.15}, "+10 poškození, rychlejší házení."),
               ({"count": 1}, "+1 vejce na hod."),
               ({"cluster": 3}, "Vejce se roztříští na 3 menší výbuchy."),
               ({"dmg": 14, "area": 10}, "+14 poškození a ještě větší výbuch."),
               ({"count": 1, "cd": -0.2}, "+1 vejce a rychlejší házení.")],
       evo_passive="shell", evo_to="golden_bomb"),
    _w(id="crow_wave", name="Kokrhací vlna", kind="pulse", icon="crow_wave", sound="wave", color=(246, 152, 42),
       desc="Kruhová rázová vlna kolem tebe. Odhodí všechno chlupaté.",
       base=dict(dmg=14, cd=2.4, area=105, kb=260, waves=1, slow=0.0, stun=0.0),
       levels=[({"dmg": 6}, "+6 poškození."),
               ({"area": 25}, "Vlna dosáhne dál."),
               ({"cd": -0.35}, "Kokrhá častěji."),
               ({"slow": 0.4}, "Vlna zpomalí zasažené lišky o 40 %."),
               ({"area": 30}, "Ještě větší dosah."),
               ({"waves": 1}, "Dvojitá vlna!"),
               ({"dmg": 14, "cd": -0.3}, "+14 poškození, častější vlny.")],
       evo_passive="megaphone", evo_to="apocalypse"),
    _w(id="chick_army", name="Kuřecí armáda", kind="chicks", icon="chick_army", sound="bite", color=(252, 216, 64),
       desc="Kuřátka obíhají kolem tebe a klovou do lišek. Roztomilé. Smrtící.",
       base=dict(count=3, dmg=10, range=150, speed=420, cd=0.9, orbit=62),
       levels=[({"dmg": 4}, "+4 poškození."),
               ({"count": 1}, "+1 kuře."),
               ({"cd": -0.25}, "Rychlejší výpady."),
               ({"dmg": 6}, "+6 poškození."),
               ({"range": 60}, "Kuřata vyrážejí dál."),
               ({"count": 1}, "+1 kuře."),
               ({"dmg": 8}, "Kuřata ve varu: +8 poškození.")],
       evo_passive="feed", evo_to="legion"),
    _w(id="shuriken", name="Peří-shuriken", kind="spiral", icon="shuriken", sound="whip", color=(240, 240, 250),
       desc="Ostrá pírka létají po spirále kolem tebe.",
       base=dict(count=3, dmg=12, cd=2.0, pierce=2, dur=2.0, speed=150, spin=4.0),
       levels=[({"count": 1}, "+1 pírko."),
               ({"dmg": 5}, "+5 poškození."),
               ({"pierce": 2}, "Pírka proletí 2 dalšími liškami."),
               ({"count": 1}, "+1 pírko."),
               ({"cd": -0.5}, "Častější spirály."),
               ({"count": 2}, "+2 pírka."),
               ({"dmg": 8, "pierce": 3}, "+8 poškození, +3 průraz.")],
       evo_passive="legs", evo_to="feather_storm"),
    _w(id="laser", name="Zobák-laser", kind="laser", icon="laser", sound="laser", color=(255, 70, 70),
       desc="Nabije a vypálí paprsek, který projde vším.",
       base=dict(dmg=52, cd=2.8, width=10, range=420, beams=1, charge=0.5),
       levels=[({"dmg": 16}, "+16 poškození."),
               ({"width": 6}, "Širší paprsek."),
               ({"cd": -0.5}, "Rychlejší nabíjení."),
               ({"beams": 1}, "Druhý paprsek."),
               ({"dmg": 26}, "+26 poškození."),
               ({"range": 160, "width": 6}, "Delší a širší paprsek."),
               ({"beams": 1, "cd": -0.4}, "Třetí paprsek, rychlejší nabíjení.")],
       evo_passive="glasses", evo_to="falcon_eyes"),
    _w(id="nest", name="Hnízdo", kind="nest", icon="nest", sound="throw", color=(190, 140, 80),
       desc="Položí hnízdo, které samo střílí vajíčka na lišky.",
       base=dict(dmg=10, cd=6.0, count=2, dur=8.0, fire=0.65, shots=1, range=260),
       levels=[({"count": 1}, "+1 hnízdo naráz."),
               ({"dmg": 5}, "+5 poškození."),
               ({"fire": -0.2}, "Hnízda střílí rychleji."),
               ({"dur": 4.0}, "Hnízda vydrží o 4 s déle."),
               ({"shots": 1}, "Hnízda střílí 2 vejce naráz."),
               ({"count": 1}, "+1 hnízdo naráz."),
               ({"dmg": 8, "shots": 1}, "+8 poškození, 3 vejce naráz.")],
       evo_passive="grain", evo_to="fortress"),
    _w(id="lightning", name="Kvaltík", kind="lightning", icon="lightning", sound="zap", color=(255, 240, 120),
       desc="Křídla vyšlehnou blesky na nejbližší lišky.",
       base=dict(dmg=24, cd=1.8, count=2, area=22, chain=0, range=330, stun=0.0),
       levels=[({"count": 1}, "+1 blesk."),
               ({"dmg": 10}, "+10 poškození."),
               ({"cd": -0.35}, "Častější blesky."),
               ({"chain": 2}, "Blesky přeskočí na 2 další lišky."),
               ({"count": 1}, "+1 blesk."),
               ({"area": 16, "dmg": 10}, "Větší zásah, +10 poškození."),
               ({"count": 2}, "+2 blesky.")],
       evo_passive="clock", evo_to="storm_wings"),
    _w(id="stink", name="Slepičí smrad", kind="stink", icon="stink", sound="cloud", color=(124, 220, 92),
       desc="Jedovatý mrak, který zpomaluje a leptá. Lišky omdlévají.",
       base=dict(dmg=7, cd=3.2, count=1, area=52, dur=3.0, slow=0.35, aura=0),
       levels=[({"area": 12}, "Větší mrak."),
               ({"count": 1}, "+1 mrak."),
               ({"dmg": 5}, "+5 poškození."),
               ({"dur": 1.5}, "Mraky vydrží déle."),
               ({"count": 1}, "+1 mrak."),
               ({"slow": 0.25, "area": 12}, "Silnější zpomalení, větší mrak."),
               ({"dmg": 8, "cd": -0.7}, "+8 poškození, častější mraky.")],
       evo_passive="vest", evo_to="bioweapon"),
    _w(id="wolf_howl", name="Vlčí vytí", kind="foxes", icon="wolf_howl", sound="howl", color=(250, 140, 40),
       desc="Přivolá spřátelenou liščí smečku. Ironie osudu.",
       base=dict(count=2, dmg=9, dur=6.0, cd=9.0, speed=210, permanent=0),
       levels=[({"count": 1}, "+1 liška ve smečce."),
               ({"dur": 2.5}, "Smečka zůstane déle."),
               ({"dmg": 5}, "+5 poškození."),
               ({"count": 1}, "+1 liška."),
               ({"cd": -2.5}, "Častější vytí."),
               ({"speed": 70, "dmg": 5}, "Rychlejší a silnější lišky."),
               ({"count": 2}, "+2 lišky.")],
       evo_passive="clover", evo_to="godfather"),
    _w(id="sky_cake", name="Koláč z vajec", kind="cake", icon="sky_cake", sound="whistle", color=(255, 168, 190),
       desc="Z nebe padá koláč. Velký. Těžký. Babiččin.",
       base=dict(dmg=70, cd=4.2, count=1, area=66, cream=0),
       levels=[({"dmg": 25}, "+25 poškození."),
               ({"count": 1}, "+1 koláč."),
               ({"area": 16}, "Větší koláč."),
               ({"cd": -0.8}, "Babička peče rychleji."),
               ({"count": 1}, "+1 koláč."),
               ({"dmg": 35, "cream": 1}, "+35 poškození, šlehačka zpomaluje."),
               ({"count": 2}, "+2 koláče.")],
       evo_passive="lucky_egg", evo_to="wedding_cake"),
)

# --- startovní zbraně zvířat ------------------------------------------------------------
_reg(
    _w(id="water_pistol", name="Vodní pistole", kind="gun", icon="water_pistol", sound="water", owner="duck",
       color=(70, 205, 235), desc="Rychlé vodní střely, které prorazí celou řadu lišek.",
       base=dict(dmg=9, cd=0.42, count=1, pierce=3, speed=520, spread=8, life=0.9, slow=0.0, kb=40),
       levels=[({"pierce": 2}, "+2 průraz."),
               ({"dmg": 4}, "+4 poškození."),
               ({"count": 1}, "+1 střela."),
               ({"cd": -0.1}, "Rychlejší palba."),
               ({"speed": 150, "pierce": 3}, "Rychlejší střely, +3 průraz."),
               ({"dmg": 5}, "+5 poškození."),
               ({"count": 1, "slow": 0.3}, "+1 střela, mokré lišky zpomalí.")],
       evo_passive="magnet", evo_to="fire_hose"),
    _w(id="beak_whip", name="Husí štípanec", kind="whip", icon="beak_whip", sound="whip", owner="goose",
       color=(255, 230, 200), desc="Štípne zobákem všechno kolem sebe. Husa nezná slitování.",
       base=dict(dmg=26, cd=0.95, area=92, arc=150, sides=1, kb=200, lifesteal=0),
       levels=[({"dmg": 9}, "+9 poškození."),
               ({"area": 16}, "Delší krk, delší dosah."),
               ({"sides": 1}, "Štípe dopředu i dozadu."),
               ({"cd": -0.25}, "Rychlejší štípání."),
               ({"dmg": 16}, "+16 poškození."),
               ({"area": 20}, "Ještě delší dosah."),
               ({"arc": 210}, "Štípe dokola – 360°!")],
       evo_passive="grain", evo_to="goose_rage"),
    _w(id="feather_shotgun", name="Brokovnice z peří", kind="shotgun", icon="feather_shotgun", sound="shotgun",
       owner="turkey", color=(220, 160, 100), desc="Vějíř ostrých per na nejbližší lišku. Bum.",
       base=dict(dmg=13, cd=1.55, count=5, spread=40, pierce=1, speed=480, life=0.55, bursts=1),
       levels=[({"count": 2}, "+2 broky."),
               ({"dmg": 5}, "+5 poškození."),
               ({"cd": -0.3}, "Rychlejší přebíjení."),
               ({"pierce": 1}, "+1 průraz."),
               ({"count": 2, "spread": 12}, "+2 broky, širší rozptyl."),
               ({"dmg": 7}, "+7 poškození."),
               ({"bursts": 1}, "Dvojitá rána!")],
       evo_passive="clover", evo_to="gatling"),
    _w(id="sound_waves", name="Zvukové vlny", kind="waves", icon="sound_waves", sound="wave", owner="rooster",
       color=(70, 205, 235), desc="Rockové vlny ve směru pohybu. Procházejí vším.",
       base=dict(dmg=21, cd=1.15, dirs=1, size=1.0, speed=300, life=0.9, kb=90, stun=0.0),
       levels=[({"dmg": 6}, "+6 poškození."),
               ({"dirs": 1}, "Vlna i dozadu."),
               ({"size": 0.4}, "Větší vlny."),
               ({"cd": -0.25}, "Rychlejší rytmus."),
               ({"dirs": 2}, "Vlny do 4 směrů."),
               ({"dmg": 12, "kb": 90}, "+12 poškození, silnější odhoz."),
               ({"stun": 0.4}, "Vlny omráčí.")],
       evo_passive="megaphone", evo_to="rock_concert"),
    _w(id="fan_tail", name="Páví vějíř", kind="fan", icon="fan_tail", sound="whip", owner="peacock",
       color=(44, 172, 160), desc="Rozevře ocas a vystřelí vějíř barevných per.",
       base=dict(dmg=17, cd=1.3, count=5, spread=100, pierce=1, speed=380, life=0.8),
       levels=[({"count": 2}, "+2 pera."),
               ({"dmg": 6}, "+6 poškození."),
               ({"spread": 40, "count": 2}, "Vějíř 140°, +2 pera."),
               ({"cd": -0.3}, "Rychlejší střelba."),
               ({"pierce": 2}, "+2 průraz."),
               ({"dmg": 8}, "+8 poškození."),
               ({"count": 4, "dmg": 4}, "+4 pera, +4 poškození.")],
       evo_passive="lucky_egg", evo_to="rainbow_show"),
    _w(id="fish", name="Mražená ryba", kind="boomerang", icon="fish", sound="whip", owner="penguin",
       color=(150, 210, 240), desc="Hodí zmraženou rybu, která se vrátí. Lišky mrznou.",
       base=dict(dmg=16, cd=1.6, count=1, range=230, speed=360, slow=0.5, freeze=0.0, size=1.0),
       levels=[({"count": 1}, "+1 ryba."),
               ({"dmg": 7}, "+7 poškození."),
               ({"range": 70}, "Delší let."),
               ({"freeze": 0.6}, "Zásah lišku úplně zmrazí."),
               ({"count": 1}, "+1 ryba."),
               ({"dmg": 9, "size": 0.4}, "Větší ryba, +9 poškození."),
               ({"count": 1, "cd": -0.4}, "+1 ryba, rychlejší házení.")],
       evo_passive="clock", evo_to="frozen_tsunami"),
    _w(id="trinkets", name="Lesklé cetky", kind="bounce", icon="trinkets", sound="trinket", owner="magpie",
       color=(255, 226, 120), desc="Hází blýskavé cetky, které se odrážejí z lišky na lišku.",
       base=dict(dmg=20, cd=1.1, count=1, bounces=3, speed=430, life=1.4, range=380, hop=220),
       levels=[({"bounces": 1}, "+1 odraz."),
               ({"dmg": 8}, "+8 poškození."),
               ({"count": 1}, "+1 cetka."),
               ({"cd": -0.25}, "Rychlejší házení."),
               ({"bounces": 2}, "+2 odrazy."),
               ({"dmg": 13}, "+13 poškození."),
               ({"count": 1, "bounces": 2}, "+1 cetka, +2 odrazy.")],
       evo_passive="magnet", evo_to="treasure"),
)

# --- evoluce ---------------------------------------------------------------------------
_reg(
    _w(id="golden_bomb", name="Zlatá bomba", kind="lob", icon="egg", evolution=True, evolved_from="egg",
       sound="nuke", color=(255, 214, 70),
       desc="Nukleární zlaté vejce. Zabití občas vysype minci.",
       base=dict(dmg=170, cd=2.2, count=3, area=130, range=300, kb=320, cluster=5, nuke=1, coin=0.25)),
    _w(id="apocalypse", name="Apokalypsa", kind="pulse", icon="crow_wave", evolution=True, evolved_from="crow_wave",
       sound="wave", color=(255, 90, 40),
       desc="Čtyři drtivé vlny za sebou. Omračují.",
       base=dict(dmg=48, cd=2.2, area=300, kb=420, waves=4, slow=0.6, stun=0.7)),
    _w(id="legion", name="Kohoutí legie", kind="chicks", icon="chick_army", evolution=True, evolved_from="chick_army",
       sound="bite", color=(246, 120, 42),
       desc="Dvacet kohoutků. Žádné slitování.",
       base=dict(count=20, dmg=22, range=260, speed=520, cd=0.5, orbit=92, rooster=1)),
    _w(id="feather_storm", name="Peřinová vichřice", kind="spiral", icon="shuriken", evolution=True,
       evolved_from="shuriken", sound="whip", color=(255, 255, 255),
       desc="Tornádo pírek, které neprorazí nic. Protože prorazí všechno.",
       base=dict(count=14, dmg=26, cd=1.0, pierce=999, dur=3.0, speed=110, spin=6.0)),
    _w(id="falcon_eyes", name="Oči sokola", kind="laser", icon="laser", evolution=True, evolved_from="laser",
       sound="laser", color=(255, 60, 200),
       desc="Neprůstřelné laserové oči, které kropí okolí.",
       base=dict(dmg=60, cd=1.6, width=26, range=700, beams=2, charge=0.25, sweep=1, dur=2.4)),
    _w(id="fortress", name="Pevnost Kurník", kind="nest", icon="nest", evolution=True, evolved_from="nest",
       sound="throw", color=(226, 48, 52),
       desc="Opevněné hnízdo s děly. Poblíž léčí.",
       base=dict(dmg=24, cd=5.0, count=3, dur=14.0, fire=0.45, shots=5, range=340, heal=3, explode=1)),
    _w(id="storm_wings", name="Bouřková křídla", kind="lightning", icon="lightning", evolution=True,
       evolved_from="lightning", sound="zap", color=(160, 220, 255),
       desc="Bouře v peří. Blesky skáčou a omračují.",
       base=dict(dmg=52, cd=0.9, count=8, area=46, chain=4, range=420, stun=0.5)),
    _w(id="bioweapon", name="Biologická zbraň", kind="stink", icon="stink", evolution=True, evolved_from="stink",
       sound="cloud", color=(160, 255, 80),
       desc="Trvalá toxická aura. Lišky nemají šanci.",
       base=dict(dmg=18, cd=2.5, count=3, area=80, dur=4.0, slow=0.55, aura=140)),
    _w(id="godfather", name="Liščí kmotr", kind="foxes", icon="wolf_howl", evolution=True, evolved_from="wolf_howl",
       sound="howl", color=(255, 190, 60),
       desc="Trvalá smečka a její alfa. Nabídka, která se neodmítá.",
       base=dict(count=6, dmg=30, dur=999, cd=1.0, speed=300, permanent=1, alpha=1)),
    _w(id="wedding_cake", name="Svatební dort", kind="cake", icon="sky_cake", evolution=True, evolved_from="sky_cake",
       sound="whistle", color=(255, 220, 240),
       desc="Třípatrový dort z nebe. Rozdrtí vše a nasype zrní.",
       base=dict(dmg=300, cd=4.0, count=3, area=150, cream=1, xp_drop=1)),
    _w(id="fire_hose", name="Hasičská hadice", kind="gun", icon="water_pistol", evolution=True,
       evolved_from="water_pistol", sound="water", color=(120, 220, 255), owner="duck",
       desc="Nepřetržitý proud vody. Odplaví celou smečku.",
       base=dict(dmg=18, cd=0.06, count=2, pierce=12, speed=700, spread=5, life=0.9, slow=0.4, kb=80)),
    _w(id="goose_rage", name="Husí hněv", kind="whip", icon="beak_whip", evolution=True, evolved_from="beak_whip",
       sound="whip", color=(255, 120, 120), owner="goose",
       desc="Nepřetržitá smršť zobáku. Každé zabití léčí.",
       base=dict(dmg=70, cd=0.55, area=140, arc=360, sides=1, kb=300, lifesteal=1)),
    _w(id="gatling", name="Peří Gatling", kind="shotgun", icon="feather_shotgun", evolution=True,
       evolved_from="feather_shotgun", sound="shotgun", color=(255, 180, 120), owner="turkey",
       desc="Kulomet na peří. Rambo by byl hrdý.",
       base=dict(dmg=22, cd=0.15, count=3, spread=16, pierce=2, speed=620, life=0.6, bursts=1)),
    _w(id="rock_concert", name="Rockový koncert", kind="waves", icon="sound_waves", evolution=True,
       evolved_from="sound_waves", sound="wave", color=(255, 100, 255), owner="rooster",
       desc="Vlny do všech osmi směrů. Elvis neodešel z budovy.",
       base=dict(dmg=44, cd=0.8, dirs=8, size=1.8, speed=340, life=1.0, kb=200, stun=0.5)),
    _w(id="rainbow_show", name="Duhová show", kind="fan", icon="fan_tail", evolution=True, evolved_from="fan_tail",
       sound="whip", color=(255, 120, 255), owner="peacock",
       desc="Ohňostroj per v plném kruhu. Hypnóza zaručena.",
       base=dict(dmg=24, cd=0.7, count=24, spread=360, pierce=4, speed=420, life=0.9, hyp=0.15)),
    _w(id="frozen_tsunami", name="Ledová tsunami", kind="boomerang", icon="fish", evolution=True,
       evolved_from="fish", sound="freeze", color=(200, 240, 255), owner="penguin",
       desc="Hejno zmražených ryb do všech stran. Zmrazí cokoli.",
       base=dict(dmg=55, cd=1.1, count=8, range=320, speed=420, slow=0.6, freeze=1.2, size=1.6, radial=1)),
    _w(id="treasure", name="Strakatý poklad", kind="bounce", icon="trinkets", evolution=True, evolved_from="trinkets",
       sound="trinket", color=(255, 214, 70), owner="magpie",
       desc="Cetky skáčou do všech lišek kolem a občas z nich vypadne mince.",
       base=dict(dmg=52, cd=0.7, count=3, bounces=9, speed=500, life=1.8, range=420, hop=260, coin=0.06)),
)

BASE_WEAPONS = ["egg", "crow_wave", "chick_army", "shuriken", "laser", "nest", "lightning", "stink", "wolf_howl", "sky_cake"]
STARTER_WEAPONS = ["water_pistol", "beak_whip", "feather_shotgun", "sound_waves", "fan_tail", "fish"]
SECRET_WEAPONS = ["trinkets"]   # zbraň tajného zvířete – mimo sbírku (jinak by 100 % nešlo splnit bez Straky)
EVOLUTIONS = [w.evo_to for w in WEAPONS.values() if w.evo_to and w.id not in SECRET_WEAPONS]
ALL_BASE = BASE_WEAPONS + STARTER_WEAPONS
