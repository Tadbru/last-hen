"""Rozdíly mezi platformami: PC / Android (python-for-android) / iOS.

Vše mobilní je obalené try/except – na PC se z toho stanou no-op funkce.
"""
from __future__ import annotations

import os
import sys

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")
IS_IOS = sys.platform == "ios" or "KIVY_BUILD" in os.environ and os.environ.get("KIVY_BUILD") == "ios"
MOBILE = IS_ANDROID or IS_IOS


def data_dir(default: str) -> str:
    """Trvalý zapisovatelný adresář pro save.json a crash.log.

    Na Androidu je to soukromé úložiště aplikace (přežije aktualizace APK), jinak složka projektu.
    """
    if IS_ANDROID:
        for key in ("ANDROID_PRIVATE", "ANDROID_APP_PATH"):
            p = os.environ.get(key)
            if p and os.path.isdir(p):
                return p
    return default


# --- pygame kompatibilita (python-for-android používá pygame 2.1, na PC běží pygame-ce) -------
def _make_fblits():
    import pygame
    if hasattr(pygame.Surface, "fblits"):
        return lambda surf, seq: surf.fblits(seq)

    def fblits(surf, seq):
        surf.blits(seq, False)
    return fblits


fblits = _make_fblits()


HAPTICS = True      # nastavuje App podle Nastavení

# --- Android přes pyjnius --------------------------------------------------------------------
_vibrator = None
_vib_failed = False
_vib_last = -10.0
VIB_MIN_GAP = 0.35        # s – telefon nebzučí nepřetržitě ani při sérii výbuchů


def _activity():
    from jnius import autoclass  # type: ignore
    return autoclass("org.kivy.android.PythonActivity").mActivity


def vibrate(ms: int = 30) -> None:
    """Krátká haptická odezva (Android). Na PC nic nedělá."""
    global _vibrator, _vib_failed, _vib_last
    if not IS_ANDROID or _vib_failed or not HAPTICS:
        return
    import time
    now = time.monotonic()
    if now - _vib_last < VIB_MIN_GAP:
        return
    _vib_last = now
    try:
        if _vibrator is None:
            from jnius import autoclass, cast  # type: ignore
            Context = autoclass("android.content.Context")
            _vibrator = cast("android.os.Vibrator", _activity().getSystemService(Context.VIBRATOR_SERVICE))
        _vibrator.vibrate(int(ms))
    except Exception:  # noqa: BLE001 – haptika je jen bonus
        _vib_failed = True


def keep_screen_on() -> None:
    """Nezhasínat obrazovku během hraní."""
    if not IS_ANDROID:
        return
    try:
        from android.runnable import run_on_ui_thread  # type: ignore
        from jnius import autoclass  # type: ignore
        WindowManager = autoclass("android.view.WindowManager$LayoutParams")

        @run_on_ui_thread
        def _set():
            _activity().getWindow().addFlags(WindowManager.FLAG_KEEP_SCREEN_ON)
        _set()
    except Exception:  # noqa: BLE001
        pass


def share_image(path: str, text: str) -> str:
    """Uloží PNG do Galerie (Obrázky/LastChicken) a otevře systémové sdílení.

    Vrací popis výsledku pro toast. Na PC soubor jen zůstane ve složce shares/.
    """
    if not IS_ANDROID:
        return f"Uloženo: shares/{os.path.basename(path)}"
    try:
        from jnius import autoclass, cast  # type: ignore
        ContentValues = autoclass("android.content.ContentValues")
        Media = autoclass("android.provider.MediaStore$Images$Media")
        Intent = autoclass("android.content.Intent")
        act = _activity()
        values = ContentValues()
        values.put("_display_name", os.path.basename(path))
        values.put("mime_type", "image/png")
        try:
            values.put("relative_path", "Pictures/LastChicken")
        except Exception:  # noqa: BLE001 – starší Android
            pass
        resolver = act.getContentResolver()
        uri = resolver.insert(Media.EXTERNAL_CONTENT_URI, values)
        out = resolver.openOutputStream(uri)
        with open(path, "rb") as f:
            out.write(f.read())
        out.close()
        intent = Intent(Intent.ACTION_SEND)
        intent.setType("image/png")
        intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))
        intent.putExtra(Intent.EXTRA_TEXT, text)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        chooser = Intent.createChooser(intent, "Sdílet výsledek")
        act.startActivity(chooser)
        return "Uloženo do Galerie"
    except Exception as e:  # noqa: BLE001
        return f"Sdílení se nepovedlo ({type(e).__name__})"
