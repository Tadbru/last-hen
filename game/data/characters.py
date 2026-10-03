"""Hratelná zvířata."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharDef:
    id: str
    name: str
    female: bool
    weapon: str
    desc: str
    passive_name: str
    passive_desc: str
    weakness: str
    unlock: str                 # start | eggs | boss | challenge | secret
    unlock_text: str
    cost: int = 0
    hp: float = 1.0             # násobek základních 100 HP
    speed: float = 1.0
    cooldown: float = 1.0       # násobek cooldownů (víc = pomalejší)
    crit_chance: float = 0.05
    crit_mult: float = 2.0
    crow_mult: float = 1.0
    xp_req: float = 1.0
    might: float = 1.0
    special: str = ""
    color: tuple = (255, 255, 255)


CHARACTERS: dict[str, CharDef] = {c.id: c for c in [
    CharDef("hen", "Slepice Božena", True, "egg",
            "Poslední slepice na farmě. Průměrná ve všem, výjimečná v přežití.",
            "Zlaté vejce", "Každých 20 s snese zlaté vejce plné XP.",
            "Je prostě průměrná.", "start", "Od začátku", 0,
            special="golden_egg", color=(250, 248, 240)),
    CharDef("duck", "Kachna Kvak", True, "water_pistol",
            "Bývalá plavčice. Střílí vodou a nebojí se louží.",
            "Vodní živel", "Ve vodě a na ledu o 40 % rychlejší, ne pomalejší.",
            "Jen 70 % životů.", "eggs", "Koupit za 500 vajec", 500,
            hp=0.7, speed=1.05, special="water", color=(252, 216, 64)),
    CharDef("goose", "Husa Gerta", True, "beak_whip",
            "Agresivní husa ze statku. Lišky ji znají a bojí se jí.",
            "Husí kůže", "+30 % životů.",
            "Pomalá (−12 % rychlost).", "eggs", "Koupit za 1 500 vajec", 1500,
            hp=1.3, speed=0.88, color=(255, 168, 190)),
    CharDef("turkey", "Krocan Rambo", False, "feather_shotgun",
            "Veterán z Díkůvzdání. Přežil. Tohle taky přežije.",
            "Krocaní kritik", "Kritické zásahy ×3 a o 5 % častější.",
            "Střílí o 20 % pomaleji.", "eggs", "Koupit za 3 000 vajec", 3000,
            cooldown=1.2, crit_chance=0.10, crit_mult=3.0, color=(226, 48, 52)),
    CharDef("rooster", "Kohout Elvis", False, "sound_waves",
            "Král dvora. Kokrhá v rytmu rokenrolu.",
            "Král kokrhání", "Kokrhání se nabíjí 2× rychleji.",
            "Jen 65 % životů.", "boss", "Poraz Zombie Kohouta", 0,
            hp=0.65, crow_mult=2.0, color=(246, 152, 42)),
    CharDef("peacock", "Páv Diva", True, "fan_tail",
            "Hvězda zahradní párty. Lišky na ni zírají… doslova.",
            "Hypnóza", "Zásahy občas lišku zhypnotizují (bloudí, bere víc).",
            "Potřebuje o 25 % víc XP.", "challenge", "Splň výzvu „Tisíc lišek“", 0,
            xp_req=1.25, special="hypnosis", color=(82, 142, 232)),
    CharDef("penguin", "Tajný tučňák", False, "fish",
            "Nikdo neví, jak se dostal na farmu. On taky ne.",
            "Klouzání po břiše", "Rovně klouže až o 60 % rychleji a zraňuje, co srazí.",
            "Pomalu zatáčí.", "secret", "Tajemství… zkus klepat na logo", 0,
            hp=1.0, speed=0.95, special="slide", color=(80, 140, 230)),
]}

CHAR_ORDER = ["hen", "duck", "goose", "turkey", "rooster", "peacock", "penguin"]
