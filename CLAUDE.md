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
- `main.py` — Game loop, rendering, UI, input handling
- `sphere.py` — S³ math (point generation, distance, slerp, tangent space projection, orientation frame rotation, name decoding, colors)
- `audio.py` — Procedural techno ambient music (synthesis, caching, proximity-based playback)
- `test_sphere.py` — Unit tests (point count, FOV visibility, travel speed, name format, travel queue, rotation smoothness, audio volume/quality)
- `.gitignore` — venv exclusions

### Scale
- **30,000 points** uniformly distributed on S³ surface
- **FOV: 0.116 rad** (~6.6°) — tuned to show ~10 visible points at once
- **Travel speed:** 0.000008 per frame (5x slower than original)
- **Projection scale:** 2500 (10x original for narrow FOV)
- **Camera distance:** 0.08 rad from player (reduced from 0.15 for tight framing)

### Features
- **Lazy identicon generation:** 32×32 identicons cached on-demand with LRU eviction, never all 30k at startup
- **Lazy name generation:** 11.8M unique name space (4 regions: core+end+suffix+number, core+end+suffix, core+suffix+number, core+suffix). Numbers always appended after word suffixes, never replacing them. Keys sampled once at startup, decoded deterministically per point
- **Tangent space projection:** Points projected into camera's local tangent plane, so visible points cluster around crosshair
- **Colored points:** Random HSV colors with consistent brightness; distance-modulated rendering
- **Two view modes** (toggle V):
  - Assigned: permanent random colors per point
  - 4D Position: color derived from normalized relative 4D direction (shows which direction in 4D space)
- **Navigation:** Click points in view or list to travel (slerp interpolation); WASD/QE rotate camera relative to current orientation
  - Travel completes at 0.02 rad proximity (snap to target) → pop animation (400ms expanding fade-out circle)
  - Travel target marked with `<` in list and 3 rotating blue triangles in view (6s rotation)
  - **Travel queue:** Clicking a new target while traveling queues it; travel starts after arriving at current target. Queued target shown with `<<` in list (blue)
- **UI:** Crosshair at camera position, scrollable distance-sorted list with color swatches, hover tooltips
- **Distance color gradient:** Green (0% of LoS) → Yellow (60% of LoS) → Red (100% of LoS)
- **Distance display:** mrad for distances < 1 rad, rad for >= 1 rad
- **Procedural ambient music:** Each point has a unique techno soundscape (seeded by name key), audible within 10 mrad (`AUDIO_RANGE`). Volume fades linearly with distance. Four timbres: supersaw pad, acid bass, synth pluck, FM bass — all low-frequency (root 58–185 Hz, harmonics capped ~500 Hz). RMS-normalized for consistent perceived loudness. 15-second seamless loops with crossfade

### Controls
| Input | Action |
|-------|--------|
| W/S | Rotate up/down (relative to view) |
| A/D | Rotate left/right (relative to view) |
| Q/E | Rotate in 4D depth |
| V | Toggle view mode (Assigned ↔ 4D Position) |
| UP/DOWN | Scroll point list |
| Drag | Rotate camera (relative to view) |
| Left click (view) | Travel to nearest point |
| Left click (list) | Travel to selected point |

---

## Implementation Notes

- **Persistent orientation frame:** 4×4 orthogonal matrix (row 0 = camera, rows 1-3 = tangent basis). `rotate_frame()` applies exact planar rotations in the (camera, basis[i]) plane, co-rotating camera and tangent vectors. `reorthogonalize_frame()` corrects numerical drift via Gram-Schmidt from current frame vectors (not fixed standard basis), preserving orientation continuity. This replaces the old per-frame Gram-Schmidt approach which caused direction flipping when the camera moved away from standard basis axes.
- **Tangent space projection:** 3 orthonormal basis vectors from orientation frame, perpendicular to camera in ℝ⁴, points projected onto basis scaled by angular distance
- **Name key sampling:** `np.random.choice(TOTAL_NAMES, 30000, replace=False)` at startup with fixed seed (42) ensures deterministic, collision-free 30k unique names from 11.8M name space
- **Lazy caching:** Both identicons and names cached separately with LRU eviction in `update_visible()` to keep memory bounded
- **Travel completion:** Snaps to target at < 0.02 rad proximity, fires pop animation. If a queued target exists, immediately begins traveling to it
- **Audio synthesis:** `generate_signal()` returns raw float64 array (testable without pygame). `generate_sound()` wraps it into a `pygame.mixer.Sound`. Four timbre functions (`_synth_supersaw`, `_synth_acid`, `_synth_pluck`, `_synth_fm`) each take frequency, time array, and RNG. DC offset removed before RMS normalization to target 0.25. `update_audio()` manages channel allocation per frame based on proximity
- Keep 4D rotation math clean and testable
- Minimize over-engineering: navigation + rendering first, fancy visuals second

---

## Project-Specific Rules

- **Math correctness:** Test 4D rotations carefully. Quaternion vs. matrix representation choice will impact implementation.
- **No commits without explicit request.** (Standard rule applies.)
- **Iterative:** Expect this to evolve — start with basic traversal, then refine projection/rendering.

