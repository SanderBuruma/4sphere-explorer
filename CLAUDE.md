# Project: 4-Sphere Explorer

Interactive S³ (3-sphere) explorer — navigate the 3D surface of a 4D ball, projected to 2D via Pygame.

## Tech Stack

Python, Pygame, NumPy. Venv at `~/Projects/4sphere-explorer/venv`.

## Files

- `main.py` — Game loop, rendering, UI, input, mutable state
- `lib/constants.py` — Display/color/game constants, `distance_to_color()`, `format_dist()`
- `lib/gamepedia.py` — In-game encyclopedia content + layout (`GP_*` constants), `word_wrap_text()`
- `lib/graphics.py` — Procedural creature generation (low-poly faceted, appendages, eyes)
- `lib/planets.py` — Procedural rotating planets (two-tier equirect textures, background preload)
- `sphere.py` — S³ math (points, distance, slerp, tangent projection, orientation frame, fixed-Y frame, names, colors)
- `lib/persistence.py` — Save/load game state to JSON (atomic writes, versioned format)
- `audio.py` — Procedural techno ambient (10 timbres, 12 scales, proximity playback)
- `screenshot.py` — Headless screenshot tool (SDL dummy drivers, scripted actions → output/)
- `tests/` — test_sphere (47), test_dialogue (44), test_eye_tracking (41), test_reputation (29), test_planets (22), test_gamepedia (22), test_persistence (13), test_rotation (12), test_traits (10), test_audio (9)

## Key Parameters

30,000 points on S³ | FOV 0.116 rad (~6.6°) | Travel speed 0.00008/frame | Projection scale 2500 | Camera dist 0.08 rad

## Architecture

- **Orientation frame:** 4×4 orthogonal matrix (row 0 = camera, rows 1-3 = tangent basis). `rotate_frame()` applies planar rotations, `reorthogonalize_frame()` corrects drift via Gram-Schmidt from current frame vectors
- **Fixed-Y frame:** `build_fixed_y_frame(player_pos, w_angle)` computes frame directly from player position and a tracked angle, bypassing orientation hints. Guarantees uniform screen-space angular velocity for Q/E rotation. The `xyz_w_angle` state variable tracks the angle
- **Name keys:** `np.random.choice(11.8M, 30000, replace=False)` with seed 42 — deterministic, collision-free
- **Lazy caching:** Creatures, names, planets cached with LRU eviction
- **Planet pipeline:** Low-res (32×64) on main thread (6/frame budget), high-res (128×256) via background worker
- **Audio:** `generate_signal()` → raw float64 (testable), `generate_sound()` → pygame Sound. RMS-normalized, 15s seamless loops
## Controls

W/S up/down, A/D left/right, Q/E rotate into 4th dimension, Ctrl+/-/scroll zoom, UP/DOWN scroll list, drag rotate, click travel, F1 Gamepedia. WASD moves camera on S³, Q/E rotates view in tangent subspace via direct angle tracking (`xyz_w_angle`) for uniform speed

## View

XYZ Fixed-Y with W-colored halos. Vertical axis locked to absolute Y. Planet sprites use assigned colors, halos show W coordinate (blue→white→red). Q/E rotates into 4th dimension at uniform speed

## Rules

- **No commits without explicit request**
- **Math correctness:** Test 4D rotations carefully. Clamp dot products to [-1,1] before arccos
- **Gamepedia maintenance:** When changing gameplay aspects (controls, UI widgets, mechanics, audio, view modes), update the corresponding `GAMEPEDIA_CONTENT` entry in `lib/gamepedia.py` in the same change. Update `tests/test_gamepedia.py` if topic structure changes
- **Planning docs:** `.planning/` artifacts should be committed alongside implementation changes, not left as untracked files
- **Iterative:** Start with basic traversal, refine projection/rendering
