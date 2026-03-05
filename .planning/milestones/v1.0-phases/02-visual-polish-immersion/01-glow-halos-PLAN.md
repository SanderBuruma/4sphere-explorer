---
phase: 02-visual-polish-immersion
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [main.py]
autonomous: true
requirements: [VIS-01]

must_haves:
  truths:
    - "Points near the crosshair render with visible glowing halos that grow brighter as distance decreases"
  artifacts:
    - path: "main.py"
      provides: "Distance-based glow halos drawn behind point circles"
      section: "Point rendering loop (~lines 455-480)"
  key_links:
    - from: "main.py:point draw loop"
      to: "glow halo rendering"
      via: "Draw SRCALPHA glow circle before opaque point circle"
      pattern: "pygame.draw.circle.*screen.*color.*p2d"
---

<objective>
Add distance-based glow halos to points in the viewport. Closer points get larger, brighter halos; farther points get smaller, dimmer halos.

Purpose: Visual depth cue that makes nearby points feel more prominent and alive, enhancing immersion.

Output:
- Glow halo rendered behind each visible point, scaling with proximity (main.py)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Current point rendering loop (main.py:455-480):
```python
for p2d, angular_dist, depth, idx in projected_points:
    if 0 <= p2d[0] < view_width and 0 <= p2d[1] < SCREEN_HEIGHT:
        max_distance = FOV_ANGLE
        normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
        radius = int(2 + normalized_dist * 5)
        # ... color calculation ...
        brightness_factor = 0.3 + normalized_dist * 0.7
        color = tuple(int(c * brightness_factor) for c in base_color)
        pygame.draw.circle(screen, color, p2d.astype(int), radius)
```

Existing SRCALPHA pattern (used for pop animation and hover circle):
```python
temp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
pygame.draw.circle(temp_surf, (r, g, b, alpha), (cx, cy), radius)
screen.blit(temp_surf, (x, y))
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add glow halo rendering to point draw loop</name>
  <files>main.py</files>
  <action>
    In the point rendering loop (main.py, inside the `for p2d, angular_dist, depth, idx in projected_points:` block), add glow halo rendering **before** the existing `pygame.draw.circle(screen, color, p2d.astype(int), radius)` call.

    After `radius = int(2 + normalized_dist * 5)` and before the color calculation block, insert:

    ```python
    # Glow halo: larger, semi-transparent circle behind the point
    # Intensity scales with proximity (normalized_dist: 0.1=far, 1.0=near)
    glow_radius = int(radius * 2.5 + normalized_dist * 8)
    glow_alpha = int(30 + normalized_dist * 60)  # 30-90 alpha range
    glow_surf = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
    ```

    Then after the color is computed (after `brightness_factor` and `color` are set), draw the glow using the point's color:
    ```python
    # Draw glow with point's color at reduced alpha
    glow_color = (*color, glow_alpha)
    pygame.draw.circle(glow_surf, glow_color, (glow_radius + 2, glow_radius + 2), glow_radius)
    screen.blit(glow_surf, (int(p2d[0]) - glow_radius - 2, int(p2d[1]) - glow_radius - 2))
    ```

    The full modified section within the `if 0 <= p2d[0] < view_width ...` block becomes:
    ```python
    # Size based on angular distance
    max_distance = FOV_ANGLE
    normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
    radius = int(2 + normalized_dist * 5)

    # Color calculation (existing view_mode logic)
    if view_mode == 0:
        base_color = point_colors[idx]
    else:
        # ... existing 4D position color logic ...

    brightness_factor = 0.3 + normalized_dist * 0.7
    color = tuple(int(c * brightness_factor) for c in base_color)

    # Glow halo behind point
    glow_radius = int(radius * 2.5 + normalized_dist * 8)
    glow_alpha = int(30 + normalized_dist * 60)
    glow_surf = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*color, glow_alpha), (glow_radius + 2, glow_radius + 2), glow_radius)
    screen.blit(glow_surf, (int(p2d[0]) - glow_radius - 2, int(p2d[1]) - glow_radius - 2))

    # Point circle (existing)
    pygame.draw.circle(screen, color, p2d.astype(int), radius)
    ```

    Design rationale: SRCALPHA surface per point is the established pattern (pop animation uses it). Glow radius is ~2.5x point radius + proximity bonus, alpha 30-90 gives visible-but-subtle halos. Close points get large bright halos; edge-of-FOV points get barely visible ones.
  </action>
  <verify>
    <manual>
      Run main.py, observe:
      - Points near crosshair have visible colored halos behind them
      - Halos shrink and dim as points approach FOV edge
      - No flickering or visual artifacts
      - Frame rate remains smooth (glow uses same SRCALPHA pattern as existing animations)
    </manual>
  </verify>
  <done>
    - Glow halos rendered behind each visible point
    - Glow radius and alpha scale with proximity (normalized_dist)
    - Uses established SRCALPHA surface pattern
    - Halos use point's own color for visual coherence
  </done>
</task>

</tasks>

<verification>
After completion, verify:

1. **Close points glow visibly:** Travel near a cluster — points within ~30% of FOV should have obvious halos
2. **Far points are subtle:** Points at FOV edge should have barely visible or invisible halos
3. **Color coherence:** Glow color matches point color in both view modes (Assigned and 4D Position)
4. **Performance:** No frame drops from glow rendering (~10 SRCALPHA blits per frame is negligible)
</verification>

<success_criteria>
- Points near the crosshair render with visible glowing halos that grow brighter as distance decreases
- Glow halos use the point's assigned or 4D position color
- Halos scale continuously with distance (no abrupt cutoff)
- No frame rate degradation
</success_criteria>

<output>
After completion, create `.planning/phases/02-visual-polish-immersion/01-SUMMARY.md`
</output>
