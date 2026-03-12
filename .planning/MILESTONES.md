# Milestones

## v1.2 4S Compass (Shipped: 2026-03-12)

**Phases completed:** 2 phases, 3 plans
**Lines of code:** 7,503 Python (+733/-100 during milestone)
**Timeline:** 1 day (2026-03-12)

**Key accomplishments:**
- lib/compass.py: 4D angle math (heading/tilt/W-depth) against fixed standard basis axes
- Lerp needle animation (200ms) with shortest-path pi-boundary wraparound
- Three-indicator widget: compass rose, vertical tilt bar, W-depth color gauge
- Gamepedia Compass topic documenting all three indicators
- Conditional rendering: compass hidden during Gamepedia and non-default view modes

**Requirements:** 8/8 complete (COMP-01..03, ORIE-01..02, WIDG-01..03)

---

## v1.0 Explorer MVP (Shipped: 2026-03-05)

**Phases completed:** 3 phases, 9 plans, 20 commits
**Lines of code:** 2,172 Python (+911/-120 during milestone)
**Timeline:** 1 day (2026-03-05)

**Key accomplishments:**
- KDTree spatial indexing for sub-linear visibility queries (replaced O(n) scan of 30k points)
- Bookmark system with save/load/restore for revisiting locations on S3
- Real-time name search with instant prefix filtering in sidebar
- Tab auto-travel to nearest unvisited visible point
- Visual immersion: glow halos, parallax starfield, animated travel line, breadcrumb trail
- Click-hold radial menu with detail panel showing 4D coordinates, audio params, planet sprite

**Requirements:** 10/10 complete (NAV-01..04, VIS-01..03, INFO-01..02, PERF-01)

---

