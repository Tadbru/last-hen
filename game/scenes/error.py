"""Přátelská chybová obrazovka – výjimka je zapsaná v crash.log a hra se může vrátit do menu."""
from __future__ import annotations

import pygame

from .. import assets
from ..config import C_OUTLINE, W
from ..ui.widgets import Button, draw_panel
from .base import Scene


class ErrorScene(Scene):
    music = None

    def __init__(self, app, tb: str) -> None:
        super().__init__(app)
        self.tb = tb.strip().splitlines()[-1][:200] if tb else ""
        self.add(Button((40, 760, W - 80, 84), "Zpět do menu", self.back, icon="back", style="primary", scale=3,
                        key=pygame.K_RETURN))

    def back(self) -> None:
        from .menu import MenuScene
        try:
            self.app.save.save()
        except Exception:
            pass
        self.app.switch(MenuScene(self.app), fade=False)

    def draw(self, surf) -> None:
        font = assets.font
        surf.fill((40, 20, 26))
        font.draw(surf, "KVOK!", (W // 2, 120), (255, 120, 100), 8, "midtop", outline=C_OUTLINE)
        font.draw(surf, "Kurník se na chvíli zhroutil.", (W // 2, 230), (255, 230, 200), 3, "midtop", outline=C_OUTLINE)
        r = pygame.Rect(30, 300, W - 60, 380)
        draw_panel(surf, r, (60, 36, 44))
        hen = assets.sprites.players["hen"].flash[0][0]
        surf.blit(hen, hen.get_rect(center=(W // 2, r.y + 70)))
        font.draw_wrapped(surf, "Neboj, tvůj postup je uložený. Podrobnosti jsme zapsali do souboru crash.log.",
                          pygame.Rect(r.x + 20, r.y + 130, r.w - 40, 120), (230, 220, 220), 2, "center")
        font.draw_wrapped(surf, self.tb, pygame.Rect(r.x + 20, r.y + 260, r.w - 40, 110), (190, 160, 170), 1, "center")
        self.draw_buttons(surf)
