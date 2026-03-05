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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 | 20 | 3 | Initial milestone, coarse granularity, yolo mode |

### Cumulative Quality

| Milestone | Tests | LOC | Key Files |
|-----------|-------|-----|-----------|
| v1.0 | test_sphere.py | 2,172 | main.py, sphere.py, audio.py |

### Top Lessons (Verified Across Milestones)

1. (First milestone -- lessons to be verified in future milestones)
