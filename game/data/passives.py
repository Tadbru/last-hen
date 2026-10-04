"""Pasivní vylepšení (5 úrovní)."""
from __future__ import annotations

from dataclasses import dataclass

MAX_PASSIVE_LEVEL = 5


@dataclass(frozen=True)
class PassiveDef:
    id: str
    name: str
    desc: str          # efekt na úroveň
    flavor: str
    icon: str
    stat: str
    step: float


PASSIVES: dict[str, PassiveDef] = {p.id: p for p in [
    PassiveDef("grain", "Zdravé zrno", "+20 % max. zdraví", "Celozrnné. Bez lepku. Bez lišek.", "grain", "max_hp", 0.20),
    PassiveDef("legs", "Rychlé nohy", "+10 % rychlost pohybu", "Běží jako kuře bez hlavy, ale s hlavou.", "legs", "speed", 0.10),
    PassiveDef("magnet", "Magnet na zrní", "+30 % dosah sběru", "Zrní k tobě přiletí samo.", "magnet", "magnet", 0.30),
    PassiveDef("shell", "Zlatá skořápka", "+10 % poškození", "Tvrdší než babiččin perník.", "shell", "might", 0.10),
    PassiveDef("clock", "Budík", "−8 % doba přebíjení zbraní i ultimátky", "Kokrhá dřív než kohout.", "clock",
               "cooldown", -0.08),
    PassiveDef("vest", "Peřová vesta", "−1 přijaté poškození, +5 % odolnost", "Neprůstřelná. Skoro.", "vest", "armor", 1.0),
    PassiveDef("lucky_egg", "Šťastné vejce", "+12 % zkušeností", "Má na sobě čtyřlístek. Nebo plíseň.", "lucky_egg", "growth", 0.12),
    PassiveDef("megaphone", "Megafon", "+10 % velikost efektů", "KVOK. ALE HLASITĚJI.", "megaphone", "area", 0.10),
    PassiveDef("feed", "Krmivo", "+0,4 HP/s regenerace", "Snídaně šampionů.", "feed", "regen", 0.4),
    PassiveDef("clover", "Čtyřlístek", "+15 % štěstí, +2 % kritický zásah", "Vzácné karty chodí častěji.", "clover", "luck", 0.15),
    PassiveDef("glasses", "Brýle", "+12 % rychlost projektilů, +1 průraz (úr. 2 a 4)", "Konečně vidí lišky ostře.", "glasses", "proj_speed", 0.12),
]}

PASSIVE_ORDER = ["grain", "legs", "magnet", "shell", "clock", "vest", "lucky_egg", "megaphone", "feed", "clover", "glasses"]
