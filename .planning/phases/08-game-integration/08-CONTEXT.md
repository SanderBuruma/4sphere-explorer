# Phase 8: Game Integration - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire conditional rendering guards into the compass widget call in main.py so the compass respects game state: hidden when Gamepedia overlay is open and visible only in view mode 0 (Assigned colors).

</domain>

<decisions>
## Implementation Decisions

### Gamepedia guard (WIDG-02)
- Compass must not render when `gamepedia_open` is True
- The gamepedia overlay already draws after the compass (Z-order covers it visually), but an explicit guard prevents unnecessary rendering and removes visual flash
- Guard check: `not gamepedia_open`

### View mode gate (WIDG-03)
- Compass renders only when `view_mode == 0` (Assigned colors mode)
- Other view modes (1: 4D Position, 2: XYZ Projection, 3: XYZ Fixed-Y) have their own visual indicators — compass is irrelevant there
- Guard check: `view_mode == 0`

### Guard style
- Single combined conditional: `if view_mode == 0 and not gamepedia_open:` wrapping the existing `render_compass()` call at line 1240
- No fade/transition animation — instant show/hide matches existing Gamepedia and mode-switch behavior

### Gamepedia documentation
- Update the existing Compass topic in GAMEPEDIA_CONTENT to note visibility conditions (only in Assigned mode, hidden behind Gamepedia)

### Claude's Discretion
- Whether to update the Compass Gamepedia entry text (minor wording)
- Test approach for the guards

</decisions>

<specifics>
## Specific Ideas

No specific requirements — the implementation is fully prescribed by the two requirements and existing code patterns.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_compass(screen, orientation, x=10, y=10, size=120)` — already integrated at main.py:1240
- `gamepedia_open` boolean — main.py:195, toggled at lines 322-332
- `view_mode` integer — main.py:184, cycled at line 351

### Established Patterns
- Gamepedia guards: `if not gamepedia_open:` used at lines 260, 308 for input suppression
- View mode checks: `if view_mode in (2, 3):` at line 607, `if view_mode == 0:` at line 704
- Mode label display: line 1234 shows current mode name

### Integration Points
- Single change point: main.py:1240 — wrap in conditional
- Gamepedia content: lib/gamepedia.py GAMEPEDIA_CONTENT Compass entry
- Test assertions: tests/test_gamepedia.py if topic text changes

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-game-integration*
*Context gathered: 2026-03-12*
