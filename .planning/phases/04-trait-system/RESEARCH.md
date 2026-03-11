# Phase 4 Research: Trait System

## Codebase Analysis

### Seed Infrastructure
- `_name_keys`: 30k unique integers, sampled with seed 42
- Already used by: creatures (`generate_creature(seed)`), planets, audio, names
- Trait generation: hash same key → 4 independent axis values

### Creature Generation Pipeline (`lib/graphics.py`)
- `generate_creature(seed, size)` → `(Surface, eye_info)`
- Uses `np.random.RandomState(seed)` — all RNG calls consume in fixed order
- Pipeline: `_color_from_seed` → `_generate_body_outline` → `_generate_appendages` → `_triangulate_and_shade` → `_apply_markings` → `_apply_eyes`
- **Key constraint:** Cannot insert trait-based RNG calls before existing pipeline without breaking all creature appearances
- **Solution:** Generate traits from a separate RNG (e.g., `RandomState(seed ^ TRAIT_SALT)`) or hash-based derivation, then apply as post-pipeline modifiers

### Detail Panel (`main.py:906-977`)
- Renders: planet (64px), creature (64px), then text lines (name, dist, coords, audio)
- `line_height = 16`, `padding = 8`
- Panel size computed dynamically from content
- Adding trait bars: append below existing text lines, adjust panel height

### Color/Marking Pipeline
- `_color_from_seed(rng)` → HSV color with hue [0,360], sat [0.5,1.0], val [0.6,1.0]
- `_generate_body_outline(rng, size)` → symmetric polygon, 6-12 control points, width [0.06,0.32]*size
- `_generate_appendages(rng, ...)` → 1-4 appendages (horn/fin/limb/spike)
- Trait visual mapping (from 4-CONTEXT.md):
  - Aggressive-Passive → body spikiness/angularity
  - Curious-Aloof → eye size
  - Friendly-Hostile → color temperature
  - Brave-Fearful → body size/bulk

## Approach: Trait-Biased Creature Modification

**Generate traits independently** of creature RNG (separate seed derivation) to avoid breaking existing visuals for neutral creatures (traits ≈ 50).

**Apply as post-pipeline modifiers:**
1. Color temperature shift (friendly-hostile): adjust hue after `_color_from_seed`
2. Body scale (brave-fearful): scale outline verts before rasterize
3. Spikiness (aggressive-passive): modify appendage count/length
4. Eye size (curious-aloof): scale eye radius in `_apply_eyes`

**Dead zone 40-60:** traits in this range produce no visual change.

## Risk Assessment

- **Breaking existing creatures**: Mitigated by separate RNG + dead zone
- **32px visibility**: Color temperature most visible; spikiness may be subtle at small sizes
- **Panel height growth**: 4 trait bars add ~80px; may need scroll or condensed layout at screen edges
