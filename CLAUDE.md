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
- Rotations in 4D (6 independent planes: xy, xz, xw, yz, yw, zw)
- Keyboard/mouse input → 4D rotation matrix → update surface

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
- `sphere.py` — S³ math (point generation, distance, slerp, tangent space projection, name generation, colors)
- `.gitignore` — venv exclusions

### Features
- **300 points** randomly distributed on S³ surface
- **Tangent space projection:** Points projected into camera's local tangent plane, so nearby points cluster around crosshair
- **Named points:** Procedurally generated futuristic names (Core+End Suffix pattern, 90% 3-syllable / 10% 2-syllable)
- **Colored points:** Random HSV colors with consistent brightness; depth-modulated rendering
- **Two view modes** (toggle V):
  - Assigned: permanent random colors per point
  - 4D Position: color derived from relative XYZW offset to camera (R=X, G=Y, B=Z, W=brightness)
- **Navigation:** Click points in view or list to travel (slerp interpolation); WASD/QE rotate camera in 4D planes
- **UI:** Crosshair at camera position, scrollable distance-sorted list with color swatches, hover tooltips

### Controls
| Key | Action |
|-----|--------|
| W/S | Rotate XY plane |
| A/D | Rotate XZ plane |
| Q/E | Rotate XW plane |
| V | Toggle view mode |
| UP/DOWN | Scroll point list |
| Left click (view) | Travel to nearest point |
| Left click (list) | Travel to selected point |

---

## Implementation Notes

- Tangent space projection: 3 orthonormal basis vectors perpendicular to camera in ℝ⁴, points projected onto basis scaled by angular distance
- Keep 4D rotation math clean and testable
- Minimize over-engineering: navigation + rendering first, fancy visuals second

---

## Project-Specific Rules

- **Math correctness:** Test 4D rotations carefully. Quaternion vs. matrix representation choice will impact implementation.
- **No commits without explicit request.** (Standard rule applies.)
- **Iterative:** Expect this to evolve — start with basic traversal, then refine projection/rendering.

