"""Biomy – paleta, dekorace, zóny, hazardy, nepřátelé, hudba."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BiomeDef:
    id: str
    name: str
    desc: str
    music: str
    ground: tuple                 # základní barva
    ground2: tuple                # tmavší skvrny
    detail: tuple                 # stébla / detaily
    decor: tuple                  # (druh, váha) – překážky/dekorace
    density: float                # průměrný počet objektů na chunk
    zones: tuple = ()             # (druh, váha)
    zone_density: float = 0.6
    hazards: tuple = ()           # globální periodické hazardy
    replace: dict = field(default_factory=dict)    # náhrady nepřátel (fox -> snow_fox)
    extra: tuple = ()             # (nepřítel, váha, od minuty)
    hp_mult: float = 1.0
    spawn_mult: float = 1.0
    fog: bool = False
    slippery: bool = False
    night: tuple = (40, 30, 90)   # barva nočního přítmí
    unlock_cost: int = 0
    unlock_after: str = ""
    reward_mult: float = 1.0
    accent: tuple = (120, 200, 90)
    short: str = ""


BIOMES: dict[str, BiomeDef] = {b.id: b for b in [
    BiomeDef("farm", "Farma", "Pole, stodola, kurník. Lišky ze všech stran.", "farm",
             (98, 152, 66), (84, 136, 58), (124, 178, 80),
             (("haybale", 5), ("fence_h", 3), ("fence_v", 2), ("scarecrow", 1), ("rock", 2), ("barn", 0.35),
              ("coop", 0.6), ("barrel", 1.2), ("flowers", 6), ("bush", 2)),
             7.0, zones=(("puddle", 1.0),), zone_density=0.7,
             accent=(120, 200, 90), short="Farma"),
    BiomeDef("forest", "Temný les", "Stromy blokují výhled, z mlhy vylézají vlci.", "forest",
             (54, 96, 56), (46, 84, 50), (70, 120, 64),
             (("tree", 7), ("bush", 3), ("log", 2), ("mushroom", 3), ("rock", 1.5), ("barrel", 0.5)),
             9.0, zones=(("puddle", 1.0),), zone_density=0.5,
             replace={}, extra=(("wolf", 3, 1.0), ("mist_wolf", 3, 2.0), ("bat", 3, 0.5)),
             fog=True, night=(20, 20, 70), unlock_cost=800, unlock_after="farm", hp_mult=1.1, reward_mult=1.15,
             accent=(70, 170, 110), short="Les"),
    BiomeDef("city", "Opuštěné město", "Auta, uličky a krysy v kanálech.", "city",
             (92, 92, 104), (80, 80, 92), (120, 120, 132),
             (("car", 4), ("bin", 3), ("lamp", 2), ("hydrant", 2), ("wall", 3), ("barrel", 2), ("crate", 1.5)),
             8.0, zones=(("puddle", 1.0),), zone_density=0.5,
             extra=(("rat", 6, 0.3),), night=(30, 30, 80), unlock_cost=1500, unlock_after="forest",
             hp_mult=1.15, reward_mult=1.25, accent=(150, 160, 200), short="Město"),
    BiomeDef("mountain", "Hory", "Sníh, kluzký led a laviny.", "mountain",
             (226, 232, 242), (208, 216, 232), (190, 200, 220),
             (("pine", 6), ("snowrock", 3), ("rock", 2), ("barrel", 0.5)),
             7.0, zones=(("ice", 2.0), ("snowdrift", 1.0)), zone_density=1.1, hazards=("avalanche",),
             replace={"fox": "snow_fox"}, extra=(("wolf", 2, 1.0),), slippery=True,
             night=(40, 50, 110), unlock_cost=2500, unlock_after="city", hp_mult=1.2, reward_mult=1.35,
             accent=(160, 210, 255), short="Hory"),
    BiomeDef("factory", "Továrna na kuřata", "Pásy, lisy, stroje. Nejtěžší místo na světě.", "factory",
             (108, 110, 122), (96, 98, 110), (130, 132, 146),
             (("machine", 4), ("crate", 4), ("pipe", 2), ("barrel", 3)),
             7.5, zones=(("conveyor", 1.0), ("oil", 0.6)), zone_density=1.0, hazards=("stamper",),
             replace={"armored_fox": "robo_fox"}, extra=(("robo_fox", 3, 2.0), ("exploder", 2, 1.0)),
             night=(50, 20, 40), unlock_cost=4000, unlock_after="mountain", hp_mult=1.3, spawn_mult=1.1,
             reward_mult=1.5, accent=(230, 120, 60), short="Továrna"),
]}

BIOME_ORDER = ["farm", "forest", "city", "mountain", "factory"]
