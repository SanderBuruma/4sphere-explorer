---
phase: 07-compass-widget
plan: 01
subsystem: ui
tags: [pygame, numpy, compass, hud, 4d-orientation, lerp-animation]

requires: []
provides:
  - lib/compass.py with render_compass(screen, orientation, x, y, size) interface
  - calculate_heading(camera_pos) using fixed X/Z basis via atan2
  - calculate_tilt(camera_pos) using clipped arccos on Y dot product
  - calculate_w_alignment(camera_pos) using clipped dot product with W axis
  - Lerp animation state with shortest-path wraparound at ±pi
affects:
  - 07-compass-widget (plan 02 will integrate render_compass into main.py)

tech-stack:
  added: []
  patterns:
    - "Module-level Lerp animation state with _needle_angle / _target_angle / _lerp_progress"
    - "Widget surface pattern: create pygame.Surface((size,size), SRCALPHA), draw, blit to screen"
    - "Delta-time via module-level _last_render_ms tracking (no clock reference needed)"

key-files:
  created:
    - lib/compass.py
  modified: []

key-decisions:
  - "heading = atan2(-z_comp, x_comp) so +X = 0 and +Z = -pi/2 (clockwise from above)"
  - "tilt uses arccos(abs(y_comp)) so values are always [0, pi/2] regardless of Y sign"
  - "Lerp duration 200ms with shortest-path delta to avoid needle spinning around 0/2pi boundary"
  - "Module-level _last_render_ms for dt tracking avoids needing a clock parameter in the public API"

patterns-established:
  - "Compass widget: functions-only, no classes, module-level state for animation"
  - "Fixed basis axes are module-level constants prefixed with _AXIS_*"

requirements-completed: [COMP-01, COMP-02, COMP-03, ORIE-01, ORIE-02, WIDG-01]

duration: 2min
completed: 2026-03-12
---

# Phase 7 Plan 01: Compass Widget Module Summary

**Self-contained lib/compass.py with fixed-basis 4D angle math (heading/tilt/W-depth), Lerp needle animation with pi-boundary wraparound, and a three-indicator pygame widget (compass rose, tilt bar, W gauge)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-12T05:28:15Z
- **Completed:** 2026-03-12T05:29:53Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `calculate_heading()` derives XZ-plane heading from dot products with fixed standard basis, returns [-pi, pi]
- `calculate_tilt()` uses clipped arccos for NaN-safe Y-axis tilt in [0, pi/2]
- `calculate_w_alignment()` returns [-1, 1] W-depth reading with clip guard
- `_update_needle()` implements Lerp animation with shortest-path delta to prevent spin past ±pi
- `render_compass()` draws semi-transparent rounded-rect widget with compass rose + animated needle, vertical tilt bar, and color-interpolated W gauge

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/compass.py with angle calculations and Lerp animation state** - `bcec0f6` (feat)
2. **Task 2: Visual smoke-test render_compass output** - `6b69027` (chore — no code changes needed)

## Files Created/Modified

- `/home/sanderburuma/Projects/4sphere-explorer/lib/compass.py` - Full compass widget module: 3 calculation functions, Lerp animation state, render_compass() drawing all three indicators

## Decisions Made

- Used `atan2(-z_comp, x_comp)` so that pointing along +X gives heading 0 and +Z gives -pi/2, consistent with right-hand XZ orientation from above
- `tilt = arccos(abs(y_comp))` so tilt is always non-negative regardless of whether camera has +Y or -Y component
- Module-level `_last_render_ms` for delta time avoids requiring a clock argument in the public API signature
- 200ms Lerp duration: fast enough to feel responsive, slow enough to visually track rotation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all angle math and rendering passed verification on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `lib/compass.py` is complete and import-safe
- `render_compass(screen, orientation, x, y, size)` is ready for integration into `main.py`
- Plan 02 should call `render_compass` in the main draw loop, gated on `view_mode == 0`, positioned in a corner

---
*Phase: 07-compass-widget*
*Completed: 2026-03-12*
