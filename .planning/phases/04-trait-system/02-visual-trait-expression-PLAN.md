# Plan 02: Visual Trait Expression

**Phase:** 4 — Trait System
**Requirements:** TRAIT-03
**Depends on:** Plan 01 (needs `generate_traits()`)
**Goal:** Creatures with extreme traits look visibly different from neutral ones

---

## Tasks

### 1. Add trait-aware creature generation (`lib/graphics.py`)

Modify `generate_creature(seed, size)` to accept optional traits and apply visual biases. The existing RNG sequence stays untouched — trait effects are layered on top.

**Signature change:**
```python
def generate_creature(seed, size=32, traits=None):
```

When `traits` is None, behavior is identical to current (backwards compatible).

**Trait → visual mapping (graduated, dead zone 40-60):**

**a) Friendly-Hostile → color temperature shift**
- Applied after `_color_from_seed()`: shift hue toward warm (friendly, value→0) or cool (hostile, value→100)
- Intensity: `abs(value - 50) / 50` scaled to max ±30° hue shift
- Dead zone: no shift when 40-60
- Most visible at 32px — color is the strongest signal at small sizes

**b) Brave-Fearful → body scale**
- Scale outline control point widths: brave (→0) = wider/bulkier, fearful (→100) = narrower
- Multiply `ctrl_w` by factor: `1.0 + (50 - value) / 50 * 0.25` (±25% width change)
- Applied inside `_generate_body_outline()` via a scale parameter

**c) Aggressive-Passive → appendage intensity**
- Aggressive (→0): more appendages, longer, favor spikes/horns
- Passive (→100): fewer appendages, shorter, favor fins
- Modify `n_appendages` range and type weights in `_generate_appendages()`
- Pass trait value as parameter to bias RNG choices without changing RNG sequence for neutral creatures

**d) Curious-Aloof → eye size**
- Curious (→0): larger eyes (scale `eye_r` up to 1.3×)
- Aloof (→100): smaller eyes (scale `eye_r` down to 0.7×)
- Applied in `_apply_eyes()` via a scale parameter

### 2. Wire traits into creature generation call sites

In `main.py`, wherever `generate_creature()` is called:
- Import `generate_traits`
- Pass `traits=generate_traits(name_key)` to `generate_creature()`

Call sites:
- `get_creature()` in `lib/graphics.py` — sidebar/tooltip creatures (32px)
- Detail panel creature render (`main.py:962`) — large creature (64px)

### 3. Invalidate creature cache on first run

Since existing cached creatures won't have trait modifications, the LRU cache will naturally replace them as creatures are evicted and regenerated. No explicit cache bust needed — the cache is session-only.

### 4. Add visual trait expression tests (`tests/test_traits.py`)

Extend existing test file:
- Neutral creature (traits all 50) produces same output as `generate_creature(seed)` with no traits
- Extreme aggressive creature has more appendage pixels than passive one (count non-transparent pixels in appendage region)
- Extreme friendly creature has warmer hue than hostile one (measure average hue of body pixels)
- Extreme brave creature is wider than fearful one (measure body bounding box width)
- Extreme curious creature has larger eye radius than aloof one

---

## Acceptance Criteria (maps to success criteria)

- [SC-3] Creature with extreme trait values shows visible difference from a neutral creature
- Visual differences are glanceable at 32px (color temperature is primary signal)
- Neutral creatures (traits 40-60) look identical to current generation

---

## Files Modified

| File | Change |
|------|--------|
| `lib/graphics.py` | Add `traits` param to `generate_creature`, `_generate_body_outline`, `_generate_appendages`, `_apply_eyes`; apply graduated visual biases |
| `main.py` | Pass traits to `generate_creature()` calls |
| `tests/test_traits.py` | Add visual expression tests |
