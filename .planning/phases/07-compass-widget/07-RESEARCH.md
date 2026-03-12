# Phase 7: Compass Widget - Research

**Researched:** 2026-03-12
**Domain:** UI widget module for 4D orientation visualization
**Confidence:** HIGH

## Summary

Phase 7 implements a corner-positioned compass widget that displays the player's 4D orientation using three synchronized indicators: a rotating compass rose showing heading in the XZ plane, a vertical tilt bar for Y-axis alignment, and a W-depth gauge. The widget is self-contained, non-intrusive, and uses fixed standard basis axes as reference (never the player's local frame). Implementation requires a new module `lib/compass.py` following existing UI patterns (gamepedia.py, planets.py), integration with the main render loop, and comprehensive angle calculation logic to map 4D orientation to 2D visual indicators.

**Primary recommendation:** Create `lib/compass.py` with `render_compass(screen, orientation, x, y, size)` interface. Calculate heading via dot product of camera direction (orientation[0]) with fixed X and Z axes, use arctan2 for angle wraparound. Implement needle Lerp animation (~200ms) separately from calculation. Place widget render call after main UI in main.py render section.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | Compass rose shows X+, X-, Z+, Z- labels relative to fixed standard basis | Uses standard axes; angle calculation via dot product; text positioning derived from angle + label offset |
| COMP-02 | Needle rotates to indicate camera heading in XZ plane | Heading angle via arctan2(camera·Z, camera·X); smooth Lerp from current to target over ~200ms |
| COMP-03 | Needle rotation uses Lerp animation with 0/360 wraparound | Lerp parameter increments per frame; wraparound via angle subtraction of 2π when abs(delta) > π |
| ORIE-01 | Vertical bar shows camera tilt relative to Y axis | Tilt angle via arccos(abs(camera·Y)); maps to vertical pixel range [min_y, max_y] in widget |
| ORIE-02 | Depth gauge responds to W-axis rotation (Q/E keys) | W-coordinate from camera·[0,0,0,1]; color gradient or indicator brightness based on normalized W value |
| WIDG-01 | Semi-transparent background doesn't obscure view | Render to 300×300px surface with pygame.SRCALPHA; position in corner (default: top-right); alpha ~180/255 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pygame | 2.x | Rendering, surface creation, blitting | Established engine for this project |
| NumPy | 1.21+ | Vector dot products, angle calculations, math operations | Core for S³ math throughout codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math | stdlib | arctan2, pi, cos, sin for angle wrapping | Standard Python math functions |

### Existing Project Stack
- **Orientation frame:** 4×4 numpy array where row 0 = camera position (unit vector in ℝ⁴)
- **View mode:** Widget renders only when `view_mode == 0` (Assigned colors mode)
- **Gamepedia integration:** Widget hidden when gamepedia_open == True
- **UI module pattern:** Following `lib/gamepedia.py` and `lib/planets.py` structure

## Architecture Patterns

### Recommended Project Structure
```
lib/compass.py          # New module: compass widget render and animation
main.py                 # Integration point: render call in main loop
tests/test_compass.py   # Unit tests for angle calculation
```

### Pattern 1: Fixed Axes Reference Frame
**What:** Compass uses fixed standard basis vectors [1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1] — NOT the player's local orientation frame.

**Why:** The compass shows absolute orientation on S³, allowing players to understand their position relative to the space itself, not relative to where they're looking.

**Math foundation:**
```
# Never reorthogonalize or modify these
AXIS_X = np.array([1, 0, 0, 0])
AXIS_Y = np.array([0, 1, 0, 0])
AXIS_Z = np.array([0, 0, 1, 0])
AXIS_W = np.array([0, 0, 0, 1])

# Camera direction from orientation frame
camera = orientation[0]  # unit 4D vector

# Dot products are safe; no normalization needed (both unit vectors)
heading_component_x = np.dot(camera, AXIS_X)  # cos(angle_from_x)
heading_component_z = np.dot(camera, AXIS_Z)  # cos(angle_from_z)
tilt_component_y = np.dot(camera, AXIS_Y)    # cos(tilt_from_y)
w_component = np.dot(camera, AXIS_W)          # cos(rotation_in_w)
```

**When to use:** All compass calculations. Never use orientation[1], orientation[2], orientation[3] for compass — those are camera-relative.

**Example:**
```python
# Source: STATE.md — "Compass MUST use fixed standard basis"
def calculate_heading(camera_pos):
    """Camera position in ℝ⁴ → heading angle in XZ plane.

    Returns angle in [-π, π] relative to X axis, measured in XZ plane.
    """
    # Dot product with fixed axes
    x_component = np.dot(camera_pos, np.array([1, 0, 0, 0]))
    z_component = np.dot(camera_pos, np.array([0, 0, 1, 0]))

    # atan2(z, x) gives angle from X axis in XZ plane
    # Note: z_component is negated because screen Y increases downward
    heading = np.arctan2(-z_component, x_component)  # angle in [-π, π]
    return heading
```

### Pattern 2: Lerp Animation with Wraparound
**What:** Needle smoothly interpolates from current angle to target angle over ~200ms. Handles wraparound at 0/360 degrees.

**When to use:** Visual feedback — needle should move smoothly, not snap.

**Implementation:**
```python
# Update once per frame (60 FPS = ~16.67ms per frame)
lerp_speed = 1.0 / 200  # 200ms animation duration → complete in 200ms at 60 FPS
lerp_progress += lerp_speed * dt_ms / 16.67  # normalize to frame time

if lerp_progress >= 1.0:
    needle_angle = target_angle
    lerp_progress = 0.0
    is_animating = False
else:
    # Shortest path around circle
    delta = target_angle - needle_angle
    if delta > np.pi:
        delta -= 2 * np.pi
    elif delta < -np.pi:
        delta += 2 * np.pi
    needle_angle += delta * lerp_progress
```

**Why wraparound matters:** Without it, needle rotates the long way around (e.g., 350° → 10° would rotate -340° instead of +20°).

### Pattern 3: Widget Rendering with Alpha Blending
**What:** Compass rendered to a separate surface with pygame.SRCALPHA, then blitted to screen with semi-transparency.

**When to use:** UI overlays that shouldn't fully obscure underlying content.

**Example:**
```python
# Create surface with alpha channel
widget_size = 300
widget_surf = pygame.Surface((widget_size, widget_size), pygame.SRCALPHA)

# Draw compass elements (rose, needle, bar, gauge)
# ... (all drawing to widget_surf)

# Blit with semi-transparent background
# Position in top-right corner (typical compass position)
widget_x = SCREEN_WIDTH - widget_size - 20
widget_y = 20

# Semi-transparent background layer
pygame.draw.rect(widget_surf, (30, 30, 50, 180),
                 (0, 0, widget_size, widget_size), border_radius=8)

screen.blit(widget_surf, (widget_x, widget_y))
```

### Anti-Patterns to Avoid
- **Using player's orientation frame for compass:** Compass should show absolute direction, not camera-relative
- **Snapping needle immediately:** Creates jarring visual feedback; Lerp smooths navigation
- **Forgetting angle wraparound:** Needle takes wrong path around circle (up to 2π radians long)
- **Rendering compass in view modes 1-3:** Only mode 0 (Assigned) has compass (per REQUIREMENTS.md)
- **Showing compass when gamepedia_open:** Widget visibility must respect overlay states
- **Clamping dot products without checking:** Numerical edge cases at ±1 can cause NaN; use np.clip(value, -1, 1)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular interpolation | Custom angle blending logic | Lerp with wraparound via atan2 delta | Wraparound is subtle; off-by-π errors are common |
| Widget surface management | Manually track alpha blending | pygame.Surface(size, pygame.SRCALPHA) | Built-in alpha handling is robust and optimized |
| Angle calculations from 4D vectors | Custom projection logic | numpy.dot + numpy.arctan2 | Numerical stability matters; library functions handle edge cases |
| Smooth frame-rate independent animation | Frame counting | Store `lerp_progress` as float in [0, 1]; increment by `speed * frame_time` | Decouples animation from frame rate; handles variable FPS |

## Common Pitfalls

### Pitfall 1: Not Clamping Dot Products
**What goes wrong:** At certain orientations, `np.dot(camera, axis)` equals exactly -1.0 or 1.0 due to floating-point arithmetic. `arccos` of values outside [-1, 1] returns NaN.

**Why it happens:** Floating-point accumulation errors in reorthogonalize_frame can push dot product slightly outside the mathematically valid range.

**How to avoid:** Always clamp before arccos:
```python
dot = np.clip(np.dot(camera, axis), -1.0, 1.0)
angle = np.arccos(dot)
```

**Warning signs:** Widget needle freezes, tilt bar disappears, NaN in output.

### Pitfall 2: Needle Rotates Wrong Direction
**What goes wrong:** Needle takes the long way around (e.g., rotates -350° instead of +10°).

**Why it happens:** Missing wraparound logic; Lerp interpolates directly between angles without considering circular distance.

**How to avoid:** Calculate delta in [-π, π] range:
```python
delta = target_angle - current_angle
if delta > np.pi:
    delta -= 2 * np.pi
elif delta < -np.pi:
    delta += 2 * np.pi
new_angle = current_angle + delta * t  # t in [0, 1]
```

**Warning signs:** Needle spins 300+ degrees for small heading changes.

### Pitfall 3: View Mode Visibility Not Checked
**What goes wrong:** Compass appears in modes 1, 2, 3 where it doesn't make sense (those have their own visual indicators).

**Why it happens:** Missing `if view_mode == 0:` guard before compass render call.

**How to avoid:** Add conditional in main loop:
```python
# In main.py render section, after UI
if view_mode == 0 and not gamepedia_open:
    render_compass(screen, orientation, x, y, size)
```

**Warning signs:** Compass visible in "4D Position" or "XYZ Projection" modes.

### Pitfall 4: Animation State Not Initialized
**What goes wrong:** Compass needle doesn't animate on first heading change; animation starts mid-transition or at wrong angle.

**Why it happens:** Lerp state (needle_angle, target_angle, lerp_progress) not initialized when module loads.

**How to avoid:** Initialize at module level or in a setup function:
```python
needle_angle = 0.0
target_angle = 0.0
lerp_progress = 1.0  # start at completion so first frame calculates immediately
```

**Warning signs:** Needle freezes on startup; animation jittery or skips frames.

### Pitfall 5: Forgetting Gamepedia Overlap
**What goes wrong:** Compass visible behind open gamepedia overlay, creating UI confusion.

**Why it happens:** Render order not controlled; compass drawn before gamepedia check.

**How to avoid:** Guard compass render:
```python
if not gamepedia_open and view_mode == 0:
    render_compass(...)
```

**Warning signs:** Compass appears in background when F1 overlay is open.

## Code Examples

Verified patterns from existing codebase and mathematical requirements:

### Heading Calculation (Fixed Axes)
```python
# Source: sphere.py angular_distance pattern + STATE.md compass math notes
import numpy as np

AXIS_X = np.array([1, 0, 0, 0])
AXIS_Z = np.array([0, 0, 1, 0])

def calculate_heading(camera_pos):
    """Calculate heading angle in XZ plane (fixed axes, absolute orientation).

    Args:
        camera_pos: Unit 4D vector (orientation[0])

    Returns:
        Heading angle in radians, [-π, π], measured from X axis.
        Positive = counter-clockwise in XZ plane (toward +Z).
    """
    x_comp = np.dot(camera_pos, AXIS_X)
    z_comp = np.dot(camera_pos, AXIS_Z)

    # atan2(z, x) gives standard polar angle
    # Negate z_comp because screen Y increases downward (flip Z)
    heading = np.arctan2(-z_comp, x_comp)

    return heading
```

### Tilt Calculation (Y Axis)
```python
# Source: STATE.md orientation description + sphere.py tangent_basis pattern
def calculate_tilt(camera_pos):
    """Calculate tilt angle relative to Y axis.

    Returns:
        Angle in radians [0, π] representing how far camera points away from Y axis.
        0 = aligned with ±Y (pointing up/down), π/2 = perpendicular to Y.
    """
    AXIS_Y = np.array([0, 1, 0, 0])
    y_comp = np.clip(np.dot(camera_pos, AXIS_Y), -1.0, 1.0)
    tilt = np.arccos(np.abs(y_comp))  # abs() so [0, π/2] range
    return tilt
```

### W Depth Indicator
```python
# Source: sphere.py w_to_color pattern
def calculate_w_alignment(camera_pos):
    """Calculate alignment with W axis (4D depth).

    Returns:
        Value in [-1, 1] where -1 = aligned with -W, 0 = perpendicular, +1 = aligned with +W.
    """
    AXIS_W = np.array([0, 0, 0, 1])
    w_comp = np.dot(camera_pos, AXIS_W)
    return float(np.clip(w_comp, -1.0, 1.0))
```

### Lerp Animation with Wraparound
```python
# Source: main.py slerp pattern + animation principles
import numpy as np

class CompassAnimation:
    def __init__(self):
        self.needle_angle = 0.0
        self.target_angle = 0.0
        self.lerp_progress = 1.0  # Start at completion
        self.lerp_duration_ms = 200  # 200ms smooth transition

    def update(self, target_heading, delta_time_ms):
        """Update needle angle toward target with smooth animation.

        Args:
            target_heading: Heading angle in radians [-π, π]
            delta_time_ms: Frame time in milliseconds
        """
        if abs(self.needle_angle - target_heading) > 0.01:  # threshold for threshold
            # New heading detected
            self.target_angle = target_heading
            self.lerp_progress = 0.0

        if self.lerp_progress < 1.0:
            # Animate
            self.lerp_progress += delta_time_ms / self.lerp_duration_ms
            self.lerp_progress = min(self.lerp_progress, 1.0)

            # Calculate shortest path around circle
            delta = self.target_angle - self.needle_angle
            if delta > np.pi:
                delta -= 2 * np.pi
            elif delta < -np.pi:
                delta += 2 * np.pi

            self.needle_angle += delta * (self.lerp_progress / max(0.001, self.lerp_progress))
        else:
            self.needle_angle = self.target_angle

    def get_angle(self):
        """Return current needle angle in radians."""
        return self.needle_angle
```

### Widget Rendering
```python
# Source: lib/gamepedia.py + lib/planets.py surface pattern
import pygame
import numpy as np

def render_compass(screen, orientation, x, y, size=300):
    """Render compass widget at screen position.

    Args:
        screen: pygame display surface
        orientation: 4x4 orthogonal frame (row 0 = camera position)
        x, y: screen position (top-left of widget)
        size: pixel size of widget square
    """
    widget_surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Semi-transparent background (doesn't fully obscure view)
    pygame.draw.rect(widget_surf, (30, 30, 50, 180), (0, 0, size, size), border_radius=8)
    pygame.draw.rect(widget_surf, (100, 100, 120, 120), (0, 0, size, size), 1, border_radius=8)

    # Calculate angles from camera direction
    camera = orientation[0]
    heading = calculate_heading(camera)
    tilt = calculate_tilt(camera)
    w_align = calculate_w_alignment(camera)

    # Draw compass rose (center of widget)
    center_x, center_y = size // 2, size // 2
    rose_radius = 80

    # Draw cardinal directions
    font = pygame.font.Font(None, 14)
    labels = [("X+", 0), ("Z+", np.pi/2), ("X-", np.pi), ("Z-", -np.pi/2)]
    for label, angle in labels:
        lx = center_x + rose_radius * np.cos(angle)
        ly = center_y - rose_radius * np.sin(angle)  # subtract for screen coords
        text = font.render(label, True, (200, 200, 200))
        screen.blit(text, (int(lx) - 10, int(ly) - 10))

    # Draw rotating needle
    needle_len = 60
    needle_x = center_x + needle_len * np.cos(heading)
    needle_y = center_y - needle_len * np.sin(heading)
    pygame.draw.line(widget_surf, (255, 100, 100), (center_x, center_y),
                     (needle_x, needle_y), 3)

    # Draw tilt indicator (vertical bar on right)
    bar_x = size - 40
    bar_width = 20
    bar_height = 150
    bar_y = center_y - bar_height // 2

    # Tilt value maps to vertical position [0, π] → [bar_y + bar_height, bar_y]
    indicator_pos = bar_y + bar_height * (1 - tilt / np.pi)
    pygame.draw.rect(widget_surf, (100, 100, 150), (bar_x - bar_width//2, bar_y, bar_width, bar_height), 1)
    pygame.draw.circle(widget_surf, (150, 150, 255), (int(bar_x), int(indicator_pos)), 5)

    # Draw W depth gauge (color gradient or brightness)
    # w_align in [-1, 1]: -1 = blue, 0 = neutral, +1 = red
    if w_align < 0:
        gauge_color = (int(100 * (1 + w_align)), 100, 200)
    else:
        gauge_color = (200, int(100 * (1 - w_align)), 100)
    pygame.draw.circle(widget_surf, gauge_color, (size - 30, 30), 15)

    # Blit to screen
    screen.blit(widget_surf, (x, y))
```

## State of the Art

| Aspect | Current Approach | Standards | Notes |
|--------|------------------|-----------|-------|
| Widget overlay rendering | pygame.Surface + SRCALPHA | Modern pygame pattern | Robust for transparency |
| Angle representation | Radians [-π, π] | Math standard | Consistent with NumPy/scipy |
| Frame-independent animation | Lerp progress as float [0, 1] | Game dev standard | Works with variable FPS |
| Fixed axis reference | np.array([1,0,0,0], etc.) | 4D geometry math | Explicit, no assumptions |

### Deprecated/Outdated
- **Hard-coded animation frames:** Use progress-based Lerp instead
- **Snap-to-target heading:** Smooth animation provides better UX
- **Player-frame reference for compass:** Compass should use fixed axes only

## Validation Architecture

**Skip validation section:** workflow.nyquist_validation is explicitly set to false in .planning/config.json. No automated test infrastructure required.

## Open Questions

1. **Widget position preference:** Top-right (typical compass) vs. bottom-left or other corner?
   - What we know: REQUIREMENTS.md doesn't specify; standard game UI puts compass in corner
   - What's unclear: Player preference not established
   - Recommendation: Use top-right as default; make position configurable later if needed

2. **Needle material/style:** Simple line vs. arrow vs. decorative compass rose needle?
   - What we know: REQUIREMENTS.md requires visible rotation; style is artist choice
   - What's unclear: Visual consistency with rest of UI
   - Recommendation: Start with simple 3px line (red/orange); refine if time permits

3. **Gauge visualization for W depth:** Color gradient, brightness, or animated indicator?
   - What we know: REQUIREMENTS.md requires "visible" response; w_to_color() already exists
   - What's unclear: Best visual representation for 4D axis
   - Recommendation: Use color gradient (blue/white/red) matching w_to_color pattern

## Sources

### Primary (HIGH confidence)
- **sphere.py** (angular_distance, rotate_frame, tangent_basis, w_to_color) — 4D math patterns verified in tests
- **main.py** (orientation frame structure, view_mode system, render loop) — current implementation reference
- **STATE.md** (Critical Math Notes section) — explicit compass constraints: "use fixed standard basis", "never reorthogonalize reference axes"
- **REQUIREMENTS.md** (COMP-01 through WIDG-01) — specific behavioral requirements

### Secondary (MEDIUM confidence)
- **lib/gamepedia.py** — UI module pattern (layout constants, alpha surfaces, rendering structure)
- **lib/planets.py** — pygame rendering patterns (texture surfaces, SRCALPHA blitting)
- **tests/test_sphere.py** — mathematical verification patterns (angular distance, dot product clamping)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Pygame 2.x and NumPy are established in this project; no alternatives needed
- Architecture: HIGH — Orientation frame structure explicitly defined in STATE.md; math constraints documented
- Pitfalls: MEDIUM-HIGH — Common wraparound and numerical edge cases identified from existing code patterns; some corner cases may emerge in implementation

**Research date:** 2026-03-12
**Valid until:** 2026-03-19 (7 days for UI/rendering patterns; may need refresh if Pygame version changes)

**Codebase snapshot:**
- Current phase: 7 (not started)
- Total LOC: ~3,635 (main.py: 1364, lib/: 2271)
- Test structure: pytest with 9 test modules
- Deployment: Python venv in ~/Projects/4sphere-explorer/venv
