---
phase: 02-visual-polish-immersion
plan: 03
type: execute
wave: 2
depends_on: [01]
files_modified: [main.py]
autonomous: true
requirements: [VIS-03]

must_haves:
  truths:
    - "An animated line connects the player position to the current travel target during active movement"
  artifacts:
    - path: "main.py"
      provides: "Animated dashed travel line from crosshair to target"
      section: "Render section, near travel target triangles (~lines 527-563)"
  key_links:
    - from: "main.py:travel target rendering"
      to: "travel line drawing"
      via: "Draw animated line before rotating triangles when traveling"
      pattern: "traveling.*travel_target_idx.*pop_animation"
---

<objective>
Draw an animated line connecting the player (crosshair) to the current travel target during active movement, giving visual feedback for the travel trajectory.

Purpose: Make travel feel directed and intentional — the line shows where you're heading and closes as you approach.

Output:
- Animated dashed line from crosshair center to travel target screen position during active travel (main.py)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Travel target rendering section (main.py:527-563):
```python
# Draw rotating blue triangles around travel target (hide once pop starts)
if traveling and travel_target_idx is not None and pop_animation_idx is None:
    for p2d, angular_dist, depth, idx in projected_points:
        if idx == travel_target_idx:
            # ... triangle drawing ...
            break
```

Crosshair position (main.py:566):
```python
center_x, center_y = view_width // 2, SCREEN_HEIGHT // 2
```

Travel state variables: `traveling` (bool), `travel_target_idx` (int or None)
projected_points: list of `(p2d, angular_dist, depth, idx)` tuples
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add animated dashed travel line</name>
  <files>main.py</files>
  <action>
    In the render section, just **before** the rotating blue triangles block (`if traveling and travel_target_idx is not None and pop_animation_idx is None:`), add the travel line:

    ```python
    # Draw animated travel line from crosshair to target
    if traveling and travel_target_idx is not None and pop_animation_idx is None:
        target_screen = None
        for p2d, angular_dist, depth, idx in projected_points:
            if idx == travel_target_idx:
                target_screen = p2d.astype(int)
                break

        if target_screen is not None:
            line_start = np.array([center_x, center_y])
            line_end = target_screen
            diff = line_end - line_start
            line_length = np.linalg.norm(diff)

            if line_length > 5:  # only draw if target is far enough from center
                direction = diff / line_length
                # Animated dash: offset moves over time
                dash_len = 8
                gap_len = 6
                cycle = dash_len + gap_len
                elapsed_ms = pygame.time.get_ticks() - start_time
                offset = (elapsed_ms * 0.05) % cycle  # dash flows toward target

                travel_line_surf = pygame.Surface((view_width, SCREEN_HEIGHT), pygame.SRCALPHA)
                pos = -offset  # start before line_start for seamless entry
                while pos < line_length:
                    seg_start = max(0.0, pos)
                    seg_end = min(line_length, pos + dash_len)
                    if seg_end > seg_start:
                        p1 = line_start + direction * seg_start
                        p2_line = line_start + direction * seg_end
                        # Fade alpha: stronger near midpoint, softer at endpoints
                        mid_t = (seg_start + seg_end) / (2 * line_length)
                        alpha = int(120 * (1 - abs(mid_t - 0.5) * 1.5))
                        alpha = max(30, min(120, alpha))
                        pygame.draw.line(travel_line_surf, (100, 150, 255, alpha),
                                        p1.astype(int), p2_line.astype(int), 2)
                    pos += cycle

                screen.blit(travel_line_surf, (0, 0))
    ```

    Note: `center_x, center_y` are currently defined later (line 566). Move their definition **before** this block, or define them earlier in the render section (after `view_width = SCREEN_WIDTH - 300` on line 432). Specifically, add right after `view_width = SCREEN_WIDTH - 300`:
    ```python
    center_x, center_y = view_width // 2, SCREEN_HEIGHT // 2
    ```
    And remove the duplicate definition at line 566.

    Design rationale:
    - Dashed line with flowing animation (offset increases over time) gives a sense of movement direction
    - SRCALPHA surface for per-dash alpha variation — dashes are brighter in the middle, dimmer at endpoints
    - Color matches the existing travel indicator blue (100, 150, 255)
    - Line only draws when target is >5px from center (avoid visual clutter when nearly arrived)
    - Dash pattern: 8px dash, 6px gap — visible but not heavy
  </action>
  <verify>
    <manual>
      Run main.py, click a point to travel:
      - Animated dashed blue line appears from crosshair to target point
      - Dashes flow along the line (animation)
      - Line shortens as you approach the target
      - Line disappears when arrival pop animation begins
      - No line visible when not traveling
      - Line does not extend into sidebar area
    </manual>
  </verify>
  <done>
    - Animated dashed travel line from crosshair to travel target
    - Dash animation flows toward target using time-based offset
    - Alpha fades at endpoints for soft appearance
    - Uses travel indicator blue (100, 150, 255)
    - Only visible during active travel, hidden during pop animation
  </done>
</task>

</tasks>

<verification>
After completion, verify:

1. **Line visible during travel:** Click a visible point — dashed blue line connects crosshair to target
2. **Animation flows:** Dashes move along the line toward the target
3. **Line disappears on arrival:** When snap-to-target triggers, line is gone before pop animation
4. **No visual when idle:** Line only renders when `traveling` is True
5. **Works with queue:** When a queued target becomes active, line redirects to new target
</verification>

<success_criteria>
- An animated line connects the player position to the current travel target during active movement
- Line uses animated dashes that flow toward the destination
- Line color matches existing travel indicators (blue)
- Line disappears appropriately on arrival
</success_criteria>

<output>
After completion, create `.planning/phases/02-visual-polish-immersion/03-SUMMARY.md`
</output>
