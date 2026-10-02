[app]

# --- identita aplikace ---
title = Last Chicken
package.name = lastchicken
package.domain = cz.lastchicken
# verzi přepisuje GitHub Actions (1.0.<číslo buildu>)
version = 1.0.0

# --- zdrojáky (do APK jde jen hra, ne testy a nástroje) ---
source.dir = .
source.include_exts = py
source.exclude_dirs = tests, tools, shares, app_assets, bin, .buildozer, .github, __pycache__
source.exclude_patterns = save.json*, crash.log

# pygame = pygame 2.1 recept z python-for-android, numpy = syntéza zvuku, pyjnius/android = vibrace, sdílení
requirements = python3,pygame,numpy,pyjnius,android

# --- vzhled ---
orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/app_assets/icon.png
presplash.filename = %(source.dir)s/app_assets/presplash.png
android.presplash_color = #1C1422

# --- Android ---
android.permissions = VIBRATE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
p4a.bootstrap = sdl2
# Pevná verze python-for-android: Python 3.10 + NDK 25b + numpy 1.22 sedí k receptu pygame 2.1.0.
# (master od 2026 staví Python 3.14, se kterým se pygame 2.1.0 nezkompiluje.)
p4a.branch = v2023.05.21

[buildozer]
log_level = 2
warn_on_root = 0
