# Phase 5 Context: Reputation & Dialogue

**Phase Goal**: Creatures respond to the player with trait-appropriate dialogue, and their tone changes based on how many times they have been visited and interacted with
**Requirements**: DIAL-01, DIAL-02, REP-01, REP-02, REP-03

---

## Decisions

### 1. Dialogue Trigger (radial menu)

**Approach**: Add a "Talk" wedge to the existing radial menu (top position, wedge index 3). Clicking Talk on any creature triggers dialogue generation and display.

**Why not auto-on-arrival**: Feels intrusive during rapid exploration. Players should opt into conversations.

**Why not extend detail panel**: Dialogue is an action (reputation changes), not just viewing — deserves its own trigger.

### 2. Template System Design (DIAL-01)

**Structure**: Templates are short strings with `{slots}` filled by trait-influenced word banks.

```
"{greeting}, traveler. {body} {farewell}"
```

**Template pools**: Grouped by reputation tier (5 tiers: stranger, acquaintance, familiar, friend, devoted). Each tier has 4-6 templates. Trait axes bias word selection within slots:
- friendly_hostile → greeting warmth, farewell tone
- curious_aloof → body topic (asks questions vs. makes statements)
- aggressive_passive → verb intensity
- brave_fearful → confidence modifiers

**Total**: ~25 base templates × trait word banks → thousands of effective combinations. Deterministic: same creature + same reputation = same dialogue (seeded by name_key + reputation score).

### 3. Dialogue Display

**Location**: Speech bubble above the creature in the viewport, or overlay text panel near the creature's screen position. Fades after 4-5 seconds or on next click.

**Fallback**: If creature isn't on screen, show dialogue in a centered text overlay.

### 4. Reputation Model (REP-01, REP-02)

**Score**: Integer 0-10, starts at 0.
**Storage**: `dict[int, dict]` mapping point index → `{"score": int, "visits": int, "last_visit": int}`. Sparse — only populated on interaction.
**Actions**:
- First visit: score +1, visits +1
- Talk: score +1 (once per visit)
- No hostile actions in Phase 5 scope

**Tier thresholds** (REP-03):
| Score | Tier | Effect |
|-------|------|--------|
| 0 | Stranger | Wary tone, minimal dialogue |
| 1-2 | Acquaintance | Neutral, brief |
| 3-5 | Familiar | Warm, conversational |
| 6-8 | Friend | Enthusiastic |
| 9-10 | Devoted | Affectionate |

### 5. Reputation Display (visible in radial menu info panel)

**Location**: Detail panel (Info wedge) — add reputation score and tier label below trait bars.
```
Reputation: ★★★★★☆☆☆☆☆ (5/10) — Familiar
Visits: 12
```

### 6. Visit Tracking (REP-01)

**When counted**: Travel completion (arrival snap). Increment visit count in reputation store. First visit also grants +1 reputation.

**Integration point**: The travel completion block in main.py (line ~481-502 area where `ARRIVAL_THRESHOLD` check happens).

---

## Code Context

**Radial menu**: `main.py:862-905` — 4 wedges, only wedge 0 ("Info") active. Wedges A/B/C at indices 1,2,3 are placeholders.

**Detail panel**: `main.py:907-1007` — renders name, distance, coords, audio, traits. Reputation display extends this.

**Travel completion**: `main.py:481` — `angular_distance < ARRIVAL_THRESHOLD` triggers snap. Visit tracking hooks here.

**Trait system**: `lib/traits.py` — `generate_traits(name_key)` returns dict of 4 axes. Dialogue system consumes these.

**Name keys**: `_name_keys` array in main.py — `int` keys per point, used for all seeded generation.

---

## Deferred Ideas

- Hostile actions (attack/ignore options) — future phase
- Reputation decay over time — unnecessary complexity for prototype
- Creature-to-creature relationships — out of scope
- Dialogue history / memory — save for persistence phase

---
*Created: 2026-03-11*
