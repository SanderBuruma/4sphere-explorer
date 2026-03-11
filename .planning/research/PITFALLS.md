# Domain Pitfalls: Creature Interactions & Dialogue

**Domain:** Procedural dialogue, trait systems, and reputation mechanics added to existing Pygame exploration game

**Researched:** 2026-03-11

**Confidence:** MEDIUM (Implementation patterns proven in Dwarf Fortress, Wildermyth, Tech Support: Error Unknown; integration pitfalls specific to this codebase require Phase 1 validation)

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Seed Determinism Broken by Reputation Mutation

**What goes wrong:**
Creature traits are derived deterministically from name seed (good), but if reputation changes traits (hostile → friendly after high visits), the creature no longer matches its original seed output. On reload, the seed regenerates the original trait, contradicting persisted reputation. Player reaches a creature again and it's "reset" to hostile despite high reputation.

**Why it happens:**
The codebase generation pattern is seed → name → creature visual → audio (all deterministic). Adding reputation inverts this: reputation modifies traits dynamically. Developers assume seed determinism applies to all properties, not realizing reputation must be *separate* from seeded generation to maintain reproducibility.

**Consequences:**
- Creature appearance/behavior flickers on reload (breaks expected determinism)
- Player reports: "I befriended this creature but it forgot me"
- Reputation system feels broken even if code is correct

**How to avoid:**
- **Traits are immutable (seeded).** Reputation modifies *dialogue options and interaction likelihood*, NOT underlying traits.
- Store reputation separately: `reputation[point_id] = {visits: int, disposition: float}`. Never write back to trait generation.
- Creatures that are inherently hostile still *exist*; high reputation means they talk to you instead of fleeing. Traits persist, disposition changes.
- Test: Same creature with different reputation states → appearance unchanged, dialogue/behavior differs.

**Warning signs:**
- Creature appearance changes on reload
- Dialogue tone contradicts creature's base trait
- Same creature seed produces different visuals in different playthroughs

**Phase to address:**
Phase 1 (Architecture) — Before implementing traits, establish the contract: "Visuals = seed only; Behavior = seed + reputation."

---

### Pitfall 2: Dialogue State Explosion from Trait × Reputation Combinations

**What goes wrong:**
With N traits (friendly, curious, shy) and M reputation states (hostile, neutral, friendly), dialogue branches explode combinatorially: 3 traits × 3 reputation levels = 9 variations minimum. With 30,000 creatures and testers only verifying happy paths, bugs appear: contradictory dialogue (creature says "I trust you" and "Stay away" in same conversation), impossible states (replies that don't match the question).

**Why it happens:**
Developers add one trait, then another, then a third. Each feels independent. By trait count 4–5, the system has 2^4 to 2^5 logical branches. Procedural generation hides complexity: "it's randomized so it should be fine" is false confidence.

**Consequences:**
- Dialogue system file grows >500 lines, unmaintainable
- Two creatures with same traits say contradictory things
- Player gets nonsensical replies (branch condition undefined)
- Testing becomes impossible to comprehend ("test all 81 combinations")

**How to avoid:**
- **Cap traits to 2–3 maximum.** Each trait should mechanically affect dialogue. Friendly/Hostile + Curious/Shy = 4 combinations, testable. More than 5 traits becomes unmaintainable.
- **Reputation as numeric scale, not multi-state enum.** Float (-1.0 to +1.0), threshold for dialogue: if reputation > 0.5 "trusts you," else "neutral." Reduces combinatorial explosion.
- **Template-based dialogue, not explicit branches.** Instead of 9 separate trees, assemble at runtime: `[creature_mood] [greeting], [curiosity_question]? [reputation_consequence]` with 1–2 fallbacks per slot.
- **Test matrix:** For each trait combo × reputation threshold, verify at least 2 creatures behave consistently. Don't test all 30k, test all *combinations* (9–16 total states).

**Warning signs:**
- Dialogue system code >500 lines
- Testing a single dialogue change takes >30 minutes
- Two creatures with same traits say contradictory things
- You can't enumerate all possible dialogue states (red flag)

**Phase to address:**
Phase 1 (Design) — Spend 2–3 hours designing trait count and dialogue template architecture *before* implementation. Document the state model.

---

### Pitfall 3: Reputation Storage Becomes Unmaintainable JSON Blob

**What goes wrong:**
Reputation starts simple: `{creature_id: {visits: 3, disposition: 0.5}}`. By Phase 2, it's `{creature_id: {visits, disposition, last_mood, dialogue_flags, quest_state, ...}}`. By 10+ fields, JSON serialization is fragile: schema changes break old saves, circular dependencies appear (Quest A depends on Creature B reputation which depends on Quest A), memory bloats. With 30k creatures and 20 properties each, saves are slow to load/parse.

**Why it happens:**
Incremental feature addition. "We need to track if they've talked about X" → another field. By 10 fields, the dict is a bag of unrelated state with no coherent schema. This works in Python but breaks JSON versioning and complicates persistence.

**Consequences:**
- Save file grows >1MB
- Load time climbs noticeably after 10k creatures
- Schema migration requires manual scripts
- Diff/debug of save files becomes impossible

**How to avoid:**
- **Define schema upfront (Phase 1).** For this project: only `{creature_id: {total_interactions: int, disposition: float, last_visit_frame: int}}`. Three fields, period. Resist scope creep.
- **Separate concerns.** Reputation is global NPC memory (visits, disposition). Quest/dialogue history is a *separate* system if needed later.
- **Use pickle, not JSON.** For a solo project with no web sync, `pickle.dump(reputation_dict, file)` is faster, handles Python types, avoids schema parsing.
- **Lazy load.** Load reputation on-demand in `update_visible()` for ~10–20 visible creatures, not all 30k at startup.

**Warning signs:**
- Schema has >10 fields
- Save file >1MB
- Load time increases noticeably with playtime
- You need migration scripts to upgrade saves

**Phase to address:**
Phase 1 (Design & Persistence) — Define minimal schema and choose serialization format (pickle vs JSON) before writing persistence layer.

---

### Pitfall 4: Trait Interpretation Ambiguous Without Clear Mechanical Rules

**What goes wrong:**
Designer says creature A is "curious" and creature B is "shy." Traits exist but "curious" has no mechanical definition. Does it mean they ask questions? Approach faster? React to items? Different creatures interpret "curious" differently (creature 1 asks questions, creature 2 follows the player). Behavior is inconsistent and confusing.

**Why it happens:**
Trait systems are borrowed from D&D/RPGs where traits are flavor text for humans to interpret. In a procedural system, traits must *drive behavior*, not just describe it. Developers design traits, implement creatures, then realize mid-implementation that "friendly" has no clear meaning.

**Consequences:**
- Dialogue doesn't match trait (hostile creature is suddenly warm)
- Same trait produces different behavior in different creatures
- Playtesting reveals inconsistency too late to fix

**How to avoid:**
- **For each trait, write a one-sentence rule:** Curious = "Asks questions about the player's recent actions or visited locations." Hostile = "Opens dialogue with suspicion or threats." Shy = "Requires higher reputation before offering rare dialogue."
- **Trait truth table.** For each trait value, enumerate dialogue options available: Friendly can say [greeting, offer help, question]. Hostile: [threat, demand, refusal].
- **Test:** Play 5 creatures with same trait. Verify behavior matches the rule *exactly*, not personality interpretation.

**Warning signs:**
- Dialogue tone contradicts creature's trait
- Same trait produces different behavior across creatures
- You can't write a one-sentence rule explaining what a trait does

**Phase to address:**
Phase 1 (Design) — Before Phase 2 implementation, write one sentence per trait explaining its mechanical effect. Enforce during code review.

---

### Pitfall 5: Non-Deterministic Trait Generation

**What goes wrong:**
Using global `random.seed()` or `np.random.seed()` at module load causes traits to vary between runs or conflict with existing seeded generation (planets, audio, names). Creature at index 5 has different personality in session 1 vs. session 2. Reputation JSON refers to "hostile creature" that's now "friendly" because seed changed.

**Why it happens:**
Forgetting that global PRNG state is shared. Multiple modules (creatures, planets, audio) competing for same seed namespace causes interaction effects. Developer assumes `random.seed(creature_id)` is isolated, but it's global state.

**Consequences:**
- Creature personality changes between playthroughs (breaks determinism)
- Reputation data becomes stale (refers to old traits)
- Audio/planets may also become non-deterministic if trait generation interferes

**How to avoid:**
- **Use `random.Random(seed)` to create isolated instances.** Not global `random.seed()`.
- Seed with creature's name key (already unique per point).
- Never call `random.seed()` or `np.random.seed()` in trait module; always use instance method.

**Code pattern (correct):**
```python
def generate_traits(name_key: int):
    rng = random.Random(name_key)  # Isolated instance per creature
    return {
        'friendliness': rng.choice(['friendly', 'neutral', 'hostile']),
    }
```

**Code pattern (incorrect):**
```python
import random
random.seed(name_key)  # Global state — interferes with other seeding
def generate_traits(name_key: int):
    return {
        'friendliness': random.choice(['friendly', 'neutral', 'hostile']),
    }
```

**Warning signs:**
- Same creature has different personality on reload
- Reputation JSON becomes inconsistent with actual creature traits
- Audio/planets also become non-deterministic

**Phase to address:**
Phase 1 (Implementation) — Establish isolated PRNG pattern from day one. Add test: `generate_traits(key)` 5x, verify output identical each time.

---

### Pitfall 6: Memory Leak from Unbounded Reputation Cache

**What goes wrong:**
Reputation dict grows with every creature encountered. After exploring 5,000 creatures, reputation dict has 5,000 entries. After 10,000 creatures, memory grows. The codebase already uses LRU caching for creatures/planets (bounded), but reputation is unbounded — no eviction. On a 30k-point explorer, a player could theoretically accumulate data for all 30k creatures, staying in memory forever.

**Why it happens:**
Creatures/planets cache with eviction (maxsize=32, maxsize=1024). Reputation looks different: "why would we delete an NPC's memory?" feels wrong. But reputation is tiny (3 ints per creature = 24 bytes × 30k = 720KB worst case), so unbounded is low-risk short-term, high-risk for long sessions.

**Consequences:**
- Memory grows monotonically with playtime
- OOM crash after 2+ hour sessions
- No graceful degradation

**How to avoid:**
- **Apply same eviction logic to reputation.** Use `functools.lru_cache(maxsize=2000)` for load_reputation(). Load-on-demand, evict LRU when full.
- **Or:** Lazy load reputation into dict only during `update_visible()` for ~10–20 visible creatures, discard on frame exit.
- **Monitor:** Print memory usage in debug mode. Should stay <10MB even after 5k+ interactions.

**Warning signs:**
- Memory grows monotonically with play time
- OOM crash after extended play
- Profile shows reputation dict with 30k+ entries

**Phase to address:**
Phase 3 (Persistence) — Implement LRU eviction from the start. Prevents retrofit later.

---

### Pitfall 7: Dialogue References Undefined Game State

**What goes wrong:**
Creature says "I remember when you defeated that dragon," but player never fought a dragon (feature not implemented). Creature references a quest reward, invented location, or game mechanic that doesn't exist. Player is confused: creature seems to know things that never happened.

**Why it happens:**
Dialogue is templatized early with ambitious flavor text ("creatures reference your deeds"), but reputation tracking is minimal (just a counter). When dialogue says "I saw you fight the Crimson Titan," there's no backing data for actual combat. Developers assume dialogue is flavor and don't enforce it against game state.

**Consequences:**
- Creature says something the player knows is false
- Dialogue assumes game features not implemented
- Player reports immersion break: "Creature talked about something that never happened"

**How to avoid:**
- **Dialogue only references reputation and trait.** Creature can say "You've visited me X times" or "You seem curious" — facts stored in reputation. Avoid dialogue implying quests, inventory, combat, or unimplemented mechanics.
- **If dialogue needs to reference events, formalize them.** Add `event_log = [(creature_id, timestamp, interaction_type)]` and let dialogue check: `if (creature_id, "visited") in event_log.recent(weeks=4): can_say(...)`.
- **Test:** For every dialogue line, verify the condition it assumes actually exists in the reputation/event model. If not implemented, remove the line.

**Warning signs:**
- Creature says something the player knows is false
- Dialogue assumes features not implemented
- You reference untracked events or stats

**Phase to address:**
Phase 2 (Dialogue Design) — Write dialogue *after* defining what reputation actually tracks, not before.

---

## Moderate Pitfalls

### Pitfall 8: Trait Distribution Imbalance

**What goes wrong:**
Randomized trait generation produces 80% friendly creatures, 15% neutral, 5% hostile. Exploration feels bland; hostile creatures should feel rare and special. Or the reverse: 80% hostile, making the world feel hostile rather than explorable.

**Why it happens:**
Using uniform `rng.choice()` on trait pools without thinking about distribution consequences. Weights aren't specified until playtesting reveals imbalance.

**Consequences:**
- World flavor is off; dialogue lacks tension or warmth
- Playtesting feedback: "All creatures feel the same"

**How to avoid:**
- **Playtesting early.** Sample 100 creatures, count trait distributions. Does it feel right?
- **Explicit weights:** If friendly should be 60%, use `rng.choices(['friendly', 'neutral', 'hostile'], weights=[60, 30, 10])`.

---

### Pitfall 9: Dialogue Exhaustion (Repetition Too Early)

**What goes wrong:**
With 27 trait profiles × 6 templates = 162 unique lines, players exhaust dialogue within 10–15 interactions per creature. Subsequent visits show repeats. Players stop interacting because dialogue feels canned.

**Why it happens:**
Template pools are shallow. No variation mechanism (randomization between visits, mood states, context).

**Consequences:**
- Players stop interacting (dialogue feels hollow)
- Relationships feel unfulfilling
- Game feels unfinished despite technically working

**How to avoid:**
- **Start minimal.** 3–5 templates per trait combo, not max.
- **Playtesting at 5–10 interactions per creature** catches repetition early.
- **Variation mechanism:** Randomize within templates each visit (choose random from pool, not the same line). Add "nth visit" variants (greeting on 1st visit, different on 2nd+).

**Code pattern:**
```python
def get_dialogue(creature_idx: int, visit_count: int, traits: dict) -> str:
    rng = random.Random(creature_idx + visit_count * 1000)  # Vary seed by visit
    if visit_count == 0:
        pool = DIALOGUE_GREETING[traits['friendliness']]
    else:
        pool = DIALOGUE_RETURNING[traits['friendliness']]
    return rng.choice(pool)
```

---

### Pitfall 10: Reputation Not Persisting Across Sessions

**What goes wrong:**
Save file isn't created, isn't flushed on exit, or is loaded but not synced with in-memory state. Player builds relationships, then on reload everything is reset. Core differentiator broken.

**Why it happens:**
- Forgetting to call `save_reputation()` on game exit
- Reputation loaded at startup but not kept in sync (in-memory diverges from JSON)
- File path issues (wrong directory, permissions) that silently fail

**Consequences:**
- Relationships feel ephemeral
- Player frustration: "I spent an hour with this creature, it forgot me"
- Core feature (creatures remember you) broken

**How to avoid:**
- Load reputation on startup; don't crash if file missing.
- Keep in-memory copy synced with storage (write-through on each interaction, or flush on exit).
- Write saves to well-known directory: `./saves/` or platform-specific app data.
- Test: Save file exists after exiting → Reload → Reputation restored.

**Code pattern:**
```python
SAVE_PATH = Path("saves/reputation.json")

def load_reputation():
    try:
        if SAVE_PATH.exists():
            with open(SAVE_PATH) as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load reputation: {e}")
    return {}

def save_reputation(rep_data):
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SAVE_PATH, 'w') as f:
            json.dump(rep_data, f, indent=2)
    except Exception as e:
        print(f"Error: failed to save reputation: {e}")

# In main.py cleanup:
# pygame.quit()
# save_reputation(reputation)  # Must be called
```

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Traits hard-coded as numbers, not enum | Fast to prototype | Hard to refactor if trait names change | Use enum from day one; cleaner. |
| Dialogue branches with no fallback | Quick to write | Crashes if branch undefined | Never acceptable; always have fallback. |
| Reputation as ad-hoc JSON | Works immediately | Schema breaks on updates | Use pickle or versioned JSON. |
| Traits affect both visuals AND behavior | Code reuse | Visuals flicker when reputation changes | Never; visuals = seed only. |
| Trait system separate from dialogue system | Modular in theory | Dialogue doesn't know trait rules | Design both together; verify contracts. |
| Unbounded reputation dict, no eviction | Simplest to code | Memory leak in long sessions | MVP only; use LRU from start. |

---

## Integration Gotchas

| Integration Point | Common Mistake | Correct Approach |
|---|---|---|
| **Reputation + Procedural Generation** | Assume seed output is immutable; reputation modifies traits on reload | Traits are seed-derived, read-only. Reputation *modifies behavior*, not traits. Visuals always from seed. |
| **Dialogue + Trait System** | Write dialogue without knowing what traits exist or their rules | Define trait rules and dialogue slots *before* writing any dialogue. Dialogue should only reference reputation/trait/count. |
| **Reputation + Visible Set (KDTree)** | Load all 30k creatures' reputation at startup | Load reputation on-demand in `update_visible()` for ~10–20 visible creatures only. Lazy load + LRU evict. |
| **Traits + Naming System** | Traits derived from name hash, causing collisions | Traits derived from creature's unique name_key seed; deterministic collision-free. Reuse existing seed infrastructure. |
| **Serialization + Version Changes** | Save reputation without versioning; old saves break | Serialize with version number. Document upgrade path even if v1.0 → v1.1 incompatibility is acceptable. |
| **Dialogue + Audio Synthesis** | Trait-based dialogue + trait-based audio timbre create coupling | Dialogue is behavioral; audio timbre comes from separate audio seed. Keep independent. |

---

## Performance Traps

| Trap | Symptoms | Prevention | Breaks At |
|---|---|---|---|
| **Unbounded Reputation Dict** | Memory grows; OOM crash in long sessions | Use LRU cache or lazy load in `update_visible()` only | >5k creatures (~2 hour playthrough) |
| **Dialogue State Explosion** | Testing 2^N combinations; bugs appear in untested branches | Cap traits to 2–3; use numeric reputation; template-based dialogue | >5 traits or >3 reputation states |
| **Seed Hash Collision in Trait Derivation** | Creatures with different names get same traits | Use deterministic PRNG seeded per creature_id, not name hash | Unlikely if trait derivation is careful |
| **Reputation Serialization Bottleneck** | Load time climbs with creature count | Use pickle or binary format; load lazily | >10k creatures in save file |
| **Dialogue Branching Complexity** | Dialogue system code unmaintainable | Template-based generation, not explicit branches | >20 dialogue lines per creature |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---|---|---|
| **Creature "forgets" player after reload** | Player thinks reputation is broken | Persist reputation correctly; verify load on creature encounter. Test: reload save, talk to creature, verify it remembers. |
| **Dialogue contradicts creature's trait** | Creature seems inconsistent | Dialogue templates should only reference stored reputation/trait. Test: every dialogue option consistent with trait + reputation. |
| **Reputation number with no visible effect** | Player increases reputation but creature behavior doesn't change | Make reputation *obvious*: friendly creatures offer unique dialogue, hostile refuse, neutral is default. Threshold should be clear (>0.7 = friendly). |
| **Too many creatures with same dialogue** | World feels flat, repetitive | Randomize dialogue within template (3–5 variants per slot). 30k creatures should have variety. Test: talk to 5 creatures with same traits, see different lines. |
| **Dialogue assumes events that never happened** | Immersion break; player confused | Dialogue references only: creature visuals, player reputation, visit count. No quests, inventory, unimplemented mechanics. |

---

## "Looks Done But Isn't" Checklist

- [ ] **Trait System:** Traits immutable from seed, not modified by reputation — verify by reloading with different reputation and checking visuals unchanged.
- [ ] **Reputation Persistence:** Loads correctly after save/load; creature remembers interaction count — test by saving after 3 visits, reloading, verifying creature says "I've seen you X times."
- [ ] **Dialogue Consistency:** All dialogue lines mechanically justified (reference only reputation/trait/count) — audit dialogue file and cross-reference against reputation system.
- [ ] **Memory Bounded:** Reputation dict stays <10MB even after 5k+ encounters — profile during extended play.
- [ ] **Trait Rules Documented:** Each trait has one-sentence rule explaining mechanical effect (not just flavor) — in code comments or design doc.
- [ ] **Fallback Dialogue:** Every dialogue branch has fallback if condition undefined — no KeyError crashes from missing data.
- [ ] **Schema Versioning:** Reputation serialization versioned (even if v1) — saves have version number, load() checks it.
- [ ] **Non-Determinism Tested:** Same creature generated 5 times with same seed → identical traits — test in unit test.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| **Creature "forgets" player (reputation persistence broken)** | LOW | Check load_reputation() called on creature encounter. Add debug log: `print(f"Rep for {creature_id}: {rep_dict}")`. Verify rep data matches save file. |
| **Reputation memory leak (unbounded dict)** | MEDIUM | Refactor to LRU cache. Add `reputation = lru_cache(maxsize=2000)(load_reputation)`. Test memory stays bounded. May require save-file migration. |
| **Dialogue branches undefined (missing trait check)** | MEDIUM | Audit all dialogue conditions. For each line, verify trait/reputation field exists. Add fallback: `condition or "default dialogue"`. Test all branches. |
| **Save file incompatible (schema mismatch)** | HIGH | Write schema migration function. Load v1, add missing fields with defaults, save as v2. Or document incompatibility, ask users to restart. |
| **Traits affect visuals (breaking determinism)** | HIGH | Separate trait from visual generation. Visuals = seed-derived, immutable. Traits modify behavior only. Rebuild creature visual pipeline. Requires refactor of graphics.py. |

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|---|---|---|---|
| Phase 1 | Trait Generation | Non-deterministic PRNG / global state conflict | Test: run `generate_traits(key)` 5x, verify identical output. Use isolated `random.Random(key)` instances. |
| Phase 1 | Architecture | Seed determinism vs. mutable reputation | Establish rule: "Visuals = seed only; Behavior = seed + reputation." Document before implementation. |
| Phase 1 | Design | Ambiguous trait rules | Write one-sentence rule per trait. Enforce during Phase 2 implementation. Create trait truth table. |
| Phase 2 | Dialogue Templates | Repetition / exhaustion | Playtest with 5–10 interactions per creature. Measure unique lines before repeat. Plan iteration if <8 unique per creature. |
| Phase 2 | Dialogue | Undefined game state references | Audit all dialogue; verify only references reputation/trait/count, not unimplemented features. |
| Phase 3 | Reputation I/O | Failed saves / schema mismatch | Test save/load cycle. Verify JSON readable and valid. Test backwards compatibility (load old schema). |
| Phase 3 | Persistence | Memory leaks | Implement LRU eviction from start. Monitor memory in debug mode. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| Seed determinism breaks | Phase 1 (Design) | Same seed = identical appearance across all reputation states. Test reload with different reputation. |
| Dialogue state explosion | Phase 1 (Design) | Define max trait count (2–3) and reputation thresholds; verify no >9 total dialogue branches per creature. |
| Reputation storage unmaintainable | Phase 1 (Design) | Design schema with ≤5 fields; document serialization format. |
| Trait variance breaks determinism | Phase 1 (Architecture) | Rule: "Visuals = seed only; Behavior = seed + reputation" — enforce in code review. |
| Memory leaks from reputation | Phase 1 (Architecture) | Plan LRU eviction from start; implement load-on-demand pattern. |
| Non-deterministic trait generation | Phase 1 (Implementation) | Test: `generate_traits(key)` 5x, verify output identical. Use isolated PRNG instances. |
| Dialogue references undefined state | Phase 2 (Dialogue Design) | Audit all dialogue; verify only references reputation/trait/count, not unimplemented features. |
| Trait ambiguity | Phase 1 (Design) | Write 1-sentence rule per trait; enforce during Phase 2 implementation. |
| Persistence breaks on format change | Phase 3 (Persistence) | Implement versioned serialization; document upgrade path. |

---

## Sources

Pitfalls research draws from game design patterns, community discussions, and documented mistakes in procedural systems:

- [Branching Dialogue Nightmare: Why Systems Fail | StoryFlow Editor](https://storyflow-editor.com/blog/branching-dialogue-nightmare-how-to-fix/) — Exponential complexity of dialogue branching
- [Procedural Generation on Mobile: Balancing Complexity and Performance - DEV Community](https://dev.to/oceanviewgames/procedural-generation-on-mobile-balancing-complexity-and-performance-11d8) — Memory and performance traps in procedural systems
- [Procedural World: Storage Matters](https://procworld.blogspot.com/2013/03/storage-matters.html) — Serialization and persistence pitfalls
- [A Study Into Replayability -- Random vs. Procedural Generation | Game Developer](https://www.gamedeveloper.com/design/a-study-into-replayability----random-vs-procedural-generation) — Determinism and seed-based generation
- [LLM-Driven NPCs: Cross-Platform Dialogue System for Games and Social Platforms](https://arxiv.org/html/2504.13928v1) — NPC memory and dialogue state management challenges
- [Developing a procedural dialogue system for Tech Support: Error Unknown | Game Developer](https://www.gamedeveloper.com/design/developing-a-procedural-dialogue-system-for-tech-support-error-unknown) — Procedural dialogue templates at scale
- [Personality stats or traits? - Choice of Games Forum](https://forum.choiceofgames.com/t/personality-stats-or-traits/167199) — Trait system design and player agency
- [Design Unpredictable AI in Games. Part 1 — Architecture | Medium](https://medium.com/@stannotes/design-unpredictable-ai-in-games-part-1-architecture-3752a618db6) — NPC behavior coupling and state management

---

*Pitfalls research for: Procedural dialogue, trait systems, and reputation mechanics in a Pygame 4D exploration game*

*Researched: 2026-03-11 as research input for v1.1 milestone planning*
