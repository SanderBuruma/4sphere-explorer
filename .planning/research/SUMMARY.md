# Research Summary: Creature Interaction Systems for 4-Sphere Explorer

**Domain:** Procedural dialogue, trait-based personalities, and reputation systems in exploration games
**Researched:** 2026-03-11
**Overall Confidence:** MEDIUM — Ecosystem well-documented (Dwarf Fortress, Wildermyth, indie studios); minimalist implementations in solo projects less published. Recommendation grounded in real game analysis but needs Phase 1 validation.

## Executive Summary

Exploration games don't need complex dialogue systems or LLM APIs. The proven pattern is **seed-deterministic personality traits that modulate dialogue templates**, paired with simple per-creature reputation counters. Dwarf Fortress uses discrete trait facets (0–100 per axis) driving emergent behavior; Wildermyth uses trait compatibility to generate friendships/rivalries dynamically; Tech Support: Error Unknown varies speech patterns procedurally by customer personality.

For 4-Sphere Explorer's 30,000 creatures, the smart approach avoids dialogue debt:
1. Hash creature name/key into 4 personality trait axes (Aggressive–Passive, Curious–Aloof, Friendly–Hostile, Brave–Fearful), each 0–100
2. Build 20–30 dialogue templates grouped by trait combinations
3. Store a single 0–10 reputation counter per creature (no decay, no faction logic)
4. Display traits in radial menu on interaction; select dialogue from trait vector
5. Apply reputation delta (+1 friendly, -1 hostile) on player action

This is **minimalist but coherent**: avoids LLM dependency/latency, avoids exponential dialogue tree state space, and integrates cleanly with existing procedural generation (name keys, audio seeds). Proven by Wildermyth (personality + compatibility = engagement), Dwarf Fortress (trait facets drive emergent play), and indie procedural games (template + modulation scales to thousands of NPCs).

**Anti-patterns to avoid:** Full LLM dialogue (adds cloud dependency, breaks determinism), real-time branching dialogue trees (exponential complexity with 30k creatures), multiplayer reputation (solo game scope).

## Key Findings

**Stack:** Traits from seed hash (4 axes, 0–100) + template selection (20–30 dialogue variations per trait vector) + reputation counter (0–10 per creature). No new dependencies; reuse stdlib `random` and `json` (already used for creature/planet/audio generation).

**Architecture:** Each creature stores `{traits: [aggressive, curious, friendly, brave], visited_count, reputation}`. On interaction: display traits in radial menu, select dialogue template from trait vector, apply reputation delta. Reuse existing name/audio seeds for determinism—this is core to the 4-Sphere Explorer ethos.

**Critical pitfall:** Dialogue branching (even simple 3-node trees per state) becomes exponentially complex with 30k creatures. Template + modulation avoids this. Dwarf Fortress insight: personality as discrete facets drives behavior without explicit branching.

## Implications for Roadmap

Research suggests a **three-phase rollout** with clear dependency management:

### Phase 1: Trait Foundation (5–6 hours, LOW risk)
**Goal:** Prove seed-deterministic traits + template dialogue feel good.

**Features:**
- Seed-deterministic trait generation (hash creature name → 4 trait scores, 0–100)
- Traits display in radial menu (visual proof of uniqueness per creature)
- Visit counter persistence (foundation for reputation system)
- Simple procedural dialogue (5–10 templates covering main trait combinations)
- Basic reputation counter (+1 on friendly action, -1 on hostile, shown in menu)

**Addresses table stakes:**
- "Creature traits visible on interaction" — proves uniqueness
- "Procedural dialogue varies by creature" — trait-driven template selection
- "Persistent state across revisits" — visit counter + reputation storage

**Avoids pitfall:** Not building full dialogue branching system before validating trait vector works

**Depends on:** Existing radial menu, name/seed infrastructure (already built)

### Phase 2: Relationship Evolution (2–3 weeks, MEDIUM risk)
**Goal:** Extend Phase 1 reputation into meaningful creature reactions.

**Features:**
- Threshold-based creature reactions (high rep → helpful tone, low rep → evasive/hostile)
- Trait-based dialogue variation (more templates, grouping by trait combinations not just trait vector)
- Optional: Relationship affects audio palette (warmer timbre for liked creatures, harsher for disliked)

**Addresses differentiators:**
- "Creature reactions to relationship level" — gating dialogue/mechanics based on rep
- "Relationship changes based on actions" — deepens Phase 1 counter system

**Defers:** Complex features until Phase 1 feedback validates engagement

**Risk:** Dialogue template volume. Start with ~20 templates, expand based on playtest feedback.

### Phase 3: Social Depth (3–4 weeks, HIGH risk)
**Goal:** Optional advanced features — rival/mentor relationships, creature networks.

**Features:**
- Rival/mentor relationships (Wildermyth compatibility algorithm: trait distance drives friendship/rivalry)
- Creature social networks (cross-references in dialogue; implied relationships)
- Relationship evolution over time (compatibility score drives faster point accumulation)

**Addresses differentiators:**
- "Rival/mentor relationships evolve over time"
- "Creature social networks" (high complexity; needs Phase 1 validation first)

**Defers:** Validate Phase 1/2 engagement before committing to this complexity.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Seed-deterministic trait generation | HIGH | Proven by Dwarf Fortress, Wildermyth, Minecraft seeds. Determinism from seed is established pattern. |
| Template + trait modulation dialogue | MEDIUM | Proven by Tech Support: Error Unknown, procedural narrative community. Less documented than LLM approaches, but sufficient for exploration scale. Needs playtesting to validate feel. |
| Simple reputation counter system | HIGH | Used in Star Traders, Fallout series, Wildermyth. Well-understood pattern, low implementation complexity. |
| Avoiding dialogue trees | MEDIUM | Strong indie consensus (Emily Short, procedural narrative GDC talks), but requires discipline. Risk: scope creep into branching. |
| Trait→dialogue template selection works at 30k scale | MEDIUM | Logic is straightforward; needs validation via playtest. Memory/performance not a concern (traits are lightweight vectors). |
| Phase 1 5–6 hour estimate | MEDIUM | Assumes existing radial menu framework, name/seed infrastructure intact. No major refactoring. May slip if integration points are tangled. |

## Gaps to Address

**In Phase 1 prototyping:**
- How many dialogue templates are "enough"? Initial research suggests 5–20 per trait combo; feedback will tell.
- Do procedural traits feel mechanically distinct or do they blur together in practice?
- Does trait display in menu reduce mystery or increase intrigue? (Design question, not technical.)

**In Phase 2+:**
- Relationship decay: Should reputation fade over time? (Defer decision to Phase 1 feedback.)
- Creature memory: Should creatures reference your past actions in dialogue? (Requires interaction history tracking, higher complexity.)
- Audio integration: Feasible within existing synthesis, or scope creep?

**Not researched (recommend Phase-specific investigation):**
- Dialogue template authoring: What's the simplest format (JSON, YAML, procedural code)?
- Performance validation: Does 30k creatures × {traits, visited_count, reputation} impact save file size or memory?
- Test coverage: How to systematically test trait generation, template selection, reputation math?

## Phase-Specific Research Flags

| Phase | Topic | Flag | Why |
|-------|-------|------|-----|
| Phase 1 | Dialogue template structure | YES | Define syntax (token substitution, fallback handling, etc.) before writing 20+ templates |
| Phase 1 | Trait value interpretation | YES | Are 0–100 ranges optimal, or should they be discrete buckets (low/med/high)? Impacts template selection logic. |
| Phase 2 | Reputation thresholds | YES | What values trigger reactions? (-5 / 0 / +5?) Needs playtesting to tune. |
| Phase 3 | Compatibility algorithm | YES | Wildermyth's is complex; simplify or port? High risk if left unresolved. |

## Sources

Research draws from real games and documented systems:
- [Dwarf Fortress personality facets: discrete personality values drive emergent social behavior](https://dwarffortresswiki.org/index.php/DF2014:Personality_trait)
- [Wildermyth relationship algorithm: trait compatibility + charisma determine relationship evolution](https://wildermyth.com/wiki/Relationship)
- [Tech Support: Error Unknown: procedural dialogue via trait-modulated speech patterns](https://www.gamedeveloper.com/design/developing-a-procedural-dialogue-system-for-tech-support-error-unknown)
- [No Man's Sky: minimal dialogue via language learning, not branching trees](https://nomanssky-archive.fandom.com/wiki/Procedural_generation)
- [Cultist Simulator: minimalist narrative design emphasizes gaps, not exhaustive dialogue](https://intothespine.com/2018/04/24/interview-cultist-simulator-speedrunning-and-minimalistic-narrative/)
- [Emily Short procedural narrative research: NLG techniques and template + modulation patterns](https://github.com/jd7h/nlg-games)
- [Seed-based procedural generation: deterministic from seed enables community discovery and reproducibility](https://generalistprogrammer.com/procedural-generation-games)

---
*Last updated: 2026-03-11 as Phase 1 research foundation for v1.1 milestone*
