# Phase 4 Context: Trait System

**Phase Goal**: Every creature has a deterministic personality that the player can see and that shows through its appearance
**Requirements**: TRAIT-01, TRAIT-02, TRAIT-03

---

## Decisions

### 1. Visual Trait Expression (TRAIT-03)

**Approach**: Modify existing creature generation — traits bias the RNG choices already in `generate_creature()`. No new visual layers (auras, badges, particles).

**Mapping**: 1:1 — each trait axis controls a specific visual channel:
- Aggressive-Passive → body spikiness / outline angularity
- Curious-Aloof → eye size
- Friendly-Hostile → color temperature (warmer ↔ cooler)
- Brave-Fearful → body size / bulk

**Visibility**: Glanceable at 32×32 — color shifts and shape changes must be visible even in sidebar thumbnails.

**Baseline**: Neutral creatures (traits near 50) look exactly like current generation. Traits only modify appearance at extremes.

### 2. Trait Display Format (TRAIT-02)

**Format**: Horizontal labeled bars in the detail panel:
```
Aggressive-Passive  [████████░░] Ferocious
Curious-Aloof       [█████░░░░░] Curious
Friendly-Hostile    [██░░░░░░░░] Hostile
Brave-Fearful       [███████░░░] Bold
```

**Labels**: Full axis names (Aggressive-Passive, not just Aggressive).

**Placement**: Inline in the existing detail panel, below current info lines (name, dist, coords, audio).

**Qualitative labels**: Descriptive words replace raw numbers — "Ferocious" instead of "82". Words only appear outside the dead zone; within the dead zone, show plain axis name only.

### 3. Extreme Trait Thresholds

**Scaling**: Graduated — visual intensity scales linearly with distance from 50. Farther from 50 = more pronounced visual change.

**Dead zone**: 40–60 (narrow) — only truly middling creatures look neutral. Most creatures show some trait influence.

**Stacking**: All traits express simultaneously — a creature that's aggressive AND curious shows both spikiness and large eyes. No cap on concurrent visual changes.

**Descriptor thresholds**: Words in the panel only appear outside the 40–60 dead zone. Within dead zone, display just the axis name (no descriptor).

---

## Code Context

**Seed infrastructure**: `_name_keys` array (30k unique integers), already used for creatures, planets, audio. Trait generation will hash these same keys.

**Creature generation**: `lib/graphics.py:generate_creature(seed, size)` — takes integer seed, uses `np.random.RandomState(seed)` for all RNG. Trait biases will need to be injected into or layered on top of this pipeline.

**Detail panel**: `main.py:906–977` — renders name, distance, coords, audio params as text lines with `font.render()`. Trait bars will be added below existing lines.

**Radial menu**: Only "Info" wedge is active (wedges A/B/C are placeholder). Traits go in the Info panel, not a new wedge.

---

## Deferred Ideas

(None — all discussion stayed within Phase 4 scope)

---
*Created: 2026-03-11*
