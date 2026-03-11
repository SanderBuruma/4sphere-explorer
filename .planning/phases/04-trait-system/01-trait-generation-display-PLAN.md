# Plan 01: Trait Generation & Display

**Phase:** 4 — Trait System
**Requirements:** TRAIT-01, TRAIT-02
**Goal:** Every creature has 4 deterministic personality traits (0-100), displayed as labeled bars in the detail panel

---

## Tasks

### 1. Create `lib/traits.py` — trait generation module

New file with:

```python
def generate_traits(name_key: int) -> dict:
    """Return 4 trait axes (0-100) deterministically from name_key.

    Uses hash-based derivation (not RandomState) to avoid coupling
    with creature RNG sequence.

    Returns dict with keys:
        aggressive_passive, curious_aloof, friendly_hostile, brave_fearful
    Each value int 0-100.
    """
```

**Implementation:** Use `hashlib.md5(name_key.to_bytes(8, 'little'))` → split 16 digest bytes into 4 groups of 4 bytes → `int.from_bytes % 101` for each axis. Fast, deterministic, zero coupling with existing RNG.

**Axis semantics (0→100):**
- aggressive_passive: 0=aggressive, 100=passive
- curious_aloof: 0=curious, 100=aloof
- friendly_hostile: 0=friendly, 100=hostile
- brave_fearful: 0=brave, 100=fearful

Add descriptor function:
```python
def trait_descriptor(axis_name: str, value: int) -> str:
    """Return qualitative label for trait value, or '' if in dead zone (40-60)."""
```

Descriptor table per axis, 4-5 tiers per side (e.g., aggressive_passive: 0-10 "Ferocious", 11-25 "Aggressive", 26-39 "Assertive", 40-60 "", 61-74 "Gentle", 75-89 "Docile", 90-100 "Placid").

### 2. Add trait bars to detail panel (`main.py`)

After existing text lines (name, dist, coords, audio), render 4 horizontal trait bars:

```
Aggressive-Passive  [████████░░] Ferocious
```

Each bar:
- Label text (axis name) left-aligned
- Filled rect proportional to value/100, colored with panel_color
- Empty rect remainder in dark gray
- Descriptor text right of bar (or omitted if dead zone)
- Bar width: ~120px, height: 10px
- Total added height: 4 × line_height (~64px)

Update `panel_h` calculation to include trait bar rows. Update `panel_w` if bar labels are wider than existing content.

### 3. Wire traits into `main.py` state

- Import `generate_traits` from `lib/traits.py`
- In the detail panel render block: call `generate_traits(_name_keys[inspected_point_idx])` (no caching needed — hash is fast)
- Build bar rendering loop after existing text lines

### 4. Add tests (`tests/test_traits.py`)

- Determinism: same key → same traits across calls
- Different keys → different trait values (test 10+ keys)
- Range: all values 0-100
- Descriptor: correct labels at extremes, empty in dead zone
- Independence from creature RNG: generating traits doesn't affect `generate_creature()` output

---

## Acceptance Criteria (maps to success criteria)

- [SC-1] Detail panel shows 4 labeled trait scores for any inspected creature
- [SC-2] Two different creatures have different traits; same creature always has same traits
- Traits generated via hash (no coupling with creature/planet/audio RNG)

---

## Files Modified

| File | Change |
|------|--------|
| `lib/traits.py` | **NEW** — trait generation + descriptors |
| `main.py` | Detail panel: add trait bar rendering |
| `tests/test_traits.py` | **NEW** — trait tests |
