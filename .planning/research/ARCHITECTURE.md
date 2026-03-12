# Architecture: 4D Compass Widget Integration

**Project:** 4-Sphere Explorer
**Researched:** 2026-03-12
**Context:** Adding a corner compass widget to existing Pygame rendering pipeline

## Executive Summary

The compass widget integrates into the existing Pygame rendering pipeline with minimal coupling. It derives orientation data from a persistent 4×4 orientation frame (row 0 = camera direction, rows 1-3 = tangent basis vectors in ℝ⁴), applies visual transformations to map 4D basis vectors to 2D screen space, and renders to a corner of the screen after the main viewport but before the sidebar.

The widget architecture is:
- **Data source:** 4×4 `orientation` matrix from sphere math
- **Rendering phase:** Post-viewport, pre-sidebar (approximately line ~1155 in main.py)
- **Screen real estate:** Fixed top-left or top-right corner (e.g., 80×120 px)
- **New code:** Single dedicated module `lib/compass.py` (150-250 LOC) with no modifications to core orientation frame or rotation logic
- **Build strategy:** Implement rendering first (direction arrows), then depth indicator (W axis color), keeping each component testable in isolation

---

## 1. Data Flow: Orientation Frame → Compass

### 1.1 Orientation Frame Structure

**Current state** (main.py, lines 69-74):
```python
orientation = np.eye(4)  # 4x4 orthonormal matrix
orientation[0] = camera_pos.copy()  # row 0 = current camera direction (unit vector in R4)
for _i in range(3):
    orientation[_i + 1] = tangent_basis_vec  # rows 1-3 = orthonormal basis perpendicular to camera
```

The frame is:
- **Row 0:** Camera position on S³ (unit vector in ℝ⁴) — direction player is "looking toward"
- **Rows 1, 2, 3:** Orthonormal tangent vectors spanning the 3D manifold perpendicular to the camera direction
- **Invariant:** All rows are unit vectors; rows 1-3 are pairwise orthogonal and orthogonal to row 0

### 1.2 Compass Data Requirements

The compass displays player **orientation** relative to **fixed standard basis axes** (e₁=[1,0,0,0], e₂=[0,1,0,0], e₃=[0,0,1,0], e₄=[0,0,0,1]).

Required data per frame:
- **Horizontal compass (X/Z axes):** Projections of `orientation[0]` onto X/Z plane
  - Computation: `x_proj = orientation[0][0]`, `z_proj = orientation[0][2]`

- **Vertical indicator (Y axis):** Projection of `orientation[0]` onto Y
  - Computation: `y_proj = orientation[0][1]`, range [-1, 1]

- **Depth indicator (W axis):** Projection of `orientation[0]` onto W
  - Computation: `w_proj = orientation[0][3]`, range [-1, 1]

No modifications needed to orientation frame or rotation logic.

---

## 2. Rendering Pipeline Integration

### 2.1 Current Render Sequence (main.py)

Lines 580–1356 render in this order:
1. Background fill
2. Starfield parallax
3. Viewport planets
4. Travel line
5. Tooltips/menus
6. Divider line (~1154)
7. Sidebar header/search
8. Sidebar list
9. Status line
10. Gamepedia overlay (if open)

### 2.2 Compass Integration Point

**Insert after line 1153** (between divider and sidebar header):
```python
if not gamepedia_open:
    render_compass(screen, orientation, 10, 10)
```

**Reasoning:**
- Corner widget, viewport-independent
- Rendered after viewport but before gamepedia modal
- Won't be covered by sidebar or overlays

### 2.3 Screen Placement

**Recommendation:** Top-left corner (x=10, y=10)
- Standard compass UI convention
- Small footprint (70×90 px), minimal obstruction
- Visible in all view modes

---

## 3. Compass Component Architecture

### 3.1 New Module: `lib/compass.py`

**Public interface:**
```python
def render_compass(screen, orientation, x, y, size=70):
    """Render 4D compass to screen at (x, y)."""
```

**Internal components:**

| Component | Purpose |
|-----------|---------|
| `_compute_compass_angles()` | Extract X/Z plane angle from orientation[0] |
| `_compute_y_tilt()` | Extract Y projection |
| `_compute_w_depth()` | Extract W projection |
| `_draw_compass_rose()` | Draw cardinal directions + needle |
| `_draw_y_indicator()` | Draw vertical bar for Y |
| `_draw_w_indicator()` | Draw color block for W |

### 3.2 Compass Calculations

**X/Z Angle (compass rose):**
```python
x_proj = orientation[0][0]
z_proj = orientation[0][2]
angle = np.arctan2(x_proj, z_proj)  # direction in X/Z plane
magnitude = np.sqrt(x_proj**2 + z_proj**2)  # alignment with plane
```

**Y Tilt:**
```python
y_proj = orientation[0][1]  # range [-1, 1]
```

**W Depth:**
```python
w_proj = orientation[0][3]  # range [-1, 1]
```

### 3.3 Data Flow

```
orientation[0] (4D unit vector)
    ↓
+---+---+---+---+
|x  |y  |z  |w  |
+---+---+---+---+
 ↓   ↓   ↓   ↓
 +--+   +--+   +--+
 |Rose   |Y |  |W |
 +--+   +--+   +--+
    ↓        ↓
 render_compass(screen)
```

---

## 4. Visual Design

### 4.1 Compass Rose (X/Z Plane)

**Display:** 45×45 px circle with:
- Cardinal ticks (+X right, -X left, +Z up, -Z down)
- Text labels "X+", "X-", "Z+", "Z-"
- Direction needle (arrow) showing orientation[0] projection
- Opacity scales with magnitude (dim if perpendicular to X/Z plane)

### 4.2 Y Indicator (Vertical Axis)

**Display:** 8×40 px vertical bar (right of compass rose)
- Color gradient: blue (-1) → white (0) → red (+1)
- Tick mark at current Y position
- Label "Y"

### 4.3 W Indicator (Depth)

**Display:** 12×12 px color block + label (below compass)
- Color gradient: blue (-1) → white (0) → red (+1)
- Label "W: [value]"

### 4.4 Layout

```
Top-left (x=10, y=10):

+----------- Compass Widget (70×90 px) -----------+
|                                                |
|  [Compass Rose]        [Y Bar]                 |
|  (45×45 px)            (8×40 px)               |
|  - Cardinal ticks                              |
|  - Direction needle                            |
|                                                |
|  [W: 0.23] (12×12 color block + label)        |
|                                                |
+------------------------------------------------+
```

All text: 10-12pt font, color (200, 200, 200)

---

## 5. Component Responsibilities

### 5.1 Compass Module (`lib/compass.py`)

**Owns:**
- Extracting orientation[0] components
- Computing angle, Y tilt, W depth
- Drawing all visuals (rose, Y bar, W block)
- Text rendering for labels
- Color mapping for gradients

**Does NOT own:**
- Managing orientation frame
- Updating orientation
- Reorthogonalization
- Game state changes

### 5.2 Main Loop (`main.py`)

**Remains responsible for:**
- Managing `orientation` 4×4 matrix
- Updating via `rotate_frame()` / `rotate_frame_tangent()`
- Reorthogonalization via `reorthogonalize_frame()`
- Calling `render_compass()` each frame
- Passing read-only orientation to compass

**Files NOT modified:**
- `sphere.py` — rotation math untouched
- `audio.py`, `lib/graphics.py`, `lib/planets.py` — no changes
- Game loop, input, state management — no changes

---

## 6. Integration Phases

### Phase A: Setup

1. Create `lib/compass.py` (stub)
2. Add import to `main.py` (line ~23)
3. Add render call (line ~1153)
4. Test: gray rectangle visible

### Phase B: Compass Rose

5. Implement `_compute_compass_angles()`
6. Implement `_draw_compass_rose()`
7. Integrate into `render_compass()`
8. Test: rose rotates with WASD

### Phase C: Y/W Indicators

9. Implement `_compute_y_tilt()` and `_compute_w_depth()`
10. Implement `_draw_y_indicator()` and `_draw_w_indicator()`
11. Integrate into `render_compass()`
12. Test: bars respond to Q/E rotation

### Phase D: Polish

13. Adjust colors/sizing
14. Add unit tests (`test_compass.py`)
15. Document in Gamepedia
16. Manual play-test

### Phase E: Optional (v1.3+)

- Click compass to snap to cardinal
- Keyboard shortcuts (Ctrl+arrow)
- Customizable position
- Compass in XYZ view modes

---

## 7. Potential Pitfalls

### Pitfall 1: Frame Drift

**What goes wrong:** Compass shows stale orientation after reorthogonalization.

**Why:** Gram-Schmidt (line 296) may adjust frame. Stale cached values show old direction.

**Mitigation:**
- Read `orientation[0]` fresh each frame, never cache
- Test with small perturbations (noise) to verify correctness

### Pitfall 2: Axis Confusion

**What goes wrong:** Compass rose points wrong direction (inverted, off by 90°).

**Why:** X/Z conventions (Y down in Pygame) vs math conventions (Y up).

**Mitigation:**
- Document clearly: "+Z is up, +X is right"
- Test: Rotate to align with +Z, verify needle points up
- Use `arctan2(x, -z)` if screen orientation differs

### Pitfall 3: Gamepedia Modal

**What goes wrong:** Compass hidden when Gamepedia open.

**Why:** Modal overlay fills screen.

**Current mitigation:** Compass only renders when `not gamepedia_open`.

### Pitfall 4: Performance

**What goes wrong:** Frame rate drops from compass rendering.

**Why:** Excessive `font.render()` per frame is slow.

**Mitigation:**
- Cache font surfaces for labels at init
- Pre-render, don't call font.render() in loop
- Use geometric primitives (fast)

### Pitfall 5: W Depth Color Semantics

**What goes wrong:** Blue→white→red gradient confused with temperature (blue=cold).

**Why:** W depth isn't temperature, just direction.

**Mitigation:**
- Add clear "W Depth" label
- Gamepedia: "Purple = -W, White = W=0, Cyan = +W"

---

## 8. Files Modified

| File | Change |
|------|--------|
| `lib/compass.py` | NEW (150-250 LOC) |
| `main.py` | Add import (~23), add render call (~1153) |
| `lib/constants.py` | OPTIONAL: compass position constants |
| `tests/test_compass.py` | NEW: unit tests |
| `lib/gamepedia.py` | OPTIONAL: UI section entry |

---

## 9. Testing Strategy

### Unit Tests (test_compass.py)

```python
def test_compass_angle_aligned_z():
    orientation = np.eye(4)
    orientation[0] = np.array([0, 0, 1, 0])  # +Z
    angle, mag, x, z = _compute_compass_angles(orientation[0])
    assert abs(angle - np.pi/2) < 1e-6  # pointing up

def test_compass_angle_aligned_x():
    orientation = np.eye(4)
    orientation[0] = np.array([1, 0, 0, 0])  # +X
    angle, mag, x, z = _compute_compass_angles(orientation[0])
    assert abs(angle) < 1e-6  # pointing right

def test_y_tilt():
    orientation = np.eye(4)
    orientation[0] = np.array([0.7071, 0.7071, 0, 0])
    y = _compute_y_tilt(orientation[0])
    assert abs(y - 0.7071) < 1e-3

def test_w_depth():
    orientation = np.eye(4)
    orientation[0] = np.array([0, 0, 0.7071, 0.7071])
    w = _compute_w_depth(orientation[0])
    assert abs(w - 0.7071) < 1e-3

def test_color_w_negative():
    color = _w_to_color(-1.0)
    assert color[2] > color[0]  # B > R (blue)

def test_color_w_zero():
    color = _w_to_color(0.0)
    assert all(abs(color[i] - color[j]) < 20 for i in range(3) for j in range(3))
```

### Integration Tests (manual checklist)

- [ ] Compass visible at top-left at startup
- [ ] Rose rotates correctly with WASD
- [ ] Rose dims when rotating in Y (Q/E perpendicular to X/Z)
- [ ] Y bar updates correctly
- [ ] W block changes color blue→white→red
- [ ] Hidden when Gamepedia open
- [ ] No FPS regression
- [ ] No visual glitches
- [ ] Updates smoothly every frame

---

## 10. Future Extensions

**v1.3+ possibilities:**
- Click compass to snap to cardinal direction
- Keyboard shortcuts (Ctrl+arrow) to align to axes
- Customizable position (settings)
- Compass in XYZ view modes (2, 3)
- Snap-to-cardinal on keyboard press
- Compass scale/sizing options

**Architecture already supports:**
- Parameterized position (x, y in function signature)
- Click bounding box detection (simple addition)
- View mode conditional rendering
- Snap logic in rotation handler

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Frame integration | HIGH | Stable, well-documented, unchanged |
| Pipeline placement | HIGH | Clear insertion point identified |
| Component math | HIGH | Vector projection is straightforward |
| Visual design | MEDIUM | Sensible but untested; may iterate after impl |
| Performance | HIGH | Minimal draws, cached surfaces = fast |
| Testing | HIGH | Unit tests simple, integration tests clear |

---

## Summary

**Approach:**
1. New `lib/compass.py` module reads `orientation[0]` (4D), renders 2D compass to corner
2. Single `render_compass()` call in main.py (~line 1153)
3. No modifications to sphere.py rotation math or orientation frame management
4. Build in phases: rose → Y indicator → W indicator → polish
5. Minimal risk: read-only, self-contained, no game state mutation

**Key property:** Compass is entirely decoupled from navigation logic. Pure visualization layer over orientation frame. Future rotation math changes transparent to compass.
