# POLISH_LOG

## Audit (baseline screenshots in `polish/before/`, ordered by visibility in the first 30 s / store shots)
1. **Explosions** (`fx_explosion_f2..24`): a thin ring and a handful of 3 px square specks; no fireball, no smoke body, nothing left on the ground. Reads as a placeholder.
2. **Enemy deaths** (`game_busy`): 4 single-colour square feathers; with dozens of kills per second nothing reads as a "pop".
3. **Hits**: no impact effect at all, only the sprite flash and a number.
4. **Gameplay depth** (`game_early`): flat-lit field, no vignette, no ambient life (night farm with no fireflies, forest with no leaves, mountain without snow).
5. **Projectiles**: enemy slime and player projectiles have no glow, so hostile shots are hard to pick out in crowds.
6. **Menu sub-screens** (select, nest, shop, settings, collection, challenges, daily): flat single-colour backgrounds, which looks unfinished next to the menu.
7. **Menu**: the hill and grass are flat filled shapes and the moon has no glow. Nothing moves except the hen and the foxes.
8. **Panels and buttons**: clean, but plain square rectangles; no idle motion on the primary button.
9. **Results**: numbers appear instantly with no count-up and no celebratory particles.
10. **Settings**: no version, credits or privacy info (store requirement).
11. Good already: pixel font with diacritics, consistent outline, shadows under entities, level-up and chest pop-ins, wipe transition, capped shake, flash limiter and settings toggles.

## Decisions
- Style: the game is already coherent pixel art (3 px grid). All new effects are pixel sprites snapped to a 3 px grid. No smooth gradients and no TTF fonts.
- Extend the existing `ParticleSystem` (same pool, API and kind ids) instead of adding `fx_toolkit.py`. Shake and slow-mo are already capped and decaying, so I kept them.
- Extend `ui/widgets.py` instead of copying `ui_kit.py`. The bitmap font stays (it works on Android and covers Czech).
- Pass A: particles are now cached pixel sprites (3 px grid), drawn in one `fblits` batch plus one additive batch. New kinds: FIRE, SMOKE, GLOW, DEBRIS, POP. Kept the cap, the API, and kind ids 0–5.
- Explosion = glow (0.5×radius) → chunky fireballs (white → yellow → orange → red-orange → grey) → streak sparks with gravity → smoke rising → debris → scorch decal (4 s, max 24). The damage ring stays at the real radius.
- Tuned after screenshots: the first version made a pale "cloud" at frame 2 and red "meat" at frame 24. I shrank the glow to half the radius, shortened the white phase, and made the tail cool to grey.
- Enemy hit = 2–3 directional sparks, only when the enemy is not already flashing (≤ 1 burst per 0.09 s per enemy). Crit sparks are yellow.
- Enemy death = small pop ring + 2 fur puffs + feathers in the enemy's own `fluff` colour (≈5 particles, density-scaled).
- Density: 1.0 below 80 enemies, linearly down to 0.4 at 350+ (visual only, set in `Run.update`).
- Hostile projectiles get a pulsing additive glow in their own colour (slime green, carrot orange, feather white) to stay readable in crowds. Player projectiles get a faint glow only when fewer than 160 are on screen.
- Ambient per biome: farm fireflies (fade toward dawn), forest leaves + fireflies, city dust motes, mountain snow, factory embers + motes. World-anchored with slight parallax.
- Player footstep dust every 0.16 s while walking, coloured per biome.
- Permanent edge vignette drawn only as 4 edge strips (about ⅓ of the screen's pixels), because classic pygame on Android is slow at full-screen alpha blits.
