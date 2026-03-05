---
phase: 01-performance-navigation-foundation
plan: "02"
subsystem: UI/Navigation
tags: [search, filter, sidebar, ui]
dependency_graph:
  requires: []
  provides: [search-filter-ui]
  affects: [main.py sidebar rendering, event loop, click-to-travel]
tech_stack:
  added: []
  patterns: [per-frame filter computation, prefix match filtering]
key_files:
  created: []
  modified:
    - main.py
decisions:
  - "Compute filtered_indices once per frame before event loop so click/hover handlers use current-frame filter state"
  - "Prefix match (not substring) keeps search fast and predictable with small visible set"
  - "Search activated by / or F; Escape clears — avoids W/A/S/D conflict during navigation"
metrics:
  duration: "3 minutes"
  completed: "2026-03-05"
  tasks_completed: 2
  files_modified: 1
---

# Phase 1 Plan 02: Search Filtering Summary

Real-time prefix-match search field in sidebar filters the visible point list by name; results remain distance-sorted and click-to-travel works through the filter.

---

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add search input state, apply_search_filter(), keyboard event handling | ebaa1c2 |
| 2 | Render search field in sidebar, integrate filtered list with hover/click | ebaa1c2 |

---

## What Was Built

### Search State and Logic

Added at module level (after UI state initialization):

```python
search_text = ""
search_active = False

def apply_search_filter(search_query):
    if not search_query:
        return visible_indices[:]
    query_lower = search_query.lower()
    return [idx for idx in visible_indices if get_name(idx).lower().startswith(query_lower)]
```

### Per-Frame Filter Computation

`filtered_indices` and `filtered_distances` are computed once per frame immediately after `update_visible()`, before the event loop and render sections. This ensures click-to-travel, hover detection, and scroll clamping all operate on consistent filter state within a frame.

### Keyboard Bindings

- `/` or `F` — activate search (clears field)
- Typing — accumulates alphanumeric, space, hyphen characters
- Backspace — removes last character
- Escape — clears and deactivates search

Navigation keys (WASD/QE/drag) are suppressed in search mode via the `search_active` branch. UP/DOWN scrolling continues to work via the `keys[]` poll (which runs before the event loop), so list scrolling works in search mode.

### Sidebar UI

Search field rendered between bookmark section and point list:
- Inactive: dark background with gray border, dim `/` placeholder
- Active: tinted background (dark teal) with blue border, cursor `|` appended to query text
- Count label above field shows `POINTS (n/total)` when filter active, `POINTS (n)` when inactive

### List Integration

All list-related logic updated to use `filtered_indices`:
- Scroll clamping: `min(max(0, len(filtered_indices) - max_items), ...)`
- Click-to-travel: resolves from `filtered_indices[item_idx]`
- Hover detection: bounds-checked against `filtered_indices`
- Viewport hover circle: looks up from `filtered_indices`
- Travel/queue markers (`<` / `<<`): check `point_idx` from `filtered_indices`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale global declaration causing SyntaxError**
- **Found during:** Task 1 verification (py_compile)
- **Issue:** `global list_start_y` was declared late in the render block. After moving `filtered_indices` computation above the event loop (which reads `list_start_y` for scroll clamping), Python flagged "name used prior to global declaration"
- **Fix:** Removed the `global list_start_y` statement — it was unnecessary at module scope (global declarations are only needed inside functions)
- **Files modified:** main.py
- **Commit:** ebaa1c2

**2. [Rule 2 - Design] Moved filter computation before event loop (not in render section as planned)**
- **Found during:** Task 2 planning — click-to-travel and hover handlers needed current-frame `filtered_indices`
- **Fix:** Compute `filtered_indices`/`filtered_distances` once after `update_visible()`, before events. Removed the redundant computation from the render section
- **Files modified:** main.py
- **Commit:** ebaa1c2

---

## Self-Check: PASSED

- main.py modified: FOUND
- Commit ebaa1c2: FOUND (`git log --oneline | grep ebaa1c2`)
- Syntax: `python -m py_compile main.py` passed
- Search logic test: all 5 assertions passed
