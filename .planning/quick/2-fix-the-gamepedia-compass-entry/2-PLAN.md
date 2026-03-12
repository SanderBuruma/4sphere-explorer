---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - lib/gamepedia.py
autonomous: true
requirements: [QUICK-2]

must_haves:
  truths:
    - "Gamepedia Compass entry describes two rings, not three components"
    - "NS ring (blue-white, Y-axis poles) is documented accurately"
    - "W ring (amber, W+/W- poles) is documented accurately"
    - "Visibility condition (Assigned color mode only) is mentioned"
  artifacts:
    - path: "lib/gamepedia.py"
      provides: "Updated Compass topic text"
      contains: "NS ring"
  key_links:
    - from: "lib/gamepedia.py Compass text"
      to: "lib/compass.py render_compass()"
      via: "Manual accuracy check"
      pattern: "NS ring|W ring|blue|amber"
---

<objective>
Rewrite the Gamepedia "Compass" entry to describe the current two-ring widget
instead of the old three-component design (rose + tilt bar + W gauge).

Purpose: Keep in-game documentation accurate after the compass rewrite in quick task 1.
Output: Updated Compass topic text in lib/gamepedia.py lines 254-268.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite Gamepedia Compass entry</name>
  <files>lib/gamepedia.py</files>
  <action>
Replace the ("Compass", """...""") tuple at lines 254-268 in GAMEPEDIA_CONTENT.

The new text must describe the two-ring widget accurately. Key facts to include:

- Widget location: top-left corner, visible in Assigned color mode only (V to cycle), hidden in other view modes and while Gamepedia is open.
- NS ring: blue-white ring, great circle in the XY plane of R4. Its poles mark the Y+ (N) and Y- (S) directions. Front arcs are bright and solid, back arcs are dim and dashed.
- W ring: amber ring, great circle in the XW plane of R4. Its poles mark the W+ and W- directions. Same front/back rendering convention.
- Faint grey horizon circle serves as a reference for the widget center.
- All rings use fixed standard basis axes — shows absolute 4D orientation, not camera-relative.

Write it as flowing prose matching the style and length of other Gamepedia entries (roughly 80-120 words). Do NOT mention the old compass rose, tilt bar, or W gauge.
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -m pytest tests/test_gamepedia.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>Compass entry describes the NS ring and W ring. No references to "compass rose", "tilt bar", or "W Gauge". Gamepedia tests pass.</done>
</task>

</tasks>

<verification>
- grep for "NS ring" and "W ring" appears in the Compass entry
- grep for "Compass Rose", "Tilt Bar", "W Gauge" returns nothing in the Compass entry
- ./venv/bin/python -m pytest tests/test_gamepedia.py -x -q passes
</verification>

<success_criteria>
Gamepedia Compass entry accurately describes the two-ring widget. Tests pass.
</success_criteria>

<output>
After completion, create .planning/quick/2-fix-the-gamepedia-compass-entry/2-SUMMARY.md
</output>
