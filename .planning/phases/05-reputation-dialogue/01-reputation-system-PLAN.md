# Plan 01: Reputation System

**Phase:** 5 — Reputation & Dialogue
**Requirements:** REP-01, REP-02, REP-03
**Goal:** Each creature tracks visits and has a reputation score (0-10) that changes based on player actions, with observable tier-based behavior changes

---

## Tasks

### 1. Create `lib/reputation.py` — reputation data module

New file with:

```python
REPUTATION_TIERS = [
    (0, 0, "Stranger"),
    (1, 2, "Acquaintance"),
    (3, 5, "Familiar"),
    (6, 8, "Friend"),
    (9, 10, "Devoted"),
]

def get_tier(score: int) -> str:
    """Return tier name for reputation score."""

def get_reputation(store: dict, idx: int) -> dict:
    """Return reputation entry for point idx, or default {score:0, visits:0}."""

def record_visit(store: dict, idx: int) -> dict:
    """Increment visit count. First visit: +1 reputation. Returns updated entry."""

def record_talk(store: dict, idx: int) -> dict:
    """Grant +1 reputation for talking (once per visit, tracked via 'talked_this_visit' flag).
    Returns updated entry."""

def reset_visit_flags(store: dict):
    """Clear 'talked_this_visit' flags for all entries (call at session start or when
    leaving a creature's vicinity — prevents farming)."""
```

**Storage:** `store` is a plain `dict[int, dict]` passed in from main.py. Each entry:
```python
{
    "score": int,     # 0-10, clamped
    "visits": int,    # total visit count
    "talked_this_visit": bool,  # prevents talk-farming within one visit
}
```

Score clamped to [0, 10] on every mutation. Sparse — default for missing idx is `{"score": 0, "visits": 0, "talked_this_visit": False}`.

### 2. Hook visit tracking into travel completion (`main.py`)

In the travel completion block (where `angular_distance < ARRIVAL_THRESHOLD`):
- Import `record_visit` from `lib/reputation`
- Call `record_visit(reputation_store, travel_target_idx)` on arrival
- Add `reputation_store = {}` to global state near other game state vars

### 3. Add reputation display to detail panel (`main.py`)

Below the trait bars in the detail panel, add:
```
Reputation: ★★★★★☆☆☆☆☆ Familiar (5/10)
Visits: 12
```

- Stars rendered as filled/empty using score out of 10
- Tier name from `get_tier(score)`
- Visit count from `reputation_store[idx]["visits"]`
- For unvisited creatures (not in store): show "Stranger (0/10)" with 0 visits

Update `panel_h` to accommodate 2 new lines.

### 4. Reset talk flags on departure

When the player starts traveling to a new target (travel initiation), call `reset_visit_flags(reputation_store)` or just reset the flag for the creature being left. Simpler: reset `talked_this_visit` for ALL entries when travel starts — prevents any farming exploits.

Actually simpler: just reset the flag for the specific creature when the player arrives at a new target. In `record_visit`, set `talked_this_visit = False` for the newly visited creature.

### 5. Add tests (`tests/test_reputation.py`)

- `record_visit` increments visits, first visit adds +1 score
- `record_visit` on repeat visit: visits increments, score unchanged
- `record_talk` grants +1, second talk in same visit: no change
- Score clamping: never goes below 0 or above 10
- `get_tier` returns correct tier name at all boundaries (0, 1, 2, 3, 5, 6, 8, 9, 10)
- `get_reputation` returns default for unknown idx
- Sparse: store only contains entries for interacted creatures

---

## Acceptance Criteria (maps to success criteria)

- [SC-3] Reputation score visible in detail panel (radial menu Info), changes on visit/talk
- [SC-4] At defined thresholds, tier label changes (observable without internal state)
- Visit count tracks correctly across multiple visits
- Score never exceeds [0, 10] bounds

---

## Files Modified

| File | Change |
|------|--------|
| `lib/reputation.py` | **NEW** — reputation store, tier calc, action handlers |
| `main.py` | Global `reputation_store`, visit hook in travel completion, reputation display in detail panel |
| `tests/test_reputation.py` | **NEW** — reputation logic tests |
