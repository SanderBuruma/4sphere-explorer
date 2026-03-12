# Feature Landscape: Creature Interactions & Relationships

**Domain:** Interactive exploration game with procedural NPCs
**Researched:** 2026-03-11
**Confidence:** MEDIUM overall (ecosystem well-established, but minimalist implementations less documented than AAA systems)

## Table Stakes

Features users expect for creature interaction to feel meaningful. Missing these = interaction feels hollow or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Creature traits visible on interaction** | Players want immediate personality impression — this is the hook that makes a creature memorable | Low | 2-4 core traits (friendly/hostile, curious/shy, aggressive/calm) shown visually or in text. Dwarf Fortress model: discrete facets with 0–100 values drive behavior. |
| **Procedural dialogue that varies by creature** | Static dialogue kills replayability. With 30k creatures, each must feel unique. | Medium | Tech Support: Error Unknown approach: traits modulate speech patterns (emoji usage, formality, tone). No LLM needed — template + trait modulation. |
| **Persistent state across revisits** | Creature remembers you visited. Revisits feel different from first encounter. | Low | Single counter per creature: "visited_count" or "last_relationship_change". Resets only on new game session. |
| **Relationship changes based on actions** | Interactions have consequences. No relationship system = interactions are cosmetic. | Low | Wildermyth/Fallout model: +/- points on interaction. Simplest: +1 for positive action, -1 for negative, threshold at ±5 for "liked/disliked" status. |
| **Creature reactions to relationship level** | Reputation should matter for gameplay, not just cosmetics. | Medium | High rep: creature grants bonuses (rare dialogue, audio boost, lore unlock). Low rep: creature becomes hostile or uncooperative. |

## Differentiators

Features that set interaction system apart. Not expected, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Seed-deterministic personality generation** | Every creature's personality is identical across playthroughs — enables sharing worlds, community personalities emerge | Low | Hash creature name/key into 4-8 trait scores (0–100). Deterministic from seed, no save state required. Creates consistent NPC societies. |
| **Rival/mentor relationships evolve over time** | Creatures you befriend become allies; enemies become nemeses that reappear. Wildermyth's dynamic nemesis system ported to exploration. | Medium | Compatibility algorithm: distance between trait vectors determines friendship/rivalry odds. Repeated interactions increase relationship points (linear accumulation). |
| **Trait-based dialogue variation** | Dialogue content changes based on creature traits, not just formatting. A curious creature asks YOU questions; a hostile one threatens. | Medium | Template library: "approach_curious", "approach_hostile", etc. Trait vector selects template. No template = fallback to generic. |
| **Procedural name-based lore hints** | Creature's generated name encodes history (existing naming system). Dialogue references name components. | Low | Decode name key to extract lore fragments (e.g., "ancient_creature" prefix → references age). Gamepedia topics can expand on name etymology. |
| **Relationship affects ambient audio** | A creature you befriend has warmer, friendlier soundscape. Hostile creatures have harsher tones. | Medium | Reuse existing audio synthesis: adjust timbre selection, scale, and tempo based on relationship_score instead of purely random. |
| **Creature social networks** | Creatures reference each other. "Have you met Axx'tar? We're rivals." Dialogue creates web of implied relationships. | Medium-High | Cross-reference creature name keys. Store lightweight "rumors" (X dislikes Y) derived from trait compatibility. Expensive: O(n) graph traversal per interaction. |

## Anti-Features

Features to deliberately NOT build, and why.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Full procedural dialogue generation (LLM-style)** | Adds cloud API dependency, latency, cost, loss of determinism. Overkill for indie solo project. | Use template + trait modulation (Tech Support: Error Unknown model). Write 20–30 templates that cover interaction states, select based on traits. |
| **Real-time dialogue branching trees** | Massive design debt. 30k creatures × 5+ dialogue options per state = exponential state space. Unmanageable. | Single-interaction approach: click creature → see traits + one dialogue response + relationship change. One transaction, move on. |
| **Multiplayer reputation (global server state)** | Project spec is solo exploration. Multiplayer reputation requires conflict resolution, cheating prevention, network sync. | Keep reputation local to save file. Community can share personality discoveries via Discord/wiki, but no shared state. |
| **Learning alien language progression** | No Man's Sky style: cool but requires designed vocabulary system, lore depth, NPC language generation. High complexity. | Skip this. Use English dialogue with trait-modulated tone/formality. Language as lore element in Gamepedia, not mechanic. |
| **Creature hiring / party system** | Scope creep: requires managing creature inventory, ability trees, combat synergies. Changes core exploration loop. | Interaction remains read-only: observe, gather lore, build relationships, but creatures stay on their points. |
| **Dynamic faction warfare** | Reputation between factions creates complex web of consequences. Fine for Fallout: New Vegas, too much for this scope. | Single creature-to-player reputation only. Avoid creature-to-creature competition that requires arbitration. |
| **Time-based reputation decay** | "Creatures forget you over time." Adds real-time game state persistence, session complexity. | Reputation locked once earned. No decay, no time pressure. If you visit in 1 year or 1 hour, reputation persists. |

## Feature Dependencies

```
Creature traits visible on interaction
    → Seed-deterministic personality generation (traits must be generated from seed)

Procedural dialogue varies by creature
    → Creature traits visible (dialogue selects templates based on traits)

Relationship changes on actions
    → Persistent state (must track visits/relationship counters per creature)
    → Creature reactions to relationship (changes must impact behavior)

Creature reactions to relationship
    → Relationship changes on actions (prerequisite)

Trait-based dialogue variation
    → Procedural dialogue varies by creature (prerequisite)

Rival/mentor relationships evolve
    → Relationship changes on actions (prerequisite)
    → Seed-deterministic personality (trait compatibility is seed-determined)
```

## MVP Recommendation

**Phase 1 (Prototype): Build these first**
1. **Seed-deterministic personality generation** — 4 core traits: Aggressive–Passive, Curious–Aloof, Friendly–Hostile, Brave–Fearful. Each 0–100, hash from creature name key.
2. **Traits visible in radial menu** — Display trait bars or text description (e.g., "Curious, Friendly, Brave") when you interact. Low effort, high impact.
3. **Persistent visit counter** — Track "visited_count" per creature. Reappear next time you visit. Foundation for relationship logic.
4. **Single procedural dialogue per interaction** — 3–5 templates per trait combination (e.g., "friendly_curious_approach"). Select based on traits. Single response, no branching.
5. **Simple +/- relationship on click** — Clicking a friendly creature +1 rep, hostile -1 rep. Show current rep in radial menu (0–10 scale, 5 = neutral).

**Why this order:**
- Traits are deterministic foundation; everything else builds on them.
- Traits visible immediately proves the system works and makes creatures memorable.
- Persistent state makes revisits meaningful.
- Single dialogue response keeps complexity manageable while proving the mechanic.
- Simple rep counter is minimum viable — players see consequences without branching tree debt.

**Defer to Phase 2:**
- Trait-based dialogue variation (more templates, more states) — wait for feedback on core mechanic
- Creature reactions to rep (gating/unlocking content) — once Phase 1 proves engagement
- Rival/mentor relationships — complexity emerges from Phase 1 feedback
- Relationship affects audio — nice-to-have, add after Phase 1 stabilizes
- Creature social networks — high complexity, defer to Phase 3 or later

## Complexity Breakdown

| Feature | Implementation Effort | Risk | Test Coverage Needed |
|---------|----------------------|------|----------------------|
| Seed-deterministic traits | 30 minutes (hash function + trait scoring) | Low | Unit tests: seed→traits determinism, value ranges |
| Traits display | 1 hour (update radial menu layout) | Low | Visual: trait text rendering, tooltip layout |
| Visit counter | 30 minutes (add counter to creature state, save/load) | Low | Tests: persistence across sessions, counter increments |
| Procedural dialogue (5 templates) | 2–3 hours (write templates, select logic) | Low | Tests: all trait combinations produce valid dialogue |
| Simple reputation system | 1 hour (counter, threshold logic) | Low | Tests: +/- on action, threshold crossing, display |
| **Phase 1 Total** | **5–6 hours** | **Low** | **Manageable** |

## Sources

- [Dwarf Fortress personality system: Personality facets determine NPC behavior and relationship compatibility](https://dwarffortresswiki.org/index.php/DF2014:Personality_trait)
- [Wildermyth relationship algorithm: trait compatibility drives friendship/rivalry with dynamic evolution](https://wildermyth.com/wiki/Relationship)
- [Tech Support: Error Unknown approach to procedural dialogue: traits modulate speech patterns](https://www.gamedeveloper.com/design/developing-a-procedural-dialogue-system-for-tech-support-error-unknown)
- [No Man's Sky minimal dialogue through language learning rather than branching trees](https://nomanssky-archive.fandom.com/wiki/Procedural_generation)
- [Cultist Simulator: minimalist card-based narrative emphasizes spaces between actions, not dialogue trees](https://intothespine.com/2018/04/24/interview-cultist-simulator-speedrunning-and-minimalistic-narrative/)
- [Seed-based procedural generation: deterministic from seed enables sharing and community discovery](https://generalistprogrammer.com/procedural-generation-games)
- [Star Traders: Frontiers reputation system: multiple independent faction counters with swift penalty/reward](https://gamerant.com/best-reputation-mechanics-rpgs/)
- [Game design exploration table stakes: discovery and meaningful consequences require self-direction and rewards](https://medium.com/black-shell-media/lets-take-a-look-at-the-four-types-of-exploration-in-game-design-ac9d6a679304)
- [Procedural dialogue generation GitHub: Ubisoft/independent approaches using template + trait modulation](https://github.com/JosselinSomervilleRoberts/Procedural-Dialog-Generation)
- [NPC generator tools and trait databases: 600–1000+ trait combinations common in indie design](https://www.skullrpg.com/personality-traits/)
