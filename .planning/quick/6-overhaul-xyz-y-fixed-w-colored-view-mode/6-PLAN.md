---
phase: quick-6
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py
  - lib/gamepedia.py
autonomous: true
requirements: [QUICK-6]
must_haves:
  truths:
    - "Game starts in XYZ Fixed-Y W-Colored view mode by default"
    - "Planet dots/sprites retain their assigned color in the overhauled view mode"
    - "Each planet has a halo colored by its W-axis value (blue for -W, red for +W)"
    - "The view mode is visually rich with planet sprites, glow halos, and distance-based sizing"
    - "Gamepedia accurately describes the updated view mode behavior"
  artifacts:
    - path: "main.py"
      provides: "Default view mode changed, overhauled XYZ modes rendering"
    - path: "lib/gamepedia.py"
      provides: "Updated View Modes and Colors & View Modes descriptions"
  key_links:
    - from: "main.py"
      to: "sphere.py:w_to_color"
      via: "W-axis halo coloring"
      pattern: "w_to_color"
    - from: "main.py"
      to: "lib/planets.py"
      via: "Planet sprite rendering in XYZ modes"
      pattern: "get_planet_equirect|render_planet_frame"
---

<objective>
Overhaul the XYZ Fixed-Y W-Colored view mode to be the default and make it visually rich and easy to interpret. Planet dots keep their own assigned color; only the glow halo uses blue/red W-axis coloring.

Purpose: The XYZ Fixed-Y mode is the most spatially intuitive view, but currently renders as bare colored dots with no sprites or halos. Making it the default with rich rendering gives new players the best first impression.
Output: Overhauled rendering for XYZ view modes (2 and 3), updated default, updated Gamepedia.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@main.py
@sphere.py
@lib/gamepedia.py
@lib/constants.py
@lib/planets.py

<interfaces>
<!-- Key functions the executor needs -->

From sphere.py:
```python
def w_to_color(w):
    """Map w in [-1, 1] to RGB: -1=blue(0,0,255), 0=white(255,255,255), +1=red(255,0,0)."""

def project_tangent_to_screen(tangent_xyz, screen_width, screen_height, scale=2500):
    """Project tangent space (x, y, z) to 2D screen coordinates."""
```

From lib/planets.py:
```python
def get_planet_equirect(idx, name_key): ...
def render_planet_frame(equirect, size, rotation, tint_color=None): ...
def get_planet_rotation_angle(idx, elapsed_ms): ...
```

From main.py current state:
- `view_mode` initialized to `0` on line 186; loaded from save on line 249
- XYZ modes (2, 3) rendered in lines 664-733: bare circles, W-color only, no sprites/halos
- Standard modes (0, 1) rendered in lines 735-811: sprites, glow halos, distance sizing
- `planet_colors[idx]` = assigned random color per planet
- `w_to_color(w_vals[vi] / FOV_ANGLE)` used for current XYZ W coloring
- Compass guard on line 1297: `if view_mode == 0 and not gamepedia_open:`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Make XYZ Fixed-Y the default and overhaul XYZ rendering with W-colored halos</name>
  <files>main.py</files>
  <action>
**1. Change default view mode to 3 (XYZ Fixed-Y):**
- Line 186: Change `view_mode = 0` to `view_mode = 3`
- The save/load system already persists `view_mode` (line 249: `view_mode = _save_data.get("view_mode", 0)`), so change the fallback default there too: `_save_data.get("view_mode", 3)`

**2. Overhaul the XYZ rendering block (currently lines 664-733) to render planets with assigned color + W-colored halo:**

Replace the current simple-circle rendering inside the `for vi in sort_order:` loop (lines 704-723) with rich rendering matching the quality of modes 0/1. The new rendering for each visible planet should:

a) **Compute W-halo color** from the W-axis value:
```python
w_color = w_to_color(max(-1.0, min(1.0, w_vals[vi] / FOV_ANGLE)))
```

b) **Use the planet's assigned color** as the planet body color:
```python
base_color = planet_colors[idx]
```

c) **Compute distance-based sizing** (same approach as modes 0/1):
```python
angular_dist = visible_distances[vi]
normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / FOV_ANGLE)))
radius = max(2, int((2 + normalized_dist * 5) * view_zoom))
```
Note: `sort_order` contains indices into `visible_indices`/`visible_distances`/`rel_vis` arrays. So `visible_distances[vi]` correctly retrieves the angular distance for planet `visible_indices[vi]`.

d) **Draw W-colored glow halo BEHIND the planet** (using an SRCALPHA surface, same technique as modes 0/1 line 781-784):
```python
glow_radius = int(radius * 2.5 + normalized_dist * 8)
glow_surf = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
pygame.draw.circle(glow_surf, (*w_color, 60), (glow_radius + 2, glow_radius + 2), glow_radius)
screen.blit(glow_surf, (sx - glow_radius - 2, sy - glow_radius - 2))
```

e) **Render planet sprite** (rotating equirectangular texture, same as modes 0/1 lines 787-794), tinted with the assigned base_color:
```python
equirect = get_planet_equirect(idx, _name_keys[idx])
if equirect is not None:
    rot = get_planet_rotation_angle(idx, elapsed_ms)
    sz = max(4, int(2 * radius))
    surf = render_planet_frame(equirect, sz, rot, tint_color=base_color)
    screen.blit(surf, (sx - sz // 2, sy - sz // 2))
else:
    pygame.draw.circle(screen, base_color, (sx, sy), radius)
```

f) **Set planet_display_colors[idx]** to the assigned color (NOT the W color), so sidebar/tooltip show the assigned color:
```python
planet_display_colors[idx] = base_color
```

g) **Add inspection ring** (like modes 0/1, lines 797-802) for the inspected planet if in XYZ modes.

**3. Also add the breadcrumb trail** rendering for XYZ modes (currently only drawn in modes 0/1, lines 813-828). For XYZ modes, the trail dots should use the XYZ projection coordinates rather than tangent space:
- After the main planet rendering loop, iterate `visit_history`
- For each trail planet, compute its XYZ screen position using the same `player_frame` projection
- Draw fading dots at those positions (same alpha logic as the existing trail)

**4. Ensure hover/click detection still works.** The current `hover_planet` and `projected_planets` logic in the XYZ block (lines 726-732) should continue working since we keep the same `sx, sy` coordinates.

**DO NOT** change the compass guard (`view_mode == 0`). Per STATE.md, compass is for Assigned mode only. Since we're changing the default to mode 3, the compass will not show by default, which is fine -- it was designed for mode 0.
  </action>
  <verify>
    <automated>cd C:/Projects/4sphere-explorer && python -c "from main import *; print('Import OK')" 2>&1 | head -5 || echo "Note: main.py runs game loop on import, verify by running: python main.py"</automated>
    Manual: Run `python main.py` and verify:
    1. Game starts in XYZ Fixed-Y view mode (not Assigned)
    2. Planets show their assigned colors (varied hues) not uniform W-coloring
    3. Each planet has a colored halo: blue tint for negative-W planets, red tint for positive-W
    4. Planet sprites rotate (not just flat circles)
    5. Press V to cycle through all 4 modes -- all still work
    6. Sidebar colors match the planet body color, not the W-halo color
  </verify>
  <done>XYZ Fixed-Y is the default view mode. Planets render with assigned-color sprites and W-colored halos. View is visually rich with glow effects and distance-based sizing matching modes 0/1 quality.</done>
</task>

<task type="auto">
  <name>Task 2: Update Gamepedia entries for new view mode behavior</name>
  <files>lib/gamepedia.py</files>
  <action>
Update two Gamepedia entries in `GAMEPEDIA_CONTENT` to reflect the overhauled view mode:

**1. "View Modes" entry** (under Controls category, currently lines 32-46):
Update the XYZ Fixed-Y description to explain:
- It is now the default view mode (shown on startup)
- Planets keep their assigned colors
- The halo/glow around each planet indicates W-axis position: blue for negative W, red for positive W, white near zero
- The vertical axis is locked to absolute "up"

Also update the XYZ Projection description similarly (since it shares the same rendering now -- planets keep color, halo shows W).

Update the Assigned mode description to note it is no longer the default (just say "Press V to cycle to Assigned mode" or similar -- keep it natural).

**2. "Colors & View Modes" entry** (under World category, currently lines 99-108):
Update the XYZ modes paragraph to explain:
- In XYZ modes, each planet keeps its own assigned color
- The glowing halo around each planet shows the 4th coordinate (W): blue for negative W, white near zero, red for positive W
- This separates planet identity (body color) from spatial information (halo color)

Keep the writing style consistent with existing Gamepedia text: conversational, player-facing, no technical jargon. Use present tense.
  </action>
  <verify>
    <automated>cd C:/Projects/4sphere-explorer && python -m pytest tests/test_gamepedia.py -x -q 2>&1</automated>
  </verify>
  <done>Gamepedia View Modes and Colors & View Modes entries accurately describe the new default view mode and the halo-based W-coloring behavior. Test suite passes.</done>
</task>

</tasks>

<verification>
1. `python main.py` launches in XYZ Fixed-Y mode by default
2. Planet bodies show varied assigned colors (not uniform blue-white-red)
3. Planet halos show W-axis coloring (blue/red gradient)
4. Planet sprites render and rotate in XYZ modes
5. Press V cycles through all 4 view modes correctly
6. Sidebar/tooltip colors match planet body color
7. Gamepedia F1 > Controls > View Modes describes updated behavior
8. `python -m pytest tests/ -x -q` all tests pass
</verification>

<success_criteria>
- Game starts in XYZ Fixed-Y W-Colored view mode
- Planet identity is preserved (assigned color on body)
- W-axis information shown through halo coloring only
- Visual quality of XYZ modes matches modes 0/1 (sprites, halos, sizing)
- Gamepedia is accurate and up to date
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/6-overhaul-xyz-y-fixed-w-colored-view-mode/6-SUMMARY.md`
</output>
