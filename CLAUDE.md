# Project: 4-Sphere Explorer

Interactive exploration of a 4-dimensional sphere (S³) embedded/projected into our visual space.

**Inspiration:** fsLh-NYhOoU transcript summary — high-dimensional geometry, sphere volume formulas, counterintuitive properties of 4D space.

---

## Core Concept

A 4-sphere (S³) is the 3D "surface" of a 4D ball — topologically equivalent to a circle (S¹, 1D surface of 2D disk) or standard sphere (S², 2D surface of 3D ball), but one dimension higher. The challenge is making it navigable and visualizable.

**Goals:**
- Traversable 4D navigation (rotating, moving across the surface)
- Projection strategy: 4D → 3D → 2D for rendering
- Intuitive controls for exploring 4D geometry
- Visualize how 4D curvature/volume properties differ from 3D

---

## Tech Stack

- **Language:** Python
- **Engine:** Pygame (established game framework)
- **Math:** NumPy (4D rotations, projections)
- **Venv:** standard ~/Projects/4sphere-explorer/venv

---

## 4-Sphere Representation

**Parametrization (Hyperspherical coordinates):**
- θ₁, θ₂, θ₃ ∈ [0, π]
- φ ∈ [0, 2π]

Or simpler: points on S³ as unit vectors in ℝ⁴ where x² + y² + z² + w² = 1.

**Projection to 3D:**
- Stereographic projection (preserves angles locally)
- Or simple orthogonal projection + rotation visualization

**Navigation:**
- Rotations relative to camera's local orientation frame (persistent, co-rotated)
- Keyboard/mouse input → frame rotation → update camera and tangent basis

---

## Known Properties (from transcript)

- S³ has 3-dimensional surface (the boundary)
- Volume peaks at n=5, so 4D volume behavior is significant
- Most volume is near the boundary (unusual for high-D)
- Useful conceptually: appears in SU(2) group representations, quaternions, and topology

---

## Current Implementation

### Files
- `main.py` — Game loop, rendering, UI, input handling, mutable game state
- `lib/constants.py` — Display/color/game constants, `distance_to_color()`, `format_dist()`
- `lib/gamepedia.py` — Gamepedia content, layout constants (`GP_*`), `word_wrap_text()`
- `lib/graphics.py` — Identicon generation, googly eyes
- `lib/planets.py` — Procedural rotating planet generation (equirect textures, hemisphere rendering, caching)
- `sphere.py` — S³ math (point generation, distance, slerp, tangent space projection, orientation frame rotation, name decoding, colors)
- `audio.py` — Procedural techno ambient music (synthesis, caching, proximity-based playback)
- `tests/test_sphere.py` — Sphere math, navigation, and name generation tests (22 tests)
- `tests/test_audio.py` — Audio signal generation and quality tests (17 tests)
- `tests/test_planets.py` — Procedural planet generation and rendering tests (17 tests)
- `tests/test_gamepedia.py` — Gamepedia click geometry and word-wrap tests (12 tests)
- `.gitignore` — venv exclusions

### Scale
- **30,000 points** uniformly distributed on S³ surface
- **FOV: 0.116 rad** (~6.6°) — tuned to show ~10 visible points at once
- **Travel speed:** 0.00008 per frame (10x faster than previous 0.000008)
- **Projection scale:** 2500 (10x original for narrow FOV)
- **Camera distance:** 0.08 rad from player (reduced from 0.15 for tight framing)

### Features
- **Lazy identicon generation:** 32×32 identicons cached on-demand with LRU eviction, never all 30k at startup
- **Lazy name generation:** 11.8M unique name space (4 regions: core+end+suffix+number, core+end+suffix, core+suffix+number, core+suffix). Numbers always appended after word suffixes, never replacing them. Keys sampled once at startup, decoded deterministically per point
- **Tangent space projection:** Points projected into camera's local tangent plane, so visible points cluster around crosshair
- **Procedural rotating planets:** Each point is a unique procedurally generated planet with smooth gradient noise textures (12 color palettes, seeded by name key). Planets rotate (20s period, per-point phase offset). Equirectangular textures (64×128) generated lazily (max 2 per frame), hemisphere rendered via UV lookup with edge darkening and highlight shading. Falls back to circles for uncached planets
- **Unified point coloring:** All UI elements (3D viewport, tooltip, detail panel, sidebar, inspection ring) use the same color per point. No distance-based brightness or hue modulation — color is purely from the point's identity
- **Four view modes** (toggle V):
  - 0: Assigned — permanent random HSV colors per point
  - 1: 4D Position — color derived from normalized relative 4D direction
  - 2: XYZ Projection — 3D position relative to player, W coordinate → blue/white/red color
  - 3: XYZ Fixed-Y — like mode 2 but Y axis locked to absolute [0,1,0,0], only horizontal panning
- **Navigation:** Click points in view or list to travel (slerp interpolation); WASD/QE rotate camera relative to current orientation
  - Travel completes at 0.02 rad proximity (snap to target) → pop animation (400ms expanding fade-out circle)
  - Travel target marked with `<` in list and 3 rotating blue triangles in view (6s rotation)
  - **Travel queue:** Clicking a new target while traveling queues it; travel starts after arriving at current target. Queued target shown with `<<` in list (blue)
- **UI:** Crosshair at camera position, scrollable distance-sorted list with point colors, hover tooltips with identicons
- **Detail panel:** Radial menu "Info" option shows large (64×64) rotating planet with tint color, plus name, distance, 4D coordinates, and audio parameters
- **Gamepedia (F1):** In-game encyclopedia overlay. Left panel lists topics grouped by category (Controls, Navigation, World, Audio, 4D Geometry, UI) with per-group accent colors. Right panel shows word-wrapped scrollable content. Click topics or use UP/DOWN to navigate, mouse wheel to scroll content. All game input suppressed while open. Layout constants (`GP_LEFT_X`, `GP_LEFT_W`, `GP_TOP_Y`, `GP_LINE_H`) shared between click handler and renderer. Content in `GAMEPEDIA_CONTENT` must be kept up to date when features change.
- **Distance display:** mrad for distances < 1 rad, rad for >= 1 rad
- **Procedural ambient music:** Each point has a unique techno soundscape (seeded by name key), audible within 10 mrad (`AUDIO_RANGE`). Volume fades linearly with distance. Ten timbres: supersaw pad, acid bass, synth pluck, FM bass, noise drone, ring mod, PWM, organ, wavefold, stutter — root 33–466 Hz (MIDI 25–70), harmonics capped at 700 Hz with rolloff above 580 Hz. Twelve scales (pentatonic, dorian, phrygian, whole tone, blues, harmonic minor, lydian, mixolydian, locrian, japanese in-sen). Five tempo levels (0.08–5.0s). Tone frequencies octave-folded above 580 Hz. 2.14M+ discrete configurations. RMS-normalized for consistent perceived loudness. 15-second seamless loops with crossfade

### Controls
| Input | Action |
|-------|--------|
| W/S | Rotate up/down (relative to view) |
| A/D | Rotate left/right (relative to view) |
| Q/E | Rotate in 4D depth |
| V | Cycle view mode (Assigned → 4D Position → XYZ Projection → XYZ Fixed-Y) |
| Ctrl +/- or scroll (modes 2-3) | Zoom XYZ projection |
| UP/DOWN | Scroll point list |
| Drag | Rotate camera (relative to view) |
| Left click (view) | Travel to nearest point |
| Left click (list) | Travel to selected point |
| F1 | Toggle Gamepedia encyclopedia |

---

## Implementation Notes

- **Persistent orientation frame:** 4×4 orthogonal matrix (row 0 = camera, rows 1-3 = tangent basis). `rotate_frame()` applies exact planar rotations in the (camera, basis[i]) plane, co-rotating camera and tangent vectors. `reorthogonalize_frame()` corrects numerical drift via Gram-Schmidt from current frame vectors (not fixed standard basis), preserving orientation continuity. This replaces the old per-frame Gram-Schmidt approach which caused direction flipping when the camera moved away from standard basis axes.
- **Tangent space projection:** 3 orthonormal basis vectors from orientation frame, perpendicular to camera in ℝ⁴, points projected onto basis scaled by angular distance
- **Name key sampling:** `np.random.choice(TOTAL_NAMES, 30000, replace=False)` at startup with fixed seed (42) ensures deterministic, collision-free 30k unique names from 11.8M name space
- **Lazy caching:** Identicons, names, and planet textures cached separately with LRU eviction in `update_visible()` to keep memory bounded
- **Planet rendering pipeline:** `generate_equirect_texture(seed)` → `(64,128,3)` uint8 array sampled via snoise3 + gradient LUT. `render_planet_frame()` samples a hemisphere via precomputed UV arrays (bilinear for ≥48px, nearest-neighbor below). Per-frame budget caps generation at 2 textures to avoid stalls. Tint via `BLEND_MULT` preserves point color identity
- **Travel completion:** Snaps to target at < 0.02 rad proximity, fires pop animation. If a queued target exists, immediately begins traveling to it
- **Audio synthesis:** `generate_signal()` returns raw float64 array (testable without pygame). `generate_sound()` wraps it into a `pygame.mixer.Sound`. Ten timbre functions each take `(freq, t, rng, tempo_range)`. `_rolloff(h)` attenuates harmonics linearly between 580–700 Hz to keep energy warm. Acid resonance uses proper phase accumulation (`np.cumsum`) instead of `freq*t`. Ring mod filters ratios to keep both sum and difference frequencies below 580 Hz, with full sideband suppression above. DC offset removed before RMS normalization to target 0.25. `update_audio()` manages channel allocation per frame based on proximity
- Keep 4D rotation math clean and testable
- Minimize over-engineering: navigation + rendering first, fancy visuals second

---

## Project-Specific Rules

- **Math correctness:** Test 4D rotations carefully. Quaternion vs. matrix representation choice will impact implementation.
- **Gamepedia maintenance:** When adding or changing features, update the corresponding `GAMEPEDIA_CONTENT` entries in `lib/gamepedia.py` to keep the in-game encyclopedia accurate. Also update `tests/test_gamepedia.py` if topic structure changes (group/topic counts).
- **No commits without explicit request.** (Standard rule applies.)
- **Iterative:** Expect this to evolve — start with basic traversal, then refine projection/rendering.

