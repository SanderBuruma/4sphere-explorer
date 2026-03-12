# 4D Compass Widget: Quick Reference for Implementation

**TL;DR:** Build a compass that shows the fixed standard basis axes (X, Y, Z, W) relative to the player's current orientation. Never use the player's local frame as a reference. Use standard RGB colors + text labels. Test that compass output doesn't change when player rotates in place.

---

## The Core Insight

```
COMPASS ≠ LOCAL FRAME

Local frame (orientation):           Compass (fixed):
  Rotates with player                Never rotates
  Row 0 = camera direction           Always shows X/Y/Z/W axes
  Rows 1-3 = tangent basis           Relative to player position only

Example:
  Player rotates 90° WASD     →  orientation changes
                              →  compass unchanged (still shows same axis alignment)

If compass rotates with player, it's a gyroscope, not a compass.
```

---

## Math Recipe

```python
# Define fixed standard basis axes (never change)
X_AXIS = np.array([1.0, 0.0, 0.0, 0.0])
Y_AXIS = np.array([0.0, 1.0, 0.0, 0.0])
Z_AXIS = np.array([0.0, 0.0, 1.0, 0.0])
W_AXIS = np.array([0.0, 0.0, 0.0, 1.0])

# Compute compass output (in update loop)
def compute_compass_output(orientation):
    """
    orientation: 4x4 orthogonal matrix from main.py
    Returns: dict with alignment values for each axis
    """
    # Batch compute alignments with player's frame
    basis_axes = np.array([X_AXIS, Y_AXIS, Z_AXIS, W_AXIS])

    # Shape: (4,) - dot products with camera direction
    camera_alignment = basis_axes @ orientation[0]  # axis · camera

    # Shape: (4, 3) - dot products with tangent basis
    tangent_alignments = basis_axes @ orientation[1:4].T  # axis · each tangent vector

    return {
        'camera': camera_alignment,        # For determining if axis visible
        'tangent': tangent_alignments,     # For computing screen position
    }

# In render loop:
compass_data = compute_compass_output(orientation)
render_compass(compass_data)
```

---

## Rendering Recipe

```python
def render_compass(compass_data, screen, pos=(70, 70)):
    """Render compass rose in corner"""

    # 1. Horizontal compass rose (X/Z axes)
    for axis_name, axis_idx, angle_offset, color in [
        ('E', 0, 0.0, RED),          # +X is East
        ('W', 0, np.pi, DARK_RED),   # -X is West
        ('F', 2, -np.pi/2, BLUE),    # +Z is Forward
        ('B', 2, np.pi/2, DARK_BLUE),# -Z is Back
    ]:
        # Get tangent space position
        x_tangent = compass_data['tangent'][axis_idx, 0]
        z_tangent = compass_data['tangent'][axis_idx, 2]

        # Draw arrow at this position
        draw_arrow(screen, pos, (x_tangent, z_tangent), color, label=axis_name)

    # 2. Vertical indicator (Y axis)
    y_alignment = compass_data['tangent'][1, 1]  # Y component in tangent space
    draw_vertical_bar(screen, pos + (0, 25), y_alignment, GREEN)

    # 3. W-axis depth indicator (separate)
    w_camera_dot = compass_data['camera'][3]  # W · camera
    color = RED if w_camera_dot > 0 else BLUE
    draw_depth_gauge(screen, pos + (50, 0), w_camera_dot, color)
```

---

## Key Rules (Enforce in Code Review)

1. **Use exact basis vectors**
   ```python
   # Good
   axis = np.array([1.0, 0.0, 0.0, 0.0])

   # Bad: never do this
   axis = tangent_basis(camera)[0]  # This computes a NEW basis!
   reorthogonalize_frame(axis)      # This changes the axis!
   ```

2. **Never project compass output through player frame rotation**
   ```python
   # Good: compass data is independent of player rotations
   compass_data = compute_compass_output(orientation)
   # compass_data stays the same if player rotates

   # Bad: compass output changes with player rotation
   rotated_axis = orientation @ X_AXIS  # Don't do this!
   ```

3. **Invalidate cache after frame changes**
   ```python
   # In main.py update loop
   rotate_frame(orientation, axis_idx, angle)
   compass_dirty = True  # Must invalidate!

   # In compass update
   if compass_dirty or compass_cache is None:
       compass_data = compute_compass_output(orientation)
       compass_dirty = False
   ```

4. **Clamp values to prevent NaN**
   ```python
   dot = np.clip(np.dot(axis, camera), -1.0, 1.0)
   angle = np.arccos(dot)  # Safe from domain error
   ```

5. **Test invariant before rendering**
   ```python
   # In test_compass.py
   def test_compass_invariant_under_rotation():
       """Compass should not change when player rotates"""
       orientation = np.eye(4)

       compass1 = compute_compass_output(orientation)

       # Player rotates 45° in XY plane
       rotate_frame(orientation, 1, np.pi/4)

       compass2 = compute_compass_output(orientation)

       # Compass should be unchanged
       np.testing.assert_allclose(compass1['camera'], compass2['camera'], atol=1e-6)
       np.testing.assert_allclose(compass1['tangent'], compass2['tangent'], atol=1e-6)
   ```

---

## Performance Checklist

- [ ] Vectorized: Use `basis_axes @ orientation` (4×4 @ 4×4), not 4 separate loops
- [ ] Cached: Read `orientation[1:4]` directly, don't call `tangent_basis()` again
- [ ] Profiled: Compass update <0.2ms per frame (test with `timeit` or pygame profiler)
- [ ] No allocations in hot loop: Reuse arrays, don't create new ones each frame
- [ ] No arccos per axis: Use dot products directly when possible

---

## Visual Design Checklist

- [ ] **Colors:** Red=X, Green=Y, Blue=Z, Cyan=W (standard convention)
- [ ] **Labels:** "E", "W", "F", "B" for ±X, ±Z; "Y" for Y bar; "W" separate
- [ ] **Size:** Compass ≤70×70 pixels (fits corner without clutter)
- [ ] **Hierarchy:** Primary: 2D rose (X/Z). Secondary: Y bar. Tertiary: W gauge.
- [ ] **Shapes:** Arrows for axes, slider/glow for secondary, separate gauge for W
- [ ] **Text:** Clear labels for each element; include "North=+X" in F1 help

---

## Testing Checklist

- [ ] **Invariant test:** Compass unchanged when player rotates (unit test)
- [ ] **W-axis test:** W indicator changes when Q/E keys pressed (integration test)
- [ ] **Edge case test:** Camera aligned with +X, +Y, +Z, +W (no NaN/inf)
- [ ] **Drift test:** 30+ minute session, verify compass stable (long-session test)
- [ ] **Performance test:** Compass overhead <0.2ms (profiling test)
- [ ] **Clarity test:** Player feedback "I understand compass" (playtesting)

---

## Pitfall Checklist

Verify these before release:

- [ ] **Not rotating with player:** Compass points same direction when player spins (CRITICAL)
- [ ] **W-axis visible:** W indicator responds to Q/E input (CRITICAL)
- [ ] **No reorthogonalization:** Compass uses exact [1,0,0,0] vectors, never reorthogonalized (CRITICAL)
- [ ] **Cache invalidated:** Compass updates after every frame rotation (MODERATE)
- [ ] **Numerical stability:** No NaN/inf at edge cases (MODERATE)
- [ ] **Visual clarity:** Player understands compass in 3 seconds (MODERATE)
- [ ] **No color confusion:** Standard RGB + text labels used (MINOR)

---

## Common Mistakes to Avoid

| Mistake | Why Bad | Fix |
|---------|---------|-----|
| `tangent_basis()` in compass update | Recomputes basis every frame; expensive + inconsistent | Use `orientation[1:4]` directly |
| `reorthogonalize_frame()` on compass axes | Introduces drift + breaks invariant | Never reorthogonalize compass axes |
| Using player frame as reference | Compass rotates with player (gyroscope not compass) | Use fixed [1,0,0,0] vectors |
| Caching compass without invalidation | Compass out-of-sync after frame rotation | Invalidate cache after `rotate_frame()` |
| Projecting all axes into tangent space only | W-axis invisible | Use separate W indicator |
| Complex animations/rotating needles | Distracting; expensive | Static widget only |
| No edge case handling | NaN/crashes at axis alignment | Clamp values; test edge cases |
| Color-only axis distinction | Colorblind players confused | Add text labels + shapes |

---

## Quick Validation

Before committing, run this checklist:

```python
# 1. Math correctness
import numpy as np
from sphere import rotate_frame

orientation = np.eye(4)
X_AXIS = np.array([1.0, 0.0, 0.0, 0.0])

compass1 = np.dot(X_AXIS, orientation[0])
rotate_frame(orientation, 1, 0.5)
compass2 = np.dot(X_AXIS, orientation[0])

assert np.allclose(compass1, compass2), "FAIL: Compass changed after rotation!"
print("PASS: Compass invariant holds")

# 2. Performance
import time
start = time.time()
for _ in range(10000):
    compute_compass_output(orientation)
elapsed = (time.time() - start) / 10000 * 1000
assert elapsed < 0.2, f"FAIL: Compass update took {elapsed:.3f}ms"
print(f"PASS: Compass update {elapsed:.3f}ms (target <0.2ms)")

# 3. Edge case
for axis in [np.array([1,0,0,0]), np.array([0,1,0,0]), np.array([0,0,1,0]), np.array([0,0,0,1])]:
    orientation[0] = axis  # Camera aligned with axis
    result = compute_compass_output(orientation)
    assert not np.any(np.isnan(result['camera'])), f"NaN at {axis}"
    assert not np.any(np.isinf(result['camera'])), f"Inf at {axis}"
print("PASS: Edge cases handled")
```

---

## When You're Done

1. Compass points same direction when player rotates (unit test passes)
2. W indicator changes with Q/E input (integration test passes)
3. Compass update <0.2ms per frame (profiling passes)
4. No crashes at edge cases (unit tests pass)
5. Player feedback: "I understand my 4D orientation" (playtesting passes)
6. All files created, no commits yet (awaiting orchestrator)

---

*Quick reference for v1.2 compass widget implementation*
*Keep this open during Phase 2 coding*
