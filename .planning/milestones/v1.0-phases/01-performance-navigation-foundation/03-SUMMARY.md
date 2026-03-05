---
phase: 01-performance-navigation-foundation
plan: "03"
subsystem: navigation
tags: [auto-travel, visited-tracking, tab-key, ui, sidebar]
dependency_graph:
  requires: []
  provides: [auto-travel-tab, visited-tracking]
  affects: [main.py]
tech_stack:
  added: []
  patterns: [session-state-set, nearest-first-scan, deferred-queue]
key_files:
  created: []
  modified:
    - main.py
decisions:
  - "visited_points as a plain set — O(1) membership check, session-only (no persistence needed)"
  - "find_nearest_unvisited scans visible_indices in existing distance order (already sorted) — no extra sort needed"
  - "Tab respects the travel queue: if already traveling, auto-travel target is queued, not dropped"
  - "Feedback banner at y=70 avoids conflict with status (y=10) and controls (y=30/50)"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-05"
  tasks_completed: 2
  files_modified: 1
---

# Phase 1 Plan 03: Auto-Travel to Nearest Unvisited Point Summary

Tab key auto-travel with session-based visited tracking, sidebar dimming, visited count header, and transient feedback banner.

## What Was Built

Pressing Tab now instantly starts travel to the nearest unvisited visible point (by angular distance). Once arrived, that point is recorded in `visited_points` and excluded from future Tab selections. When all visible points are visited, Tab prints a console hint and does nothing.

### Key components

- `visited_points: set` — session-scoped index set, O(1) membership check
- `find_nearest_unvisited(indices, distances)` — linear scan through pre-sorted visible list, returns first non-visited entry
- `auto_travel_to_nearest_unvisited()` — initiates immediate travel or queues if already traveling
- Tab key binding in KEYDOWN block (not intercepted by search mode)
- Visited marking in travel completion block (co-located with pop animation trigger)
- Sidebar: visited items rendered with `(50, 50, 70)` dimmed background
- Header: `POINTS (N) | VISITED (N)` counter
- Feedback banner: green text at `(10, 70)` for 2000ms after each arrival

## Commits

| Hash | Description |
|------|-------------|
| 623847a | feat(01-03): add Tab auto-travel to nearest unvisited point |

## Deviations from Plan

None - plan executed exactly as written. Tasks 1 and 2 were committed together as one coherent feature unit.

## Self-Check: PASSED

- main.py modified: confirmed (77 insertions, 7 deletions)
- Commit 623847a: confirmed via git log
- Syntax check: passed (py_compile)
- Logic test: passed (find_nearest_unvisited traversal and all-visited case)
