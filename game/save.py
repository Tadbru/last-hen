"""Ukládání progresu do save.json – atomický zápis, odolnost vůči poškození, doplnění chybějících klíčů."""
from __future__ import annotations

import copy
import json
import os
import time

from .config import SAVE_PATH

SAVE_VERSION = 1

DEFAULT_SETTINGS = {
    "music_vol": 0.6,
    "sfx_vol": 0.8,
    "music_on": True,
    "sfx_on": True,
    "damage_numbers": True,
    "screen_shake": True,
    "season": "auto",        # auto | off | halloween | christmas | easter
    "show_fps": False,
    "fullscreen": False,
    "vibration": True,
}

DEFAULT: dict = {
    "version": SAVE_VERSION,
    "eggs": 0,
    "gold": 0,
    "tokens": 0,
    "unlocked_chars": ["hen"],
    "unlocked_maps": ["farm"],
    "unlocked_diffs": ["normal"],
    "meta": {"hp": 0, "dmg": 0, "speed": 0, "magnet": 0, "xp": 0, "reroll": 0},
    "records": {
        "best_time_quick": 0, "best_time_full": 0, "best_kills": 0, "total_kills": 0,
        "runs": 0, "wins": 0, "boss_kills": 0, "max_level": 0, "total_eggs": 0,
    },
    "collection": {"enemies": [], "weapons": [], "evolutions": [], "bosses": [], "passives": []},
    "collection_rewards": [],
    "challenges": {},
    "skins_owned": [],
    "skin": {},
    "settings": dict(DEFAULT_SETTINGS),
    "daily": {"last_played": "", "scores": [], "login_last": "", "login_streak": 0},
    "weekly": {"last_claim_week": "", "best": 0},
    "rubber_band": False,
    "played_biomes": [],
    "last_char": "hen",
    "last_map": "farm",
    "last_mode": "quick",
    "last_diff": "normal",
    "seen_intro": False,
}


def _merge(defaults, data):
    """Doplní chybějící klíče z defaults a opraví typy (poškozená data → výchozí)."""
    if isinstance(defaults, dict):
        if not isinstance(data, dict):
            return copy.deepcopy(defaults)
        out = {}
        for k, dv in defaults.items():
            out[k] = _merge(dv, data[k]) if k in data else copy.deepcopy(dv)
        # zachovat neznámé klíče (dopředná kompatibilita) u volných slovníků
        for k, v in data.items():
            if k not in out:
                out[k] = v
        return out
    if isinstance(defaults, bool):
        return data if isinstance(data, bool) else defaults
    if isinstance(defaults, (int, float)):
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            return defaults
        return type(defaults)(data) if isinstance(defaults, float) else data
    if isinstance(defaults, str):
        return data if isinstance(data, str) else defaults
    if isinstance(defaults, list):
        return data if isinstance(data, list) else copy.deepcopy(defaults)
    return data


class SaveData:
    def __init__(self, path: str = SAVE_PATH, persist: bool = True) -> None:
        self.path = path
        self.persist = persist
        self.data: dict = copy.deepcopy(DEFAULT)
        self.load_error: str | None = None
        if persist:
            self.load()

    # --- IO ---------------------------------------------------------------------
    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("save není objekt")
            self.data = _merge(DEFAULT, raw)
            self.data["version"] = SAVE_VERSION
        except Exception as e:
            self.load_error = str(e)
            try:
                bad = self.path + f".corrupt-{int(time.time())}"
                os.replace(self.path, bad)
            except OSError:
                pass
            self.data = copy.deepcopy(DEFAULT)

    def save(self) -> None:
        if not self.persist:
            return
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError as e:
            print("[save] zápis selhal:", e)

    def reset(self) -> None:
        settings = dict(self.data.get("settings", DEFAULT_SETTINGS))
        self.data = copy.deepcopy(DEFAULT)
        self.data["settings"] = settings
        self.save()

    # --- pohodlné přístupy -------------------------------------------------------------
    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def discover(self, category: str, item_id: str) -> bool:
        lst = self.data["collection"].setdefault(category, [])
        if item_id not in lst:
            lst.append(item_id)
            return True
        return False

    def is_discovered(self, category: str, item_id: str) -> bool:
        return item_id in self.data["collection"].get(category, [])
