---
phase: 03-information-context
plan: 02
type: execute
wave: 2
depends_on: [01-audio-params-PLAN.md]
files_modified: [main.py]
autonomous: true
requirements: [INFO-01]

must_haves:
  truths:
    - "User can click-hold any visible point to open a radial menu, select Info, and see a detail panel with 4D coordinates, name, distance, and audio summary"
  artifacts:
    - path: "main.py"
      provides: "Radial menu state machine, detail panel rendering, inspection ring"
      section: "Event loop + render section"
  key_links:
    - from: "main.py:MOUSEBUTTONDOWN"
      to: "radial menu state machine"
      via: "Hold timer starts on click, menu opens after 200ms threshold"
      pattern: "event.type == pygame.MOUSEBUTTONDOWN"
    - from: "main.py:radial menu Info selection"
      to: "detail panel rendering"
      via: "Sets inspected_point_idx, panel renders each frame"
      pattern: "inspected_point_idx"
---

<objective>
Implement click-hold radial menu on viewport points with an Info option that opens a floating detail panel showing point name, 4D coordinates, angular distance, and audio summary.

Purpose: Deliver INFO-01 — user can inspect any visible point's full data.

Output:
- Radial menu system with hold-to-open interaction (main.py)
- Detail panel rendering with audio summary from get_audio_params (main.py)
- Inspection ring highlight on inspected point (main.py)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-information-context/01-CONTEXT.md

Key integration points in main.py:
- **Click handling:** Lines 345-387. `MOUSEBUTTONDOWN` sets `drag_start`, `MOUSEBUTTONUP` checks drag distance < 10px. Must add hold timer logic.
- **Point rendering:** Lines 479-520. `last_projected_points` stores screen positions for hit detection.
- **Hover detection:** Lines 474-520 already compute `hover_point` via distance-squared against projected points.
- **SRCALPHA pattern:** Used by glow, pop animation, breadcrumbs — reuse for panel and menu.
- **Font:** `pygame.font.Font(None, 14)` at line 39.

Audio import needed: `from audio import get_audio_params` (Plan 01 provides this).

Interaction design from CONTEXT.md:
- **Trigger:** Click-hold on viewport point for ~200ms opens radial menu
- **Quick release:** < 200ms = normal travel-to-point (preserve existing behavior)
- **Layout:** 4 wedges arranged radially: Info (functional) + 3 placeholders (A, B, C)
- **Selection:** Move mouse to desired wedge while holding, release to select
- **Dismiss:** Release outside any wedge = no action
- **Panel:** Semi-transparent overlay near point, stays open during travel
- **Panel dismiss:** Escape key or click outside panel
- **Inspection ring:** Distinct colored ring on inspected point
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add radial menu state and detail panel state variables</name>
  <files>main.py</files>
  <action>
    Add imports at top of main.py:
    ```python
    import math
    from audio import init_audio, update_audio, cleanup_audio, get_audio_params
    ```

    After the `auto_travel_feedback_duration` line (~line 149), add state variables:

    ```python
    # Radial menu state
    HOLD_THRESHOLD = 200  # ms before radial menu opens
    MENU_RADIUS = 50  # pixel radius of radial menu
    WEDGE_INNER = 15  # inner dead zone radius
    menu_state = "idle"  # idle | hold_pending | menu_open
    menu_hold_start = 0  # tick when mouse went down on a point
    menu_point_idx = None  # point index the menu is for
    menu_center = None  # (x, y) screen position of menu

    # Detail panel state
    inspected_point_idx = None  # point currently inspected (panel open)
    ```

    Design: The state machine is minimal — 3 states, transitions driven by mouse events and time.
  </action>
  <verify>
    <manual>Run main.py, confirm no errors from new variables.</manual>
  </verify>
  <done>
    - Radial menu and detail panel state variables added
    - get_audio_params imported from audio
  </done>
</task>

<task type="auto">
  <name>Task 2: Modify click handling for hold-to-open radial menu</name>
  <files>main.py</files>
  <action>
    Replace the existing MOUSEBUTTONDOWN/MOUSEBUTTONUP handling for viewport clicks to support the hold timer. The sidebar click handling stays unchanged.

    In the `MOUSEBUTTONDOWN` handler (currently lines 345-349), change to:

    ```python
    elif event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            mx, my = event.pos
            dragging = True
            drag_start = (mx, my)
            # Check if click is on a viewport point for potential radial menu
            if mx <= SCREEN_WIDTH - 300 and last_projected_points:
                best_dist_sq = float("inf")
                best_idx = None
                best_p2d = None
                for p2d, ang, dep, idx in last_projected_points:
                    dx, dy = mx - p2d[0], my - p2d[1]
                    d_sq = dx * dx + dy * dy
                    if d_sq < best_dist_sq:
                        best_dist_sq = d_sq
                        best_idx = idx
                        best_p2d = p2d
                if best_idx is not None and best_dist_sq < 400:
                    menu_state = "hold_pending"
                    menu_hold_start = pygame.time.get_ticks()
                    menu_point_idx = best_idx
                    menu_center = best_p2d.astype(int)
    ```

    In the `MOUSEBUTTONUP` handler (currently lines 350-388), modify the viewport click section:

    ```python
    elif event.type == pygame.MOUSEBUTTONUP:
        if event.button == 1:
            mx, my = event.pos
            if menu_state == "menu_open":
                # Check which wedge the mouse is in
                dx = mx - menu_center[0]
                dy = my - menu_center[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if WEDGE_INNER < dist < MENU_RADIUS:
                    angle = math.atan2(-dy, dx)  # negative dy for screen coords
                    wedge = int((angle + math.pi) / (math.pi / 2) + 2) % 4
                    if wedge == 0:  # Info wedge (right)
                        inspected_point_idx = menu_point_idx
                    # wedges 1,2,3 are placeholders — no action
                menu_state = "idle"
                menu_point_idx = None
                menu_center = None
            elif menu_state == "hold_pending":
                # Released before threshold — treat as normal click
                menu_state = "idle"
                if dragging and drag_start is not None:
                    drag_dist_sq = (mx - drag_start[0]) ** 2 + (my - drag_start[1]) ** 2
                    if drag_dist_sq < 100:
                        clicked_idx = None
                        if mx > SCREEN_WIDTH - 300:
                            item_idx = (my - list_start_y) // 40 + list_scroll
                            if 0 <= item_idx < len(filtered_indices):
                                clicked_idx = filtered_indices[item_idx]
                        elif last_projected_points:
                            best_dist_sq = float("inf")
                            best_idx = None
                            for p2d, ang, dep, idx in last_projected_points:
                                dx, dy = mx - p2d[0], my - p2d[1]
                                d_sq = dx * dx + dy * dy
                                if d_sq < best_dist_sq:
                                    best_dist_sq = d_sq
                                    best_idx = idx
                            if best_idx is not None and best_dist_sq < 400:
                                clicked_idx = best_idx
                        if clicked_idx is not None:
                            if traveling:
                                queued_target_idx = clicked_idx
                                queued_target = points[clicked_idx]
                            else:
                                travel_target_idx = clicked_idx
                                travel_target = points[clicked_idx]
                                traveling = True
                                travel_progress = 0.0
                                pop_animation_idx = None
                                pop_animation_start_time = None
                menu_point_idx = None
                menu_center = None
            else:
                # Normal release (no menu involved) — existing behavior
                if dragging and drag_start is not None:
                    drag_dist_sq = (mx - drag_start[0]) ** 2 + (my - drag_start[1]) ** 2
                    if drag_dist_sq < 100:
                        clicked_idx = None
                        if mx > SCREEN_WIDTH - 300:
                            item_idx = (my - list_start_y) // 40 + list_scroll
                            if 0 <= item_idx < len(filtered_indices):
                                clicked_idx = filtered_indices[item_idx]
                        elif last_projected_points:
                            best_dist_sq = float("inf")
                            best_idx = None
                            for p2d, ang, dep, idx in last_projected_points:
                                dx, dy = mx - p2d[0], my - p2d[1]
                                d_sq = dx * dx + dy * dy
                                if d_sq < best_dist_sq:
                                    best_dist_sq = d_sq
                                    best_idx = idx
                            if best_idx is not None and best_dist_sq < 400:
                                clicked_idx = best_idx
                        if clicked_idx is not None:
                            if traveling:
                                queued_target_idx = clicked_idx
                                queued_target = points[clicked_idx]
                            else:
                                travel_target_idx = clicked_idx
                                travel_target = points[clicked_idx]
                                traveling = True
                                travel_progress = 0.0
                                pop_animation_idx = None
                                pop_animation_start_time = None
            dragging = False
            drag_start = None
    ```

    Also add in the KEYDOWN handler (non-search branch), before the `if event.key == pygame.K_v:` line:
    ```python
    if event.key == pygame.K_ESCAPE:
        if inspected_point_idx is not None:
            inspected_point_idx = None
        elif menu_state != "idle":
            menu_state = "idle"
            menu_point_idx = None
            menu_center = None
    ```

    Between the event loop and the travel update section, add the hold timer check:
    ```python
    # Check hold threshold for radial menu
    if menu_state == "hold_pending":
        if pygame.time.get_ticks() - menu_hold_start >= HOLD_THRESHOLD:
            menu_state = "menu_open"
    ```

    Note: `math` is imported at the top level (Task 1) and used in both the wedge selection logic here and the radial menu rendering in Task 3. The wedge formula `int((angle + math.pi) / (math.pi / 2) + 2) % 4` maps: right→0 (Info), up→1, left→2, down→3 — matching the `wedge_angles` array in Task 3's rendering.
  </action>
  <verify>
    <manual>
      Run main.py:
      - Quick click on a viewport point → travel to it (existing behavior preserved)
      - Click-and-hold on a viewport point for >200ms → observe menu_state changes via debug print (add temporarily)
      - Sidebar list clicks still work normally
      - Escape key dismisses any open state
    </manual>
  </verify>
  <done>
    - Hold-to-open detection works with 200ms threshold
    - Quick clicks still trigger travel (existing behavior preserved)
    - Wedge selection detects which quadrant the mouse is in
    - Info wedge (right) sets inspected_point_idx
    - Escape dismisses panel or menu
  </done>
</task>

<task type="auto">
  <name>Task 3: Render radial menu overlay</name>
  <files>main.py</files>
  <action>
    Add radial menu rendering after the hover tooltip section (after line ~699) and before the divider line:

    ```python
    # Draw radial menu
    if menu_state == "menu_open" and menu_center is not None:
        mx_now, my_now = pygame.mouse.get_pos()
        dx_menu = mx_now - menu_center[0]
        dy_menu = my_now - menu_center[1]
        hover_dist = (dx_menu * dx_menu + dy_menu * dy_menu) ** 0.5
        hover_angle = math.atan2(-dy_menu, dx_menu)
        hover_wedge = int((hover_angle + math.pi) / (math.pi / 2) + 2) % 4 if WEDGE_INNER < hover_dist < MENU_RADIUS else -1

        menu_surf = pygame.Surface((MENU_RADIUS * 2 + 4, MENU_RADIUS * 2 + 4), pygame.SRCALPHA)
        mc = MENU_RADIUS + 2  # center of surface

        # Draw background circle
        pygame.draw.circle(menu_surf, (20, 20, 40, 180), (mc, mc), MENU_RADIUS)

        # Draw wedge labels
        wedge_labels = ["Info", "A", "B", "C"]
        wedge_colors = [(100, 200, 255), (100, 100, 120), (100, 100, 120), (100, 100, 120)]
        wedge_angles = [0, math.pi / 2, math.pi, 3 * math.pi / 2]  # right, down-ish, left, up-ish (screen coords inverted)
        for wi, (label, color, wa) in enumerate(zip(wedge_labels, wedge_colors, wedge_angles)):
            # Wedge center position
            wr = (WEDGE_INNER + MENU_RADIUS) / 2
            wx = mc + int(wr * math.cos(wa))
            wy = mc - int(wr * math.sin(wa))  # invert y for screen
            # Highlight hovered wedge
            if wi == hover_wedge:
                pygame.draw.circle(menu_surf, (*color, 60), (wx, wy), 18)
            lbl = font.render(label, True, color if wi == 0 else (80, 80, 100))
            menu_surf.blit(lbl, (wx - lbl.get_width() // 2, wy - lbl.get_height() // 2))

        # Inner dead zone circle
        pygame.draw.circle(menu_surf, (30, 30, 50, 200), (mc, mc), WEDGE_INNER)

        screen.blit(menu_surf, (menu_center[0] - mc, menu_center[1] - mc))
    ```

    The wedge angle mapping: wedge 0 (Info) at angle 0 (right), wedge 1 at π/2 (up on screen), wedge 2 at π (left), wedge 3 at 3π/2 (down on screen). The `+ 2` offset in the selection formula `int((angle + π) / (π/2) + 2) % 4` aligns right→0, up→1, left→2, down→3 to match this rendering order.
  </action>
  <verify>
    <manual>
      Run main.py, hold-click on a viewport point:
      - Radial menu appears centered on the point after 200ms
      - 4 labels visible: "Info" (blue-ish), "A", "B", "C" (grayed)
      - Moving mouse over a wedge highlights it
      - Releasing on Info wedge triggers inspection (Task 4 will render the panel)
      - Releasing outside any wedge dismisses the menu
    </manual>
  </verify>
  <done>
    - Radial menu renders as semi-transparent overlay
    - Info wedge highlighted in distinct color, placeholders grayed
    - Hover highlight shows which wedge will be selected
    - Inner dead zone prevents accidental selection
  </done>
</task>

<task type="auto">
  <name>Task 4: Render detail panel and inspection ring</name>
  <files>main.py</files>
  <action>
    Add detail panel rendering after the radial menu section, before the divider line. Also add the inspection ring in the point rendering loop.

    **Inspection ring** — in the point rendering loop (after `pygame.draw.circle(screen, color, p2d.astype(int), radius)`, around line 512), add:

    ```python
    # Inspection ring on currently inspected point
    if idx == inspected_point_idx:
        ring_radius = radius + 10
        ring_surf = pygame.Surface((ring_radius * 2 + 4, ring_radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (255, 200, 50, 160), (ring_radius + 2, ring_radius + 2), ring_radius, 2)
        screen.blit(ring_surf, (int(p2d[0]) - ring_radius - 2, int(p2d[1]) - ring_radius - 2))
    ```

    **Detail panel** — add after the radial menu render block:

    ```python
    # Draw detail panel for inspected point
    if inspected_point_idx is not None:
        # Find screen position of inspected point
        panel_anchor = None
        for p2d, angular_dist, depth, idx in last_projected_points:
            if idx == inspected_point_idx:
                panel_anchor = p2d.astype(int)
                panel_dist = angular_dist
                break

        if panel_anchor is not None:
            name = get_name(inspected_point_idx)
            coords = points[inspected_point_idx]
            audio_info = get_audio_params(int(_name_keys[inspected_point_idx]))

            lines = [
                name,
                f"Dist: {format_dist(panel_dist)}",
                f"4D: ({coords[0]:+.3f}, {coords[1]:+.3f}, {coords[2]:+.3f}, {coords[3]:+.3f})",
                f"Audio: {audio_info['summary']}",
                f"Root: {audio_info['root_hz']} Hz | Tempo: {audio_info['tempo']}",
            ]

            # Measure panel size
            line_height = 16
            padding = 8
            max_w = max(font.size(line)[0] for line in lines)
            panel_w = max_w + padding * 2
            panel_h = len(lines) * line_height + padding * 2

            # Position: offset right and above the anchor point
            px = panel_anchor[0] + 20
            py = panel_anchor[1] - panel_h - 10
            # Keep on screen
            if px + panel_w > SCREEN_WIDTH - 300:
                px = panel_anchor[0] - panel_w - 20
            if py < 0:
                py = panel_anchor[1] + 20

            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            pygame.draw.rect(panel_surf, (20, 20, 40, 200), (0, 0, panel_w, panel_h), border_radius=4)
            pygame.draw.rect(panel_surf, (255, 200, 50, 120), (0, 0, panel_w, panel_h), 1, border_radius=4)

            for li, line in enumerate(lines):
                color = (255, 200, 50) if li == 0 else TEXT_COLOR
                lbl = font.render(line, True, color)
                panel_surf.blit(lbl, (padding, padding + li * line_height))

            screen.blit(panel_surf, (px, py))
        else:
            # Inspected point not visible — keep panel state but skip render
            pass
    ```

    **Dismiss on outside click** — In the existing `MOUSEBUTTONDOWN` handler, at the very start of the `if event.button == 1:` block (before the drag/menu logic), add:

    ```python
    # Dismiss detail panel on click outside it
    if inspected_point_idx is not None and menu_state == "idle":
        # Simple dismiss: any new click clears the panel
        # (unless it leads to a new inspection via radial menu)
        inspected_point_idx = None
    ```

    This ensures clicking anywhere (including starting a new hold) dismisses the current panel. If the user hold-clicks another point, the panel gets replaced by the new inspection.
  </action>
  <verify>
    <manual>
      Run main.py:
      1. Hold-click a viewport point → radial menu appears
      2. Release on "Info" → detail panel appears near the point
      3. Panel shows: name, distance, 4D coords (signed floats), audio summary, root Hz + tempo
      4. Gold/yellow ring visible around the inspected point
      5. Travel away → panel stays open, ring follows point position
      6. Press Escape → panel dismissed
      7. Click anywhere → panel dismissed
      8. Hold-click another point and select Info → previous panel replaced
    </manual>
  </verify>
  <done>
    - Detail panel renders near inspected point with all required data
    - Audio summary shows human-readable "Timbre in scale" format
    - Inspection ring distinguishes inspected point from travel target markers
    - Panel non-blocking: stays during travel, updates position each frame
    - Dismissible via Escape or any click
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify end-to-end:

1. **Quick click preserved:** Quick click on viewport point → travel starts immediately (no 200ms delay felt)
2. **Hold triggers menu:** Hold ~200ms → radial menu appears centered on point
3. **Info selection works:** Release on Info wedge → panel appears with correct data
4. **Panel content correct:** Name matches sidebar, distance matches list, 4D coords are unit-length, audio summary is human-readable
5. **Inspection ring visible:** Gold ring distinguishes inspected point from hover/travel markers
6. **Panel persists during travel:** Start travel while panel is open → panel stays, updates position
7. **Dismiss works:** Escape and click-outside both close the panel
8. **Placeholders inactive:** Releasing on A/B/C wedges does nothing
9. **Sidebar unaffected:** List clicks still trigger travel, no hold delay on sidebar
10. **Drag rotation unaffected:** Dragging in viewport still rotates camera when not on a point
</verification>

<success_criteria>
- User can click-hold any visible point to open a radial menu with Info + 3 placeholder options
- Selecting Info opens a floating detail panel showing: name, angular distance, 4D coordinates, audio timbre/scale summary
- Inspected point has a distinct colored ring
- Panel is non-blocking and dismissible via Escape or clicking
- Existing click-to-travel behavior preserved for quick clicks
</success_criteria>

<output>
After completion, create `.planning/phases/03-information-context/02-SUMMARY.md`
</output>
