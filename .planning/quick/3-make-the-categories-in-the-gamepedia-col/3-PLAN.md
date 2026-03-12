---
phase: quick-3
plan: 3
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py
  - tests/test_gamepedia.py
autonomous: true
requirements: [QUICK-3]

must_haves:
  truths:
    - "Gamepedia opens to an intro page, not the first topic"
    - "All category groups are collapsed by default on open"
    - "Clicking a group header expands or collapses it"
    - "Topics in a collapsed group are invisible and unclickable"
    - "Selecting a topic still shows its content in the right panel"
    - "UP/DOWN keyboard navigation skips hidden (collapsed) topics"
  artifacts:
    - path: "main.py"
      provides: "collapsible groups state + intro page logic + updated click/keyboard handling"
    - path: "tests/test_gamepedia.py"
      provides: "updated click-select tests accounting for collapsed state"
  key_links:
    - from: "gamepedia_open state"
      to: "gamepedia_selected_topic = -1 on open"
      via: "reset on F1 keydown"
    - from: "group header click"
      to: "gamepedia_collapsed_groups toggle"
      via: "MOUSEBUTTONDOWN hit-test against header rows"
    - from: "UP/DOWN key handling"
      to: "visible_flat_indices list"
      via: "filter _gamepedia_flat by expanded groups"
---

<objective>
Add collapsible category groups and an intro page to the Gamepedia overlay.

Purpose: The Gamepedia currently dumps all 24 topics in a long always-expanded list. Collapsing categories reduces visual noise and an intro page gives new users a navigation hint before they start reading.
Output: Updated main.py with new state variables and rendering/input changes. Updated tests.
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
  <name>Task 1: Add collapse state, intro page, and update rendering</name>
  <files>main.py</files>
  <action>
Make these changes to main.py:

**State variables (near gamepedia_open/gamepedia_selected_topic block, ~line 197):**
Add:
```python
gamepedia_collapsed_groups = set(g for g, _ in GAMEPEDIA_CONTENT)  # all collapsed by default
```
Change initial value of `gamepedia_selected_topic` to `-1` (intro page shown until user picks a topic). Keep the reset-to-`-1` (not 0) whenever gamepedia is re-opened (F1 keydown that sets gamepedia_open = True).

**Left-panel rendering (~line 1287):**

When iterating groups, check if the group is collapsed:
```python
collapsed = gname in gamepedia_collapsed_groups
```

On the group header line, prepend a triangle indicator: `▶` when collapsed, `▼` when expanded. Keep all existing header styling (bg, accent bar, font color). Change render text to:
```python
indicator = "▶" if collapsed else "▼"
header_surf = font.render(f"{indicator} {gname.upper()}", True, accent)
```

If collapsed, skip rendering topic rows for that group (do not advance `y_cursor` for them, do not increment `flat_idx` for the visible count — but still increment the logical `flat_idx` to keep _gamepedia_flat indexing correct... actually: `flat_idx` is only used to compare against `gamepedia_selected_topic`, so skip both the render and the flat_idx increment for hidden topics — hidden topics can't be selected via keyboard, so treat them as non-existent in the visual layout).

Actually the cleanest approach: skip `y_cursor` advancement AND `flat_idx` advancement for topics in collapsed groups during rendering. Keep a separate `abs_flat_idx` (absolute position in _gamepedia_flat) for right-panel lookup. So:
- `vis_idx` — index into visible topics only (used for highlight comparison with `gamepedia_selected_topic`)
- `abs_idx` — absolute index into `_gamepedia_flat`

Rename the rendering loop variable to be clear. `gamepedia_selected_topic` stores the ABSOLUTE flat index (same as today). Collapsed groups just don't render their rows.

Simpler: keep `gamepedia_selected_topic` as the absolute `_gamepedia_flat` index (no change to meaning). During rendering, if `gname in gamepedia_collapsed_groups`, skip the topic rows entirely (no y_cursor increment, no row rendered). Highlighting still works: check `abs_flat_idx == gamepedia_selected_topic`.

**Right panel — intro page:**
Where the right panel currently starts `if 0 <= gamepedia_selected_topic < len(_gamepedia_flat):`, add an `elif gamepedia_selected_topic == -1:` branch (or restructure to check -1 first):

```python
if gamepedia_selected_topic == -1:
    # Intro page
    intro_title = font_22.render("Welcome to Gamepedia", True, (200, 220, 255))
    screen.blit(intro_title, (right_x, top_y))
    pygame.draw.line(screen, (60, 80, 120, 80), (right_x, top_y + 22), (right_x + right_w, top_y + 22))
    intro_lines = [
        "Gamepedia is your in-game reference for everything in",
        "the 4-Sphere Explorer.",
        "",
        "HOW TO NAVIGATE",
        "",
        "  Click a category header on the left to expand it.",
        "  Click a topic to read it in this panel.",
        "  Use UP / DOWN to move between visible topics.",
        "  Scroll the mouse wheel to scroll long articles.",
        "  Press F1 or ESC to close.",
        "",
        "CATEGORIES",
        "",
    ]
    # List category names with their topic counts
    for gname, topics in GAMEPEDIA_CONTENT:
        accent = _gp_group_colors.get(gname, (180, 200, 255))
        intro_lines.append(f"  {gname}  ({len(topics)} topics)")
    content_y = top_y + 32
    content_line_h = 18
    for i, line in enumerate(intro_lines):
        color = (200, 200, 210) if not line.isupper() and line else (180, 200, 255) if line.isupper() else (200, 200, 210)
        # Accent color for category name lines
        is_cat = any(line.strip().startswith(gname) for gname, _ in GAMEPEDIA_CONTENT)
        if is_cat:
            # Find which group
            for gname, topics in GAMEPEDIA_CONTENT:
                if line.strip().startswith(gname):
                    color = _gp_group_colors.get(gname, (180, 200, 255))
                    break
        elif line.isupper() and line.strip():
            color = (180, 200, 255)
        surf = font.render(line, True, color)
        screen.blit(surf, (right_x, content_y + i * content_line_h))
elif 0 <= gamepedia_selected_topic < len(_gamepedia_flat):
    # existing right-panel rendering unchanged
    ...
```

**Update the hint bar (~line 1358):**
Change to:
```python
hint = font.render("F1/ESC: Close | Click header: Expand/Collapse | UP/DOWN: Topics | Scroll: Content", True, (100, 100, 120))
```

**MOUSEBUTTONDOWN click handling (~line 374):**
In the gamepedia left-panel click block, update to handle group header clicks:

```python
if GP_LEFT_X <= mx <= GP_LEFT_X + GP_LEFT_W and my >= GP_TOP_Y:
    y_cursor = GP_TOP_Y
    abs_flat_idx = 0
    hit = False
    for gname, topics in GAMEPEDIA_CONTENT:
        # Check group header hit
        if y_cursor <= my < y_cursor + GP_LINE_H:
            if gname in gamepedia_collapsed_groups:
                gamepedia_collapsed_groups.discard(gname)
            else:
                gamepedia_collapsed_groups.add(gname)
            hit = True
            break
        y_cursor += GP_LINE_H
        if gname not in gamepedia_collapsed_groups:
            for title, _text in topics:
                if y_cursor <= my < y_cursor + GP_LINE_H:
                    gamepedia_selected_topic = abs_flat_idx
                    gamepedia_scroll = 0
                    hit = True
                    break
                y_cursor += GP_LINE_H
                abs_flat_idx += 1
            if hit:
                break
        else:
            abs_flat_idx += len(topics)
```

**UP/DOWN keyboard navigation (~line 327):**
Replace the current simple increment/decrement with navigation that skips topics in collapsed groups. Build a list of visible absolute indices:

```python
def _visible_topic_indices():
    """Return list of absolute _gamepedia_flat indices currently visible (expanded groups)."""
    result = []
    abs_idx = 0
    for gname, topics in GAMEPEDIA_CONTENT:
        if gname not in gamepedia_collapsed_groups:
            for _ in topics:
                result.append(abs_idx)
                abs_idx += 1
        else:
            abs_idx += len(topics)
    return result
```

Define this as a local function or inline the logic near the keyboard handler. Then:
```python
elif event.key == pygame.K_UP:
    visible = _visible_topic_indices()
    if visible:
        if gamepedia_selected_topic == -1:
            gamepedia_selected_topic = visible[-1]
        elif gamepedia_selected_topic in visible:
            pos = visible.index(gamepedia_selected_topic)
            gamepedia_selected_topic = visible[max(0, pos - 1)]
        gamepedia_scroll = 0
elif event.key == pygame.K_DOWN:
    visible = _visible_topic_indices()
    if visible:
        if gamepedia_selected_topic == -1:
            gamepedia_selected_topic = visible[0]
        elif gamepedia_selected_topic in visible:
            pos = visible.index(gamepedia_selected_topic)
            gamepedia_selected_topic = visible[min(len(visible) - 1, pos + 1)]
        gamepedia_scroll = 0
```

**On gamepedia open (F1 keydown that sets gamepedia_open = True):**
Also reset:
```python
gamepedia_selected_topic = -1
gamepedia_collapsed_groups = set(g for g, _ in GAMEPEDIA_CONTENT)
gamepedia_scroll = 0
```
This resets to intro + all-collapsed each time the user opens it fresh.
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -c "import main" 2>&1 | head -20</automated>
  </verify>
  <done>
    main.py imports without error. Gamepedia state has gamepedia_collapsed_groups. Rendering loops account for collapsed groups. Click handler distinguishes header vs topic clicks. UP/DOWN skips collapsed topics.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update gamepedia tests for collapse-aware layout</name>
  <files>tests/test_gamepedia.py</files>
  <action>
The existing tests use `resolve_click` and `compute_topic_positions` helpers that assume all groups are always expanded. Update them to accept an optional `collapsed_groups` parameter (defaulting to empty set = all expanded), matching the new behaviour.

**Update `resolve_click`:**
```python
def resolve_click(mx, my, content, collapsed_groups=None):
    if collapsed_groups is None:
        collapsed_groups = set()
    if not (GP_LEFT_X <= mx <= GP_LEFT_X + GP_LEFT_W and my >= GP_TOP_Y):
        return None
    y_cursor = GP_TOP_Y
    abs_flat_idx = 0
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        if gname in collapsed_groups:
            abs_flat_idx += len(topics)
            continue
        for title, _text in topics:
            if y_cursor <= my < y_cursor + GP_LINE_H:
                return abs_flat_idx
            y_cursor += GP_LINE_H
            abs_flat_idx += 1
    return None
```

**Update `compute_topic_positions`:**
```python
def compute_topic_positions(content, collapsed_groups=None):
    if collapsed_groups is None:
        collapsed_groups = set()
    positions = []
    y_cursor = GP_TOP_Y
    abs_flat_idx = 0
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        if gname in collapsed_groups:
            abs_flat_idx += len(topics)
            continue
        for title, _text in topics:
            positions.append((abs_flat_idx, y_cursor, y_cursor + GP_LINE_H))
            y_cursor += GP_LINE_H
            abs_flat_idx += 1
    return positions
```

Existing tests pass `collapsed_groups` implicitly as empty set (all expanded), so their behaviour is unchanged. Add new tests:

```python
class TestGamepediaCollapse(unittest.TestCase):
    """Tests for collapsed-group behaviour in click resolution and layout."""

    def test_collapsed_group_topics_not_clickable(self):
        """Topics in a collapsed group return None on click."""
        # Collapse 'Controls' group — its topics should not be hit
        collapsed = {"Controls"}
        # Controls topics are at positions 0,1,2 in flat list
        # Without collapsing, first topic (Keyboard) is at GP_TOP_Y + GP_LINE_H
        # With Controls collapsed, clicking there should return None
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = GP_TOP_Y + GP_LINE_H + GP_LINE_H // 2  # where Keyboard row would be
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        self.assertIsNone(result)

    def test_collapsed_group_shifts_later_groups_up(self):
        """Collapsing Controls shifts Navigation topics up by (num Controls topics) rows."""
        # With all expanded: Navigation starts at GP_TOP_Y + 1*(line_h) + 3*(line_h) + 1*(line_h) = GP_TOP_Y + 5*line_h
        # (1 header + 3 Controls topics + 1 Navigation header)
        # With Controls collapsed: Navigation header is at GP_TOP_Y + 1*line_h (Controls header) + 1*line_h = GP_TOP_Y + 2*line_h
        # First Navigation topic (Travel & Slerp, abs_idx=3) is at GP_TOP_Y + 2*line_h + line_h//2
        collapsed = {"Controls"}
        positions = compute_topic_positions(GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        # First position should be for abs_flat_idx=3 (Travel & Slerp)
        abs_idx, y_start, y_end = positions[0]
        self.assertEqual(abs_idx, 3)
        # y_start = GP_TOP_Y + 2*GP_LINE_H (Controls header + Navigation header)
        expected_y = GP_TOP_Y + 2 * GP_LINE_H
        self.assertEqual(y_start, expected_y)

    def test_all_collapsed_no_clickable_topics(self):
        """With all groups collapsed, no topic click resolves."""
        all_groups = {g for g, _ in GAMEPEDIA_CONTENT}
        mx = GP_LEFT_X + GP_LEFT_W // 2
        # Try clicking anywhere in the middle of the screen
        for my in range(GP_TOP_Y, GP_TOP_Y + 20 * GP_LINE_H, GP_LINE_H):
            result = resolve_click(mx, my, GAMEPEDIA_CONTENT, collapsed_groups=all_groups)
            self.assertIsNone(result, f"Expected None at y={my}, got {result}")

    def test_partially_collapsed_positions(self):
        """compute_topic_positions with one group collapsed returns only visible topics."""
        collapsed = {g for g, _ in GAMEPEDIA_CONTENT}  # all collapsed
        positions = compute_topic_positions(GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        self.assertEqual(len(positions), 0)
```

Also update the `test_flat_list_length` and `test_click_selects_last_topic` tests — these use absolute flat indices which remain valid (no changes needed to those tests since they use all-expanded default).

Run tests to confirm all pass: `./venv/bin/python -m pytest tests/test_gamepedia.py -v`
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -m pytest tests/test_gamepedia.py -v 2>&1</automated>
  </verify>
  <done>
    All gamepedia tests pass, including the 4 new collapse-behaviour tests.
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. `./venv/bin/python -m pytest tests/ -v` — all tests pass
2. `./venv/bin/python main.py` — launch game, press F1: intro page shown, all categories collapsed; click a category header to expand; click a topic to read it; UP/DOWN navigates only visible topics; re-opening resets to intro + all-collapsed
</verification>

<success_criteria>
- Gamepedia opens to intro page (gamepedia_selected_topic == -1)
- All 6 category groups collapsed by default
- Category header click toggles collapse with triangle indicator (▶/▼)
- Topics in collapsed groups do not appear in left panel
- UP/DOWN only navigates visible (expanded) topics
- All existing + new tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/3-make-the-categories-in-the-gamepedia-col/3-SUMMARY.md`
</output>
