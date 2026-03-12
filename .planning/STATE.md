---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: 4S Compass
status: in_progress
current_phase: 7
current_plan: 1
last_updated: "2026-03-12T05:30:00Z"
last_activity: "Completed 07-01-PLAN.md"
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
---

# State: 4-Sphere Explorer

**Project:** Interactive 4D sphere (S3) explorer

**Milestone:** v1.2 4S Compass

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Navigable, intuitive traversal of S3
**Current focus:** Corner compass widget showing 4D orientation

---

## Current Position

Phase: 7 (Compass Widget) -- Plan 1 complete
Plan: 07-01 done (lib/compass.py created)
Status: In progress -- 1/2 plans complete
Last activity: 2026-03-12 -- Completed 07-01 (compass module)

Progress: [█████░░░░░] 50%

---

## Accumulated Context

- v1.0 shipped with 3 phases, 9 plans, 20 commits (phases 1-3)
- v1.1 shipped with 3 phases, 6 plans (phases 4-6): traits, dialogue, reputation, persistence
- Post-v1.0: procedural planets, creature avatars, wandering eyes, Gamepedia, view modes, lib/ restructure
- Codebase: ~5,400 LOC Python
- Orientation frame: 4x4 orthogonal matrix (row 0 = camera, rows 1-3 = tangent basis)
- 4 view modes: Assigned, 4D Position, XYZ Projection, XYZ Fixed-Y
- Compass is for default view (mode 0) only
- New module: lib/compass.py with render_compass(screen, orientation, x, y, size) interface

---

## Key Decisions (v1.2)

| Decision | Rationale |
|----------|-----------|
| Compass rose + depth style | Familiar compass metaphor extended to 4D |
| XZ horizontal, Y vertical, W depth | Natural mapping: XZ = floor plan, Y = tilt, W = 4th dimension |
| Corner widget | Non-intrusive, always visible |
| Fixed axes reference | Shows absolute orientation on S3, not relative to travel target |
| Default view only | Keep scope small; other view modes have their own visual indicators |
| 2 phases (coarse) | Small milestone, tightly coupled requirements -- no benefit to splitting further |
| heading = atan2(-z_comp, x_comp) | +X = 0 and +Z = -pi/2, clockwise from above |
| tilt = arccos(abs(y_comp)) | Always non-negative regardless of Y sign |
| 200ms Lerp with shortest-path wraparound | Responsive feel, prevents spin past ±pi boundary |

---

## Critical Math Notes

- Compass MUST use fixed standard basis [1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1] -- never the player frame
- Extract angles via dot product with orientation[0] (camera direction), then arctan2
- Never reorthogonalize the reference axes -- they are exact constants
- Clamp dot products to [-1,1] before arccos to avoid NaN at axis alignment

---

## Session Continuity

**Last activity:** 2026-03-12 -- Completed 07-01-PLAN.md (lib/compass.py created)
**Next action:** Execute 07-02 (integrate render_compass into main.py)

---

**State initialized:** 2026-03-12
**Roadmap created:** 2026-03-12
