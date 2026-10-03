# CODE_MAP – Last Chicken (polish pass)

Read-only map written before the polish pass. ~14.4k lines Python, pygame-ce 2.5.8 on PC, classic pygame 2.1 on Android (python-for-android).

## Architecture and loop
- `main.py` → `game/app.py:App.run()` (line ~324 in the file: fixed 60 Hz logic step `DT`, `MAX_FRAME_SKIP=5`, render once per loop, `clock.tick(60)`).
- Loop order: `process_events()` (SDL events → `Ev` logical events, focus-loss → `scene.pause()`, Android back → ESC) → `step(DT)` × n (`scene.update`, audio update, wipe fade) → `render()` (`scene.draw(self.screen)`, wipe overlay, FPS text, letterbox scale to window, flip).
- Every call is wrapped by `App.safe()`: exceptions → `crash.log` + `ErrorScene`.
- Scenes (`game/scenes/*`) derive from `scenes/base.py:Scene`; switching = `app.switch(scene)` (wipe 0.16 s out/in, `app.py:step`). Modal `Dialog` lives on the scene (`scene.modal`).
- `assets.py` is a global registry: `font` (BitmapFont), `sprites` (SpriteBank), `icons` (IconBank), `audio`.
- Run simulation is pure logic: `world/run.py:Run` (headless capable: bot, tests, `tools/simulate.py`). Rendering is separate: `world/render.py:RunRenderer`, HUD in `ui/hud.py`, overlays in `ui/overlays.py`, glue in `scenes/game.py:GameScene`.

## Render pipeline
- Logical canvas 540×960 (`config.W,H`), everything drawn into `App.screen`, scaled into the window viewport (`App.viewport`, integer scale on mobile when close) — nearest neighbour (`transform.scale`).
- Pixel art scale `PX=3` (1 art px = 3 logical px). Bitmap font pixels = `scale` logical px (UI uses 2–8).
- `RunRenderer.draw` order (`render.py:105`): ground tiles (fblits) → zones/decals → arena back → ground telegraphs → areas → pickups → shadows + y-sorted entities (enemies, props, allies, obstacles) → player (always on top) → projectiles → enemy projectiles → waves/rings → beams → bombs → telegraph sprites → **particles** → canopies → arena front → lighting (BLEND_MULT day/night ramp; Android fallback alpha layer) + fog → floating texts → speech bubbles → screen flash → low-HP red vignette.
- Then `GameScene.draw`: HUD → first-run hint → overlay (levelup/chest/pause) → toasts/modal.
- Sprites: generated from ASCII pixel maps (`gfx/pixelart.py:build` auto outline + top/bottom shading), cached flip/flash variants, 16-step rotation caches (`sprites.rot`).
- One coherent look: pixel art + bitmap pixel font + flat bevelled pixel panels. Smooth vector shapes appear only in a few places (pygame circles/arcs for rings, waves, beams, crow button, joystick).

## Style identity
- Pixel art, 3 px grid, dark 1-art-px outline `(26,16,30)` everywhere, light from top (auto shade). Night farm palette: purple-dark UI `C_BG (28,20,34)`, panel `(52,38,58)`, accent orange `(204,108,24)`, gold `(255,214,70)`, zombie purple `(170,90,220)`, slime green `(130,240,80)`.
- Font: custom 5×7 bitmap font with Czech diacritics (`gfx/font.py`), outline or 1 px shadow, cached renders. No TTF needed (works on Android).
- Tone: humorous, Czech, cartoon farm vs zombie foxes.

## Existing systems (decision)
| System | Where | Decision |
|---|---|---|
| Particles | `gfx/particles.py:ParticleSystem` – pooled, capped (`MAX_PARTICLES` 700/450 mobile), kinds FEATHER/SPARK/PUFF/BLOB/STAR, drawn as `surf.fill` squares | **Extend**: keep pool, API and kind ids; draw kinds as cached pixel sprites (round chunky puffs, streak sparks, glow), add FIRE/SMOKE/GLOW/DEBRIS/RING kinds, presets (`explosion`, `hit`, `pop`, `sparkle`, `dust`), ground decals (scorch), `density` |
| Shake | `core/camera.py:Camera.shake` trauma model, capped per source, decays 1.6/s, `kick`, setting `screen_shake` | **Keep** (already correct semantics) |
| Slow-mo | `run.py` `slowmo_t/slowmo_cd` (0.25× for 0.3 s, 4 s cooldown) | **Keep** (gameplay timing – do not touch) |
| Screen flash | `Run.flash` with `FLASH_GAP` limiter + setting `flashes` | **Keep** |
| Rings / beams / waves | `run.add_ring`, `Run.rings`, renderer `_waves_rings`, `_beams` | Keep; restyle in renderer only |
| Floating texts | `Run.texts`, `MAX_TEXTS=70` | Keep |
| Easing / tween | `util.py` ease_out_back/cubic/elastic, `Tween` | Reuse |
| UI widgets | `ui/widgets.py` draw_panel/draw_bar/Button/ScrollArea/draw_icon_frame/currency_row/draw_title_bar | **Extend** (pixel notched bevel, shine, ghost bar) – no parallel ui_kit |
| Scene transitions | `App` wipe (black + orange edge, 0.16 s) | Keep |
| Audio | `audio/sound.py` numpy synth + `audio/synth.py` | Untouched |
| Vignette | only low-HP red (`render.py:_make_vignette`) | Add subtle permanent edge vignette |

## Event-site table
| file:line | event | current feedback | planned |
|---|---|---|---|
| run.py:516 `damage_enemy` | enemy hit | white flash sprite, damage number | + tiny directional hit sparks (throttled, density) |
| run.py:595 `kill_enemy` | enemy death (all types, fluff colour per type) | 4 square feathers, plop sfx | + pop: small glow + fur puff + feathers (fluff colour) |
| run.py:597 | elite death | 20 feathers + shake | + mini explosion burst + smoke |
| run.py:508 | armor broken | sparks | sprite sparks (better look) |
| run.py:624 `explosion` | explosion (bombs, barrels, eggs, exploder fox) | ring + square sparks + square smoke | layered: flash glow, fireballs, sparks, chunky smoke, debris, scorch decal; ring = dmg radius kept |
| run.py:433 `boss_killed` | boss death | big explosion + feathers + flash + shake | + secondary staggered bursts via preset |
| run.py:348 `spawn_boss` | boss arrival | banner, roar, shake | + smoke burst + dark shockwave ring at boss |
| run.py:312 `spawn_enemy` | on-screen spawn | dirt puff + purple ring | dirt puff becomes chunky dust (sprite) |
| run.py:812 `collect` XP | pickup | sfx only | tiny sparkle (density-throttled) |
| run.py:818 gold egg / 822 worm / 826 magnet / 832 coin / 835 chest | pickups | stars/text/sfx | sparkle presets per type |
| run.py:1015 `_open_levelup` | level-up | sfx + vibrate | golden ring + rising stars at player |
| run.py:846 `crow` | special | wave, ring, stars, flash, text | keep + glow |
| run.py:1050 `on_player_death` | player death | feathers, shake | + glow burst + smoke |
| player.py:211 `take_damage` | player hit | feathers, shake, haptic, sprite flash | + red hit sparks |
| player.py:132 | penguin slide trail | PUFF emit | sprite puff (automatic) |
| run.py:1235 `_update_eprojs` | slime hits player | blobs | sprite blobs |
| run.py:1255 | stink cloud | puff each 2 ticks | sprite puff |
| kinds.py:52-55 | egg / golden bomb landing | explosion + blobs | via explosion preset |
| kinds.py:191 | laser charge | spark | streak spark |
| kinds.py:281 | lightning hit | sparks | streak sparks + glow |
| kinds.py:414 | cake landing | explosion + cream blobs | via explosion |
| bosses.py:146/166 | spy fox teleport | puffs | chunky smoke |
| bosses.py:272-280 | bear stomp | ring + dust | chunky dust + debris |
| bosses.py:449 | rooster wind | emit FEATHER | unchanged |
| mapgen.py:354 / 372 | avalanche, stamper | puffs / sparks | sprites |
| allies.py:120 / 171 | ally poof | puffs | sprites |
| renderer (new) | player footsteps dust, ambient biome particles | none | dust puffs while moving; fireflies / leaves / snow / smog / embers per biome |
| renderer `_projs` / `_eprojs` | projectiles | sprite only | soft glow under hostile projectiles (readability), faint under player orbs |
| overlays.py LevelUp / Chest / Pause | UI | pop-in, rays | panel restyle via widgets |
| results.py | results | title slam | count-up numbers, confetti/feather particles |

## Screen table
| screen | file:line | quality now | planned |
|---|---|---|---|
| Menu | scenes/menu.py:133 `draw` | good logo, flat hill/grass rectangles, static moon | textured night grass (biome tile), moon glow, fireflies, logo shine |
| Select | scenes/select.py:165 | flat fill bg | shared patterned scene bg + vignette |
| Nest / Shop / Settings / Collection / Challenges / Daily | nest.py:78, shop.py:130, settings.py:92, collection.py:95, challenges.py:40, daily.py:51 | flat fill bg | shared scene bg |
| Settings | settings.py | no about/credits/privacy/version | add "O hře" row → dialog (version, credits, privacy, licences) |
| HUD | ui/hud.py:19 | solid, readable | XP bar ghost/shine, crow button glow when ready (minor) |
| Level-up | ui/overlays.py:214 | decent | panel restyle (auto via widgets), epic card glow |
| Chest | overlays.py:325 | rays, ok | sparkle particles on open (optional) |
| Pause | overlays.py:450 | ok | auto via widgets |
| Results | scenes/results.py:405 | static numbers | count-up, particles |
| Dialog | scenes/base.py:101 | ok | auto via widgets |
| Error | scenes/error.py | plain | leave |

## Hazards (do not touch)
- **`Run.rng` is gameplay RNG** (daily seed determinism). New visual code must use the particle system's own RNG (`ParticleSystem.rng`) or `random`, never `run.rng`. (Existing leak: `damage_enemy` uses `run.rng` for damage-number jitter only when not headless — pre-existing, left as is, noted in report.)
- `add_ring(..., r1=r)` in `explosion` equals the real damage radius; telegraph `t.r` is the attack radius → visuals may read, never change.
- `len(run.particles)` is read in `kill_enemy`/`explosion` to throttle visuals (visual only).
- `ParticleSystem.emit(x,y,vx,vy,life,kind,col,size)` signature and kind ids 0..5 are used directly in `player.py:132`, `bosses.py:449` – keep compatible.
- `Run` must stay renderer-free for headless sims (`cfg.headless`): no pygame Surface work in `Run`.
- Android runs classic pygame 2.1: no `fblits` (shim `device.fblits`), slow `BLEND_MULT`; avoid new full-screen alpha blits / blend modes per frame.
- Save format (`save.py`) – only additive settings keys with defaults.
- Telegraph readability: effects must not hide boss telegraphs or hostile projectiles.

## Performance notes
- `tools/profile_run.py`: 400 enemies + ~300 projectiles + up to ~550 particles. Baseline (PC): 4.10 ms/frame (logic 2.02, render 2.08); `--kills`: 3.68 ms (logic 1.52, render 2.16).
- Hot loops: `_update_projs`, `update_enemies`, renderer `_entities` (fblits). Particles drawn with `surf.fill` – cheap; new sprite particles must go through one `fblits` batch.
- Caches: font render cache (3000), renderer circle cache (400), sprite flash/rot caches.
- Per-frame allocations (existing): screen flash surface, `Dialog` dim, toast surfaces, joystick surfaces, line telegraph polygon surface, band surfaces. Low frequency – acceptable; the new code must not add more.

## Polish plan (ordered)
1. Checkpoint commit.
2. Pass A – `gfx/particles.py`: sprite-based pixel particles + new kinds + presets + decals + density; `run.py` hook lines in explosion/kill/hit/levelup/boss/collect/death; `player.py` hit sparks; renderer: scorch decals under entities, projectile glows, dust, ambient biome particles, subtle edge vignette.
3. Pass B – `ui/widgets.py`: notched pixel bevel panels, button shine sweep, bar ghost; shared scene background `scenes/base.py:draw_scene_bg`; menu night grass/moon glow/fireflies; results count-up + particles; settings About dialog.
4. Pass C – world: covered by decals/ambient/vignette/glows.
5. Pass D – `LICENSES.md`, store assets script `tools/make_store_assets.py` → `store/`.
6. Verify: smoke tests, profile, screenshots `polish/after/`.
