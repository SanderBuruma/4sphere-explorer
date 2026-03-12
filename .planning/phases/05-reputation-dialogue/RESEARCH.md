# Research: Phase 5 — Reputation & Dialogue

## Domain Analysis

### Dialogue Template Systems in Procedural Games

**Proven approach:** Template strings with slot-filling, used by Dwarf Fortress, Caves of Qud, RimWorld. Templates are grouped by mood/relationship tier, with trait-specific word banks injected into slots.

**Key design principles:**
- Templates per relationship tier (stranger → acquaintance → friend → ally / rival → enemy)
- Trait axes select word banks (e.g., aggressive creatures use harsher verbs, curious creatures ask questions)
- 2-3 template pools per tier × 4 trait influence dimensions = enough variation without combinatorial explosion
- Greeting + body + farewell structure keeps lines short and composable

**Template count estimate:** ~20-30 base templates across 5 reputation tiers, with trait-specific word substitutions yielding thousands of effective combinations from a small template set.

### Reputation Systems at Scale

**Challenge:** 30,000 creatures × per-creature reputation = memory concern.

**Solution:** Sparse storage — only creatures the player has actually interacted with get reputation entries. Default reputation for unvisited creatures is 0 (neutral/stranger). At typical play rates (visiting ~100-500 creatures per session), this stays well under 1MB even with full persistence.

**Scoring models considered:**
1. **Simple counter (0-10):** Visit increments, hostile actions decrement. Matches REQUIREMENTS.md spec (REP-02).
2. **Decaying reputation:** Score drifts toward neutral over time. Adds complexity for unclear benefit at prototype stage.
3. **Event-based delta:** Each action type has a fixed +/- delta. Clean, predictable, testable.

**Chosen:** Event-based delta with integer score 0-10, clamped. Simple enough for prototype, extensible later.

### Interaction Trigger Design

**Current state:** Radial menu has "Info" wedge (right) active, wedges A/B/C are placeholders. The "Info" wedge opens the detail panel.

**Options for dialogue trigger:**
1. **New radial wedge "Talk"** — adds dedicated interaction wedge. Clear separation between viewing info and interacting.
2. **Auto-dialogue on arrival** — show dialogue when travel completes. Passive but may feel intrusive.
3. **Dialogue in detail panel** — extend existing panel with talk button/section. Keeps UI consolidated.

**Chosen:** New radial wedge "Talk" (top wedge). Clean separation, uses existing menu infrastructure, leaves room for future wedges (Trade, etc.).

### Player Actions for Reputation

**What actions change reputation?**
- **Visit** (+1 on first visit, then +0 for repeat visits within same session — prevents farming)
- **Talk** (+1 per conversation, up to once per visit)
- **Hostile action** (future: -2, but no hostile actions exist yet in Phase 5 scope)

For Phase 5 prototype: visiting a creature and talking to it are the two positive actions. Hostile actions deferred to future phases. Score starts at 0, max 10.

### Reputation Thresholds

| Score | Tier | Dialogue Tone |
|-------|------|---------------|
| 0 | Stranger | Wary, minimal |
| 1-2 | Acquaintance | Neutral, brief |
| 3-5 | Familiar | Warm, conversational |
| 6-8 | Friend | Enthusiastic, helpful |
| 9-10 | Devoted | Affectionate, reveals secrets |

5 tiers provide enough dialogue variety to be noticeable without requiring too many templates.

## Architecture Decisions

### Data Flow

```
name_key → generate_traits() → trait dict (existing)
                                    ↓
player_action + trait_dict + reputation → select_template() → dialogue string
                                    ↓
reputation_store[point_idx] → update on action → display in panel
```

### File Organization

- `lib/dialogue.py` — Template pools, slot-filling, dialogue generation
- `lib/reputation.py` — Reputation store (dict), tier calculation, action handlers
- `main.py` — "Talk" wedge handler, dialogue display UI, reputation display in panel

### Testing Strategy

- `tests/test_dialogue.py` — Template selection varies with traits, tier affects tone, deterministic for same inputs
- `tests/test_reputation.py` — Score clamping, tier boundaries, action deltas, sparse storage

---
*Researched: 2026-03-11*
