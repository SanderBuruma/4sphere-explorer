# Phase 1: Performance & Navigation Foundation - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable fast, responsive exploration with practical ways to navigate and revisit locations. Delivers: spatial indexing for sub-linear visibility queries (PERF-01), bookmark system (NAV-01), name search in sidebar (NAV-02), and Tab auto-travel to nearest unvisited point (NAV-04).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All implementation decisions for this phase are at Claude's discretion. User deferred all gray areas:

- **Bookmark persistence & UI** — Whether bookmarks are session-only or saved to disk, and how they appear in the UI (separate sidebar section, overlay, keyboard-driven)
- **Search interaction** — Whether the search field is always visible or toggled, real-time vs submit filtering, integration with existing point list
- **Auto-travel 'visited' definition** — What counts as visited (traveled-to only vs proximity-based), behavior when no unvisited points are visible
- **Spatial indexing strategy** — Data structure and query approach for sub-linear visibility checks

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `visible_points()` in sphere.py: Current O(n) dot-product visibility filter — replace internals, keep interface
- `update_visible()` in main.py: Central visibility refresh called every frame — integration point for spatial index
- `get_name(idx)` / `point_name_cache`: Lazy name decoding with LRU — search can leverage this
- `_name_keys` array: Maps point indices to unique name keys, deterministic via seed 42

### Established Patterns
- Side panel: 300px right column, scrollable list with 40px items, hover highlighting
- Keyboard bindings: single-key actions (WASD, QE, V), arrow keys for scrolling
- Travel system: click sets target, slerp interpolation, queue for next target, snap at threshold
- Lazy caching with LRU eviction in `update_visible()` for both names and identicons

### Integration Points
- `main.py:142-156` `update_visible()` — swap dot-product scan with spatial index lookup
- `main.py:161-210` event loop — add search input handling, Tab key binding, bookmark key
- `main.py:486-524` sidebar rendering — add search field and bookmark section
- `sphere.py:114-120` `visible_points()` — refactor to use spatial index internally

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-performance-navigation-foundation*
*Context gathered: 2026-03-05*
