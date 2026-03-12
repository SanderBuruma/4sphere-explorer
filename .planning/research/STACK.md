# Technology Stack: Creature Interaction & Dialogue

**Project:** 4-Sphere Explorer v1.1
**Researched:** 2026-03-11
**New Features:** Trait generation, procedural dialogue, reputation persistence

## Recommended Stack

### Core Framework (Existing)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Gameplay, math, generation | Established in codebase; NumPy ecosystem mature |
| Pygame-CE | 2.4.0+ | Game loop, rendering, UI | Already in use; lightweight and proven |
| NumPy | 2.0+ | Array operations, PRNG, math | Core to existing procedures (creature, planet, audio generation) |
| SciPy | 1.13.0+ | Spatial indexing (KDTree) | Used for visibility queries; stable |

### NEW: Trait & Dialogue System

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python `random` | stdlib | Seeded trait generation | Built-in, zero dependencies; `seed()` ensures reproducibility from name key |
| Python `json` | stdlib | Reputation persistence | Human-readable saves, portable, safe (unlike pickle), standard for game saves |

## Rationale

### Trait Generation: Use Python `random` (stdlib)

**What:** Derive creature personality traits deterministically from the name key (already sampled for each point).

**Why this approach:**
- **Zero dependencies:** Python's `random.Random` seeded with name key produces deterministic, reproducible traits
- **Matches existing procedural pattern:** Creature avatars, planets, and audio already use seed-based generation (NumPy + custom hash functions)
- **Simple and fast:** Trait generation per creature is trivial (sample from trait pools, apply modifiers)
- **No LLM, no API calls:** Fits project ethos of procedural-first, deterministic generation

**How it works:**
```python
import random

def generate_traits(name_key: int):
    """Return personality traits dict from name key."""
    rng = random.Random(name_key)
    return {
        'friendliness': rng.choice(['friendly', 'neutral', 'hostile']),
        'curiosity': rng.choice(['curious', 'indifferent', 'cautious']),
        'energy': rng.choice(['energetic', 'calm', 'sleepy']),
    }
```

**Confidence:** HIGH — Python's `random.Random(seed)` is deterministic by design and well-tested for procedural generation in games.

---

### Dialogue System: Template + Traits (No external library)

**What:** Generate brief dialogue responses by selecting from trait-modulated templates.

**Why no Markov chains / markovify:**
- Markov chains (via `markovify` library) are overkill for 30k unique creatures where dialogue is brief and context-limited
- Adds 1 external dependency + network calls to seed the model
- Template-based approach matches project constraints (minimal LOC, deterministic)

**Why no LLM (ChatGPT, Claude, etc.):**
- API costs scale linearly with 30k creatures × interactions
- Requires internet connection (breaks offline gameplay)
- Contradicts project philosophy (procedural-first, deterministic)
- Latency unacceptable for real-time dialogue in Pygame

**What to build instead:**
Simple trait-modulated templates. Example:
```python
DIALOGUE_FRIENDLY = [
    "Oh, it's you! Great to see you again.",
    "Welcome back! I missed you.",
]
DIALOGUE_HOSTILE = [
    "What do you want?",
    "Stay away from me.",
]

def generate_dialogue(traits: dict, is_returning_visit: bool) -> str:
    if traits['friendliness'] == 'friendly':
        pool = DIALOGUE_FRIENDLY_RETURNING if is_returning_visit else DIALOGUE_FRIENDLY
    elif traits['friendliness'] == 'hostile':
        pool = DIALOGUE_HOSTILE
    # ... etc
    rng = random.Random(traits_seed)
    return rng.choice(pool)
```

**Confidence:** HIGH — Approach proven in indie games (Stardew Valley, Hades, etc.); matches existing codebase patterns.

---

### Reputation System: Use Python `json` (stdlib)

**What:** Save/load per-creature reputation (visit count, relationship level, last seen).

**Why `json` over `pickle`:**

| Criterion | JSON | Pickle |
|-----------|------|--------|
| **Readability** | Human-readable, debuggable | Binary, opaque |
| **Portability** | Language-independent | Python-only |
| **Safety** | Cannot execute code | Unsafe for untrusted input |
| **Game saves** | Standard industry practice | Only if Python-only & extreme perf needed |
| **Size** | Slightly larger | Smaller for large NumPy arrays |
| **Speed** | Slower for numeric data | Faster for NumPy arrays |

Since reputation is small (dict of creature_id → {visit_count, relationship_level, last_seen}), JSON's minor size/speed drawbacks don't matter. Safety and readability are wins.

**Schema example:**
```json
{
  "creature_12345": {
    "visit_count": 3,
    "relationship_level": 0.6,
    "last_seen_timestamp": 1710158400
  }
}
```

**How to integrate:**
```python
import json
from pathlib import Path

SAVE_PATH = Path("saves/reputation.json")

def load_reputation():
    if SAVE_PATH.exists():
        with open(SAVE_PATH) as f:
            return json.load(f)
    return {}

def save_reputation(rep_data):
    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SAVE_PATH, 'w') as f:
        json.dump(rep_data, f, indent=2)
```

**Confidence:** HIGH — JSON is the standard for game save systems in Python; widely used across indie games.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **Trait generation** | `random` stdlib | NumPy (seeded) | Both deterministic; `random` slightly simpler for non-array operations |
| **Trait generation** | Procedural (templates) | Markov chains (markovify) | Overkill for brief dialogue, adds dependency, slower |
| **Trait generation** | Procedural (templates) | LLM (ChatGPT/Claude/etc.) | API costs, internet required, latency, breaks offline gameplay |
| **Reputation persistence** | JSON (stdlib) | Pickle | Safer, readable, industry standard for game saves |
| **Reputation persistence** | JSON (stdlib) | SQLite | Overengineered for 30k creatures + simple schema |
| **Reputation persistence** | JSON (stdlib) | YAML | No advantage over JSON for this use case; adds dependency |

---

## What NOT to Add

**Do NOT:**
- Add `markovify` library — dialogue templates + traits sufficient and simpler
- Add LLM API integration (OpenAI, Anthropic, etc.) — breaks offline gameplay, adds costs, contradicts project ethos
- Add `sqlalchemy` for reputation DB — JSON is simpler for this scale
- Add YAML library (`pyyaml`) — JSON covers persistence needs
- Add `dataclasses` or `pydantic` for trait schemas — plain dicts with type hints suffice
- Add dialogue trees/graph libraries — templates work for initial feature

---

## Installation & Integration

### No new pip dependencies

Trait generation and reputation persistence use only Python stdlib:

```bash
# No additional packages needed
# Existing requirements.txt unchanged:
# numpy
# pygame-ce
# scipy
```

### Code organization

```
lib/
├── traits.py         # NEW: Trait generation from name key
├── dialogue.py       # NEW: Dialogue templates + trait modulation
├── reputation.py     # NEW: Load/save reputation (JSON)
main.py              # Initialize reputation on startup
```

### Integration point

On interaction (radial menu click):
1. Load creature's reputation (from JSON cache)
2. Generate traits from name key
3. Select dialogue from templates (trait-modulated)
4. Update reputation (visit count, timestamp)
5. Save reputation (periodic flush to JSON)

---

## Scalability Notes

At 30,000 creatures:
- **Trait generation:** Instant per creature (single `random.Random(seed)` call)
- **Dialogue rendering:** Instant (text selection from list)
- **Reputation storage:** ~500 bytes per interacted creature in JSON (dict of ~100-1000 visited creatures = ~50-500 KB uncompressed)
- **Reputation I/O:** Save on exit or after threshold (e.g., every 10 interactions)

No performance bottlenecks expected with this stack.

---

## Version Pinning

Pin to versions matching existing requirements.txt approach (no minor version locks, no pre-releases):

```txt
numpy>=2.0
pygame-ce>=2.4
scipy>=1.13
```

No new pins needed (stdlib only).

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Trait generation (random stdlib) | HIGH | Deterministic PRNG well-tested in games; matches existing procedural patterns |
| Dialogue templates + traits | HIGH | Proven approach in indie games; simpler than Markov chains |
| Reputation (JSON) | HIGH | Standard game-save format; safer and more portable than pickle |
| No external dialogue/trait libraries | HIGH | Project prioritizes minimal LOC and procedural determinism over generality |

---

## Sources & References

- [Python random module documentation](https://docs.python.org/3/library/random.html) — Deterministic seeding for reproducible trait generation
- [Python json module documentation](https://docs.python.org/3/library/json.html) — Safe, portable serialization
- [Real Python: Python Pickle Module](https://realpython.com/python-pickle-module/) — Why to prefer JSON for game saves
- [Making Games with Pygame](https://www.pygame.org/) — Established Pygame patterns
- [Procedural Game Design (peerdh.com)](https://peerdh.com/blogs/programming-insights/creating-a-framework-for-procedural-npc-dialogue-generation-in-python-games) — Template-based NPC dialogue in Python games
