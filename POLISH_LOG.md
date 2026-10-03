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
- Pass B: panels, buttons, bars and icon frames have notched pixel corners (3 px), a light top/left edge and a dark bottom. One change in `widgets.py` restyles every screen consistently.
- Primary (orange) buttons get a diagonal shine sweep once every 4 s: idle motion without being distracting. Only primary buttons get it, so the hierarchy stays clear.
- `draw_bar(ghost=...)` + `Ghost` state: the boss HP bar and the HP bar under the player leave a light trail that holds 0.35 s and then drains.
- Shared menu background `draw_scene_bg`: a slowly drifting pattern of tiny pixel eggs (thematic, very low contrast) + pixel-step vignette. It keeps each screen's original base colour, is pre-rendered once and costs one blit per frame.
- Full-screen dim layers (Dialog, overlays) are now cached surfaces instead of being allocated every frame.
- Menu: the static backdrop is pre-rendered once (sky in 6 px bands, pixel hill, barn, grass from the real Farm tile darkened to night). Also added a pixel moon with a soft halo, 12 fireflies, and occasional star twinkles on the logo.
- Results: stats count up one after another (0.25 s + 0.12 s stagger), the egg total counts up after them, plus confetti on victory and slowly falling feathers on defeat.
- Settings: added an "O hře" (About) dialog with version, credits, privacy statement (no data collected) and a licence pointer. It shares a row with "Smazat postup", so the layout did not grow.
- Crow button: a warm additive glow behind it when ready.
- Fireflies were first drawn as large haloes that read as grey blobs on the purple sky. Changed to a small glow + 3 px bright core.
- Snow on the Mountains was invisible (white on white, then tinted by the night lighting). Flakes now have a blue-grey shadow pixel, near flakes are 6 px, and they are drawn after the night lighting.
- Speech bubbles use the same notched pixel frame as panels.
- Menu fireflies and twinkles use a private `random.Random(21)` so the global random stream (which seeds runs) matches the original exactly.
- Store: `tools/make_store_assets.py` → `store/` (icon 512, feature graphic 1024×500 drawn at 512×250 and scaled 2× nearest, 5 captioned screenshots 1080×1920 with the game at 1.6×). Scripted kills there hide damage numbers so no "1000000000" appears.

## Round 2 (user feedback)
- Fireflies were distracting → removed from the menu and from the game. Farm now has no ambient particles; the forest keeps only leaves.
- "Cakes make big pink blotches": the root cause was not the particles. The cream area and the stink cloud hit everyone inside every 0.4–0.5 s, so the whole crowd flashed white at once (pink under the night lighting). Added visual-only `flash=False` for area ticks (`_update_areas`): no white flash and no flood of numbers, instead an occasional small sparkle in the weapon's colour. `run.rng` is still consumed identically (gameplay determinism checked).
- Cake: telegraph = growing shadow + dotted ring instead of pink filled discs. Landing = cream splat (cream blobs, sprinkles, white ring, small cream decal) instead of a pink fireball (`explosion(fx="cream")`, damage unchanged). The cream area = scattered pixel cream dollops with sprinkles instead of one giant ellipse.
- Stink: pixel gas cloud of 7 slowly rotating, breathing lobes (dark rim, dithered fill) under entities. Above entities: bubbles + comic stink lines (bright, with a shadow). The Bioweapon aura = a ring of darker gas lobes instead of a translucent green disc.
- Menu foxes: the walk frame was changing with every pixel moved (frame index used the x position) → now time-based at about 3–4 steps/s.
- Menu landscape redrawn at 180×320 art px: dithered sky, far hills with pine silhouettes, a middle hill with the coop, scarecrow and barn (night-tinted game sprites), and a meadow running continuously to the bottom with grass tufts, flowers and blades breaking the edge. No seam. Plus the game's fence and hay bales. The store feature graphic now uses the same landscape.

## Round 3 (user feedback)
- Menu foxes walked across the pumpkins → pumpkins now stand by the fence (night-tinted) and foxes walk only in a lane in front of them (y 502–540, same number of `random` calls as before).
- Barns looked "pasted on" → buildings get aerial perspective (mixed ~30 % toward the haze colour), a contact shadow and pixel grass tufts over the bottom edge, and are sunk into the slope. Fence, hay and bushes get a lighter haze.
- The stick in front of the left building (the coop ramp) → `SpriteBank._coop(ramp=False)` used only in the menu; the in-game coop is unchanged.
- Bottom half of the menu: the meadow fades through dithered bands into a calm dark colour behind the buttons. Grass tufts only in the upper meadow, fewer random specks, plus a dark tall-grass fringe along the bottom edge as a frame.
- Character select: the panel content was moved up (sprite, name, weapon) so even 2-line passives + weakness keep a 20 px margin. Checked on all 7 animals, unlocked and locked.
- Page dots: pixel-art balls from the same generator as the sprites (`pa.build`: outline + light from the top) on the 2 px font grid. Selected 5×5, others 4×4, instead of `pygame.draw.circle`.
- Ground tiles: spots no longer wrap around the tile edge (they were cut off at seams with a different variant). The farm "road" strip and the factory hazard stripe ended abruptly at tile edges → replaced by contained motifs (irregular trodden dirt, a hazard plate inside one panel).
- Stink: the cloud was 7 lobes with dark rims = "circles on top of each other" → now billowing smoke like the explosions: many smaller puffs (shaded discs without a rim) that are born, swell, rise and fade, deterministic from time. The aura is the same puffs in a ring band.

## Round 4 (user feedback)
- Menu stars no longer switch off and on: they always shine, and about a quarter of them slowly change brightness between two tones.
- Player "squashes" when changing direction: on every turn the speed briefly drops below the walk threshold → the movement-start stretch fires again → the spring wobbled the sprite on frequent zig-zags. Visual-only fix in the renderer: deformation reduced to 35 %, capped at ±8 %, ignored below 3 %. `player.py` unchanged.
- Pause: dim 225 (almost black) → 120. The paused game stays visible behind the panel.
- Chest: rays in two layers rotating against each other (wide slow ones at the back, narrow fast ones in front), drawn at art resolution and scaled ×3 (pixel edges). Plus a pulsing glow behind the chest, a star burst on opening, rising sparkles and a gentle bob of the chest. The rays surface is reused (no per-frame allocation, unlike before).
- Results background: two stripe layers at different speeds (parallax) in pixel resolution, slow sun rays from the top on victory, and the same vignette as the other screens.
- The dark grass "spikes" at the bottom of the menu were removed; only the gradient remains.

## Round 5 (user feedback)
- Coop: the ramp is removed from the sprite entirely, so it is gone in the game as well. Collision uses constants (`mapgen.py`), not the sprite, so this is visual only.
- Chest: the persistent two-layer rays, pulsing glow, rising sparkles and bob were too much → back to the original single-layer rays, which now **shoot out once** on opening (reach grows in 0.3 s), shine briefly and fade by 1.4 s. The star burst on opening stays.
- Results background: the parallax stripes and rays were not liked → replaced by a calm static pixel scene. Victory = dawn (dithered sky gradient into orange, half-risen sun behind a dark hill, slowly drifting pink pixel clouds). Defeat = night (steady stars, moon, dark clouds). The buttons sit on the dark hill (contrast), and the messages have a light translucent band so they stay readable over the sun. The unused `draw_bg` was removed.

## Round 6 (user feedback)
- Menu stars redone: three kinds on the 3 px grid. Dim tiny dots, bright pixel stars in three tones (white, warm, cold), and a few larger cross-shaped sparkle stars whose arms slowly grow and shrink. Denser field from a private RNG (the global `random` stream is unchanged), none over the hills, the moon or the currency row.
- Chest rays no longer rotate: on opening they shoot out once in all directions (same look as before), shine briefly and fade.
