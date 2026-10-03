# Licences

## Game content
All graphics (pixel sprites, icons, tiles, bitmap font, particle effects), music and sound effects in Last Chicken are generated in code by this project (`game/gfx`, `game/audio`). The project uses no third-party art, fonts or audio files.

## Runtime dependencies (shipped in the Android APK)
| Component | Licence | Notes |
|---|---|---|
| Python 3 | PSF License | interpreter (bundled by python-for-android) |
| pygame 2.1 (Android) / pygame-ce (PC) | GNU LGPL v2.1 | dynamically linked; source: https://github.com/pygame/pygame, https://github.com/pygame-community/pygame-ce |
| SDL2, SDL2_mixer, SDL2_image, SDL2_ttf | zlib License | used by pygame |
| NumPy | BSD 3-Clause | optional, sound synthesis |
| pyjnius | MIT | Android vibration and sharing |
| python-for-android (bootstrap) | MIT | build toolchain |

The LGPL requires that users can replace the LGPL library. pygame is loaded as a separate shared library inside the APK. Keep this file with the release and link to the pygame source repository above.

## Privacy
The game collects no personal data and sends nothing over the network. Progress (`save.json`) is stored only on the device. The in-game "ads" are a mock-up and contact no ad network.
