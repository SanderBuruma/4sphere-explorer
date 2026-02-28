# 4-Sphere (S³) Projection Methods: Comprehensive Research

This document compares different mathematical approaches to projecting the 4-dimensional sphere (S³) into lower dimensions for interactive visualization.

---

## 1. Tangent Space Projection (Current Implementation)

### Mathematical Description

**Current Use**: The 4sphere-explorer uses local tangent plane projection to keep points clustered around the camera's crosshair.

**Method**:
1. Compute a 3D orthonormal basis spanning the tangent space at camera position on S³
2. For each point P on S³:
   - Calculate angular distance θ = arccos(camera · P)
   - Compute tangent direction: D = (P - (camera·P)·camera) / ||...||
   - Project D onto the 3D basis vectors to get local coordinates
   - Scale by angular distance: result = θ × basis_projection
3. Project the resulting 3D coordinates to 2D screen space

**Mathematical Formulation**:
```
θ = arccos(camera_pos · point)
direction = (point - dot(camera_pos, point) × camera_pos) / ||...||
tangent_coords = [dot(direction, b₁), dot(direction, b₂), dot(direction, b₃)]
final_3d = θ × tangent_coords
```

### Advantages
- **Intuitive clustering**: Points naturally cluster around the center (camera position)
- **Angular distance preservation**: Actual geodesic distances on S³ are preserved locally
- **Conformal (locally)**: Preserves angles between nearby curves
- **Computational efficiency**: Simple dot products and basis projections
- **Works well for exploration**: Camera stays centered; motion is intuitive
- **No singularities for visible points**: All visible points are well-defined

### Disadvantages
- **Limited global view**: Only shows a cone around the camera direction (limited by FOV)
- **Distances become distorted far from center**: Not accurate for points near edges of FOV
- **Cannot see antipodal point**: The point opposite the camera is always hidden
- **Hard to visualize global topology**: No continuous view of the entire surface
- **Z-coordinate less meaningful**: Used only for painter's algorithm, not true depth

### Code Reference
```python
# From sphere.py
def tangent_basis(cam):
    """Compute 3 orthonormal vectors spanning the tangent space at cam on S³."""
    candidates = np.eye(4)
    basis = []
    for v in candidates:
        v = v - np.dot(v, cam) * cam  # project out camera direction
        for b in basis:
            v = v - np.dot(v, b) * b  # project out previous basis vectors
        norm = np.linalg.norm(v)
        if norm > 1e-6:
            basis.append(v / norm)
        if len(basis) == 3:
            break
    return basis

def project_to_tangent(cam, point, basis):
    """Project a point on S³ into camera's tangent space."""
    dot = np.clip(np.dot(cam, point), -1.0, 1.0)
    angle = np.arccos(dot)
    if angle < 1e-6:
        return np.zeros(3)

    direction = point - dot * cam
    direction_norm = np.linalg.norm(direction)
    if direction_norm < 1e-6:
        return np.zeros(3)
    direction /= direction_norm

    coords = np.array([np.dot(direction, b) for b in basis])
    return coords * angle  # scale by angular distance
```

### Best For
- **Real-time exploration** with camera-centric navigation
- **Intuitive point selection** and interaction
- **Local topology investigation** (neighborhoods around camera)
- **Current use case**: exactly what 4sphere-explorer needs

---

## 2. Stereographic Projection (4D → 3D)

### Mathematical Description

**Method**: Project from a pole (north pole at [1,0,0,0]) to the equatorial hyperplane (3D).

For a point P = (p₁, p₂, p₃, p₄) on S³:
1. Choose a projection pole (e.g., north pole N = [1, 0, 0, 0])
2. For each point P ≠ N, draw a line from N through P
3. Find intersection with equatorial 3D hyperplane (w = 0)

**Mathematical Formula**:
```
Projection(P) = (p₂, p₃, p₄) / (1 - p₁)
```

Alternatively, using parameter t:
- Ray: N + t(P - N)
- Equatorial condition: [N + t(P - N)]₁ = 0
- Solving: t = 1 / (1 - p₁)
- Result: 3D = [p₂/(1-p₁), p₃/(1-p₁), p₄/(1-p₁)]

**Inverse** (3D back to S³):
```
|x|² = x² + y² + z²
P = (|x|² - 1, 2x, 2y, 2z) / (|x|² + 1)
```

### Advantages
- **Conformal mapping**: Preserves angles locally (geodesic curves remain undistorted at small scales)
- **Circles → Circles/Lines**: Preserves circular symmetries (major geometry preserved)
- **Entire space projection**: Can show all of S³ (except the pole itself)
- **Mathematically elegant**: Connection to complex analysis and Riemann sphere
- **Well-studied**: Extensive theoretical foundation and literature
- **Useful for topology**: Reveals fiber structures (e.g., Hopf fibration)

### Disadvantages
- **Extreme foreshortening**: Points near the pole project to infinity; inverse pole maps to ∞
- **Non-uniform scaling**: Distant regions compress toward the equator
- **Computationally singular**: Division by (1 - p₁) becomes problematic near pole
- **Hard to see global structure**: Pole region dominates the visualization
- **Less intuitive for navigation**: Moving away from pole has non-linear effect
- **Requires clipping/truncation**: Can't truly render ∞; need practical limits

### Use Cases
- **Topological visualization**: Studying global fiber structures (e.g., Hopf fibration)
- **Mathematical research**: Studying angle-preserving transformations
- **Transition between 4D and 3D**: One-to-one mapping (except at pole)
- **Combining with other methods**: Stereographic + perspective projection

### Comparison: Stereographic vs. Tangent Space

| Aspect | Stereographic | Tangent Space |
|--------|---------------|---------------|
| **Conformal** | Yes (globally) | Yes (locally) |
| **Preserves circles** | Yes | No (becomes arcs) |
| **Shows entire S³** | Yes (except pole) | No (cone FOV only) |
| **Singularities** | At pole (∞) | None (for visible region) |
| **Interactive navigation** | Harder (non-uniform) | Easier (uniform motion) |
| **Computational cost** | Low (division) | Medium (basis + projections) |

---

## 3. Orthogonal Projection (4D → 3D)

### Mathematical Description

**Method**: Drop one or more coordinates from 4D to get 3D.

**Simple axis-aligned orthogonal projection**:
```
3D = (p₁, p₂, p₃)  [drop w]
or any other selection of 3 from 4 coordinates
```

**Rotated orthogonal projection**:
1. Define a 4×3 projection matrix M (4D view direction matrix)
2. Apply: 3D = M^T · P (or transform P to new basis, select 3)

**Example: rotating camera "around" the 4D sphere in xw plane**:
```
angle α:
rotated_P = [cos(α) -sin(α) 0 0] [p₁]
             [sin(α)  cos(α) 0 0] [p₂]
             [0       0      1 0] [p₃]
             [0       0      0 1] [p₄]

then drop last coordinate (or second-to-last)
```

### Advantages
- **Simplicity**: Minimal computation (drop coordinates or single matrix multiplication)
- **No singularities**: Defined everywhere on S³
- **Speed**: Fastest projection method
- **Intuitive for axis-aligned views**: Easy to understand which 3 coordinates are shown
- **No clipping needed**: All points remain in finite bounds
- **Preserves straight lines**: Lines on S³ remain lines in projection (except poles)
- **Good for wireframe rendering**: Works well with edges and curves

### Disadvantages
- **Not conformal**: Distorts angles significantly
- **Asymmetric**: Results depend on which 3 axes are chosen
- **Circles become ellipses**: Loses circular symmetries unless aligned with axes
- **Foreshortening**: Some directions appear compressed
- **No unique "optimal" view**: Multiple possible projection directions
- **Hard to see 3D structure**: W-coordinate information completely lost (as visual depth)
- **Information loss**: One full dimension discarded without depth cue

### Variants

**Orthogonal with depth tracking**:
Include the discarded coordinate as a color or depth value:
```
3D_position = (p₁, p₂, p₃)
depth_or_color = p₄  [0,1] mapped to color or z-buffer
```

**Oblique projection** (generalization):
```
3D = (p₁ + α·p₄, p₂ + β·p₄, p₃)
where α, β are shear parameters (45° or 30° typical)
```

### Use Cases
- **Quick debugging**: Fast visualization of S³ structure
- **Multiple projections simultaneously**: Show 2-3 views from different angle combinations
- **Real-time interaction**: Minimal CPU cost for rotation/navigation
- **Educational**: Emphasize that S³ has 4 independent dimensions
- **Wireframe + rotation**: Rotate a wireframe hypersphere to understand 4D structure

---

## 4. Hopf Fibration Visualization

### Mathematical Description

**Hopf fibration**: A continuous function from S³ → S² such that:
- Each point on S² maps to a great circle (fiber) on S³
- Every fiber is a circle (S¹)
- Fibers are mutually disjoint and tile the entire S³

**Quaternion formulation** (most intuitive for visualization):
1. Represent S³ points as unit quaternions: q = q₀ + q₁i + q₂j + q₃k
2. The Hopf map: H(q) = (|q₁² + q₂²| - |q₀² + q₃²|, 2(q₀q₁ + q₂q₃), 2(q₀q₂ - q₁q₃))
3. This produces a point on S² (represented in 3D coordinates)

**Alternative form** using complex representation:
- Represent S³ as ℂ² = {(z₁, z₂) : |z₁|² + |z₂|² = 1}
- Hopf map: (z₁, z₂) → |z₁|² - |z₂|², where the sphere S² is the unit sphere in ℝ³

**Fiber structure**:
- Each fiber over a point p ∈ S² is a circle
- Can be parameterized and rendered as linked tori in 3D stereographic projection

### Visualization Technique

1. **Project S³ to 3D** using stereographic projection
2. **Partition points by Hopf value**: Group S³ points by their image in S²
3. **Color by Hopf coordinate**: Map S² position to RGB (spherical coordinates to color)
4. **Render fibers as tubes/torii**: Each Hopf fiber (circle on S³) projects to a curve in 3D

**Rendering pseudocode**:
```
for each point P on S³:
    hopf_point = hopf_map(P)  # maps to S²
    color = color_from_sphere(hopf_point)

    stereographic_3d = stereographic_projection(P)
    render_point(stereographic_3d, color)
```

### Advantages
- **Reveals intrinsic structure**: Shows the S² × S¹ fiber bundle nature of S³
- **Beautiful geometry**: Produces visually stunning linked tori and nested structures
- **Educational**: Demonstrates fundamental topology (fibers, bundles, symmetries)
- **Well-studied**: Extensively documented in academic literature
- **Quaternion connection**: Natural link to rotation groups and physics
- **Unique coloring**: Hopf coordinate provides a natural, continuous color scheme

### Disadvantages
- **Complex implementation**: Requires Hopf map calculation plus projection
- **Still uses stereographic projection issues**: Inherits singularities at poles
- **Harder to navigate**: Less intuitive for interactive exploration
- **More computation**: Extra Hopf map evaluation per point
- **Visualization-specific**: Primarily useful for understanding topology, not general exploration
- **Limited interactivity**: Best as a static or slowly-rotating visualization

### Mathematical Insight

The Hopf fibration shows that S³ is not a "product" space like S² × S¹, but rather has a twisted product structure. When visualized via stereographic projection:
- Fibers project to circles
- Collections of fibers (constant latitude on S²) project to tori
- Linked tori exhibit the intricate topological structure of S³

### Code Reference (Conceptual)

```python
def hopf_map(q):
    """
    Map S³ (represented as unit quaternion) to S².
    q = [q0, q1, q2, q3] with q0² + q1² + q2² + q3² = 1
    """
    q0, q1, q2, q3 = q
    # Hopf map formula
    s2_x = q1**2 + q2**2 - q0**2 - q3**2
    s2_y = 2 * (q0*q1 + q2*q3)
    s2_z = 2 * (q0*q2 - q1*q3)
    return np.array([s2_x, s2_y, s2_z])

def render_hopf_visualization(points):
    """
    Render S³ with Hopf fibration coloring and stereographic projection.
    """
    for p in points:
        hopf_point = hopf_map(p)
        color = color_from_s2(hopf_point)  # map S² to RGB

        stereographic_3d = stereographic_projection_s3_to_3d(p)
        projected_2d = perspective_project_3d_to_2d(stereographic_3d)

        render_point(projected_2d, color)
```

---

## 5. Quaternion-Based Representation (SU(2) Double Cover)

### Mathematical Description

**Key insight**: S³ ≅ SU(2) (as Lie groups and manifolds)

**Quaternion representation of S³**:
```
q = w + xi + yj + zk  where w² + x² + y² + z² = 1
or in vector form: q = [w, x, y, z]
```

**Rotation action**: A unit quaternion q ∈ S³ represents a rotation in 3D via:
```
v' = q·v·q*  (conjugate)
where v is treated as a quaternion [0, x, y, z]
```

**Double cover**: Each 3D rotation SO(3) is represented by two antipodal quaternions ±q.

**4D rotations**: An arbitrary 4D rotation is a product of two quaternion multiplications:
```
P' = L(q_left) · R(q_right) · P
where L and R are left and right multiplication matrices
```

### Visualization Approach

**Method 1: Quaternion as rotation viewer**
1. Represent each S³ point as a unit quaternion
2. Interpret it as a rotation
3. Visualize the rotation's effect (e.g., rotating a tetrahedron, cube, or frame)
4. Color by rotation properties (angle, axis orientation)

**Method 2: Quaternion spherical coordinates**
1. Each point on S³ is a quaternion q = [w, x, y, z]
2. Use quaternion exponential map for "natural" coordinates
3. Stereographic projection from w-axis (or any axis)

**Method 3: SU(2) matrix representation**
```
q = w + xi + yj + zk  corresponds to matrix:
[w+zi    x+yi]
[-x+yi   w-zi]
with determinant |q|² = 1
```

### Advantages
- **Intuitive for rotations**: Each S³ point directly encodes a 3D rotation
- **Smooth interpolation**: SLERP (spherical linear interpolation) gives shortest paths
- **No gimbal lock**: Quaternions avoid singularities in rotation representation
- **Compact**: 4 numbers instead of 9 (matrices) for 3D rotations
- **Lie group structure**: Powerful algebraic tools available
- **Natural navigation**: Rotating in quaternion space = rotating the viewpoint

### Disadvantages
- **Abstract visualization**: Hard to directly visualize quaternion values as 3D space
- **Requires interpretation**: Must decide how to visually represent "rotation at point P"
- **Double cover complexity**: Need to handle ±q equivalence
- **Less direct than coordinates**: Not immediately intuitive which quaternion is "where"
- **Same projection problem remains**: Still need stereographic or orthogonal projection to render

### Use Cases
- **Rotation visualization**: Show how rotations are distributed on S³
- **Camera control**: Use quaternion path for smooth camera motion (via SLERP)
- **Physics/graphics**: Natural for rigid body animation and orientation control
- **Group theory**: Demonstrate SU(2) and its relation to SO(3)

### Code Example

```python
def quaternion_to_rotation_matrix(q):
    """Convert unit quaternion to 3x3 rotation matrix."""
    w, x, y, z = q
    return np.array([
        [1 - 2(y² + z²),     2(xy - wz),     2(xz + wy)    ],
        [2(xy + wz),     1 - 2(x² + z²),     2(yz - wx)    ],
        [2(xz - wy),     2(yz + wx),     1 - 2(x² + y²)],
    ])

def visualize_as_rotation(s3_points):
    """Render each S³ point as the rotation it represents."""
    for q in s3_points:
        rotation_matrix = quaternion_to_rotation_matrix(q)
        # Rotate a canonical object (tetrahedron, frame, etc.)
        rotated_object = rotation_matrix @ canonical_object
        # Project to 2D and render
```

---

## 6. Slicing Methods (Cross-Sections)

### Mathematical Description

**Method**: Fix the w-coordinate to a constant, observe the resulting 3D cross-section.

For a fixed w = w₀ ∈ [-1, 1], the cross-section is:
```
{(x, y, z) : x² + y² + z² + w₀² = 1}
= {(x, y, z) : x² + y² + z² = 1 - w₀²}
```

This is a 2-sphere of radius r = √(1 - w₀²):
- **w₀ = 0** (equator): S³ → 3-sphere of radius 1 (maximum size)
- **w₀ = ±0.9**: 3-sphere of radius √(1 - 0.81) ≈ 0.436 (shrinking)
- **w₀ = ±1** (pole): 3-sphere degenerates to a point

### Visualization Technique

**Animated slicing**:
```
for w in [-1, -0.9, ..., 0.9, 1]:
    sphere_3d = 3D sphere of radius sqrt(1 - w²)
    render_sphere(sphere_3d, z_position=w_offset)
    or render with color encoding w
```

**Multiple simultaneous slices**:
- Show 5-10 slices at once, stacked or arranged
- Color each slice differently to indicate w value
- Allows understanding of how cross-sections change

**Rotating slices**:
- Rotate the slicing plane in 4D (not just w-axis)
- Observe different 3D structures as slicing direction changes

### Mathematical Properties

**Cross-section at w = w₀**:
- If |w₀| < 1: 2-sphere of radius √(1 - w₀²)
- Volume grows from 0 to maximum at w=0, then shrinks back to 0
- Maximum cross-sectional "volume" (surface area of 2-sphere) at w=0

**Rotating the slice plane**:
If we rotate first, slicing axis becomes arbitrary unit vector u ∈ S³, and the cross-section is still a 2-sphere but tilted.

### Advantages
- **Simple visualization**: Each slice is a familiar 3D sphere
- **Intuitive understanding**: Shows how 4D object decomposes
- **No singularities**: All values well-defined for |w₀| ≤ 1
- **Educational**: Naturally teaches dimension-reduction
- **Animation-friendly**: Time-slice animation shows evolution over 4th dimension
- **Multiple views**: Easy to show many slices simultaneously

### Disadvantages
- **Loses continuity**: Individual slices are disconnected (missing edges between them)
- **Global structure hidden**: Doesn't show how slices fit together on S³
- **Requires interpretation**: User must mentally reconstruct 4D topology
- **Information loss**: Viewing only one parameter's cross-section at a time
- **Static-feeling**: Doesn't capture the continuous surface well
- **Not ideal for exploration**: Hard to navigate to specific points

### Variants

**Oblique slicing**:
```
Cross-section for plane u·P = c (for constant c ∈ [-1, 1], unit vector u ∈ S³)
```

**Double slicing**:
Show two perpendicular planes simultaneously:
```
w = w₀ and x = x₀
resulting in 1D intersection (curve) on S³
```

**Density-based rendering**:
```
For each 3D voxel position, compute how many S³ slices pass through it.
Render density as opacity/color.
```

### Code Example

```python
def get_slice_at_w(w_value, num_points=100):
    """Get a 3D spherical cross-section of S³ at fixed w coordinate."""
    radius = np.sqrt(max(0, 1 - w_value**2))
    if radius < 1e-6:
        return np.array([[0, 0, 0]])  # degenerate point

    # Generate points on 2-sphere of radius r in xyz
    theta = np.linspace(0, 2*np.pi, num_points)
    phi = np.linspace(0, np.pi, num_points)
    points_3d = []
    for t in theta:
        for p in phi:
            x = radius * np.sin(p) * np.cos(t)
            y = radius * np.sin(p) * np.sin(t)
            z = radius * np.cos(p)
            points_3d.append([x, y, z])
    return np.array(points_3d)

def animate_slices(frames=60):
    """Animate S³ by showing cross-sections over w."""
    for frame in range(frames):
        w = -1 + 2 * frame / frames  # w from -1 to 1
        slice_points = get_slice_at_w(w)
        render_3d_sphere(slice_points, color_from_w(w))
```

---

## 7. Comparison: Pros and Cons Summary

| Method | Conformal | Global View | Singularities | Speed | Intuitive | Best For |
|--------|-----------|-------------|---------------|-------|-----------|----------|
| **Tangent Space** | Local | No (cone) | No | Fast | Yes | Real-time exploration |
| **Stereographic** | Yes | Yes* | At pole | Medium | Medium | Topological study |
| **Orthogonal** | No | Yes | No | Fastest | Medium | Quick debugging |
| **Hopf Fibration** | Yes** | Yes | At poles | Medium | No | Topology visualization |
| **Quaternion** | Varies | Varies | No | Medium | Medium | Rotation visualization |
| **Slicing** | N/A | Partial | No | Fast | Yes | Sequential understanding |

*Stereographic: except at projection pole
**Hopf: inherits from stereographic

---

## 8. Hybrid and Advanced Approaches

### Dual Projection Method
Display two projections side-by-side:
- Left: Orthogonal (current 4D rotation)
- Right: Stereographic or Hopf fibration view
- Helps understand same structure from different perspectives

### Progressive Disclosure
Start with orthogonal projection for simplicity, add:
1. Color gradients showing W-coordinate
2. Switch to stereographic with warnings about poles
3. Optional: Hopf fibration overlay

### Texture-based Coloring
Apply intrinsic colorization to any projection method:
```
color = function_of(position, angular_distance, coordinates)
e.g., color_from_hopf(stereographic_projection(P))
```

### Multi-axis Visualization
Show three orthogonal projections simultaneously (dropping w, x, y respectively) plus a 3D stereographic view.

---

## 9. Recommendations for 4sphere-explorer

### Current Choice: Tangent Space (✓ Correct)
The project correctly uses tangent space projection because:
- **Real-time interaction** demands efficiency
- **Camera-centric exploration** is the use case
- **Intuitive clustering** around crosshair is desirable
- **No singularities** in visible region
- **SLERP navigation** works perfectly with this choice

### Potential Enhancements

**1. Add Stereographic View Toggle**
```python
# Add to main.py view_mode
# 0 = assigned colors (tangent)
# 1 = 4D position colors (tangent)
# 2 = stereographic projection
# 3 = hopf fibration
```
Needs handling of poles (clipping or color-coding as "at infinity").

**2. Implement Quaternion-based Navigation**
Replace raw 4D rotation matrices with quaternion representation:
```python
camera_quat = np.array([1, 0, 0, 0])  # identity quaternion
# Rotate via quaternion multiplication
# SLERP already works with quaternions
```

**3. Add Slicing Mode**
```python
# Toggle: W key to cycle between projection methods
# When in slicing mode, show 3D sphere of current w-cross-section
# Use arrow keys to move w value
```

**4. Hopf Fibration Coloring**
```python
# Apply hopf_map(camera_pos) to auto-adjust color scheme
# Or use as optional overlay on any projection
```

**5. Multiple Simultaneous Views**
Split screen into:
- Main: Current tangent space projection (left 75%)
- Top-right: Orthogonal projection (for reference)
- Bottom-right: Hopf fibration slice
- Status info: Current method, camera position, visible point count

### Priority Order for Implementation
1. **High**: Stereographic toggle (single line FOV check becomes method selector)
2. **High**: Quaternion SLERP camera (refactor rotation code)
3. **Medium**: Slicing animation (w-parameter animation mode)
4. **Low**: Hopf visualization (purely educational, compute-intensive)
5. **Low**: Multi-view layout (major UI rewrite)

---

## 10. References and Further Reading

### Academic Papers
- Schleimer, Saul; Segerman, Henry. "Sculptures in S³." (2012) - Discusses physical and digital visualization of S³ structures.
- Lyons, David W. "An Elementary Introduction to the Hopf Fibration." - Comprehensive introduction to quaternion interpretation.

### Online Resources
- [Stereographic Projection - Wikipedia](https://en.wikipedia.org/wiki/Stereographic_projection)
- [3-sphere - Wikipedia](https://en.wikipedia.org/wiki/3-sphere)
- [Hopf fibration - Wikipedia](https://en.wikipedia.org/wiki/Hopf_fibration)
- [Quaternions and spatial rotation - Wikipedia](https://en.wikipedia.org/wiki/Quaternions_and_spatial_rotation)
- [4th Dimension Stereo-projection (interactive)](https://www.math.union.edu/~dpvc/math/4D/stereo-projection/welcome.html)
- [Four-Space Visualization of 4D Objects](https://hollasch.github.io/ray4/Four-Space_Visualization_of_4D_Objects.html)
- [Hopf Fibration Visualization - Niles Johnson](https://nilesjohnson.net/hopf.html)
- [Interactive 4D Handbook](https://baileysnyder.com/interactive-4d/)

### Software Tools
- [mwalczyk/hopf](https://github.com/mwalczyk/hopf) - Hopf fibration visualization tool
- [Tesseract Explorer](https://tsherif.github.io/tesseract-explorer/) - Interactive 4D visualization
- [Interactive 4D Visualization Tools](https://www.math.union.edu/~dpvc/math/4D/)

---

## 11. Mathematical Notation Reference

| Notation | Meaning |
|----------|---------|
| **S³** | 3-sphere (2D surface of a 4D ball); ⊂ ℝ⁴ |
| **S²** | Standard 2-sphere (familiar ball surface); ⊂ ℝ³ |
| **ℝⁿ** | n-dimensional real space |
| **||x||** | Euclidean norm of vector x |
| **x · y** | Dot product |
| **θ** | Angular distance (in radians) |
| **q*** | Complex conjugate of quaternion q |
| **SU(2)** | Special unitary group, isomorphic to S³ |
| **SO(3)** | Rotation group in 3D |
| **SLERP** | Spherical linear interpolation |

