---
phase: 02-visual-polish-immersion
plan: 04
type: execute
wave: 2
depends_on: [01]
files_modified: [main.py]
autonomous: true
requirements: [NAV-03]

must_haves:
  truths:
    - "Visited points appear as a fading trail of dots in the viewport, showing the exploration path taken"
  artifacts:
    - path: "main.py"
      provides: "Breadcrumb trail rendering for recently visited points"
      section: "Render section, after point drawing and before UI overlays"
  key_links:
    - from: "main.py:travel completion"
      to: "breadcrumb recording"
      via: "Append to visit history when travel completes"
      pattern: "visited_points\\.add"
    - from: "main.py:render loop"
      to: "breadcrumb dot rendering"
      via: "Project visited points and draw fading dots"
      pattern: "project_to_tangent.*project_tangent_to_screen"
---

<objective>
Render a fading trail of dots for recently visited points in the viewport, showing the exploration path taken during the session.

Purpose: Provide spatial memory — the player can see where they've been, making the S³ surface feel explorable rather than disorienting.

Output:
- Ordered visit history (main.py state)
- Fading breadcrumb dots rendered in viewport for visible visited points (main.py render)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Current visited tracking (main.py:137-138):
```python
visited_points = set()  # Indices of points already traveled-to
```

Travel completion (main.py:406-411):
```python
if travel_target_idx is not None:
    visited_points.add(travel_target_idx)
    auto_travel_feedback = (f"Visited: {get_name(travel_target_idx)}", pygame.time.get_ticks())
    print(f"Visited: {get_name(travel_target_idx)} ({len(visited_points)} total)")
```

Point projection pattern (main.py:437-444):
```python
for i, idx in enumerate(visible_indices):
    p4d = points[idx]
    tangent_xyz = project_to_tangent(camera_pos, p4d, basis)
    tangent_xyz[0] -= player_screen_offset[0]
    tangent_xyz[1] -= player_screen_offset[1]
    p2d, depth = project_tangent_to_screen(tangent_xyz, view_width, SCREEN_HEIGHT)
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ordered visit history and breadcrumb trail rendering</name>
  <files>main.py</files>
  <action>
    1. Add `collections.deque` import at top of main.py:
    ```python
    from collections import deque
    ```

    2. After `visited_points = set()` (line 137), add the ordered visit history:
    ```python
    visit_history = deque(maxlen=50)  # Ordered trail of visited point indices (most recent last)
    ```

    3. At travel completion (line ~409, right after `visited_points.add(travel_target_idx)`), append to history:
    ```python
    visit_history.append(travel_target_idx)
    ```

    4. In the render section, after the point drawing loop and before the hover/pop/triangle overlays (around line ~490, after the point draw loop's closing), add breadcrumb rendering:

    ```python
    # Draw breadcrumb trail: fading dots for recently visited points
    if visit_history:
        trail_len = len(visit_history)
        for trail_i, trail_idx in enumerate(visit_history):
            # Project visited point to screen
            trail_p4d = points[trail_idx]
            trail_tangent = project_to_tangent(camera_pos, trail_p4d, basis)
            trail_tangent[0] -= player_screen_offset[0]
            trail_tangent[1] -= player_screen_offset[1]
            trail_p2d, trail_depth = project_tangent_to_screen(trail_tangent, view_width, SCREEN_HEIGHT)

            # Only draw if on screen and in view area
            tx, ty = int(trail_p2d[0]), int(trail_p2d[1])
            if 0 <= tx < view_width and 0 <= ty < SCREEN_HEIGHT:
                # Fade: oldest = dimmest, newest = brightest
                fade = (trail_i + 1) / trail_len  # 0.02 (oldest) to 1.0 (newest)
                alpha = int(30 + fade * 100)  # 30-130 alpha range
                dot_radius = 3 if fade > 0.5 else 2
                dot_surf = pygame.Surface((dot_radius * 2 + 4, dot_radius * 2 + 4), pygame.SRCALPHA)
                dot_color = (180, 220, 255, alpha)  # Light blue, fading
                pygame.draw.circle(dot_surf, dot_color, (dot_radius + 2, dot_radius + 2), dot_radius)
                screen.blit(dot_surf, (tx - dot_radius - 2, ty - dot_radius - 2))
    ```

    Design rationale:
    - `deque(maxlen=50)` automatically drops oldest entries — no manual cleanup needed, 50 is enough trail for navigation context
    - `visited_points` set kept for O(1) membership check (used by auto-travel, list dimming) — visit_history is parallel ordered structure
    - Breadcrumbs project through the same tangent space as regular points — they move with the camera rotation, maintaining spatial coherence
    - Light blue color (180, 220, 255) distinguishes breadcrumbs from colored points without clashing
    - Recent breadcrumbs are 3px radius, older ones 2px — subtle size difference reinforces recency
    - Alpha 30-130: oldest barely visible, newest clearly marked but not overwhelming
  </action>
  <verify>
    <manual>
      Run main.py, travel to several points:
      - After first travel, a faint dot appears at the arrival location
      - After several travels, dots form a visible trail
      - Recent dots are brighter/larger than older ones
      - Dots move with camera rotation (projected into tangent space)
      - After 50+ travels, oldest dots drop off automatically
      - Breadcrumb dots don't interfere with point rendering or tooltips
    </manual>
  </verify>
  <done>
    - visit_history deque tracks last 50 visited points in order
    - Breadcrumb dots rendered in viewport with tangent space projection
    - Fade curve: oldest → dimmest/smallest, newest → brightest/largest
    - Light blue color distinguishes from data points
    - Automatic eviction via deque maxlen
  </done>
</task>

</tasks>

<verification>
After completion, verify:

1. **Trail forms:** Travel to 5+ points and see dots marking previous locations
2. **Fading works:** First visited point is dimmer than most recent
3. **Spatial coherence:** Rotating camera moves breadcrumbs with the view (they're projected in tangent space)
4. **Capacity limit:** After 50+ visits, oldest breadcrumbs disappear
5. **No interference:** Breadcrumbs don't block point clicks, tooltips, or travel target indicators
6. **visited_points set still works:** Auto-travel (Tab) and list dimming still function correctly
</verification>

<success_criteria>
- Visited points appear as a fading trail of dots in the viewport
- Trail shows the exploration path taken (ordered by visit time)
- Most recent visits are brighter/larger, older visits fade
- Trail capacity is bounded (50 points max)
- Existing visited_points functionality (auto-travel, list dimming) unaffected
</success_criteria>

<output>
After completion, create `.planning/phases/02-visual-polish-immersion/04-SUMMARY.md`
</output>
