# Phase 8: Game Integration - Research

**Researched:** 2026-03-12
**Domain:** Pygame event handling, conditional widget rendering
**Confidence:** HIGH

## Summary

Phase 8 adds conditional rendering guards to the compass widget, respecting two game state flags: `gamepedia_open` (Gamepedia overlay visibility) and `view_mode` (current view mode). The implementation is straightforward — a single compound conditional wraps the existing `render_compass()` call in main.py at line 1240. No changes to the compass widget itself; no new dependencies; no architectural changes. This is purely a UI orchestration task using existing game state variables and patterns already established in the codebase.

**Primary recommendation:** Wrap the `render_compass()` call with `if view_mode == 0 and not gamepedia_open:` at main.py:1240. Update the Compass Gamepedia entry to document visibility conditions.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Compass must not render when `gamepedia_open` is True
- Compass renders only when `view_mode == 0` (Assigned colors mode)
- Single combined conditional: `if view_mode == 0 and not gamepedia_open:` at line 1240
- No fade/transition animation — instant show/hide
- Update Compass Gamepedia entry to note visibility conditions

### Claude's Discretion
- Whether to update Compass Gamepedia entry wording
- Test approach for the guards

### Deferred Ideas
- None

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIDG-02 | Compass hidden when Gamepedia overlay is open | `gamepedia_open` flag at main.py:195, toggled lines 322-332; render guard pattern established in codebase |
| WIDG-03 | Compass renders only in default view mode (mode 0) | `view_mode` integer at main.py:184, cycled at line 351; existing mode checks at lines 263, 269, 607, 612, 704 show established pattern |

</phase_requirements>

---

## Standard Stack

### Core Dependencies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pygame | 2.x+ | Event loop, input handling, drawing | Established game framework |
| numpy | 1.x+ | Vector math, orientation frame | Already used for 4D math |

### Supporting
| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| Game state variables | main.py:184, 195 | `view_mode`, `gamepedia_open` flags | Conditional rendering guards |
| `render_compass()` | lib/compass.py:107 | Compass widget rendering | Called unconditionally before guard |

---

## Architecture Patterns

### Established Conditional Rendering Pattern

The codebase already uses simple guard patterns for conditional rendering:

```python
# Pattern from main.py:260 — suppress input when Gamepedia is open
if not gamepedia_open:
    # Handle camera rotation input

# Pattern from main.py:607 — render different visuals per view mode
if view_mode in (2, 3):
    # XYZ Projection rendering
elif view_mode == 0:
    # Assigned color rendering
```

### Recommended Implementation: Compound Guard

**Location:** main.py, line 1240 (compass widget call)

**Current:**
```python
render_compass(screen, orientation, x=10, y=10, size=120)
```

**After guard:**
```python
if view_mode == 0 and not gamepedia_open:
    render_compass(screen, orientation, x=10, y=10, size=120)
```

**Why this pattern:**
- Matches established codebase style (lines 260, 308, 364, 372, 411, 509)
- No function extraction needed — single conditional sufficient
- Instant show/hide matches existing Gamepedia overlay behavior (no fade transition)
- `view_mode == 0` reads naturally as "Assigned mode only"
- `not gamepedia_open` is the standard guard used at 5 locations already

### Game State Dependencies

**`view_mode`** (main.py:184)
- Integer: 0, 1, 2, or 3
- Cycled via V key at line 351
- Persisted to save file (lib/persistence.py:28)
- Labels: "Assigned", "4D Position", "XYZ Projection", "XYZ Fixed-Y"
- Compass relevant only in mode 0 (Assigned colors)

**`gamepedia_open`** (main.py:195)
- Boolean flag
- Toggled via F1 key or ESC at lines 322-332
- Used at lines 260, 308, 322, 364, 372, 411, 509 for input suppression and event handling
- Never modified elsewhere in the codebase

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|------------|-------------|-----|
| Widget visibility logic | Custom state machine or fade transition | Simple boolean guards | Compass is optional; other view modes have own indicators; no fade needed |
| View mode enumerations | String-based mode names | Integer 0–3 stored in `view_mode` | Codebase convention; matches existing checks |
| Compass re-rendering every frame | Cache canvas or skip render entirely | Single conditional check | Negligible cost; compass module already handles Lerp and timing internally |

**Key insight:** The compass is a stateless render function (aside from internal Lerp animation). Skipping the call entirely is cleaner than pre-rendering and blitting a cached surface — no extra memory, no invalidation logic needed.

---

## Common Pitfalls

### Pitfall 1: Order-Dependent Rendering (Z-fighting)
**What goes wrong:** Rendering compass after the Gamepedia overlay means the compass appears on top of the overlay, creating visual overlap.

**Why it happens:** Pygame renders in call order; later calls appear on top.

**How to avoid:** Place the conditional guard on the compass call itself, before the Gamepedia overlay block (which already starts at line 1243). The guard ensures compass is skipped entirely when `gamepedia_open=True`, avoiding any Z-order issues.

**Verification:** Compass should be completely invisible (not even a faint outline) when F1 toggles Gamepedia open/closed.

### Pitfall 2: Forgetting to Update Gamepedia Entry
**What goes wrong:** Gamepedia documents compass as "always visible" but compass disappears when opening Gamepedia or switching view modes, confusing players.

**Why it happens:** Documentation updates are easy to forget in rendering logic changes.

**How to avoid:** Update the Compass entry in `GAMEPEDIA_CONTENT` (lib/gamepedia.py:254) to note visibility conditions. Current text says "top-left corner" and "always shows" — should clarify it's visible only in Assigned mode.

**Verification:** Read Compass topic in F1 overlay after changes; confirm mention of visibility conditions.

### Pitfall 3: Conditional Placed in Wrong Location
**What goes wrong:** Guard placed after compass call, or in the wrong branch of view_mode logic, causing compass to render in unwanted modes.

**Why it happens:** Copy-paste error or misunderstanding of control flow in the long render function.

**How to avoid:** Line 1240 is the single location where compass is rendered. Wrap that call only.

**Verification:** Test compass visibility in all 4 view modes; confirm it appears only in mode 0.

### Pitfall 4: Compass State Not Reset on Mode Switch
**What goes wrong:** Needle animation state (`_needle_angle`, `_target_angle`, `_lerp_progress` in lib/compass.py) persists when compass is hidden, causing a sudden jump when it reappears.

**Why it happens:** The compass module maintains animation state globally; hiding the widget doesn't reset it.

**How to avoid:** No action needed — the module automatically resets Lerp when the needle detects a new target. The animation state is private to lib/compass.py and doesn't corrupt on view mode switch or Gamepedia toggle.

**Verification:** Open Gamepedia, then close it. Compass needle should animate smoothly from wherever it was, not jump.

---

## Code Examples

### Conditional Guard Pattern (main.py, line 1240)

```python
# Source: main.py (established pattern at lines 260, 308, 364, 372, 411, 509)
if view_mode == 0 and not gamepedia_open:
    render_compass(screen, orientation, x=10, y=10, size=120)
```

This single conditional:
- Skips compass render when in any non-Assigned view mode
- Skips compass render when Gamepedia overlay is active
- Maintains all internal state in lib/compass.py unchanged
- Incurs negligible cost (one boolean check)

### Game State Access Pattern (main.py)

```python
# view_mode is module-level global, updated at line 351
view_mode = (view_mode + 1) % 4  # cycle on V key press

# gamepedia_open is module-level global, toggled at lines 322-332
if event.key == pygame.K_F1:
    gamepedia_open = not gamepedia_open
```

Both variables are directly accessible to the render function without additional refactoring.

### Updated Gamepedia Entry (lib/gamepedia.py, line 254)

**Current:**
```python
("Compass", """\
The compass widget (top-left corner) shows your absolute 4D orientation on S3.
...
All indicators use fixed reference axes..."""),
```

**After update (adds visibility condition):**
```python
("Compass", """\
The compass widget (top-left corner) shows your absolute 4D orientation on S3. \
Only visible in Assigned color mode (V key) — hidden in other view modes and when \
Gamepedia is open.

Compass Rose: The rotating needle points toward X+ in the XZ plane. \
...
All indicators use fixed reference axes..."""),
```

---

## State of the Art

| Aspect | Current Approach | Rationale |
|--------|------------------|-----------|
| Conditional rendering | Simple boolean guards at call site | Pygame convention; no framework overhead |
| Widget state management | Internal module-level state in lib/compass.py | Encapsulation; Lerp animation stays private |
| View mode representation | Integer 0–3 in `view_mode` global | Established codebase pattern |
| Gamepedia integration | Hard guard on compass call before overlay render | No Z-order issues; cleaner than post-render skip |

**Deprecated/outdated:**
- None — this phase doesn't replace or supersede prior approaches

---

## Implementation Checklist

- [ ] **Line 1240 guard:** Wrap `render_compass()` with `if view_mode == 0 and not gamepedia_open:`
- [ ] **Gamepedia text:** Add visibility note to Compass entry in GAMEPEDIA_CONTENT
- [ ] **Manual test:** Cycle view modes with V; confirm compass only in mode 0
- [ ] **Manual test:** Toggle Gamepedia with F1; confirm compass disappears/reappears cleanly
- [ ] **No animation jump:** Close Gamepedia after compass hidden; needle should animate smoothly

---

## Sources

### Primary (HIGH confidence)
- **main.py** — `view_mode` (line 184), `gamepedia_open` (line 195), render calls (1240–1243), existing guards (260, 308, 364, 372, 411, 509)
- **lib/compass.py** — `render_compass()` signature and implementation (lines 107–268)
- **CONTEXT.md** — Locked decisions and implementation requirements

### Secondary
- **lib/gamepedia.py** — GAMEPEDIA_CONTENT structure and Compass entry location (line 254)
- **lib/persistence.py** — Game state serialization showing `view_mode` is persisted

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pygame is established; no new dependencies
- Architecture: HIGH — conditional guard pattern fully documented in codebase with 6 existing examples
- Implementation: HIGH — single-line change location clear, game state flags well-tested and stable
- Pitfalls: HIGH — common issues identified from established patterns

**Valid until:** 30 days (stable scope, no external dependencies)
**Research date:** 2026-03-12
