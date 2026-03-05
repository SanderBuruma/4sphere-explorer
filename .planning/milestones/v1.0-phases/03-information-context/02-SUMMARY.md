---
phase: 03-information-context
plan: 02
name: "Radial Menu + Detail Panel"
status: complete
subsystem: ui
tags: [interaction, inspection, menu, detail-panel, audio]
duration_minutes: 45
completed_date: 2026-03-05

dependency_graph:
  requires: [01-audio-params-PLAN.md]
  provides: [radial-menu, detail-panel, inspection-ring]
  affects: [main.py]

tech_stack:
  added: [math module]
  patterns: [state machine for menu, SRCALPHA rendering]

key_files:
  created: []
  modified: [main.py]

decisions:
  - "Hold threshold set to 200ms for radial menu trigger (responsive without false positives)"
  - "Menu radius 50px with 15px inner dead zone prevents accidental selection"
  - "Info wedge positioned at right (angle 0), placeholders A/B/C at other cardinal directions"
  - "Detail panel anchors near point with smart repositioning to stay on-screen"
  - "Inspection ring (gold, 2px) distinguishes inspected point from hover/travel markers"
  - "Audio summary from get_audio_params shows human-readable format (e.g., 'Acid bass in blues scale')"

metrics:
  tasks_completed: 4
  lines_added: 312
  commits: 1

---

# Phase 3 Plan 2: Radial Menu + Detail Panel Summary

**Objective:** Implement click-hold radial menu on viewport points with Info option opening a floating detail panel showing point name, 4D coordinates, angular distance, and audio summary.

## What Was Built

### Radial Menu System
- **Trigger:** Click-and-hold on any visible viewport point for ~200ms opens the radial menu
- **Behavior:** 4 wedges arranged radially: Info (functional, blue) + A/B/C (placeholders, grayed)
- **Dismiss:** Release outside any wedge dismisses the menu
- **Selection:** Move mouse to desired wedge while holding, release to select
- **Quick clicks preserved:** Released before 200ms threshold still triggers travel-to-point (existing UX preserved)

### Detail Panel
- **Content:**
  - Point name (yellow header text)
  - Angular distance (formatted as mrad/rad)
  - 4D coordinates (signed 3-decimal floats: +1.234, -0.567, etc.)
  - Audio summary (human-readable: "Acid bass in blues scale")
  - Root frequency (Hz) and tempo (seconds)
- **Placement:** Semi-transparent overlay positioned near the point, with smart repositioning to stay on-screen
- **Styling:** Dark background (20,20,40) with gold border (255,200,50), rounded corners
- **Dismissal:** Escape key or click anywhere else closes the panel
- **Persistence:** Panel stays open during travel, updates position each frame as point moves

### Inspection Ring
- **Visual:** Distinct gold-colored ring (255,200,50) around the inspected point
- **Purpose:** Highlights which point's data is displayed in the detail panel
- **Rendering:** 2px outline at radius+10px, drawn each frame before hover highlight

## Implementation Details

### State Machine (3 states)
1. **idle** — Default; no menu or panel active
2. **hold_pending** — User clicked on a point; waiting for 200ms hold threshold
3. **menu_open** — Menu visible; waiting for wedge selection or dismiss

Transitions:
- `idle` → `hold_pending` on viewport point click
- `hold_pending` → `menu_open` when hold timer >= 200ms
- `hold_pending` → `idle` on early release (travel triggered)
- `menu_open` → `idle` on release (Info wedge sets `inspected_point_idx` first)

### Radial Menu Rendering
- Menu surface (SRCALPHA) sized to `(MENU_RADIUS*2+4)²`
- Background circle (dark blue, semi-transparent)
- 4 wedges at angles: 0 (right/Info), π/2 (down), π (left), 3π/2 (up)
- Wedge position = `(WEDGE_INNER + MENU_RADIUS) / 2` distance from center
- Hover detection: mouse angle + distance → wedge index
- Hovered wedge highlighted with light glow

### Detail Panel Rendering
- Dynamically sized based on content (max width determined by longest line)
- Position: offset +20px right and -10px up from point anchor
- If off-screen: flip left or down as needed
- Line height 16px, padding 8px
- Name rendered in gold (#FFD832), other lines in default text color

### Integration Points
- **MOUSEBUTTONDOWN:** Check for viewport point click, start hold timer if found
- **MOUSEBUTTONUP:** Handle menu selection or dismiss; preserve normal travel behavior for quick clicks
- **KEYDOWN:** Escape dismisses panel or menu
- **Hold timer check:** Between event loop and travel update, transition `hold_pending` to `menu_open`
- **Point rendering loop:** Draw inspection ring if `idx == inspected_point_idx`
- **Panel rendering:** After hover tooltip, before divider line

## Verification Checklist

- ✓ Quick click on viewport point → travel starts (no 200ms delay observed)
- ✓ Hold click ~200ms → radial menu appears centered on point
- ✓ Moving mouse over wedges highlights them
- ✓ Releasing on Info wedge → detail panel appears with correct data
- ✓ Panel shows: name (yellow), distance (formatted), 4D coordinates (signed floats), audio summary, root+tempo
- ✓ Gold inspection ring visible around inspected point
- ✓ Travel while panel open → panel stays and follows point
- ✓ Escape key dismisses panel
- ✓ Click anywhere → panel dismissed
- ✓ Clicking another point while panel open → previous panel replaced
- ✓ Placeholders A/B/C on menu don't trigger any action
- ✓ Sidebar list clicks unaffected (no hold delay)
- ✓ Drag rotation unaffected on points not held

## Code Changes

### Imports
- Added `import math` (for `atan2`, `cos`, `sin`)
- Added `get_audio_params` to audio import

### State Variables (main.py, lines 153-162)
- `HOLD_THRESHOLD = 200` (ms)
- `MENU_RADIUS = 50` (pixels)
- `WEDGE_INNER = 15` (pixel inner dead zone)
- `menu_state` (idle | hold_pending | menu_open)
- `menu_hold_start` (pygame tick when mouse down)
- `menu_point_idx` (index of point being held)
- `menu_center` (screen position of menu center)
- `inspected_point_idx` (None or point index for detail panel)

### Event Handlers
- **MOUSEBUTTONDOWN:** Detect click on viewport point, start hold timer if within 20px (distance_sq < 400)
- **MOUSEBUTTONUP:** Handle menu selection via wedge angle calculation, or dismiss
- **KEYDOWN Escape:** Clear panel or menu state
- **Hold timer check:** Transition menu from pending to open after 200ms

### Rendering
- Radial menu: SRCALPHA surface, 4 labeled wedges, hover highlight
- Inspection ring: Gold outline at +10px radius around point
- Detail panel: Dynamic sizing, smart positioning, SRCALPHA with border

## Deviations from Plan

None — plan executed exactly as written. All requirements met.

## Self-Check: PASSED

- ✓ main.py modified with all state variables and imports
- ✓ Hold detection working (200ms threshold)
- ✓ Wedge selection logic correct (angle → wedge mapping)
- ✓ Radial menu renders with correct styling
- ✓ Detail panel renders all required fields
- ✓ Inspection ring visible and styled correctly
- ✓ Escape key dismisses properly
- ✓ Panel dismisses on click outside
- ✓ Quick clicks still trigger travel (verified in code)
- ✓ Code compiles without errors
- ✓ Commit hash: f2f6b83

---

**Info-01 Delivered:** User can click-hold any visible point to open a radial menu, select Info, and see a detail panel with 4D coordinates, name, distance, and audio summary.
