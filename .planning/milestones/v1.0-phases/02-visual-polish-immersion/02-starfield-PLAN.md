---
phase: 02-visual-polish-immersion
plan: 02
type: execute
wave: 1
depends_on: []
files_modified: [main.py]
autonomous: true
requirements: [VIS-02]

must_haves:
  truths:
    - "Background displays slowly scrolling stars that shift perspective during 4D rotation to convey depth"
  artifacts:
    - path: "main.py"
      provides: "Animated starfield background with parallax during rotation"
      section: "Render section, after screen.fill() (~line 429)"
  key_links:
    - from: "main.py:render loop"
      to: "starfield drawing"
      via: "Draw stars between screen.fill() and point projection"
      pattern: "screen\\.fill\\(BG_COLOR\\)"
---

<objective>
Add an animated starfield background that parallax-shifts during 4D camera rotation, conveying depth and movement in the exploration space.

Purpose: Break the flat black background, make rotations feel like navigating through space, enhance immersion.

Output:
- Starfield rendered behind all gameplay elements with parallax response to camera orientation (main.py)
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Current render start (main.py:429):
```python
screen.fill(BG_COLOR)
```

Camera orientation frame (available each frame):
```python
orientation  # 4x4 array: row 0 = camera_pos, rows 1-3 = tangent basis
camera_pos = orientation[0]
basis = [orientation[1], orientation[2], orientation[3]]
```

View area dimensions: view_width = SCREEN_WIDTH - 300 = 900, SCREEN_HEIGHT = 800
Sidebar starts at x = 900.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate starfield and render with parallax</name>
  <files>main.py</files>
  <action>
    1. After the game state constants (around line ~60, near the color definitions), add starfield generation:

    ```python
    # Starfield: random 4D directions for parallax background
    NUM_STARS = 200
    _star_rng = np.random.default_rng(seed=123)
    # Stars as random unit vectors in 4D (directions on S³)
    _star_dirs = _star_rng.standard_normal((NUM_STARS, 4))
    _star_dirs /= np.linalg.norm(_star_dirs, axis=1, keepdims=True)
    _star_brightness = _star_rng.uniform(0.15, 0.6, NUM_STARS)
    _star_sizes = _star_rng.choice([1, 1, 1, 2], NUM_STARS)  # mostly 1px, some 2px
    ```

    2. In the render loop, immediately after `screen.fill(BG_COLOR)` (line 429), add starfield rendering:

    ```python
    # Render starfield with parallax from camera orientation
    star_parallax_scale = 300  # pixels of shift per radian of angular separation
    for si in range(NUM_STARS):
        # Project star direction onto camera tangent basis for 2D position
        star_dir = _star_dirs[si]
        # Dot products with tangent basis vectors give screen-space offsets
        sx = np.dot(star_dir, orientation[1]) * star_parallax_scale
        sy = np.dot(star_dir, orientation[2]) * star_parallax_scale
        # Wrap to screen with generous margin for smooth scrolling
        px = int((sx % view_width + view_width) % view_width)
        py = int((sy % SCREEN_HEIGHT + SCREEN_HEIGHT) % SCREEN_HEIGHT)
        # Only draw in view area (not sidebar)
        if px < view_width:
            brightness = _star_brightness[si]
            c = int(brightness * 255)
            pygame.draw.circle(screen, (c, c, int(c * 0.9)), (px, py), _star_sizes[si])
    ```

    Design rationale:
    - Stars are fixed 4D directions — rotating the camera changes which direction each tangent axis points, so the dot products shift, creating natural parallax.
    - 200 stars is sparse enough to look like a starfield background, not a noise field.
    - Wrapping with modulo gives seamless scrolling as the camera rotates.
    - The 3rd basis vector (depth/W axis) is not used — stars respond only to screen-plane rotations (X/Y tangent axes), keeping the effect intuitive.
    - Stars have a slight blue tint (c * 0.9 on blue channel) relative to warm white to feel space-like.
    - Stars only render in the view area (x < view_width), not the sidebar.
  </action>
  <verify>
    <manual>
      Run main.py, observe:
      - Background shows scattered dim stars behind points
      - Rotating with WASD causes stars to shift position smoothly (parallax)
      - Q/E (4D depth rotation) does not cause star movement (only screen-plane basis used)
      - Stars wrap around edges seamlessly — no popping in/out
      - Stars do not appear in the sidebar area
      - Frame rate unaffected (200 tiny circles is negligible)
    </manual>
  </verify>
  <done>
    - 200 starfield points generated from fixed seed
    - Stars rendered between screen.fill() and point drawing
    - Parallax shift based on camera tangent basis dot products
    - Seamless wrapping at screen edges
    - Stars confined to view area (not sidebar)
  </done>
</task>

</tasks>

<verification>
After completion, verify:

1. **Stars visible:** Background shows dim scattered dots (not distractingly bright)
2. **Parallax works:** Rotating WASD causes stars to drift — conveys camera movement through space
3. **No sidebar bleed:** Stars only appear in the 900px view area
4. **Seamless wrapping:** No visible seam or pop as stars scroll off one edge and appear on the other
5. **Performance:** 200 1-2px circles per frame is trivial overhead
</verification>

<success_criteria>
- Background displays slowly scrolling stars that shift perspective during 4D rotation
- Stars respond to WASD rotation with smooth parallax
- Stars are subtle (dim, small) — background decoration, not distracting
- No stars rendered over sidebar
</success_criteria>

<output>
After completion, create `.planning/phases/02-visual-polish-immersion/02-SUMMARY.md`
</output>
