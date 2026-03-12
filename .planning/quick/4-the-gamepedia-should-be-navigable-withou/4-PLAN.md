---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py
  - tests/test_gamepedia.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "User can open Gamepedia with F1 and close with F1 or ESC (unchanged)"
    - "User can navigate group headers and topics using UP/DOWN arrows"
    - "User can expand/collapse a group header using Enter or Space"
    - "User can select a topic using Enter"
    - "User can scroll right-panel content using PageUp/PageDown"
    - "Hint bar reflects the new keyboard controls"
  artifacts:
    - path: "main.py"
      provides: "gamepedia_cursor state, unified nav order builder, Enter/Space/PgUp/PgDn handlers"
    - path: "tests/test_gamepedia.py"
      provides: "Tests for nav order building and cursor navigation logic"
  key_links:
    - from: "UP/DOWN handler"
      to: "gamepedia_cursor"
      via: "unified nav list built from GAMEPEDIA_CONTENT respecting collapsed_groups"
    - from: "Enter/Space handler"
      to: "gamepedia_collapsed_groups / gamepedia_selected_topic"
      via: "cursor type dispatch: group -> toggle collapse, topic -> set selected"
---

<objective>
Add keyboard-only navigation to the Gamepedia overlay so the mouse is never required.

Purpose: Navigating the encyclopedia while flying with keyboard controls is friction-free — no hand-off to mouse needed.
Output: UP/DOWN moves through group headers and topics; Enter/Space toggles groups or selects topics; PageUp/PageDown scrolls the content panel; hint bar updated.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@lib/gamepedia.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add keyboard cursor navigation to Gamepedia (main.py)</name>
  <files>main.py</files>
  <action>
Add a `gamepedia_cursor` variable alongside existing gamepedia state (near line 196):

```python
gamepedia_cursor = None  # None | ("group", gname) | ("topic", abs_idx)
```

Reset it to `None` when Gamepedia opens (F1 handler, same block as `gamepedia_selected_topic = -1`).

**Build a unified nav order helper (inline, not a module-level function):**

When UP/DOWN/Enter/Space is pressed while `gamepedia_open`, build `_nav_order` — a flat list of all rows in display order, each item is either `("group", gname)` or `("topic", abs_idx)`. Groups always included; topics only if their group is NOT in `gamepedia_collapsed_groups`. Example for current content with all expanded: `[("group","Controls"), ("topic",0), ("topic",1), ("topic",2), ("group","Navigation"), ("topic",3), ...]`. Build this inline where needed (same pattern as existing `_vis` build at UP/DOWN handler).

**Replace the existing UP/DOWN handler inside `if gamepedia_open: ... elif event.key in (pygame.K_UP, pygame.K_DOWN):`**

Old logic navigated `_vis` (visible topic indices only). New logic:
- Build `_nav_order`
- If `gamepedia_cursor is None`: UP selects last item, DOWN selects first item
- Otherwise find current cursor in `_nav_order` and move +1 (DOWN) or -1 (UP), clamped to bounds
- Set `gamepedia_cursor` to the new item
- If the new cursor is `("topic", abs_idx)`: also set `gamepedia_selected_topic = abs_idx` and `gamepedia_scroll = 0`
- If the new cursor is `("group", gname)`: do NOT change `gamepedia_selected_topic` (right panel keeps its current content)

**Add Enter/Space handler inside `if gamepedia_open:` block (after UP/DOWN handler):**

```python
elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
    if gamepedia_cursor is not None:
        kind, key = gamepedia_cursor
        if kind == "group":
            if key in gamepedia_collapsed_groups:
                gamepedia_collapsed_groups.discard(key)
            else:
                gamepedia_collapsed_groups.add(key)
        elif kind == "topic":
            gamepedia_selected_topic = key
            gamepedia_scroll = 0
```

**Add PageUp/PageDown handler inside `if gamepedia_open:` block:**

```python
elif event.key == pygame.K_PAGEDOWN:
    gamepedia_scroll += 10
elif event.key == pygame.K_PAGEUP:
    gamepedia_scroll = max(0, gamepedia_scroll - 10)
```

(The existing render code already clamps `gamepedia_scroll` to `max_scroll`, so no additional clamping needed here.)

**Update the cursor highlight in rendering:**

In the left-panel render loop (around line 1322), after the existing selected-topic highlight, add a cursor outline to make the focused row visually distinct from the selected topic. For group headers: if `gamepedia_cursor == ("group", gname)`, draw a 1px white rect outline around the header rect (use `pygame.draw.rect(screen, (220,220,255), header_rect, 1)`). For topic rows: if `gamepedia_cursor == ("topic", abs_flat_idx)`, draw a 1px white rect outline around the topic row rect (distinct from the filled selection highlight). The cursor outline must be drawn AFTER the fill, so it appears on top.

**Update the hint bar text** (search for the existing hint string and replace it):

Old: `"F1/ESC: Close | Click header: Expand/Collapse | UP/DOWN: Topics | Scroll: Content"`
New: `"F1/ESC: Close  UP/DOWN: Navigate  Enter/Space: Select/Toggle  PgUp/Dn: Scroll"`

Do NOT alter the hint bar's position, font, or color — only the text content.
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -c "import main" 2>&amp;1 | head -5; echo "import OK if no output above"</automated>
  </verify>
  <done>
    - `gamepedia_cursor` variable initialised at startup and reset on F1 open
    - UP/DOWN navigates group headers and topics in display order (groups always reachable, topics only when group expanded)
    - Enter/Space toggles collapse on a group row; selects topic on a topic row; sets selected_topic + clears scroll
    - PageUp/PageDown adjusts gamepedia_scroll (clamped by existing render code)
    - Cursor row has a white outline in the left panel (distinct from selection fill)
    - Hint bar text updated
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Tests for keyboard nav logic (tests/test_gamepedia.py)</name>
  <files>tests/test_gamepedia.py</files>
  <behavior>
    - `build_nav_order(content, collapsed_groups)` returns all group rows and visible topic rows in render order
    - With all groups collapsed, nav order contains only group rows (one per group, no topics)
    - With all groups expanded, first item is `("group", "Controls")`, second is `("topic", 0)`, etc.
    - Collapsing one group removes its topics but keeps the group row itself
    - Total nav order length equals (num_groups + num_visible_topics)
  </behavior>
  <action>
Add a `build_nav_order` pure helper to `tests/test_gamepedia.py` (mirrors the inline logic in main.py — pure, testable):

```python
def build_nav_order(content, collapsed_groups=None):
    """Build unified nav order list: [("group", gname) | ("topic", abs_idx), ...]"""
    if collapsed_groups is None:
        collapsed_groups = set()
    nav = []
    abs_idx = 0
    for gname, topics in content:
        nav.append(("group", gname))
        if gname not in collapsed_groups:
            for _title, _text in topics:
                nav.append(("topic", abs_idx))
                abs_idx += 1
        else:
            abs_idx += len(topics)
    return nav
```

Add `TestGamepediaKeyboardNav` class with these tests:
- `test_all_expanded_starts_with_group`: first item is `("group", "Controls")`
- `test_all_expanded_second_item_is_first_topic`: second item is `("topic", 0)`
- `test_all_collapsed_only_groups`: all groups collapsed → nav contains only `("group", ...)` items, count equals len(GAMEPEDIA_CONTENT)
- `test_collapsing_one_group_removes_its_topics`: collapse Controls (3 topics) → total length is (all groups) + (total topics - 3 Controls topics); Controls group row still present
- `test_nav_order_full_length_all_expanded`: len(nav) == len(GAMEPEDIA_CONTENT) + len(_gamepedia_flat) when all expanded
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -m pytest tests/test_gamepedia.py -v 2>&amp;1 | tail -20</automated>
  </verify>
  <done>
    - All existing gamepedia tests still pass (17 original)
    - 5 new `TestGamepediaKeyboardNav` tests pass
    - Total gamepedia test count: 22
  </done>
</task>

</tasks>

<verification>
Run all tests to confirm no regressions:

```bash
cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -m pytest tests/ -q 2>&1 | tail -5
```

All tests pass (should be ~237 total after adding 5 new).
</verification>

<success_criteria>
- All tests pass with no regressions
- Gamepedia can be fully operated without touching the mouse:
  - F1 to open
  - UP/DOWN to move cursor through group headers and topics
  - Enter/Space to toggle a group or select a topic
  - PageUp/PageDown to scroll the right-panel content
  - F1 or ESC to close
- Cursor position has a visible outline in the left panel
- Hint bar reflects the new key bindings
</success_criteria>

<output>
After completion, create `.planning/quick/4-the-gamepedia-should-be-navigable-withou/4-SUMMARY.md`
</output>
