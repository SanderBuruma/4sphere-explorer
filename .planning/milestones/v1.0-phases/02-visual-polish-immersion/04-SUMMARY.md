# Plan 04 Summary: Breadcrumb Trail

**Status:** Complete
**Completed:** 2026-03-05

## What was done
- Added `visit_history = deque(maxlen=50)` for ordered trail
- Appends point index at travel completion (parallel to `visited_points.add()`)
- Breadcrumb dots rendered after point draw loop, before hover/pop overlays
- Each dot projected through tangent space (moves with camera rotation)
- Fade: oldest = dim/small (alpha 30, 2px), newest = bright/larger (alpha 130, 3px)
- Light blue color (180, 220, 255) distinguishes from data points
- Auto-eviction via deque maxlen — no cleanup needed

## Files modified
- `main.py` — Import deque, visit_history state, append at travel completion, breadcrumb render loop

## Verification
- Trail forms after traveling to multiple points
- Dots fade by recency
- Spatial coherence maintained during rotation
- visited_points set still works for auto-travel and list dimming
