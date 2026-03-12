# Architecture Patterns: Creature Interactions & Dialogue

**Domain:** 4D exploration game NPC interaction system
**Researched:** 2026-03-11

## Recommended Architecture

```
Creature Interaction Pipeline

1. Player clicks creature (via radial menu)
   ↓
2. Load reputation data (in-memory cache)
   ↓
3. Generate traits (seeded from name_key)
   ↓
4. Select dialogue (trait-modulated template)
   ↓
5. Display dialogue overlay
   ↓
6. Update reputation (increment visit_count, update timestamp)
   ↓
7. Sync reputation to JSON (on exit or periodic flush)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `lib/traits.py` | Derive creature personality from seed (name_key). Return trait dict with 4 axes (aggressive/passive, curious/aloof, friendly/hostile, brave/fearful) as 0–100 scores. | (standalone — pure function) |
| `lib/dialogue.py` | Select dialogue from templates based on trait vector + visit context. Return text. | traits.py (for generating traits if not passed in) |
| `lib/reputation.py` | Load/save per-creature reputation data (JSON). Update visit counts and reputation scores. Provide API for main loop. | filesystem (JSON), main.py (on game exit) |
| `main.py` | Game loop, input handling, radial menu interaction trigger. Call dialogue module. Update in-memory reputation. | lib/dialogue.py, lib/reputation.py |
| `radial menu` (existing) | Existing UI for interaction options. Add "Interact" or "Talk" option that triggers dialogue flow. Display trait scores. | main.py, dialogue module |

### Data Flow

```
User Action: Click creature in radial menu
  ↓
main.py detects "Interact" selection
  ↓
reputation_data = load_reputation()[creature_id]  # in-memory cache
traits = generate_traits(name_key)                 # lib/traits.py
dialogue_text = get_dialogue(traits, visit_count) # lib/dialogue.py
  ↓
Display dialogue_text overlay (2-3 seconds)
Show trait scores in menu
  ↓
Update reputation:
  reputation_data['visit_count'] += 1
  reputation_data['last_seen'] = time.time()
  reputation_data['reputation'] = calculate_reputation(visit_count, action)
  ↓
Periodically flush in-memory cache to JSON:
  save_reputation(reputation_data)
  (on exit, or every N interactions, or on interval)
```

## Patterns to Follow

### Pattern 1: Trait Generation from Seed Hash

**What:** Derive 4 personality axes from creature name_key using seeded PRNG, producing 0–100 scores per axis.

**When:** On creature interaction (fast, deterministic, no state needed).

**Rationale:** Matches Dwarf Fortress approach (discrete personality facets drive behavior). Four axes cover personality space without explosion (27 combos if bucketed as low/med/high; 10k+ combos at fine granularity).

**Example:**
```python
# lib/traits.py
import random

def generate_traits(name_key: int) -> dict:
    """Generate deterministic personality from name key.
    
    Returns dict with 4 axes, each 0–100:
    - aggressive: 0 = passive, 100 = aggressive
    - curious: 0 = aloof, 100 = curious
    - friendly: 0 = hostile, 100 = friendly
    - brave: 0 = fearful, 100 = brave
    """
    rng = random.Random(name_key)
    return {
        'aggressive': rng.randint(0, 100),
        'curious': rng.randint(0, 100),
        'friendly': rng.randint(0, 100),
        'brave': rng.randint(0, 100),
    }

# Usage
traits = generate_traits(12345)  # Always same for 12345
# → {'aggressive': 47, 'curious': 82, 'friendly': 23, 'brave': 61}
```

Benefits:
- Deterministic (same key → same traits across sessions)
- Lightweight (4 integers, no complex computation)
- Scales to 30k creatures trivially
- Matches existing codebase procedural patterns (creature avatars, planets, audio)

---

### Pattern 2: Trait Vector → Dialogue Template Mapping

**What:** Bucket trait axes into low/med/high tiers, map to dialogue pools.

**When:** On dialogue generation (trait vector determines which template pool to use).

**Example:**
```python
# lib/dialogue.py
def _bucket_trait(value: int) -> str:
    """Map 0–100 trait score to low/med/high."""
    if value < 33:
        return 'low'
    elif value < 67:
        return 'med'
    else:
        return 'high'

def get_dialogue(traits: dict, visit_count: int) -> str:
    """Select dialogue based on trait vector and visit context."""
    # Bucket traits
    aggression = _bucket_trait(traits['aggressive'])
    friendliness = _bucket_trait(traits['friendly'])
    
    # Determine dialogue phase (first visit vs returning)
    phase = 'greeting' if visit_count == 0 else 'returning'
    
    # Select from trait-grouped template pool
    key = (aggression, friendliness, phase)
    pool = DIALOGUE_TEMPLATES.get(key, [])
    
    # Vary selection by visit number (avoid repetition)
    rng = random.Random(traits['name_key'] + visit_count * 10000)
    return rng.choice(pool) if pool else "..."

# Template structure (data, not code)
DIALOGUE_TEMPLATES = {
    ('low', 'high', 'greeting'): [
        "Welcome, friend! So glad to meet you.",
        "Hello! I hope your travels are going well.",
    ],
    ('low', 'high', 'returning'): [
        "You came back! That makes me so happy.",
        "I was hoping you'd visit again.",
    ],
    ('high', 'low', 'greeting'): [
        "What do you want?",
        "State your business.",
    ],
    ('high', 'low', 'returning'): [
        "You again. Don't waste my time.",
        "What now?",
    ],
    # ... more combinations
}
```

Benefits:
- Scales to 30k creatures without exponential dialogue debt
- Trait vector is 3D (low/med/high × 4 axes = 81 max, but sparse in practice)
- Templates are data (easy to edit/iterate without code changes)
- Visiting same creature twice → different dialogue (varied seed per visit)

---

### Pattern 3: Lazy Load + In-Memory Cache for Reputation

**What:** Load reputation JSON at startup, keep in-memory, flush on exit or periodic checkpoint.

**When:** Reputation is infrequently accessed (once per interaction) and is small (<1 MB).

**Example:**
```python
# lib/reputation.py
import json
from pathlib import Path
from typing import Dict
import time

SAVE_PATH = Path("saves/reputation.json")

# In-memory cache (reference held by main.py)
_reputation_cache = {}

def load_reputation() -> Dict:
    """Load reputation from JSON, or return empty dict if missing."""
    global _reputation_cache
    if SAVE_PATH.exists():
        try:
            with open(SAVE_PATH) as f:
                _reputation_cache = json.load(f)
                # Migrate old schemas
                for cid, rep in _reputation_cache.items():
                    rep.setdefault('visit_count', 0)
                    rep.setdefault('reputation', 0)  # -10 to +10 scale
                    rep.setdefault('last_seen', 0)
        except Exception as e:
            print(f"Warning: failed to load reputation: {e}")
            _reputation_cache = {}
    return _reputation_cache

def save_reputation() -> None:
    """Flush in-memory cache to JSON."""
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SAVE_PATH, 'w') as f:
            json.dump(_reputation_cache, f, indent=2)
    except Exception as e:
        print(f"Error: failed to save reputation: {e}")

def get_reputation(creature_id: int) -> dict:
    """Get or create reputation entry for creature."""
    if creature_id not in _reputation_cache:
        _reputation_cache[creature_id] = {
            'visit_count': 0,
            'reputation': 0,      # -10 (hostile) to +10 (allied)
            'last_seen': 0,
        }
    return _reputation_cache[creature_id]

def update_reputation(creature_id: int, action: str = 'visit') -> None:
    """Update reputation on interaction."""
    rep = get_reputation(creature_id)
    rep['visit_count'] += 1
    rep['last_seen'] = time.time()
    
    # Apply reputation delta based on action
    if action == 'friendly':
        rep['reputation'] = min(10, rep['reputation'] + 1)
    elif action == 'hostile':
        rep['reputation'] = max(-10, rep['reputation'] - 1)
    # 'visit' = neutral (no change)
```

**Schema (reputation.json):**
```json
{
  "12345": {
    "visit_count": 3,
    "reputation": 1,
    "last_seen": 1710158400
  },
  "67890": {
    "visit_count": 1,
    "reputation": -2,
    "last_seen": 1710150000
  }
}
```

Benefits:
- Fast access (dict lookup in memory)
- Safe writes (JSON on exit prevents corruption)
- Human-readable for debugging
- Extensible (add fields as needed)
- Auto-migration (missing fields default gracefully)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Dialogue Trees

**What:** Branching dialogue with player choices (node graphs, state machines).

**Why bad:**
- Exponential state explosion with 30k creatures
- Each path = content to write (small tree with 5 nodes × 3 choices = 15 dialogue variants per creature)
- Hard to tune (which path leads where? Why?)

**Instead:** Linear dialogue (one response per interaction) with trait modulation.

```python
# WRONG: dialogue tree
dialogue_tree = {
    'start': {
        'text': "Hello, what do you want?",
        'choices': [
            {'text': "Tell me a story", 'next': 'story_node'},
            {'text': "Leave", 'next': None},
        ]
    },
    'story_node': {
        'text': "Once upon a time...",
        'choices': [...]
    }
    # Multiply this by 30k creatures...
}

# RIGHT: single response (trait-modulated)
dialogue = get_dialogue(traits, visit_count)
# → "I'm not much of a storyteller, but I can try..."
# Personality comes from traits, not branching
```

---

### Anti-Pattern 2: Trait Decay / Complex Reputation Math

**What:** Reputation scores decay over time, or interact with other systems (faction, compatibility, etc.).

**Why bad:**
- Adds state management complexity
- Hard to debug (reputation changing without interaction)
- Players can't predict creature behavior

**Instead:** Simple counters (visit count, reputation score). No decay.

```python
# WRONG: complex decay
def update_reputation(creature_id, time_delta):
    rep = reputation[creature_id]
    rep['score'] = rep['score'] * (0.99 ** time_delta)  # Exponential decay
    # Now reputation changes silently over time

# RIGHT: simple counter
def update_reputation(creature_id, action):
    rep = get_reputation(creature_id)
    if action == 'friendly':
        rep['reputation'] += 1
    # Only changes on interaction
```

---

### Anti-Pattern 3: Pickle for Reputation

**What:** Using `pickle` to serialize reputation data.

**Why bad:**
- Not portable (Python-specific)
- Not human-readable (can't debug with text editor)
- Security risk if untrusted sources modify saves

**Instead:** JSON (see Pattern 3 above).

---

## Scalability Considerations

At 30,000 creatures:

| Concern | Cost | Bottleneck? |
|---------|------|-------------|
| Trait generation per creature | ~0.1 ms (seeded PRNG) | No. O(1) per creature, called only on interaction. |
| Dialogue selection per creature | ~0.1 ms (dict lookup + choice) | No. O(1), no string processing. |
| Reputation storage per creature | ~100 bytes JSON | No. 30k creatures × 100 bytes = 3 MB (uncompressed). |
| Reputation I/O on exit | ~100 ms (write 3 MB JSON) | No. One-time cost, acceptable. |
| In-memory reputation cache | 3–5 MB | No. Trivial. |
| Dialogue template data | ~50 KB (20–30 unique templates) | No. Static data, not per-creature. |

**Conclusion:** No bottlenecks. Interaction latency dominated by UI rendering, not generation.

---

## Testing Strategy

| Module | Test Focus | Example |
|--------|-----------|---------|
| `lib/traits.py` | Determinism | `assert generate_traits(123) == generate_traits(123)` |
| `lib/traits.py` | Range validation | `assert all(0 <= v <= 100 for v in traits.values())` |
| `lib/dialogue.py` | Correctness | `assert get_dialogue(friendly_traits, 0) in GREETING_POOL` |
| `lib/dialogue.py` | Variance | `assert get_dialogue(..., 0) != get_dialogue(..., 1)` (different responses per visit) |
| `lib/reputation.py` | I/O round-trip | Save → load → verify schema intact |
| `lib/reputation.py` | Schema migration | Load old schema → verify defaults applied |
| Integration | Full flow | Click creature → dialogue shown → reputation updated |

---

## Integration Points

### With Existing Radial Menu

Add "Interact" option to radial menu:

```python
# In main.py, radial menu handler
if selected_option == "Interact":
    creature_id = hovered_point_idx
    name_key = _name_keys[creature_id]
    
    # Generate traits (fast, deterministic)
    traits = generate_traits(name_key)
    
    # Get reputation
    rep = get_reputation(creature_id)
    
    # Show traits in menu (optional, for flavor)
    print(f"Traits: Aggressive {traits['aggressive']}, Friendly {traits['friendly']}")
    
    # Get dialogue
    dialogue = get_dialogue(traits, rep['visit_count'])
    
    # Display dialogue (2–3 second overlay)
    show_dialogue_overlay(dialogue, duration=3.0)
    
    # Update reputation
    update_reputation(creature_id, action='visit')
    
    # Periodically flush to disk
    if game_interaction_count % 10 == 0:
        save_reputation()
```

### With Existing Detail Panel

Extend detail panel to show creature traits:

```python
# In detail panel rendering
traits = generate_traits(name_key)
rep = get_reputation(creature_id)

panel_lines = [
    f"Name: {creature_name}",
    f"",
    f"Personality:",
    f"  Aggressive ▓▓░░░░░░░░ {traits['aggressive']}",
    f"  Curious   ░░░▓▓▓▓▓░░ {traits['curious']}",
    f"  Friendly  ▓▓▓▓░░░░░░ {traits['friendly']}",
    f"  Brave     ░░░░░▓▓▓▓░ {traits['brave']}",
    f"",
    f"Reputation: {rep['reputation']:+d}",
    f"Visits: {rep['visit_count']}",
]
```

---

## Sources

- [Dwarf Fortress personality traits](https://dwarffortresswiki.org/index.php/DF2014:Personality_trait) — Discrete facets drive emergent behavior
- [Wildermyth relationships](https://wildermyth.com/wiki/Relationship) — Trait compatibility + reputation progression
- [Tech Support: Error Unknown dialogue](https://www.gamedeveloper.com/design/developing-a-procedural-dialogue-system-for-tech-support-error-unknown) — Procedural speech modulation by personality
