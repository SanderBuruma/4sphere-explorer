# Plan 02: Dialogue System

**Phase:** 5 — Reputation & Dialogue
**Requirements:** DIAL-01, DIAL-02
**Goal:** Creatures produce procedural dialogue that varies with traits and shifts tone based on reputation tier

---

## Tasks

### 1. Create `lib/dialogue.py` — dialogue generation module

New file with:

```python
def generate_dialogue(name_key: int, traits: dict, reputation_score: int) -> str:
    """Return a dialogue line for a creature based on its traits and reputation.

    Deterministic: same inputs → same output (seeded by name_key + reputation_score).
    """
```

**Template structure:** Each reputation tier has a pool of 4-6 template strings with `{slots}`:

```python
TEMPLATES = {
    "stranger": [
        "{greeting}... {body_cautious} {farewell_brief}",
        "{body_question} {farewell_brief}",
        # ...
    ],
    "acquaintance": [...],
    "familiar": [...],
    "friend": [...],
    "devoted": [...],
}
```

**Word banks** — trait-influenced slot fillers:

```python
GREETINGS = {
    "warm": ["Hello there", "Welcome, friend", "Good to see you"],
    "neutral": ["Hmm", "Oh", "You again"],
    "cold": ["What do you want", "Leave me be", "Tch"],
}
```

Trait axis → bank selection:
- `friendly_hostile` (0=friendly, 100=hostile): selects greeting warmth and farewell tone
- `curious_aloof` (0=curious, 100=aloof): body content — curious creatures ask questions, aloof ones make short statements
- `aggressive_passive`: verb intensity in body text ("demands" vs "wonders" vs "suggests")
- `brave_fearful`: confidence modifiers ("boldly" vs "nervously" vs "cautiously")

**Selection logic:**
1. Get tier from reputation score
2. Pick template from tier pool: `hash(name_key, reputation_score) % len(pool)`
3. For each slot, trait values pick from appropriate word bank sub-list
4. Final string assembled via `.format()` or f-string equivalent

### 2. Write ~25 base templates across 5 tiers

**Stranger (score 0):** 4 templates — short, wary, minimal
```
"...who are you? {body_cautious}"
"{greeting_cold}. I don't know you."
"*eyes you {adverb_fearful}* {body_question_short}"
"{body_statement_brief}."
```

**Acquaintance (1-2):** 5 templates — neutral, acknowledging
**Familiar (3-5):** 5 templates — warm, conversational, may share info
**Friend (6-8):** 5 templates — enthusiastic, helpful, personal
**Devoted (9-10):** 5 templates — affectionate, reveals "secrets" (procedural lore snippets)

Each template uses 2-4 slots. Total: ~25 templates × multiple word banks = thousands of effective combinations.

### 3. Build word banks (4 trait-influenced dimensions)

Each bank has 3 temperature levels (low/neutral/high for the trait axis):
- **Greeting** bank (friendly_hostile): warm / neutral / cold → 3-4 phrases each
- **Body** bank (curious_aloof): question / statement / remark → 3-4 each
- **Verb** bank (aggressive_passive): intense / normal / gentle → 3-4 each
- **Adverb** bank (brave_fearful): bold / steady / nervous → 3-4 each
- **Farewell** bank (friendly_hostile): warm / neutral / dismissive → 3-4 each

Trait value maps to temperature: 0-33 = low end, 34-66 = neutral, 67-100 = high end.

### 4. Add lore snippets for devoted tier

At reputation 9-10, creatures share "secrets" — procedurally generated observations about the 4D world:
- References to nearby points by name (pick from visible points list)
- Vague hints about the geometry ("The paths here curve in ways you can't see...")
- Personal observations seeded by traits ("I've been watching the stars from a direction you haven't looked...")

5-8 lore snippets, selected by `hash(name_key) % len(snippets)`.

### 5. Add tests (`tests/test_dialogue.py`)

- **Determinism:** same name_key + traits + reputation → same dialogue
- **Variation:** different name_keys with same traits → different dialogue (template selection varies)
- **Trait influence:** creature with friendly=10 produces warmer greeting than friendly=90 (hostile)
- **Tier shift:** same creature at reputation 0 vs reputation 5 → different dialogue tone
- **All tiers covered:** generate dialogue at scores 0, 1, 3, 6, 9 → each returns non-empty string
- **No crashes:** edge cases — score 0, score 10, extreme trait values (0 and 100)

---

## Acceptance Criteria (maps to success criteria)

- [SC-1] Interacting with a creature displays dialogue that differs across creatures with different trait combos
- [SC-2] First-visit creature vs ten-visits creature show different dialogue tone
- Dialogue is deterministic for same inputs
- Templates cover all 5 reputation tiers

---

## Files Modified

| File | Change |
|------|--------|
| `lib/dialogue.py` | **NEW** — template pools, word banks, `generate_dialogue()` |
| `tests/test_dialogue.py` | **NEW** — dialogue generation tests |
