---
phase: quick-5
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - main.py
autonomous: true
requirements: [QUICK-5]

must_haves:
  truths:
    - "All in-game text renders visibly larger than before"
    - "Gamepedia left sidebar rows still fit text without overflow"
    - "Line spacing / layout spacing is unchanged"
  artifacts:
    - path: "main.py"
      provides: "Font size constants bumped"
      contains: "pygame.font.Font(None, 18)"
  key_links:
    - from: "main.py font declarations (lines 57-59)"
      to: "All font.render() calls throughout main.py"
      via: "shared font variable"
      pattern: "font\\.render"
---

<objective>
Increase base font size from 14 to 18 (and scale the heading fonts proportionally)
without touching any line-height or layout spacing constants.

Purpose: Text at size 14 is hard to read; bumping to 18 improves readability while
keeping GP_LINE_H=24 and all padding values intact.
Output: main.py with updated font sizes, visually larger text, no layout breakage.
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
  <name>Task 1: Bump font sizes in main.py</name>
  <files>main.py</files>
  <action>
    In main.py around lines 57-59, change the three font declarations:

    Before:
      font     = pygame.font.Font(None, 14)
      font_22  = pygame.font.Font(None, 22)
      font_28  = pygame.font.Font(None, 28)

    After:
      font     = pygame.font.Font(None, 18)
      font_22  = pygame.font.Font(None, 26)
      font_28  = pygame.font.Font(None, 32)

    Rationale:
    - Base font 14 -> 18: +4px, roughly 28% bigger, much more readable
    - font_22 -> 26 and font_28 -> 32: proportional bump so headings keep visual hierarchy
    - GP_LINE_H = 24 is left unchanged. At size 18, actual glyph height is ~18px, which fits
      inside 24px rows with ~3px padding each side — no text overflow
    - No other constants (GP_LINE_H, GP_TOP_Y, GP_LEFT_W, sidebar widths, padding values)
      should be touched in this task

    Do not change screenshot.py — that file has its own independent font at size 14 used
    only for debug overlays, not the main game UI.
  </action>
  <verify>
    <automated>cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -c "import ast, sys; ast.parse(open('main.py').read()); print('syntax ok')"</automated>
  </verify>
  <done>
    main.py parses cleanly. Font(None, 18) appears on the base font line.
    font_22 is now 26, font_28 is now 32.
    No layout spacing constants were modified.
  </done>
</task>

</tasks>

<verification>
Run the test suite to confirm nothing broke:

  cd /home/sanderburuma/Projects/4sphere-explorer && ./venv/bin/python -m pytest tests/ -q

All tests should still pass — font sizes are not tested by the existing suite (tests use mock
fonts with explicit char_width), so zero test changes are expected.
</verification>

<success_criteria>
- main.py syntax is valid
- Base font is Font(None, 18), heading fonts are 26 and 32
- All existing tests pass
- GP_LINE_H and all other layout constants are unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/5-text-should-be-a-little-bigger-without-i/5-SUMMARY.md`
</output>
