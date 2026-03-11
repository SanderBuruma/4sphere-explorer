"""Seed-deterministic personality traits for creatures."""

import hashlib

TRAIT_AXES = ("aggressive_passive", "curious_aloof", "friendly_hostile", "brave_fearful")

TRAIT_LABELS = {
    "aggressive_passive": "Aggressive-Passive",
    "curious_aloof": "Curious-Aloof",
    "friendly_hostile": "Friendly-Hostile",
    "brave_fearful": "Brave-Fearful",
}

_DESCRIPTORS = {
    "aggressive_passive": [
        (0, 10, "Ferocious"), (11, 25, "Aggressive"), (26, 39, "Assertive"),
        (61, 74, "Gentle"), (75, 89, "Docile"), (90, 100, "Placid"),
    ],
    "curious_aloof": [
        (0, 10, "Obsessed"), (11, 25, "Curious"), (26, 39, "Inquisitive"),
        (61, 74, "Reserved"), (75, 89, "Aloof"), (90, 100, "Detached"),
    ],
    "friendly_hostile": [
        (0, 10, "Devoted"), (11, 25, "Friendly"), (26, 39, "Warm"),
        (61, 74, "Cold"), (75, 89, "Hostile"), (90, 100, "Vicious"),
    ],
    "brave_fearful": [
        (0, 10, "Fearless"), (11, 25, "Brave"), (26, 39, "Bold"),
        (61, 74, "Nervous"), (75, 89, "Fearful"), (90, 100, "Terrified"),
    ],
}


def generate_traits(name_key):
    """Return 4 trait axes (0-100) deterministically from name_key.

    Uses md5 hash to avoid coupling with creature/planet/audio RNG.
    """
    digest = hashlib.md5(int(name_key).to_bytes(8, "little")).digest()
    traits = {}
    for i, axis in enumerate(TRAIT_AXES):
        # 4 bytes per axis -> int mod 101 for range [0, 100]
        val = int.from_bytes(digest[i * 4:(i + 1) * 4], "little") % 101
        traits[axis] = val
    return traits


def trait_descriptor(axis_name, value):
    """Return qualitative label for trait value, or '' if in dead zone (40-60)."""
    for lo, hi, label in _DESCRIPTORS.get(axis_name, []):
        if lo <= value <= hi:
            return label
    return ""
