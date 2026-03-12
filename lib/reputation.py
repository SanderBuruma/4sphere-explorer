"""Reputation tracking for creature relationships.

Sparse dict storage: only creatures the player has interacted with get entries.
Score clamped to [0, 10] on every mutation.
"""

REPUTATION_TIERS = [
    (0, 0, "Stranger"),
    (1, 2, "Acquaintance"),
    (3, 5, "Familiar"),
    (6, 8, "Friend"),
    (9, 10, "Devoted"),
]


def get_tier(score):
    """Return tier name for reputation score."""
    for lo, hi, name in REPUTATION_TIERS:
        if lo <= score <= hi:
            return name
    return "Stranger"


def get_reputation(store, idx):
    """Return reputation entry for point idx, or default."""
    return store.get(idx, {"score": 0, "visits": 0, "talked_this_visit": False})


def record_visit(store, idx):
    """Increment visit count. First visit grants +1 reputation. Returns updated entry."""
    entry = store.get(idx)
    if entry is None:
        # First ever visit: create entry with +1 rep
        entry = {"score": 1, "visits": 1, "talked_this_visit": False}
    else:
        entry["visits"] += 1
        entry["talked_this_visit"] = False
    entry["score"] = max(0, min(10, entry["score"]))
    store[idx] = entry
    return entry


def record_talk(store, idx):
    """Grant +1 reputation for talking (once per visit). Returns updated entry."""
    entry = store.get(idx)
    if entry is None:
        entry = {"score": 0, "visits": 0, "talked_this_visit": False}
        store[idx] = entry
    if not entry["talked_this_visit"]:
        entry["score"] = max(0, min(10, entry["score"] + 1))
        entry["talked_this_visit"] = True
    return entry


def reset_visit_flags(store):
    """Clear talked_this_visit flags for all entries."""
    for entry in store.values():
        entry["talked_this_visit"] = False
