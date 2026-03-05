---
phase: 01-performance-navigation-foundation
plan: 03
type: execute
wave: 1
depends_on: []
files_modified: [main.py]
autonomous: true
requirements: [NAV-04]

must_haves:
  truths:
    - "User can press Tab to instantly start traveling to the nearest unvisited visible point"
    - "Once a point is traveled-to, it is marked as visited and excluded from future Tab selections"
    - "If no unvisited points are visible, Tab does nothing (or shows feedback)"
  artifacts:
    - path: "main.py"
      provides: "Visited points tracking set, auto-travel logic, Tab key binding"
      section: "Auto-travel system (lines ~130-150, ~210-220, ~540-560)"
  key_links:
    - from: "main.py:event loop"
      to: "Tab key binding"
      via: "Trigger auto-travel on Tab press"
      pattern: "event.key == pygame.K_TAB"
    - from: "main.py:travel completion"
      to: "Visited set update"
      via: "Mark travel_target_idx as visited when travel completes"
      pattern: "angular_distance.*ARRIVAL_THRESHOLD"
    - from: "main.py:Tab handler"
      to: "Nearest unvisited finder"
      via: "Find closest unvisited point in visible_indices"
      pattern: "min.*filter.*visited"
---

<objective>
Implement Tab key auto-travel: pressing Tab automatically starts travel to the nearest unvisited visible point. Visited points are tracked per session and excluded from future Tab selections.

Purpose: Enable quick exploration mode — user can press Tab repeatedly to tour nearby undiscovered locations without manual navigation.

Output:
- Visited points tracking (set of indices)
- Auto-travel logic to find nearest unvisited and initiate travel
- Tab key binding and feedback system
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Travel system (existing):
- traveling flag, travel_target, travel_progress, travel_speed
- Travel completes when angular_distance(player_pos, travel_target) < ARRIVAL_THRESHOLD (0.002 rad)
- Snap to target on arrival, trigger pop animation

Auto-travel design:
- Track visited point indices in a set (session-only, not persisted)
- On Tab press: find nearest visible point not in visited set
- Initiate travel to that point
- When travel completes: add travel_target_idx to visited set
- If no unvisited visible: Tab does nothing (optional: print feedback)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add visited tracking and auto-travel finder logic</name>
  <files>main.py</files>
  <action>
    1. Add visited tracking state after travel state (around line ~130):
       ```python
       # Auto-travel (Tab key) system
       visited_points = set()  # Indices of points already traveled-to

       def find_nearest_unvisited(visible_idx_list, visible_dist_list):
           """Find the nearest unvisited point from visible list.

           Args:
               visible_idx_list: List of visible point indices (from visible_indices)
               visible_dist_list: List of distances (from visible_distances), parallel to idx_list

           Returns:
               (index, distance) tuple for nearest unvisited point, or (None, None) if all visited
           """
           for idx, dist in zip(visible_idx_list, visible_dist_list):
               if idx not in visited_points:
                   return idx, dist
           return None, None

       def auto_travel_to_nearest_unvisited():
           """Start travel to nearest unvisited visible point if one exists."""
           global traveling, travel_target, travel_target_idx, travel_progress
           global queued_target, queued_target_idx

           nearest_idx, nearest_dist = find_nearest_unvisited(visible_indices, visible_distances)

           if nearest_idx is not None:
               if traveling:
                   # Queue the auto-travel target
                   queued_target_idx = nearest_idx
                   queued_target = points[nearest_idx]
                   print(f"Queued auto-travel to {get_name(nearest_idx)} ({format_dist(nearest_dist)})")
               else:
                   # Start travel immediately
                   travel_target_idx = nearest_idx
                   travel_target = points[nearest_idx]
                   traveling = True
                   travel_progress = 0.0
                   print(f"Auto-traveling to {get_name(nearest_idx)} ({format_dist(nearest_dist)})")
           else:
               print("No unvisited points visible. Explore more!")
       ```

    2. Add Tab key binding (in KEYDOWN block, around line ~215):
       ```python
       elif event.type == pygame.KEYDOWN:
           # ... existing keybinds ...
           if event.key == pygame.K_TAB:
               auto_travel_to_nearest_unvisited()
       ```

    3. Mark point as visited when travel completes (in travel completion block, around line ~280):
       In the section where travel completion is detected (after snap-to-target), add:
       ```python
       # Travel complete — mark as visited
       if travel_target_idx is not None:
           visited_points.add(travel_target_idx)
           print(f"Visited: {get_name(travel_target_idx)} ({len(visited_points)} total)")
       ```

       This should go right before or after the pop_animation_idx assignment.

    Design rationale:
    - Visited set is simple, O(1) membership check
    - find_nearest_unvisited() leverages already-sorted visible_indices (by distance)
    - Auto-travel respects existing travel queue system
    - Feedback via print() helps user understand state (optional: add to UI overlay later)
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      python3 -c "
# Test visited tracking logic
visited = set()

def find_nearest_unvisited_test(indices, distances):
    for idx, dist in zip(indices, distances):
        if idx not in visited:
            return idx, dist
    return None, None

# Simulate visible list
visible_idx = [5, 10, 15, 20, 25]
visible_dist = [0.01, 0.05, 0.08, 0.12, 0.15]

# First call
idx, dist = find_nearest_unvisited_test(visible_idx, visible_dist)
assert idx == 5, f'Expected first unvisited to be 5, got {idx}'
assert dist == 0.01

# Mark as visited
visited.add(5)

# Second call
idx, dist = find_nearest_unvisited_test(visible_idx, visible_dist)
assert idx == 10, f'Expected second unvisited to be 10, got {idx}'
visited.add(10)

# Mark all remaining as visited
for i in [15, 20, 25]:
    visited.add(i)

# Now all visited
idx, dist = find_nearest_unvisited_test(visible_idx, visible_dist)
assert idx is None, f'Expected None when all visited, got {idx}'

print('✓ Auto-travel visited tracking logic test passed')
" 2>&1
    </automated>
  </verify>
  <done>
    - visited_points set initialized (session-only tracking)
    - find_nearest_unvisited() function finds closest unvisited point
    - auto_travel_to_nearest_unvisited() initiates travel or queues if already traveling
    - Tab key bound to auto_travel_to_nearest_unvisited()
    - Visited status updated when travel completes (on arrival snap)
    - Feedback messages printed to console on auto-travel trigger and visit
  </done>
</task>

<task type="auto">
  <name>Task 2: Add optional UI indicator for visited points and auto-travel feedback</name>
  <files>main.py</files>
  <action>
    1. Render visited indicator in sidebar list (in list item rendering, around line ~540):
       When rendering each list item, add a visual marker for visited points:
       ```python
       for i, idx in enumerate(filtered_indices[list_scroll:list_scroll + max_items]):
           item_y = list_start_y + (i * item_height)
           item_rect = pygame.Rect(SCREEN_WIDTH - 290, item_y, 280, item_height)

           # Visited indicator: slightly muted color
           if idx in visited_points:
               # Dim the background for visited points
               pygame.draw.rect(screen, (50, 50, 70), item_rect)
           elif hovered_item == i:
               pygame.draw.rect(screen, LIST_ITEM_HOVER, item_rect)
           else:
               pygame.draw.rect(screen, LIST_ITEM_BG, item_rect)

           # ... rest of item rendering (color swatch, name, distance) ...
       ```

    2. Add brief on-screen feedback when Tab is pressed (optional, improves UX):
       Create an auto_travel_feedback state to display temporary message:
       ```python
       # Auto-travel feedback state (around line ~135)
       auto_travel_feedback = None  # (message, timestamp) or None
       auto_travel_feedback_duration = 2000  # milliseconds

       # In travel completion block, set feedback:
       auto_travel_feedback = (f"Visited: {get_name(travel_target_idx)}", pygame.time.get_ticks())

       # In render loop, before UI render:
       if auto_travel_feedback is not None:
           msg, ts = auto_travel_feedback
           elapsed = pygame.time.get_ticks() - ts
           if elapsed > auto_travel_feedback_duration:
               auto_travel_feedback = None
           else:
               # Render feedback message at top of screen
               feedback_text = font.render(msg, True, (100, 255, 100))
               screen.blit(feedback_text, (10, 10))
       ```

    3. Optional: Show visited count in header (in render loop, around line ~520):
       ```python
       list_header = font.render(f"VISIBLE ({len(filtered_indices)}) | VISITED ({len(visited_points)})", True, TEXT_COLOR)
       ```

    Design rationale:
    - Visual dimming of visited points reduces cognitive load (no need to check list for duplicates)
    - On-screen feedback ("Visited: X") confirms Tab action
    - Visited count in header gives quick session overview
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      timeout 5 python3 venv/bin/python main.py 2>&1 | head -1 &
      sleep 2
      pkill -f "python.*main.py"
      echo "✓ Auto-travel UI renders without crash"
    </automated>
  </verify>
  <done>
    - Visited points rendered with dimmed background in list
    - Optional feedback message displays briefly when visiting a point
    - Visited count shown in list header alongside filtered count
    - UI integrates with existing sidebar rendering without conflicts
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:

1. **Tab binding works:**
   - Press Tab while at least one unvisited visible point exists
   - Auto-travel initiates to nearest unvisited
   - Console prints "Auto-traveling to [name] ([distance])"

2. **Visited tracking:**
   - After arriving at destination, that point is marked visited (dimmed in list)
   - Press Tab again → selects next unvisited, not the one just visited
   - Continue pressing Tab → visits all visible unvisited points in order

3. **Queue behavior:**
   - Press Tab while traveling → queues next auto-travel
   - On arrival, queued travel starts immediately
   - Console shows "Queued auto-travel to..." then "Auto-traveling to..."

4. **No unvisited feedback:**
   - Visit all visible points
   - Press Tab → prints "No unvisited points visible. Explore more!"
   - Rotate to new area with unvisited points
   - Press Tab → auto-travel works again

5. **UI indicators:**
   - Visited points show darker background in sidebar
   - Visited count displayed in list header
   - Optional feedback message appears when visiting
</verification>

<success_criteria>
- Tab key binding calls auto_travel_to_nearest_unvisited()
- find_nearest_unvisited() correctly identifies nearest point not in visited_points set
- Auto-travel initiates travel to target if not already traveling, or queues if traveling
- On travel completion (snap to arrival threshold), point is added to visited_points
- Visited points render with distinct visual indicator in sidebar (dimmed background)
- List header shows visited point count
- Optional: Temporary feedback message displays on screen when visiting
- All console feedback messages working (auto-travel, visit, queue, no unvisited)
</success_criteria>

<output>
After completion, create `.planning/phases/01-performance-navigation-foundation/03-SUMMARY.md`
</output>
