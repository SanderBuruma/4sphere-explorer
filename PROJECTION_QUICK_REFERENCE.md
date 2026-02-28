# 4-Sphere Projection Methods: Quick Reference Guide

A visual summary of the 7 major approaches to visualizing S³, with implementation sketches and decision matrix.

---

## Visual Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     S³ PROJECTION METHODS OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. TANGENT SPACE (Current)                                               │
│     [Camera]──────[Tangent Basis]──────[Local Projection]                 │
│        • Points cluster around center (crosshair)                         │
│        • Angular distance preserved                                       │
│        • FOV limited cone                                                 │
│                                                                             │
│  2. STEREOGRAPHIC                                                          │
│     [Pole]──────[Ray casting]──────[3D Hyperplane]                        │
│        • Conformal (angles preserved)                                     │
│        • Entire S³ visible (except pole)                                  │
│        • Extreme foreshortening near pole                                 │
│                                                                             │
│  3. ORTHOGONAL                                                             │
│     [S³ coords]──────[Drop 1 axis]──────[3D]                              │
│        • Simple and fast                                                   │
│        • No singularities                                                  │
│        • Distorts angles significantly                                    │
│                                                                             │
│  4. HOPF FIBRATION                                                         │
│     [S³ point]──────[Hopf Map]──────[S² color]──────[Stereographic]       │
│        • Reveals fiber bundle structure                                   │
│        • Visually beautiful                                               │
│        • More computational cost                                          │
│                                                                             │
│  5. QUATERNION                                                             │
│     [Unit Quaternion]──────[Rotation]──────[3D Visualization]             │
│        • Natural for rotations (SU(2))                                    │
│        • No gimbal lock                                                    │
│        • Requires interpretation layer                                    │
│                                                                             │
│  6. SLICING                                                                │
│     [w parameter]──────[Cross-section]──────[3D Sphere]                   │
│        • Intuitive sequences                                              │
│        • Individual slices simple                                         │
│        • Loses continuity between slices                                  │
│                                                                             │
│  7. HYBRID/ADVANCED                                                        │
│     [Multiple methods]──────[Simultaneous views]──────[Progressive UI]     │
│        • Best of multiple approaches                                      │
│        • Complex implementation                                           │
│        • Educational value high                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Decision Tree: Choosing a Projection Method

```
START: "What do I want to visualize?"

├─ "Interactive real-time exploration of S³"
│  └─> TANGENT SPACE (current choice) ✓
│      └─ "Need to see opposite side of sphere?"
│         └─> ADD: Stereographic toggle or switch to Hopf
│
├─ "Understand topology & fiber structure"
│  └─> HOPF FIBRATION
│      └─ "Want interactive control too?"
│         └─> HYBRID: Hopf + Tangent space dual view
│
├─ "Study how coordinate changes affect S³"
│  └─> ORTHOGONAL PROJECTION
│      └─ "Multiple views for comparison?"
│         └─> Multiple projection axes simultaneously
│
├─ "Teach dimension reduction (4D → 3D → 2D)"
│  └─> SLICING METHOD
│      └─ "Animate the slicing process?"
│         └─> Yes: Animated cross-section sequence
│
├─ "Work with rotations & orientations"
│  └─> QUATERNION REPRESENTATION
│      └─ "Visualize the rotation's effect?"
│         └─> Render rotated reference frame/object
│
├─ "Need one mathematically elegant method"
│  └─> STEREOGRAPHIC PROJECTION
│      └─ "Handle pole singularities?"
│         └─> Clipping near pole OR special coloring
│
└─ "Want everything: exploration + topology + education"
   └─> PROGRESSIVE DISCLOSURE
       ├─ Level 1: Tangent space (fast)
       ├─ Level 2: Add color from coordinates
       ├─ Level 3: Toggle Stereographic view
       └─ Level 4: Hopf fibration overlay

```

---

## Formula Quick Reference

### Tangent Space (Current)
```python
# Core calculation
angle = arccos(camera · point)
direction = (point - (camera · point) × camera) / ||...||
coords_in_basis = [dot(direction, b1), dot(direction, b2), dot(direction, b3)]
final_3d = angle × coords_in_basis
```

### Stereographic (4D → 3D)
```python
# Forward: S³ to ℝ³
result_3d = point[1:4] / (1 - point[0])

# Backward: ℝ³ to S³
r² = x² + y² + z²
s3_point = [(r² - 1), 2x, 2y, 2z] / (r² + 1)
```

### Orthogonal (Simple axis-aligned)
```python
# Drop w coordinate
result_3d = point[0:3]

# Or rotate first, then drop:
rotated = rotation_matrix @ point
result_3d = rotated[0:3]
```

### Hopf Map (S³ to S²)
```python
# Input: q = [q0, q1, q2, q3] (unit quaternion)
# Output: point on S²
s2_x = q1² + q2² - q0² - q3²
s2_y = 2(q0·q1 + q2·q3)
s2_z = 2(q0·q2 - q1·q3)
```

### Slicing (Fixed w = w₀)
```python
# Cross-section is a 2-sphere of radius r
r = sqrt(1 - w₀²)
# Points satisfy: x² + y² + z² = r²
# (Generate points on sphere of radius r in xyz)
```

### Quaternion Rotation
```python
# Quaternion q represents 3D rotation
# Apply to 3D vector v:
v_rotated = q * v * q*  (where q* is conjugate)

# As matrix:
R = [[1-2(y²+z²),  2(xy-wz),   2(xz+wy)  ],
     [2(xy+wz),   1-2(x²+z²),  2(yz-wx)  ],
     [2(xz-wy),   2(yz+wx),   1-2(x²+y²)]]
```

---

## Implementation Complexity & Performance

| Method | LOC Est. | CPU per pt | Memory | Comments |
|--------|----------|-----------|--------|----------|
| Tangent Space | 30-50 | 3 dot products | Low | Already implemented |
| Stereographic | 20-30 | 1 division | Low | Handle pole clipping |
| Orthogonal | 5-10 | 1 or 2 ops | Low | Trivial implementation |
| Hopf | 40-60 | Hopf + stereo | Low | ~2× tangent cost |
| Quaternion | 50-70 | quat mult | Low | Slerp already exists |
| Slicing | 30-40 | Cross-sect calc | Medium | Animated requires buffer |
| Hybrid | 100-200 | Method dependent | Medium-High | Complex UI state |

---

## Which Method for Your Use Case?

### "I just want a better look at S³"
→ **Stereographic Projection**
- Mathematical elegance
- Shows entire S³ (except pole)
- Conformal (preserves local shapes)
- Handle pole via color warning or cutoff

### "I want smooth camera navigation"
→ **Keep Tangent Space (current)**
- Designed exactly for this
- SLERP works perfectly
- Intuitive interaction
- Add Stereographic as occasional "full view"

### "I'm studying topology"
→ **Hopf Fibration**
- Reveals S³ as fiber bundle
- Beautiful mathematical structure
- Use stereographic projection as base

### "I want quick, dirty visualization"
→ **Orthogonal Projection**
- 2 lines of code to switch
- Fast as possible
- Not conformal, but clear
- Show multiple axes simultaneously

### "I'm teaching someone about dimensions"
→ **Slicing Method**
- Intuitive explanation (cross-sections)
- Animate to show evolution
- Progressive understanding

### "I want everything"
→ **Progressive Disclosure**
- Start with Tangent Space
- Add toggle to Stereographic
- Optional Hopf overlay
- Build iteratively

---

## Code Migration Path (Recommended)

### Phase 1: Current State ✓
```python
# tangent_space() projection (already done)
# WASD rotation in 4D
# SLERP-based travel
```

### Phase 2: Add Stereographic Toggle (1-2 hours)
```python
# Add stereographic_projection() function
# Toggle view_mode between tangent and stereo
# Handle pole clipping in stereo mode
# Reuse rotation/travel logic
```

### Phase 3: Quaternion Navigation (2-3 hours)
```python
# Replace raw 4D rotation matrices with quaternions
# camera_pos = Quaternion (unit)
# Rotate via: q_rotated = q_rot * camera_q * q_rot*
# SLERP already works with quaternions
```

### Phase 4: Hopf Visualization (3-4 hours, optional)
```python
# Implement hopf_map(point) -> s2_point
# Color points based on S² position
# Apply to either tangent or stereographic
# Toggle with key combination
```

### Phase 5: Multi-view UI (not recommended yet)
```python
# Split screen into multiple projections
# Requires major UI rewrite
# Low priority for core exploration goal
```

---

## Testing Checklist

When implementing a new projection:

- [ ] **Boundary cases**: Test points near poles, at cardinal directions
- [ ] **Antipodal points**: If camera at [1,0,0,0], opposite point at [-1,0,0,0] should be handled
- [ ] **FOV edge**: Points at FOV boundary should project cleanly
- [ ] **Rotation**: Rotating camera should maintain continuity (no jumping)
- [ ] **SLERP travel**: Interpolation to distant points should work smoothly
- [ ] **Numerical stability**: No NaN or inf values (even near singularities)
- [ ] **Performance**: Maintain 60 FPS with 300 points
- [ ] **Coloring**: Choose colors that work with new projection (update view modes)

---

## References for Each Method

### Tangent Space
- Current code: `sphere.py`, `main.py` (lines 195-209)
- Concept: Local tangent plane approximation of curved manifold

### Stereographic
- [Wikipedia: Stereographic Projection](https://en.wikipedia.org/wiki/Stereographic_projection)
- [3-sphere Wikipedia](https://en.wikipedia.org/wiki/3-sphere)
- [Interactive demo](https://www.math.union.edu/~dpvc/math/4D/stereo-projection/welcome.html)

### Orthogonal
- [Hollasch: Four-Space Visualization](https://hollasch.github.io/ray4/Four-Space_Visualization_of_4D_Objects.html)
- Simple linear algebra (matrix projection)

### Hopf Fibration
- [Hopf Wikipedia](https://en.wikipedia.org/wiki/Hopf_fibration)
- [Niles Johnson's visualizations](https://nilesjohnson.net/hopf.html)
- [Elementary Introduction - Lyons](https://nilesjohnson.net/hopf-articles/Lyons_Elem-intro-Hopf-fibration.pdf)

### Quaternions
- [Quaternions Wikipedia](https://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation)
- Current code uses: `slerp()` in `sphere.py`
- SU(2) isomorphism: each unit quat = point on S³

### Slicing
- [Interactive 4D Handbook](https://baileysnyder.com/interactive-4d/3d-slices/)
- [Math.union.edu sphere slicing](https://www.math.union.edu/~dpvc/math/4D/sphere-slice/welcome.html)

---

## One-Paragraph Summaries

**Tangent Space**: Think of standing on the sphere's surface (camera position) and looking outward. All nearby points cluster around where you're looking. Mathematically: project into the local 3D plane tangent to the 4D surface, scaled by angular distance. Best for interactive exploration.

**Stereographic**: Imagine a 4D lightbulb at the north pole, casting shadows of S³ onto a 3D wall. Preserves angles beautifully, shows all of S³, but points near the bulb cast infinitely far shadows. Classic in mathematics.

**Orthogonal**: Drop one coordinate (e.g., ignore W). Ultra-fast, no weird behavior, but loses the "3D feel" of that dimension. Like viewing a 4D object along a cardinal axis.

**Hopf Fibration**: S³ is secretly made of circles stacked into a 2-sphere worth of arrangements. Reveals this hidden structure and creates stunning linked tori visualizations. Mathematically profound.

**Quaternion**: Each point on S³ is a 3D rotation. Visualize by rendering what that rotation does to a reference object. Natural for physics/graphics but requires extra interpretation.

**Slicing**: Freeze the W coordinate, observe a 3D sphere. Vary W and watch the sphere grow, shrink, and disappear. Like a flip-book of cross-sections through 4D.

**Hybrid**: Use multiple methods simultaneously for different insights. Teaches more, costs more CPU.

---

## Troubleshooting

**Problem**: Stereographic projection shows wild distortion near pole
- **Solution**: Either exclude points beyond distance threshold, or color them differently ("at infinity")

**Problem**: Quaternion visualization is confusing
- **Solution**: Render a canonical object (frame, tetrahedron) and show how it rotates at each point

**Problem**: Slicing loses the "flow" between slices
- **Solution**: Interpolate between slices, or show multiple simultaneous slices with connecting lines

**Problem**: Hopf visualization is too computationally expensive
- **Solution**: Pre-compute Hopf coloring, cache sphere meshes, or render at lower resolution

**Problem**: Not sure which projection to use
- **Solution**: Start with tangent space (current), add stereographic as toggle, evaluate from there

