"""Procedural dialogue generation based on creature traits and reputation."""

import hashlib

# -- Reputation tier thresholds --
# score 0 = stranger, 1-2 = acquaintance, 3-5 = familiar, 6-8 = friend, 9-10 = devoted

def _reputation_tier(score):
    """Map reputation score (0-10) to tier name."""
    if score <= 0:
        return "stranger"
    elif score <= 2:
        return "acquaintance"
    elif score <= 5:
        return "familiar"
    elif score <= 8:
        return "friend"
    else:
        return "devoted"


# -- Trait value to temperature --
# 0-33 = low end of axis, 34-66 = neutral, 67-100 = high end

def _trait_temp(value):
    """Map trait value (0-100) to 'low', 'neutral', or 'high'."""
    if value <= 33:
        return "low"
    elif value <= 66:
        return "neutral"
    else:
        return "high"


# -- Word banks --
# Each keyed by temperature level for the relevant trait axis.

# friendly_hostile: 0=friendly (low), 100=hostile (high)
GREETINGS = {
    "low": ["Hello there", "Welcome, friend", "Good to see you", "Hey, glad you came"],
    "neutral": ["Hmm", "Oh", "You again", "Ah, hello"],
    "high": ["What do you want", "Leave me be", "Tch", "Go away"],
}

# friendly_hostile: 0=friendly (low), 100=hostile (high)
FAREWELLS = {
    "low": ["Safe travels", "Come back soon", "Until next time, friend", "Take care out there"],
    "neutral": ["Later", "See you around", "Goodbye", "Right then"],
    "high": ["Now leave", "We're done here", "Don't linger", "Off with you"],
}

# curious_aloof: 0=curious (low), 100=aloof (high)
BODY_CURIOUS = [
    "What brings you to this curve of space?",
    "Have you noticed how the light bends here?",
    "I wonder what lies beyond the next fold...",
    "Tell me, what have you seen out there?",
]

BODY_NEUTRAL = [
    "Things are as they are.",
    "The geometry holds steady.",
    "Another cycle, another rotation.",
    "Not much changes around here.",
]

BODY_ALOOF = [
    "I have nothing to say.",
    "...",
    "Hmph.",
    "Don't expect conversation.",
]

BODY = {
    "low": BODY_CURIOUS,
    "neutral": BODY_NEUTRAL,
    "high": BODY_ALOOF,
}

# aggressive_passive: 0=aggressive (low), 100=passive (high)
VERBS = {
    "low": ["demands", "insists", "declares", "asserts"],
    "neutral": ["says", "mentions", "notes", "remarks"],
    "high": ["suggests", "wonders", "murmurs", "whispers"],
}

# brave_fearful: 0=brave (low), 100=fearful (high)
ADVERBS = {
    "low": ["boldly", "confidently", "fearlessly", "defiantly"],
    "neutral": ["calmly", "steadily", "evenly", "plainly"],
    "high": ["nervously", "cautiously", "timidly", "hesitantly"],
}

# -- Templates by reputation tier --
# Slots: {greeting}, {body}, {farewell}, {verb}, {adverb}

TEMPLATES = {
    "stranger": [
        "...who are you? *{adverb} steps back*",
        "{greeting}. I don't know you.",
        "*eyes you {adverb}* {body}",
        "{body} *{verb} nothing more*",
    ],
    "acquaintance": [
        "{greeting}. {body} {farewell}.",
        "*nods {adverb}* {body}",
        "{greeting}. *{adverb} {verb}* I've seen you before. {farewell}.",
        "{body} *{adverb} glances away* {farewell}.",
        "*{verb} {adverb}* You're back. {body}",
    ],
    "familiar": [
        "{greeting}! {body} *{adverb} smiles* {farewell}.",
        "*{adverb} waves* {greeting}. I was just thinking... {body}",
        "{greeting}. You know, {body} {farewell}.",
        "*{verb} {adverb}* Ah, it's you again! {body}",
        "{body} *{adverb} {verb}* I think we understand each other. {farewell}.",
    ],
    "friend": [
        "{greeting}! *{adverb} embraces you* {body} {farewell}!",
        "*{adverb} laughs* {greeting}! {body} I always enjoy our talks. {farewell}.",
        "{greeting}! I've been wanting to tell you... {body} {farewell}!",
        "*{adverb} {verb}* My friend! {body} The hypersphere feels smaller with you here.",
        "{greeting}! Between you and me... {body} *{adverb} winks* {farewell}.",
    ],
    "devoted": [
        "{greeting}! *{adverb} {verb}* {body} {lore} {farewell}!",
        "*{adverb} takes your hand* {greeting}. I must share something... {lore} {farewell}.",
        "{greeting}! {body} And listen... {lore} *{adverb} nods* {farewell}!",
        "*{adverb} {verb}* Dear friend... {lore} {body} {farewell}!",
        "{greeting}! {lore} *{adverb} gazes into the distance* {body} {farewell}.",
    ],
}

# -- Lore snippets (devoted tier only) --
# Observations about 4D geometry and the S3 world.

LORE_SNIPPETS = [
    "The paths here curve in ways you can't see. Every straight line is a great circle.",
    "I've been watching the stars from a direction you haven't looked... the fourth one.",
    "Did you know? If you walk far enough in any direction, you end up right back here.",
    "Most of the volume of our world is near the boundary. Strange, isn't it?",
    "The rotations here aren't like anything in flat space. Two perpendicular planes can spin independently.",
    "I once tried counting neighbors. In four dimensions, you can fit more than you'd expect.",
    "Our world is finite but has no edge. Like a sphere's surface, but one dimension grander.",
    "Quaternions describe every rotation in our space. Algebra made manifest.",
]


def _pick(bank, temp, rng_val):
    """Pick from a word bank list using a deterministic value."""
    items = bank[temp]
    return items[rng_val % len(items)]


def _pick_list(lst, rng_val):
    """Pick from a plain list using a deterministic value."""
    return lst[rng_val % len(lst)]


def generate_dialogue(name_key, traits, reputation_score):
    """Return a dialogue line for a creature based on its traits and reputation.

    Deterministic: same inputs produce same output (seeded by name_key + reputation_score).

    Args:
        name_key: int -- unique creature identifier
        traits: dict with keys aggressive_passive, curious_aloof, friendly_hostile,
                brave_fearful, each 0-100
        reputation_score: int 0-10

    Returns:
        str -- a single dialogue line
    """
    # Clamp reputation to valid range
    score = max(0, min(10, int(reputation_score)))
    tier = _reputation_tier(score)

    # Deterministic seed from name_key + reputation_score
    seed_bytes = int(name_key).to_bytes(8, "little") + int(score).to_bytes(4, "little")
    digest = hashlib.md5(seed_bytes).digest()

    # Extract 8 pseudo-random values from the 16-byte digest
    rng = [b for b in digest]

    # Trait temperatures
    fh_temp = _trait_temp(traits.get("friendly_hostile", 50))
    ca_temp = _trait_temp(traits.get("curious_aloof", 50))
    ap_temp = _trait_temp(traits.get("aggressive_passive", 50))
    bf_temp = _trait_temp(traits.get("brave_fearful", 50))

    # Pick slot fillers
    greeting = _pick(GREETINGS, fh_temp, rng[0])
    farewell = _pick(FAREWELLS, fh_temp, rng[1])
    body = _pick(BODY, ca_temp, rng[2])
    verb = _pick(VERBS, ap_temp, rng[3])
    adverb = _pick(ADVERBS, bf_temp, rng[4])

    # Pick lore snippet (used only in devoted tier)
    lore = _pick_list(LORE_SNIPPETS, rng[5])

    # Pick template from tier pool
    pool = TEMPLATES[tier]
    template = pool[rng[6] % len(pool)]

    # Fill slots -- only fill {lore} if it appears in template
    result = template.format(
        greeting=greeting,
        farewell=farewell,
        body=body,
        verb=verb,
        adverb=adverb,
        lore=lore,
    )

    return result
