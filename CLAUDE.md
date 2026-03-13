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
- `lib/compass.py` — 4D compass widget: two great-circle rings (Y-axis blue, W-axis amber) projected from R⁴
- `sphere.py` — S³ math (points, distance, slerp, tangent projection, orientation frame, fixed-Y frame, names, colors)
- `lib/persistence.py` — Save/load game state to JSON (atomic writes, versioned format)
- `audio.py` — Procedural techno ambient (10 timbres, 12 scales, proximity playback)
- `screenshot.py` — Headless screenshot tool (SDL dummy drivers, scripted actions → output/)
- `tests/` — test_sphere (47), test_dialogue (44), test_eye_tracking (41), test_reputation (29), test_planets (22), test_gamepedia (22), test_persistence (13), test_rotation (12), test_traits (10), test_audio (9)

## Key Parameters

30,000 points on S³ | FOV 0.116 rad (~6.6°) | Travel speed 0.00008/frame | Projection scale 2500 | Camera dist 0.08 rad

## Architecture

- **Orientation frame:** 4×4 orthogonal matrix (row 0 = camera, rows 1-3 = tangent basis). `rotate_frame()` applies planar rotations, `reorthogonalize_frame()` corrects drift via Gram-Schmidt from current frame vectors
- **Fixed-Y frame (mode 3):** `build_fixed_y_frame(player_pos, w_angle)` computes frame directly from player position and a tracked angle, bypassing orientation hints. Guarantees uniform screen-space angular velocity for Q/E rotation. The `xyz_w_angle` state variable tracks the angle
- **Tangent projection:** 3 basis vectors ⊥ camera in ℝ⁴, points projected onto basis scaled by angular distance
- **Name keys:** `np.random.choice(11.8M, 30000, replace=False)` with seed 42 — deterministic, collision-free
- **Lazy caching:** Creatures, names, planets cached with LRU eviction
- **Planet pipeline:** Low-res (32×64) on main thread (6/frame budget), high-res (128×256) via background worker
- **Audio:** `generate_signal()` → raw float64 (testable), `generate_sound()` → pygame Sound. RMS-normalized, 15s seamless loops
- **Compass:** Two great circles sampled at 64 points, projected through orientation frame. Front arcs bright, back arcs dim/dashed. Pole labels at Y±/W± positions

## Controls

W/S up/down, A/D left/right, Q/E 4D depth, V cycle view mode, Ctrl+/-/scroll zoom, UP/DOWN scroll list, drag rotate, click travel, F1 Gamepedia. XYZ modes (2 & 3): WASD moves camera on S³, Q/E rotates view in tangent subspace (mode 3 uses direct angle tracking via `xyz_w_angle` for uniform speed; mode 2 Q/E has no visible effect). W axis stays fixed for stable halo coloring

## View Modes (V)

0: Assigned (random HSV) | 1: 4D Position | 2: XYZ Projection | 3: XYZ Fixed-Y. Modes 2 & 3 render planet sprites with W-colored halos (absolute W coordinate, rotation-invariant). Mode 3 Q/E rotates view into 4th dimension at uniform speed; angle resets on mode switch

## Rules

- **No commits without explicit request**
- **Math correctness:** Test 4D rotations carefully. Clamp dot products to [-1,1] before arccos
- **Compass math:** Fixed standard basis [1,0,0,0] etc. — never the player frame, never reorthogonalize reference axes
- **Gamepedia maintenance:** When changing gameplay aspects (controls, UI widgets, mechanics, audio, view modes), update the corresponding `GAMEPEDIA_CONTENT` entry in `lib/gamepedia.py` in the same change. Update `tests/test_gamepedia.py` if topic structure changes
- **Planning docs:** `.planning/` artifacts should be committed alongside implementation changes, not left as untracked files
- **Iterative:** Start with basic traversal, refine projection/rendering
