---
phase: quick
plan: 1
subsystem: compass
tags: [compass, widget, 4d-geometry, projection]
key_files:
  modified:
    - lib/compass.py
decisions:
  - "Project great-circle rings via orientation frame dot products rather than decomposed scalar readouts"
  - "Dash every-other back-hemisphere segment for depth cue (no pygame alpha per-segment — color dimming instead)"
  - "Pole label offset computed from projected direction away from centre for automatic placement"
metrics:
  completed: "2026-03-12"
---

# Quick Task 1: Two-Ring Compass Summary

Two great-circle compass rings replacing the old rose+tilt-bar+W-gauge widget.

## What Was Built

Rewrote `lib/compass.py` as a projection-based ring renderer. Two rings are sampled as 64 points on S3 and projected through the camera orientation frame into 2D widget space each frame:

- NS ring (blue-white, `_NS_COLOR_BRIGHT = (100, 180, 255)`): XY plane, poles labelled "N" / "S"
- W ring (amber, `_W_COLOR_BRIGHT = (255, 160, 80)`): XW plane, poles labelled "W+" / "W-"

Front-hemisphere arcs are drawn solid (width 2); back-hemisphere arcs dash every other segment at 50% brightness (width 1). Pole markers are small filled circles with labels offset away from the widget centre.

The public API signature is unchanged: `render_compass(screen, orientation, x, y, size=120)`.

All old module-level lerp state (`_needle_angle`, `_target_angle`, `_lerp_progress`, `_LERP_DURATION_MS`, `_last_render_ms`) and old public helpers (`calculate_heading`, `calculate_tilt`, `calculate_w_alignment`, `_update_needle`) are removed.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- `lib/compass.py` exists and is 168 lines (above 80 line minimum).
- Smoke test passed: `render_compass()` on identity orientation raises no exceptions; `_needle_angle` and `calculate_heading` are absent from the module.
