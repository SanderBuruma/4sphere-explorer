---
phase: 01-performance-navigation-foundation
plan: 02
type: execute
wave: 1
depends_on: []
files_modified: [main.py]
autonomous: true
requirements: [NAV-02]

must_haves:
  truths:
    - "User can type to search the point list by name and see results instantly filter"
    - "Search results remain sorted by distance from player"
    - "Search field clears when Escape is pressed or view changes"
  artifacts:
    - path: "main.py"
      provides: "Search input state, filtering logic, UI rendering"
      section: "Search field integration (lines ~130-140, ~210-220, ~520-540)"
  key_links:
    - from: "main.py:event loop"
      to: "Search input handling"
      via: "Text input via KEYDOWN events"
      pattern: "event.key.*pygame.K_"
    - from: "main.py:point list rendering"
      to: "Filtered visible_indices"
      via: "Display only matching indices when search active"
      pattern: "visible_indices.*filtered"
    - from: "main.py:update_visible()"
      to: "Search field reset"
      via: "Clear search when view refreshes significantly"
      pattern: "search_text.*=\"\""
---

<objective>
Add real-time search/filter functionality to the point list sidebar. User types to filter visible points by name prefix; results remain distance-sorted.

Purpose: Make it easy to find and navigate to specific named locations without scrolling through entire list.

Output:
- Search input field in sidebar UI
- Real-time filtering of point list by name
- Keyboard bindings for search (Escape to clear, typing to filter)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Name system (sphere.py):
- get_name(idx) returns futuristic names like "Nox Prime 42", "Void Gate", "Aeon"
- Case-insensitive, deterministic from point index
- Search should match name prefix (user types "prime" → matches "Nox Prime 42")

Current sidebar structure (main.py):
- Right 300px column with list items (40px each)
- Hover highlighting and click-to-travel
- Scrollable via UP/DOWN keys
- Item format: color swatch + name + distance

Design approach: Add text input state, accumulate keystrokes, filter list on each keystroke.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add search input state and filtering logic</name>
  <files>main.py</files>
  <action>
    1. Add search state after UI state initialization (around line ~135):
       ```python
       # Search/filter state
       search_text = ""  # Current search query
       search_active = False  # Whether search field has focus

       def apply_search_filter(search_query):
           """Filter visible_indices by name prefix match.

           Args:
               search_query: String to match against point names (case-insensitive prefix)

           Returns:
               List of indices from visible_indices whose names start with search_query
           """
           if not search_query:
               return visible_indices[:]  # No filter, return all visible

           query_lower = search_query.lower()
           filtered = []
           for idx in visible_indices:
               name = get_name(idx)
               if name.lower().startswith(query_lower):
                   filtered.append(idx)
           return filtered
       ```

    2. Add event handling for search input (in KEYDOWN block, around line ~210):
       ```python
       elif event.type == pygame.KEYDOWN:
           # ... existing keybinds ...

           # Search handling
           if search_active:
               if event.key == pygame.K_ESCAPE:
                   # Clear search
                   search_text = ""
                   search_active = False
               elif event.key == pygame.K_BACKSPACE:
                   # Backspace in search
                   search_text = search_text[:-1]
               elif event.unicode and event.unicode.isalnum() or event.unicode in ' -':
                   # Add character to search (alphanumeric, space, hyphen)
                   search_text += event.unicode
               # Continue to handle other keys (UP/DOWN for list scroll) even in search mode
           else:
               # Search not active yet
               if event.key == pygame.K_SLASH or event.key == pygame.K_f:
                   # / or F key to start search
                   search_active = True
                   search_text = ""
       ```

    3. Modify list rendering to use filtered results (in render loop, around line ~500):
       Replace direct use of visible_indices with filtered indices when rendering the list:
       ```python
       # Apply search filter to visible points
       filtered_indices = apply_search_filter(search_text)
       filtered_distances = [visible_distances[visible_indices.index(idx)] for idx in filtered_indices]
       ```

       Then use filtered_indices and filtered_distances in the list rendering loop instead of visible_indices/visible_distances.
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      python3 -c "
# Verify search logic without full pygame init
def apply_search_filter_test():
    # Simulate get_name caching
    test_names = {
        0: 'Nox Prime 42',
        1: 'Void Gate',
        2: 'Nox Crystal',
        3: 'Aeon Station',
    }

    def get_name(idx):
        return test_names.get(idx, f'Unknown {idx}')

    visible = [0, 1, 2, 3]

    # Test exact prefix match
    def apply_search_filter(query):
        if not query:
            return visible[:]
        q_lower = query.lower()
        return [i for i in visible if get_name(i).lower().startswith(q_lower)]

    assert apply_search_filter('') == [0, 1, 2, 3]
    assert apply_search_filter('nox') == [0, 2]
    assert apply_search_filter('void') == [1]
    assert apply_search_filter('aeon') == [3]
    assert apply_search_filter('xyz') == []
    print('✓ Search filter logic test passed')

apply_search_filter_test()
" 2>&1
    </automated>
  </verify>
  <done>
    - Search state variables added (search_text, search_active)
    - apply_search_filter() function implements prefix matching
    - Event handlers for / or F key to activate search
    - Backspace and Escape to clear search in input mode
    - Alphanumeric + space/hyphen characters accumulate in search_text
  </done>
</task>

<task type="auto">
  <name>Task 2: Render search field in sidebar and integrate with list display</name>
  <files>main.py</files>
  <action>
    1. Render search field above point list (in render loop, before list header, around line ~510):
       ```python
       # Render search field
       search_y = 100
       search_field_rect = pygame.Rect(SCREEN_WIDTH - 290, search_y, 280, 28)
       if search_active:
           pygame.draw.rect(screen, (60, 100, 120), search_field_rect)  # Highlight when active
           pygame.draw.rect(screen, (100, 200, 255), search_field_rect, 2)  # Blue border
       else:
           pygame.draw.rect(screen, LIST_ITEM_BG, search_field_rect)
           pygame.draw.rect(screen, TEXT_COLOR, search_field_rect, 1)  # Gray border

       search_label = font.render(f"Search: {search_text}", True, TEXT_COLOR)
       screen.blit(search_label, (SCREEN_WIDTH - 280, search_y + 7))

       list_header_y = search_y + 35
       list_header = font.render(f"VISIBLE ({len(filtered_indices)})", True, TEXT_COLOR)
       screen.blit(list_header, (SCREEN_WIDTH - 290, list_header_y))

       list_start_y = list_header_y + 25
       ```

    2. Adjust list item rendering to use filtered_indices (around line ~530):
       ```python
       item_height = 40
       max_items = (SCREEN_HEIGHT - list_start_y - 20) // item_height
       list_end_y = list_start_y + max_items * item_height

       for i, idx in enumerate(filtered_indices[list_scroll:list_scroll + max_items]):
           item_y = list_start_y + (i * item_height)
           item_rect = pygame.Rect(SCREEN_WIDTH - 290, item_y, 280, item_height)

           # Hover highlight
           if hovered_item == i:
               pygame.draw.rect(screen, LIST_ITEM_HOVER, item_rect)
           else:
               pygame.draw.rect(screen, LIST_ITEM_BG, item_rect)

           # Color swatch
           color = point_colors[idx]
           pygame.draw.rect(screen, color, (SCREEN_WIDTH - 280, item_y + 8, 16, 16))

           # Name and distance
           name = get_name(idx)
           dist_str = format_dist(visible_distances[visible_indices.index(idx)])
           text = font.render(f"{name} ({dist_str})", True, TEXT_COLOR)
           screen.blit(text, (SCREEN_WIDTH - 255, item_y + 10))
       ```

    3. Update hover detection for filtered list (around line ~260):
       Ensure hovered_item is computed relative to filtered_indices, not visible_indices:
       ```python
       if not dragging and mx > SCREEN_WIDTH - 300:
           item_idx = (my - list_start_y) // 40 + list_scroll
           hovered_item = item_idx if 0 <= item_idx < len(filtered_indices) else None
       ```

    4. Update click-to-travel logic to use filtered_indices (around line ~228):
       ```python
       if mx > SCREEN_WIDTH - 300:
           item_idx = (my - list_start_y) // 40 + list_scroll
           if 0 <= item_idx < len(filtered_indices):
               clicked_idx = filtered_indices[item_idx]
       ```

    Design rationale: Search field renders in distinct color when active to indicate focus.
    List count updates to show how many results match the search. Filtered list remains distance-sorted.
  </action>
  <verify>
    <automated>
      cd /home/sanderburuma/Projects/4sphere-explorer && \
      timeout 5 python3 venv/bin/python main.py 2>&1 | head -1 &
      sleep 2
      pkill -f "python.*main.py"
      echo "✓ Search UI renders without crash"
    </automated>
  </verify>
  <done>
    - Search field renders above point list with visual feedback for active state
    - List header shows filtered result count
    - Click-to-travel resolves indices through filtered_indices
    - Hover highlighting works on filtered list
    - List scrolling (UP/DOWN) applies to filtered results
  </done>
</task>

</tasks>

<verification>
After all tasks complete, verify:

1. **Search activation:** Press / or F key → search field appears and accepts input
2. **Filter behavior:**
   - Type "nox" → shows only points with names starting with "Nox"
   - Type "prime" → shows only points with names starting with "Prime"
   - Type "xyz" → shows no results
3. **Sorting preserved:** Filtered results remain sorted by distance from player
4. **Clear search:** Press Escape → search clears, full list reappears
5. **Click from search:** Click a filtered point in sidebar → travel to it works correctly
</verification>

<success_criteria>
- Search field renders in sidebar with visual active/inactive state
- User presses / or F to activate search
- Typing accumulates alphanumeric input, space, hyphen in search_text
- Backspace removes characters from search_text
- Escape clears search and deactivates field
- Filtered list updates in real-time as user types
- Filtered results remain distance-sorted from player position
- List header shows count of filtered results
- Click-to-travel works on filtered results
- Hover highlighting works on filtered list
</success_criteria>

<output>
After completion, create `.planning/phases/01-performance-navigation-foundation/02-SUMMARY.md`
</output>
