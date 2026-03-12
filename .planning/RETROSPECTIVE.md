# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 -- Explorer MVP

**Shipped:** 2026-03-05
**Phases:** 3 | **Plans:** 9 | **Commits:** 20

### What Was Built
- KDTree spatial indexing replacing O(n) visibility scan
- Bookmark system, real-time search, Tab auto-travel
- Visual polish: glow halos, parallax starfield, travel line, breadcrumb trail
- Radial menu with detail panel (4D coords, audio params, planet sprite)
- Exploration statistics overlay

### What Worked
- Coarse granularity (3 phases) kept momentum high -- entire milestone shipped in a single day
- Budget model profile was sufficient for planning at this project scale
- Auto-advance chain (yolo + auto) eliminated approval bottlenecks
- Phase 1 foundation (spatial indexing) cleanly enabled Phase 2+3 features

### What Was Inefficient
- Traceability table in REQUIREMENTS.md fell behind after Phase 1 -- only 3/10 marked complete despite all being shipped
- INFO-02 (stats overlay) requirement was addressed implicitly but not as a dedicated plan

### Patterns Established
- SRCALPHA surfaces for glow/transparency effects in Pygame
- Click-hold radial menu pattern for contextual interactions
- Deterministic RNG replay for parameter extraction (audio.py get_audio_params)

### Key Lessons
1. Traceability updates should happen per-phase, not just per-plan
2. Coarse granularity works well for solo developer projects with clear scope

### Cost Observations
- Model mix: 0% opus, 0% sonnet (planning only), 100% budget
- Sessions: ~3 (planning, execution, polish)
- Notable: Budget profile sufficient for well-scoped pygame project

---

## Milestone: v1.2 -- 4S Compass

**Shipped:** 2026-03-12
**Phases:** 2 | **Plans:** 3

### What Was Built
- lib/compass.py: 4D angle math (heading/tilt/W-depth) against fixed standard basis
- Three-indicator widget: compass rose with Lerp needle, vertical tilt bar, W-depth gauge
- Conditional rendering: compass hidden during Gamepedia and non-default view modes
- Gamepedia Compass topic documenting all indicators

### What Worked
- Full auto-advance chain (discuss → plan → execute) ran both phases without intervention
- Splitting into 2 phases (module creation → integration) cleanly separated concerns
- Phase 8 was trivially small (1 conditional) — could have been part of Phase 7, but the separation kept each phase's scope unambiguous

### What Was Inefficient
- Research agent was spawned for Phase 8 despite it being a single-line change — could have used --skip-research
- discuss-phase for Phase 8 had no meaningful gray areas — auto-generated CONTEXT.md without user interaction

### Patterns Established
- Module-level Lerp animation state with delta-time tracking (no clock parameter needed)
- Widget surface pattern: create SRCALPHA surface, draw, blit to screen
- Fixed standard basis axes as module constants (never derived from player frame)

### Key Lessons
1. For trivial phases (< 3 lines of code), --skip-research saves a subagent spawn
2. Auto-advance through discuss-phase works well even when skipping discussion (creates minimal CONTEXT.md)
3. Coarse 2-phase milestones ship fast — entire milestone in one session

### Cost Observations
- Model mix: sonnet (executors, planner), haiku (researcher, checker)
- Sessions: 1 (full auto-advance pipeline)
- Notable: Entire milestone from research to ship in ~15 minutes

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 | 20 | 3 | Initial milestone, coarse granularity, yolo mode |
| v1.1 | ~12 | 3 | Gameplay layer (traits, dialogue, persistence) |
| v1.2 | 10 | 2 | Full auto-advance chain, smallest milestone yet |

### Cumulative Quality

| Milestone | Tests | LOC | Key Files |
|-----------|-------|-----|-----------|
| v1.0 | test_sphere.py | 2,172 | main.py, sphere.py, audio.py |
| v1.1 | +test_traits, test_eye_tracking | ~5,400 | +lib/traits.py, lib/dialogue.py |
| v1.2 | +test_gamepedia updates | ~7,500 | +lib/compass.py |

### Top Lessons (Verified Across Milestones)

1. Coarse granularity (2-3 phases) ships fast for solo projects — verified v1.0, v1.1, v1.2
2. Auto-advance chain eliminates approval bottlenecks — verified v1.0, v1.2
3. Budget/haiku models sufficient for research and checking at this project scale — verified v1.0, v1.2
