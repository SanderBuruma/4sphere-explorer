# Phase 2: Visual Polish & Immersion - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance exploration atmosphere and provide visual feedback for movement and location discovery. Delivers: distance-based glow halos on points (VIS-01), animated parallax starfield background (VIS-02), animated travel line to target (VIS-03), and breadcrumb trail of visited points (NAV-03).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

- **Glow rendering** — Additive blending vs SRCALPHA surfaces for glow halos, radius/alpha curves
- **Starfield density & parallax factor** — Number of stars, parallax sensitivity relative to 4D rotation
- **Travel line style** — Solid, dashed, or animated dots; color and opacity
- **Breadcrumb trail capacity** — Max number of breadcrumbs shown, fade curve, dot size

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- SRCALPHA surface pattern used for pop animation (main.py:521-523) and hover circle (main.py:501-503) — reuse for glow and breadcrumbs
- `projected_points` list built each frame with `(p2d, angular_dist, depth, idx)` — glow draws alongside point rendering
- `visited_points` set (main.py:137) — tracks which points have been traveled to, breadcrumbs can build on this
- `project_to_tangent()` / `project_tangent_to_screen()` — project any S³ point to screen coords
- `orientation` frame — rows 1-3 give camera tangent basis, useful for starfield parallax

### Established Patterns
- Render loop: screen.fill(BG_COLOR) → project points → draw points (painter's algo) → draw UI overlays → sidebar
- Point rendering (main.py:455-480): iterates projected_points, draws circles with distance-modulated size/brightness
- Travel state: `traveling`, `travel_target`, `travel_target_idx` — condition for travel line
- Constants at top: SCREEN_WIDTH=1200, SCREEN_HEIGHT=800, view_width=900, FOV_ANGLE=0.116

### Integration Points
- main.py:429 `screen.fill(BG_COLOR)` — starfield renders immediately after this
- main.py:455-480 point draw loop — glow renders just before each point circle
- main.py:527-563 travel target triangles section — travel line renders nearby
- main.py:387-425 travel update — breadcrumb recording happens at travel completion (line 406-411)
- main.py:137 `visited_points` set — breadcrumb trail needs ordered visit history (set → list/deque)

</code_context>

---

*Phase: 02-visual-polish-immersion*
*Context gathered: 2026-03-05*
