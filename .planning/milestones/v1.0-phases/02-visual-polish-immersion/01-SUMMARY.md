# Plan 01 Summary: Glow Halos

**Status:** Complete
**Completed:** 2026-03-05

## What was done
- Added SRCALPHA glow halo rendering before each visible point circle
- Glow radius = 2.5x point radius + proximity bonus (normalized_dist * 8)
- Glow alpha = 30 (far) to 90 (near)
- Uses point's own color for visual coherence across both view modes

## Files modified
- `main.py` — Point draw loop: glow surface created and blitted before opaque point circle

## Verification
- Glow halos scale continuously with distance
- Uses established SRCALPHA surface pattern
- ~10 blits per frame — negligible overhead
