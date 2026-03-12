# Research Summary: 4D Compass Widget

**Domain:** Game HUD compass widget for S³ navigation
**Researched:** 2026-03-12
**Overall confidence:** HIGH

---

## Executive Summary

A compass widget is a **table-stakes HUD element** in exploration games. Players expect directional feedback when navigating unfamiliar spaces. Standard game compasses (found in Minecraft, Skyrim, Baldur's Gate 3, GW2) converge on a single design pattern: **minimal, corner-positioned, always-visible indicator** showing cardinal directions with a rotating needle or rose.

For the 4D case, the design is analogous but not identical. Rather than showing magnetic cardinal directions, the 4D compass shows the player's **orientation frame relative to fixed standard basis axes** (X, Y, Z, W). The player's camera direction (which way they're facing) becomes a needle that rotates against four fixed axes.

**Key finding:** The math is already built in. The existing persistent orientation frame (`frame[0]` = camera direction, fixed axes) gives everything needed. No new quaternion math required — just projection and rendering.

**Confidence:** HIGH — This is a well-understood pattern in game design, directly applicable to 4D context via the existing orientation frame system.

---

## Key Findings

### Stack

**No new dependencies.** Compass uses only:
- Pygame rendering (existing)
- NumPy for angle extraction from orientation frame (existing)
- Game loop frame-update integration (existing)

**Estimate:** 2-3 pygame.Surface objects, simple per-frame transform rotation, < 1% CPU overhead.

### Features

**Table Stakes (MVP — v1.2):**
1. Cardinal direction labels (X, Y, Z, W) — identifies axes
2. Rotating needle showing camera direction in world space
3. Fixed-world axis reference (axes never rotate with camera)
4. Smooth Lerp animation on needle rotation (~200ms)
5. Corner positioning (top-right or top-left) with clean typography

**Differentiators (Phase 2–3):**
- 8-point compass rose (adds intercardinal directions)
- Vertical Y-axis indicator (shows pitch angle)
- W-axis depth indicator (color shift, ring, or glow; requires design choice)
- Numeric heading readout (degrees 0–360)
- Keyboard toggle to show/hide (declutters screen)
- Audio cue when aligned to cardinal directions

**Anti-Features to avoid:**
- Animated background textures (distracting)
- Dual compass showing two rotations (cognitive overload)
- Real-world "magnetic declination" adjustment (not applicable to 4D)
- Nested/zoomed detail view (redundant with existing detail panel)

### Architecture

**Integration points:**
1. **Rendering:** Draw in update_visible() or main loop after all 3D elements; layer on top of game view
2. **Data source:** Extract camera direction from existing `frame[0]` in sphere.py
3. **Animation:** Integrate into game loop's frame-by-frame Lerp system (same pattern as travel slerp)

**Key constraint:** Compass axes must be **absolutely fixed** (always pointing to same world directions). This is NOT relative to player's local frame — it's the inverse. Player's frame rotates; axes stay still.

**Rendering complexity:** Low. Single needle rotation per frame, cached string surfaces, simple 2D transforms.

---

## Implications for Roadmap

### Phase 1 (v1.2 — Current Milestone)

**What to build first:**
1. Static compass background with 4 cardinal labels (X, Y, Z, W) in corners
2. Needle rotation calculation from `frame[0]`
3. Smooth Lerp animation for needle
4. Place in top-right corner

**Why this order:**
- Labels must be first (visual foundation)
- Needle requires labels to be meaningful
- Animation makes it feel responsive, not janky
- Corner positioning is stable and unobtrusive

**Estimated effort:** 2 days

**Architecture:** Add function to `lib/compass.py`:
```python
class CompassWidget:
    def __init__(self, screen_size, corner='top_right'):
        self.size = 80  # pixels
        self.corner = corner
        self.needle_angle = 0.0  # current display angle
        self.target_angle = 0.0  # where needle should point
        self.update_duration = 0.2  # seconds for Lerp

    def update(self, orientation_frame, dt):
        """Update needle angle from frame[0], apply Lerp animation"""
        # Extract target angle from frame[0]
        # Lerp towards target_angle

    def draw(self, screen):
        """Draw compass surface with rotated needle"""
```

Integrate into `main.py` in update loop and draw phase.

### Phase 2 (v1.3 — Enhancements)

**Add if compass v1.2 is solid:**
- 8-point compass rose (reuse needle rotation math)
- Vertical Y-axis bar showing pitch
- Numeric heading readout

**Why defer:** Core functionality in v1.2 first; validate UX before adding complexity.

### Phase 3 (v1.4+ — Nice-to-have)

- W-axis indicator (requires visual design decision; potential high spike complexity)
- Keyboard toggle show/hide
- Audio cue on cardinal alignment

### Not Required

- Orbital/concentric rings (too complex, low value)
- Dual compasses (cognitive overload)
- Fade-on-idle animations (nice but not core)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Design pattern | HIGH | Compass rose is a proven game UI element; existing patterns in 50+ major games |
| Math correctness | HIGH | Orientation frame already validated in sphere.py; angle extraction is straightforward trig |
| Performance | HIGH | Rendering is negligible overhead; no complex geometry or real-time synthesis needed |
| Integration | HIGH | Fits cleanly into existing game loop; no architectural changes required |
| User expectations | MEDIUM | Compass is expected, but 4D context is novel; may need refinement based on player feedback (W-axis visualization) |

---

## Critical Design Decision: W-Axis Visualization

**Status:** Open question requiring design iteration.

The W-axis (4th dimension) is the unique challenge. Unlike X, Y, Z which map to standard 3D axes, W represents depth into/out of 4D space. Options:

1. **Color hue shift** (blue-to-red or blue-to-magenta)
   - Pros: Intuitive, reuses existing color system
   - Cons: Hard to precisely judge angle from hue alone

2. **Ring thickness or glow radius**
   - Pros: Independent visual channel
   - Cons: Hard to read at small sizes, feels clumsy

3. **Separate radial indicator** (second ring inside/outside compass)
   - Pros: Clear, doesn't clutter needle area
   - Cons: Takes up space, adds cognitive load

4. **No W indicator in MVP**
   - Pros: Simpler, focuses on core X/Y/Z navigation
   - Cons: Misses unique 4D aspect

**Recommendation:** Start with **option 4 (defer W-axis visualization to v1.3+)**. Get X/Y/Z compass working solidly in v1.2, then investigate W visualization with player feedback. The compass is already novel enough; don't over-engineer the first iteration.

---

## Gaps to Address

1. **W-axis visual design** — Needs prototyping and player feedback. Defer to Phase 2.
2. **Needle style aesthetics** — Arrow vs line vs other. Minor, can decide during implementation.
3. **Heading readout precision** — Do players need 1° accuracy or 5° buckets? Depends on use case. Start simple (10° buckets if shown).
4. **Keyboard hotkey** — If implementing toggle, which key? Consider conflicts with WASD/QE/V rotation controls. Suggestion: C key (intuitive for "compass").

---

## Sources

**Core references:**
- [Game UI Database - Compass](https://www.gameuidatabase.com/index.php?scrn=165)
- [Sense of Direction: Insurgency Compass Design Process](https://www.gamedeveloper.com/design/sense-of-direction-insurgency-compass-design-process)
- [Quaternions for Orientation](https://blog.endaq.com/quaternions-for-orientation)
- [Compass Rose - Wikipedia](https://en.wikipedia.org/wiki/Compass_rose)

**Implementation references:**
- [Smooth Rotation Animation JavaScript](https://javascriptio.com/view/4591131/javascript-how-to-create-a-smooth-rotation-animation-for-an-image-compass-needle)
- [Animated Compass Needle GitHub](https://github.com/carriexu24/Animated-Compass-Needle)
- [Transforming Game Interfaces with Animated UI](https://punchev.com/blog/transforming-game-interfaces-with-animated-ui)

---

*Last updated: 2026-03-12*
