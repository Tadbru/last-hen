"""LAST CHICKEN – vstupní bod.

    python main.py            # menu
    python main.py --quick    # rovnou rychlý run na Farmě
    python main.py --debug    # F3 overlay + debug klávesy (F5 boss, F6 levelup, F7 zabij vše, F8 nesmrtelnost)
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description="LAST CHICKEN – poslední slepice proti zombie liškám")
    ap.add_argument("--quick", action="store_true", help="rovnou spustit rychlý run")
    ap.add_argument("--debug", action="store_true", help="debug režim")
    args, _unknown = ap.parse_known_args()   # na Androidu mohou přijít cizí argumenty
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game.config import Flags
    Flags.debug = args.debug
    Flags.quick = args.quick
    from game.app import App, log_crash, safe_print
    try:
        App().run()
    except Exception as exc:  # poslední záchrana – nikdy neskončit bez záznamu
        safe_print(log_crash(exc))
        raise


if __name__ == "__main__":
    main()
