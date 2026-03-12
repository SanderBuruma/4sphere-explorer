---
phase: 5
plan: 03
subsystem: UI / Dialogue / Reputation
tags: [ui, dialogue, radial-menu, speech-bubble, gamepedia]
key-files:
  created:
    - lib/traits.py
  modified:
    - main.py
    - lib/constants.py
    - lib/gamepedia.py
    - tests/test_gamepedia.py
decisions:
  - Added Dialogue and Reputation as topics under World group (not new group)
  - Trait module (lib/traits.py) carried forward as untracked prerequisite from phase 4
metrics:
  duration: "4m 22s"
  completed: "2026-03-11"
  tasks: 7/7
  tests: 204
---

# Phase 5 Plan 03: UI Integration Summary

Talk wedge in radial menu triggers trait-based dialogue with speech bubble display and auto-greet on first visit

## What Was Done

1. **DIALOGUE_DURATION and DIALOGUE_FADE constants** added to `lib/constants.py` (5000ms display, 1000ms fade)

2. **Talk wedge activated** in radial menu (index 3, top position) with warm yellow color (255, 200, 100). Release handler calls `generate_traits()`, `get_reputation()`, `record_talk()`, and `generate_dialogue()` to produce dialogue line.

3. **Dialogue display state** variables added: `dialogue_text`, `dialogue_show_time`, `dialogue_point_idx`, plus `rep_feedback_text`/`rep_feedback_time` for reputation feedback.

4. **Speech bubble rendering**: semi-transparent rounded rect with border in creature's display color, word-wrapped text via `word_wrap_text()`, triangle pointer toward creature, and fade-out during final DIALOGUE_FADE ms. When creature is off-screen, shows centered overlay.

5. **Dialogue-on-arrival**: first visit (visits==0 before arrival) auto-generates stranger-tier greeting. Captures reputation state before `record_visit()` to detect first visits.

6. **Reputation change feedback**: "+1 ★" in gold text that floats upward and fades over 1 second, shown when score changes from visit or talk.

7. **Gamepedia updated**: added Dialogue and Reputation topics under World group (22 total topics, up from 20). Updated Mouse controls and Detail Panel entries to mention Talk wedge. Test counts updated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] lib/traits.py missing from worktree**
- **Found during:** Pre-execution setup
- **Issue:** `lib/traits.py` was untracked in main repo (from phase 4 trait system), not committed to git, so not available in worktree after merge
- **Fix:** Created `lib/traits.py` in worktree from main repo content
- **Files modified:** lib/traits.py (new)
- **Commit:** 5fa58af

## Commits

| Hash | Description |
|------|-------------|
| 5fa58af | feat(5-03): add dialogue constants and traits module |
| 626f721 | feat(5-03): add Talk wedge, dialogue display, and auto-greet on arrival |
| e387157 | feat(5-03): add Dialogue and Reputation gamepedia topics |

## Acceptance Criteria

- [SC-1] Talk wedge in radial menu produces visible dialogue that varies by creature -- DONE (traits + reputation seed dialogue selection)
- [SC-2] First-visit auto-greeting differs from high-reputation Talk dialogue -- DONE (auto-greet uses score=0/stranger tier)
- [SC-3] Reputation score visible and changes after Talk action -- DONE (detail panel shows stars, +1 feedback on change)
- [SC-4] Tier label changes at defined thresholds -- DONE (detail panel shows tier name from get_tier())
- Gamepedia documents new features -- DONE (2 new topics, 2 entries updated)

## Test Results

All 204 tests passed (including 12 gamepedia tests with updated counts, 44 dialogue tests, 30 reputation tests).
