# Phase 3: Information & Context - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Provide point detail data through an interactive radial menu system. Delivers: click-hold radial menu on viewport points with Info option opening a detail panel showing 4D coordinates, name, distance, and audio parameters (INFO-01). INFO-02 (stats overlay) dropped from scope.

</domain>

<decisions>
## Implementation Decisions

### Radial Menu System

- **Trigger:** Click-hold on a viewport point for ~200ms opens the radial menu
- **Quick release:** If released before 200ms threshold, travel-to-point fires as normal (existing behavior preserved)
- **Scope:** Viewport points only — sidebar list items not affected
- **Layout:** 4 options represented by symbols arranged radially. 1 = Info (functional), 3 = placeholders (A, B, C)
- **Dismiss:** Release mouse outside any option wedge = dismiss, no action taken
- **Selection:** Move mouse to desired wedge while holding, release to select

### Detail Panel (Info option)

- **Placement:** Semi-transparent overlay floating near the inspected point in the viewport
- **Content:**
  - Point name (from name system)
  - 4D coordinates (raw XYZW values)
  - Angular distance from player
  - Audio: human-readable summary (e.g., "Acid bass in blues scale") — not raw parameters
- **Highlight:** Distinct colored ring/outline on the inspected point in viewport (different from hover highlight)
- **Non-blocking:** Panel stays open during travel; updates if you inspect a different point
- **Works on any visible point** regardless of travel state
- **Dismiss:** Escape key or click anywhere outside the panel

### Scope Changes

- **INFO-02 dropped:** Stats overlay (points visited, distance traveled, session time) removed from Phase 3 scope entirely
- Phase 3 delivers only INFO-01 via the radial menu system

</decisions>

<specifics>
## Specific Ideas

- Audio summary should use timbre function names mapped to friendly labels (e.g., `_synth_acid` -> "Acid bass", `_synth_supersaw` -> "Supersaw pad") combined with scale name
- Radial menu should feel responsive — appear at mouse position centered on the held point
- Placeholder options (A, B, C) render as grayed-out / inactive symbols

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_name(idx)` — lazy name decoding, already cached
- `get_identicon(idx)` — lazy identicon generation, already cached
- `point_colors[idx]` — per-point RGB color
- `points[idx]` — raw 4D coordinates (NumPy array)
- `angular_distance()` in sphere.py — distance calculation
- `format_dist()` — mrad/rad formatting
- SRCALPHA surface pattern — used for glow, pop animation, breadcrumbs (reuse for panel and radial menu)
- `last_projected_points` — screen positions of visible points, used for click detection
- Audio parameters derivable from `_name_keys[idx]` by replaying the RNG sequence in `generate_signal()`

### Established Patterns
- Click detection: `MOUSEBUTTONDOWN` sets drag_start, `MOUSEBUTTONUP` checks drag distance < 10px threshold
- Hover detection: distance-squared check against projected points with hit_radius
- Overlay rendering: SRCALPHA surfaces blitted onto screen (glow halos, pop animation, breadcrumbs)
- Font: `pygame.font.Font(None, 14)` — small monospace-like font

### Integration Points
- main.py:345-387 — click handling in event loop (add hold timer logic here)
- main.py:474-520 — point rendering loop (add inspection ring here)
- main.py:472 — `last_projected_points` available for radial menu positioning
- audio.py:234-252 — `generate_signal()` RNG sequence defines timbre/scale/tempo (extract params without generating audio)

### New Code Needed
- Audio parameter extraction function (replay RNG to get timbre index + scale index + MIDI note without synthesizing)
- Radial menu state machine (idle → hold_pending → menu_open → action)
- Detail panel rendering function
- Timbre/scale name lookup tables

</code_context>

<deferred>
## Deferred Ideas

- INFO-02 (stats overlay) — dropped by user decision, not deferred. Remove from requirements if desired.

</deferred>

---

*Phase: 03-information-context*
*Context gathered: 2026-03-05*
