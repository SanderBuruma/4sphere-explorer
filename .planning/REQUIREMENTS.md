# Requirements: v1.1 Gameplay Prototype

**Milestone:** v1.1 Gameplay Prototype
**Created:** 2026-03-11
**Status:** Defining

---

## v1.1 Requirements

### Traits

- [ ] **TRAIT-01**: Each creature has 4 seed-deterministic personality axes (aggressive-passive, curious-aloof, friendly-hostile, brave-fearful) scored 0-100
- [ ] **TRAIT-02**: Creature traits are displayed in the radial menu info panel
- [ ] **TRAIT-03**: Creature appearance/behavior subtly reflects personality traits (visual cues)

### Dialogue

- [ ] **DIAL-01**: Creatures produce procedural dialogue selected from templates based on their trait combination
- [ ] **DIAL-02**: Dialogue tone shifts based on reputation level (friendly at high rep, evasive/hostile at low rep)

### Reputation

- [ ] **REP-01**: Each creature tracks how many times the player has visited
- [ ] **REP-02**: Each creature has a reputation score (0-10) that changes based on player actions
- [ ] **REP-03**: Creatures react differently at reputation thresholds (behavior/dialogue changes)

### Persistence

- [ ] **SAVE-01**: Game state (reputation, visit counts, player position) saves to and loads from disk

---

## Future Requirements

- Trait compatibility between creatures (rival/mentor relationships)
- Creature social networks (cross-references in dialogue)
- Reputation affects audio timbre (warmer for liked, harsher for disliked)
- Creatures reference past actions in dialogue
- Relationship decay over time

## Out of Scope

- LLM-generated dialogue — breaks determinism, adds API dependency, unnecessary cost
- Branching dialogue trees — exponential complexity at 30k creature scale
- Multiplayer reputation — solo exploration experience
- Faction systems — keep reputation per-creature, not grouped

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| TRAIT-01 | Phase 4 | — | Pending |
| TRAIT-02 | Phase 4 | — | Pending |
| TRAIT-03 | Phase 4 | — | Pending |
| DIAL-01 | Phase 5 | — | Pending |
| DIAL-02 | Phase 5 | — | Pending |
| REP-01 | Phase 5 | — | Pending |
| REP-02 | Phase 5 | — | Pending |
| REP-03 | Phase 5 | — | Pending |
| SAVE-01 | Phase 6 | — | Pending |

---
*Last updated: 2026-03-11*
