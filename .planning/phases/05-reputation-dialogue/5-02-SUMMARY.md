---
phase: 5
plan: 02
subsystem: dialogue
tags: [dialogue, traits, reputation, procedural]
dependency_graph:
  requires: [lib/traits.py]
  provides: [lib/dialogue.py]
  affects: [main.py (future integration)]
tech_stack:
  added: []
  patterns: [template-based procedural text, trait-to-temperature mapping, md5 seeding]
key_files:
  created: [lib/dialogue.py, tests/test_dialogue.py]
  modified: []
key_decisions:
  - "24 templates across 5 tiers (4-5 per tier) with 5 word bank dimensions"
  - "Trait 0-33/34-66/67-100 temperature bucketing matches plan spec"
  - "md5 hash of (name_key + reputation_score) bytes for deterministic seeding"
  - "8 lore snippets about S3 geometry for devoted tier"
metrics:
  duration: "2m 14s"
  completed: "2026-03-11T20:22:00Z"
  tasks_completed: 5
  tasks_total: 5
  tests_added: 44
  tests_passed: 44
---

# Phase 5 Plan 02: Dialogue System Summary

Template-based procedural dialogue with 24 templates across 5 reputation tiers, trait-influenced word bank selection (greetings/body/verbs/adverbs/farewells), and 8 lore snippets for devoted-tier creatures.

## What Was Built

### lib/dialogue.py (215 lines)
- `generate_dialogue(name_key, traits, reputation_score)` -- deterministic dialogue from creature identity
- `_reputation_tier(score)` -- maps 0-10 score to 5 tiers (stranger/acquaintance/familiar/friend/devoted)
- `_trait_temp(value)` -- maps 0-100 trait value to low/neutral/high temperature
- `TEMPLATES` dict with 24 templates (4 stranger, 5 each for other tiers)
- 5 word banks with 3 temperature levels each (3-4 phrases per level)
- `LORE_SNIPPETS` list with 8 entries about 4D geometry and S3 properties

### tests/test_dialogue.py (305 lines, 44 tests)
- Tier mapping (9 tests), trait temperature (3 tests)
- Template/word bank coverage (9 tests)
- Determinism (2 tests), variation (2 tests)
- Trait influence: friendly vs hostile, curious vs aloof (2 tests)
- Tier shift: stranger vs familiar/devoted (2 tests)
- All tiers produce output (5 parametrized tests)
- Edge cases: extreme traits, clamped scores, missing keys, large name_key (8 tests)
- Lore presence in devoted, absence in stranger (2 tests)

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| 24 templates (not 25+) | 4 stranger + 5x4 other = 24; adding padding templates would be filler |
| md5 of concatenated bytes | Same approach as traits.py; avoids coupling with creature RNG |
| Word bank temps match trait axes directly | friendly_hostile -> greetings/farewells, curious_aloof -> body, etc. |
| Lore only in devoted tier templates | Only devoted templates contain {lore} slot; no leakage to other tiers |

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 596d2ef | feat(5-02): add procedural dialogue generation module |
| d64019f | test(5-02): add dialogue generation tests (44 tests) |

## Acceptance Criteria Status

- [x] SC-1: Dialogue differs across creatures with different trait combos (verified by TestTraitInfluence)
- [x] SC-2: Different reputation scores produce different tone (verified by TestTierShift)
- [x] Dialogue is deterministic for same inputs (verified by TestDeterminism)
- [x] Templates cover all 5 reputation tiers (verified by TestTemplates, TestAllTiersCovered)

## Self-Check: PASSED

All files verified present, all commits verified in git log.
