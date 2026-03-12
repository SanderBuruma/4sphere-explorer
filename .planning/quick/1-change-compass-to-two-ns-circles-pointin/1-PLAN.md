---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - lib/compass.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Compass widget shows two ring ellipses instead of rose+tilt bar+W gauge"
    - "Y-axis ring passes visually through the point where [0,1,0,0] and [0,-1,0,0] project"
    - "W-axis ring passes visually through the point where [0,0,0,1] and [0,0,0,-1] project"
    - "Rings rotate correctly as the player navigates (camera orientation changes)"
    - "Ring arcs behind the camera are rendered dimmer/dashed to convey depth"
  artifacts:
    - path: "lib/compass.py"
      provides: "Two-ring compass widget"
      min_lines: 80
  key_links:
    - from: "main.py"
      to: "lib/compass.py"
      via: "render_compass(screen, orientation, x, y, size)"
      pattern: "render_compass"
---

<objective>
Replace the current compass widget (rose + tilt bar + W gauge) with two great-circle rings:
- NS ring: great circle in the plane of [0,1,0,0] and [1,0,0,0] — passes through the Y-axis poles
- W ring: great circle in the plane of [0,0,0,1] and [1,0,0,0] — passes through the W-axis poles

Each ring is sampled as N points on S3, projected through the orientation frame into 2D widget space, and drawn as a polyline. Arcs behind the camera are dimmer to convey the 3D depth illusion. Pole markers and axis labels sit at the projected Y+/Y-/W+/W- positions.

Purpose: Provides a more geometrically faithful 4D compass — the rings show the camera's position relative to absolute axes rather than decomposed scalar readouts.
Output: Revised lib/compass.py with new render_compass() and math helpers. main.py call signature is unchanged.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@lib/compass.py

# Key math notes from STATE.md
# - orientation[0] = camera direction (unit vector in R^4)
# - orientation[1..3] = tangent basis (3 orthonormal vectors in R^4 perp. to camera)
# - Fixed axes are exact constants — never re-orthogonalize them
# - Clamp dot products to [-1,1] before arccos
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite lib/compass.py as two great-circle rings</name>
  <files>lib/compass.py</files>
  <action>
Replace the entire compass implementation with a two-ring renderer. Keep the public API signature identical: render_compass(screen, orientation, x, y, size=120). Remove all old helpers (calculate_heading, calculate_tilt, calculate_w_alignment, _update_needle, and related module state). Remove the _LERP_DURATION_MS, _needle_angle, etc. state.

**New math approach — projecting a great circle into 2D widget space:**

A great circle is defined by two orthonormal vectors (a, b) in R^4:
  circle(t) = cos(t) * a + sin(t) * b    for t in [0, 2*pi)

Sample N=64 points. For each point p:
1. Project onto orientation frame using dot products:
   - front = dot(p, orientation[0])   # depth: > 0 = front hemisphere
   - right = dot(p, orientation[1])   # widget X axis
   - up    = dot(p, orientation[2])   # widget Y axis
   (orientation[3] is unused — 2D projection)
2. Widget coords:  wx = cx + right * scale,  wy = cy - up * scale
3. Depth: front > 0 → bright (full opacity), front < 0 → dim (alpha ~60)

Two rings with fixed plane vectors:
- NS ring:  a = [1,0,0,0],  b = [0,1,0,0]   (XY plane, passes through Y poles)
  Color: (100, 180, 255) blue-white, label "Y" at the Y+ and Y- projected positions
- W ring:   a = [1,0,0,0],  b = [0,0,0,1]   (XW plane, passes through W poles)
  Color: (255, 160, 80) amber, label "W" at W+ and W- projected positions

**Widget layout:**
- Widget is `size x size` pixels with translucent dark background (same as before).
- Center cx = cy = size // 2
- scale = size * 0.38  (leaves margin for labels)
- Draw a faint circle outline at radius = scale as horizon reference

**Ring rendering:**
- For each ring, split the 64 sampled points into "front" segments (front >= 0) and "back" segments (front < 0).
- Draw front segments as solid lines (width 2), back segments as dotted lines (every other segment, width 1) in a dimmer shade (~50% brightness).
- At the exact pole positions (t where p = b or p = -b), draw a small circle (radius 3) and a text label.

**Pole markers:**
- NS ring poles: b = [0,1,0,0] and -b = [0,-1,0,0]
  Project each, place label "Y+" and "Y-" (or just "N"/"S" for compactness)
- W ring poles: b = [0,0,0,1] and -b = [0,0,0,-1]
  Project each, place label "W+" and "W-"

**Font:**
- One font size: max(9, size // 13) for all labels

**No animation state needed** — rings update every frame from the current orientation directly. Remove all _lerp* module-level variables.

Do not import anything new beyond math and pygame (already imported). numpy is not imported in compass.py — keep it that way. Use plain Python lists/tuples for the 4-element vectors and manual dot products (four multiplications).

Dot product helper (inline or tiny function):
  def _dot4(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]

Orientation rows are numpy arrays, so indexing orientation[0][0] etc. works; convert with float().
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -c "
import numpy as np, pygame
pygame.init()
screen = pygame.display.set_mode((200, 200))
from lib.compass import render_compass
orientation = np.eye(4)
render_compass(screen, orientation, 10, 10, 120)
# Check no exceptions, check no old symbols exported
import lib.compass as c
assert not hasattr(c, '_needle_angle'), 'old lerp state still present'
assert not hasattr(c, 'calculate_heading'), 'old heading fn still present'
print('OK')
pygame.quit()
"
    </automated>
  </verify>
  <done>
    - render_compass() draws two elliptical rings (no rose, no tilt bar, no W gauge)
    - Y-ring (blue) and W-ring (amber) both visible with pole labels
    - Front arcs brighter than back arcs
    - No old lerp or heading state in the module
    - Smoke test passes without exceptions
  </done>
</task>

</tasks>

<verification>
Run the smoke test in the verify block. Then launch the game manually and visually confirm:
- Two rings appear in the top-left corner when view_mode == 0
- Rings rotate as you press W/A/S/D/Q/E
- Y ring (blue) poles align with up/down orientation
- W ring (amber) poles align with 4D depth orientation
</verification>

<success_criteria>
- Smoke test passes: render_compass() executes without error on identity orientation
- No old compass symbols (calculate_heading, _needle_angle, etc.) remain in lib/compass.py
- Two-ring visual confirmed via manual game run
</success_criteria>

<output>
No SUMMARY.md needed for quick plans.
</output>
