---
phase: quick-4
plan: 4
subsystem: gamepedia-ui
tags: [gamepedia, keyboard-nav, ui, tests]
dependency_graph:
  requires: [quick-3-collapsible-gamepedia]
  provides: [gamepedia-keyboard-nav]
  affects: [main.py, tests/test_gamepedia.py]
tech_stack:
  added: []
  patterns: [cursor-state-machine, unified-nav-order, tdd]
key_files:
  modified:
    - main.py
    - tests/test_gamepedia.py
decisions:
  - Unified nav order (groups + topics) rather than topics-only list — groups become navigable, cursor tracks both types
  - Cursor does NOT auto-change selected_topic when moving to a group row — right panel keeps its current content
  - Enter/Space on group toggles collapse; on topic sets selected_topic + clears scroll
  - White outline (220,220,255) drawn after fill, visible on both selected and unselected rows
  - Intro page text updated alongside hint bar — both documented the old mouse-only controls
metrics:
  duration: "~10 minutes"
  completed: "2026-03-12"
  tasks_completed: 2
  files_changed: 2
---

# Quick Task 4: Gamepedia Keyboard Navigation Summary

**One-liner:** Full keyboard-only Gamepedia navigation via cursor state machine with unified group+topic nav order, Enter/Space toggle/select, PageUp/PageDown scroll, and white outline cursor highlight.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add keyboard cursor navigation to Gamepedia | 046d9ab | main.py |
| 2 | Tests for keyboard nav logic | 95bb273 | tests/test_gamepedia.py |

---

## What Was Built

### Task 1: Keyboard navigation in main.py

**State added:**
- `gamepedia_cursor = None` — new state variable alongside existing gamepedia state
- Reset to `None` when Gamepedia opens (F1 handler)

**UP/DOWN handler rewritten:**
- Builds `_nav_order` — flat list of `("group", gname)` and `("topic", abs_idx)` in display order, respecting collapsed groups
- `None` cursor: UP selects last item, DOWN selects first item
- Cursor moves clamp at bounds (no wrap-around)
- Moving to a topic row: sets `gamepedia_selected_topic` and clears scroll
- Moving to a group row: does NOT change `gamepedia_selected_topic` (right panel stable)

**New Enter/Space handler:**
- Group cursor: toggles collapse/expand
- Topic cursor: sets selected_topic + clears scroll

**New PageUp/PageDown handler:**
- PageDown: `gamepedia_scroll += 10`
- PageUp: `gamepedia_scroll = max(0, gamepedia_scroll - 10)` (existing render code clamps to max_scroll)

**Cursor outline in render loop:**
- Group headers: store rect as `header_rect`, draw 1px (220,220,255) outline after text blit
- Topic rows: draw 1px (220,220,255) `cur_rect` outline after selection fill (so it appears on top)

**Text updates:**
- Hint bar: `"F1/ESC: Close  UP/DOWN: Navigate  Enter/Space: Select/Toggle  PgUp/Dn: Scroll"`
- Intro page HOW TO NAVIGATE section: replaced mouse-centric instructions with keyboard-first instructions

### Task 2: Tests in tests/test_gamepedia.py

Added `build_nav_order(content, collapsed_groups)` pure helper and `TestGamepediaKeyboardNav` class with 5 tests:

- `test_all_expanded_starts_with_group`: first item is `("group", "Controls")`
- `test_all_expanded_second_item_is_first_topic`: second item is `("topic", 0)`
- `test_all_collapsed_only_groups`: only group rows, count == num_groups
- `test_collapsing_one_group_removes_its_topics`: Controls collapse removes 3 topics, group row remains
- `test_nav_order_full_length_all_expanded`: len == 6 groups + 24 topics = 30

---

## Test Results

All 237 tests pass (232 before + 5 new). No regressions.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Intro page navigation instructions updated**
- **Found during:** Task 1
- **Issue:** The intro page HOW TO NAVIGATE section still described mouse-only controls after adding keyboard navigation; inconsistent with the new controls
- **Fix:** Updated intro_lines to document UP/DOWN, Enter/Space, PgUp/PgDn as the primary navigation method, with mouse as secondary
- **Files modified:** main.py
- **Commit:** 046d9ab

---

## Self-Check: PASSED

- main.py syntax check: `python -m py_compile main.py` → exit 0
- tests/test_gamepedia.py: 22 tests pass
- Full suite: 237 passed, 1 warning (pre-existing warning in test_sphere.py unrelated to this change)
- Commits 046d9ab and 95bb273 verified in `git log`
