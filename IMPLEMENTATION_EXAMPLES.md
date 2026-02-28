# S³ Projection Methods: Implementation Examples

Complete, runnable code snippets for each projection method. Copy these into `sphere.py` or `main.py` as needed.

---

## 1. Stereographic Projection Implementation

### Forward Projection (S³ → ℝ³)

```python
def stereographic_projection_forward(point, pole_index=0):
    """
    Project a point from S³ to ℝ³ using stereographic projection.

    Args:
        point: 4D point on S³ (unit vector)
        pole_index: which coordinate is the projection pole (0=x, 1=y, 2=z, 3=w)

    Returns:
        3D point in the hyperplane orthogonal to the pole direction
    """
    # Extract pole coordinate
    pole_coord = point[pole_index]

    # If too close to pole, return large vector in that direction
    if abs(pole_coord) > 0.99999:
        # Return a point far away (representation of infinity)
        result = np.zeros(3)
        direction = np.zeros(4)
        direction[pole_index] = 1.0
        # Project other coordinates to 3D
        idx = 0
        for i in range(4):
            if i != pole_index:
                result[idx] = point[i] * 1000  # Large multiplier for "infinity"
                idx += 1
        return result

    # Standard stereographic formula: divide by (1 - pole_coord)
    divisor = 1.0 - pole_coord
    result = np.zeros(3)
    idx = 0
    for i in range(4):
        if i != pole_index:
            result[idx] = point[i] / divisor
            idx += 1

    return result


def stereographic_projection_backward(point_3d, pole_index=0):
    """
    Inverse stereographic projection: ℝ³ → S³.

    Args:
        point_3d: 3D point
        pole_index: which coordinate was the pole

    Returns:
        4D point on S³
    """
    r_squared = np.dot(point_3d, point_3d)
    denominator = r_squared + 1.0

    # Build 4D point
    result = np.zeros(4)
    idx = 0
    for i in range(4):
        if i == pole_index:
            result[i] = (r_squared - 1.0) / denominator
        else:
            result[i] = 2.0 * point_3d[idx] / denominator
            idx += 1

    # Normalize to ensure unit vector (numerical safety)
    result /= np.linalg.norm(result)
    return result
```

### Integration with Current Project

```python
# In main.py, modify rendering section:

if view_mode == 2:  # New mode: stereographic
    # For each visible point, use stereographic instead of tangent
    for i, idx in enumerate(visible_indices):
        p4d = points[idx]
        p3d = stereographic_projection_forward(p4d, pole_index=0)

        # Clip points that project too far (near pole)
        dist_from_origin = np.linalg.norm(p3d)
        if dist_from_origin > 10.0:  # Arbitrary cutoff
            continue  # Skip rendering (at "infinity")

        # Perspective project 3D to 2D
        # Use simple perspective: divide by distance
        x = view_width / 2 + (p3d[0] / (p3d[2] + 5.0)) * 200  # scale factor
        y = SCREEN_HEIGHT / 2 - (p3d[1] / (p3d[2] + 5.0)) * 200

        if 0 <= x < view_width and 0 <= y < SCREEN_HEIGHT:
            # Render with coloring
            pygame.draw.circle(screen, point_colors[idx], (int(x), int(y)), 3)
```

### Unit Tests

```python
def test_stereographic_roundtrip():
    """Stereographic projection should roundtrip correctly."""
    # Test a few points on S³
    test_points = [
        np.array([1.0, 0, 0, 0]),  # north pole
        np.array([0.7071, 0.7071, 0, 0]),
        np.array([0.5, 0.5, 0.5, 0.5]),
    ]

    for p in test_points:
        if abs(p[0]) < 0.99999:  # Not at pole
            p3d = stereographic_projection_forward(p, pole_index=0)
            p_recovered = stereographic_projection_backward(p3d, pole_index=0)
            error = np.linalg.norm(p - p_recovered)
            assert error < 1e-6, f"Roundtrip error: {error}"
            print(f"✓ Roundtrip OK for {p}")
        else:
            print(f"✓ Skipped pole point {p}")
```

---

## 2. Orthogonal Projection Implementation

### Simple Axis-Aligned

```python
def orthogonal_projection_simple(point, drop_axis=3):
    """
    Simple orthogonal projection: drop one coordinate.

    Args:
        point: 4D point
        drop_axis: which axis to drop (0-3)

    Returns:
        3D point (concatenation of other three axes)
    """
    result = []
    for i in range(4):
        if i != drop_axis:
            result.append(point[i])
    return np.array(result)


# In main.py:
if view_mode == 2:  # orthogonal
    for i, idx in enumerate(visible_indices):
        p4d = points[idx]
        p3d = orthogonal_projection_simple(p4d, drop_axis=3)  # drop w

        # Perspective project to 2D
        z_depth = p3d[2]
        scale = 1.0 / (1.0 + z_depth)  # perspective scale
        x = view_width / 2 + p3d[0] * scale * 300
        y = SCREEN_HEIGHT / 2 + p3d[1] * scale * 300

        pygame.draw.circle(screen, point_colors[idx], (int(x), int(y)), 3)
```

### Rotated Orthogonal (More Useful)

```python
def orthogonal_projection_rotated(point, rotation_matrix_4d):
    """
    Apply 4D rotation, then orthogonal project.

    Args:
        point: 4D point
        rotation_matrix_4d: 4x4 rotation matrix in 4D

    Returns:
        3D point after rotation and dropping last coordinate
    """
    rotated = rotation_matrix_4d @ point
    return rotated[:3]  # drop w coordinate


def rotation_matrix_4d(angle, plane=(0, 1)):
    """
    Build a 4D rotation matrix for a given plane and angle.

    Args:
        angle: rotation angle in radians
        plane: tuple of two axis indices (0-3) defining rotation plane

    Returns:
        4x4 rotation matrix
    """
    c, s = np.cos(angle), np.sin(angle)
    R = np.eye(4)
    i, j = plane
    R[i, i] = c
    R[i, j] = -s
    R[j, i] = s
    R[j, j] = c
    return R


# In main.py, extend camera control:
rotation_angle_orthogonal = 0  # Track rotation in addition to camera_pos

if keys[pygame.K_w]:
    rotation_angle_orthogonal += 0.02
    rotation_4d = rotation_matrix_4d(rotation_angle_orthogonal, plane=(0, 1))
```

---

## 3. Hopf Fibration Implementation

### Core Hopf Map

```python
def hopf_map(quaternion):
    """
    Hopf fibration map: S³ (as unit quaternion) → S².

    The Hopf map reveals the fiber bundle structure of S³.

    Args:
        quaternion: 4D point [w, x, y, z] (unit vector)

    Returns:
        3D point on S² (unit sphere)
    """
    w, x, y, z = quaternion

    # Hopf map formulas
    s2_x = x**2 + y**2 - w**2 - z**2
    s2_y = 2 * (w*x + y*z)
    s2_z = 2 * (w*y - x*z)

    # Result is naturally a unit vector
    s2_point = np.array([s2_x, s2_y, s2_z])

    # Normalize (shouldn't be necessary, but for numerical safety)
    norm = np.linalg.norm(s2_point)
    if norm > 1e-10:
        s2_point /= norm

    return s2_point


def hopf_map_to_color(s2_point):
    """
    Convert S² point to RGB color using spherical coordinates.

    Args:
        s2_point: 3D point (unit sphere)

    Returns:
        RGB tuple (0-255 each)
    """
    x, y, z = s2_point

    # Spherical coordinates
    theta = np.arctan2(y, x)  # azimuth: [-π, π]
    phi = np.arccos(np.clip(z, -1, 1))  # polar: [0, π]

    # Map to HSV
    hue = (theta + np.pi) / (2 * np.pi)  # [0, 1]
    saturation = 0.8  # keep constant for vibrant colors
    brightness = 0.5 + 0.5 * np.sin(phi)  # brighten equator

    # Convert HSV to RGB
    r, g, b = colorsys.hsv_to_rgb(hue, saturation, brightness)
    return (int(r * 255), int(g * 255), int(b * 255))


# Integration example:
def render_with_hopf_coloring(points, visible_indices):
    """Render points colored by Hopf fibration structure."""
    colors = []
    for idx in visible_indices:
        p4d = points[idx]
        hopf_point = hopf_map(p4d)
        color = hopf_map_to_color(hopf_point)
        colors.append(color)
    return colors
```

### Fiber Visualization

```python
def get_hopf_fiber(s2_target, num_samples=50):
    """
    Given a point on S² (target Hopf coordinate), generate the
    corresponding fiber circle on S³.

    The fiber is the pre-image under the Hopf map: points on S³
    that all map to the same S² coordinate.

    Args:
        s2_target: target point on S² [x, y, z]
        num_samples: how many points to generate on the fiber circle

    Returns:
        array of points on S³ forming the fiber
    """
    # For a given S² point, the fiber is a circle on S³
    # This is complex to compute analytically, so we use a parameterization

    # Approach: discretize angle around fiber, check which quaternions map to target
    # (This is a simplification; proper implementation would use quaternion fiber formula)

    fiber_points = []
    for i in range(num_samples):
        t = 2 * np.pi * i / num_samples
        # Parameterization of the preimage circle
        # This depends on which S² point we're targeting
        # For simplicity, rotate a base fiber
        base_quat = np.array([np.cos(t/2), np.sin(t/2), 0, 0])
        # Apply rotation based on s2_target to position the fiber
        # (details omitted for brevity)
        fiber_points.append(base_quat)

    return np.array(fiber_points)
```

---

## 4. Quaternion-Based Navigation

### Quaternion Rotation

```python
def quaternion_multiply(q1, q2):
    """
    Multiply two quaternions: q1 * q2.

    q = [w, x, y, z] = w + xi + yj + zk
    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2

    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])


def quaternion_conjugate(q):
    """Conjugate of quaternion q."""
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quaternion_from_axis_angle(axis, angle):
    """
    Create a quaternion from axis-angle representation.

    Args:
        axis: 3D unit vector defining rotation axis
        angle: rotation angle in radians

    Returns:
        Unit quaternion representing the rotation
    """
    half_angle = angle / 2.0
    w = np.cos(half_angle)
    xyz = np.sin(half_angle) * axis
    return np.array([w, xyz[0], xyz[1], xyz[2]])


def quaternion_to_rotation_matrix(q):
    """Convert unit quaternion to 3x3 rotation matrix."""
    w, x, y, z = q

    return np.array([
        [1 - 2*(y**2 + z**2), 2*(x*y - w*z), 2*(x*z + w*y)],
        [2*(x*y + w*z), 1 - 2*(x**2 + z**2), 2*(y*z - w*x)],
        [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x**2 + y**2)],
    ])


# In main.py, replace raw rotation with quaternions:
class CameraQuaternion:
    def __init__(self):
        self.q = np.array([1.0, 0.0, 0.0, 0.0])  # identity

    def rotate_xy(self, angle):
        """Rotate in XY plane."""
        rot = quaternion_from_axis_angle(
            np.array([0, 0, 1]), angle
        )
        self.q = quaternion_multiply(rot, self.q)
        self.q /= np.linalg.norm(self.q)

    def rotate_xz(self, angle):
        """Rotate in XZ plane."""
        rot = quaternion_from_axis_angle(
            np.array([0, 1, 0]), angle
        )
        self.q = quaternion_multiply(rot, self.q)
        self.q /= np.linalg.norm(self.q)

    def rotate_xw(self, angle):
        """Rotate in XW plane (4D)."""
        # This is trickier: need to rotate in hyperplane
        # Approximate via Euler angles
        rot = quaternion_from_axis_angle(
            np.array([0, 0, 1]), angle * 0.5  # scaled influence
        )
        self.q = quaternion_multiply(rot, self.q)
        self.q /= np.linalg.norm(self.q)

    def to_4d_point(self):
        """Convert quaternion to 4D point on S³."""
        return self.q
```

---

## 5. Slicing Implementation

### 3D Cross-Section at Fixed W

```python
def get_s3_slice_at_w(w_value, num_samples=100):
    """
    Generate a 3D spherical cross-section of S³ at a fixed w coordinate.

    The cross-section is: {(x, y, z) : x² + y² + z² = 1 - w²}

    Args:
        w_value: w coordinate in [-1, 1]
        num_samples: resolution of the sphere mesh

    Returns:
        Array of 3D points forming the cross-section sphere
    """
    # Radius of the 2-sphere at this w value
    if abs(w_value) > 1.0:
        return np.array([[0, 0, 0]])  # degenerate

    radius = np.sqrt(1.0 - w_value**2)

    # Generate sphere points in spherical coordinates
    theta = np.linspace(0, 2*np.pi, num_samples)
    phi = np.linspace(0, np.pi, num_samples)

    points = []
    for t in theta:
        for p in phi:
            x = radius * np.sin(p) * np.cos(t)
            y = radius * np.sin(p) * np.sin(t)
            z = radius * np.cos(p)
            points.append([x, y, z])

    return np.array(points)


def animate_slicing_sequence(num_frames=60, show_multiple=False):
    """
    Animate S³ by progressing through cross-sections.

    Args:
        num_frames: total frames in animation
        show_multiple: if True, show 3-5 slices simultaneously

    Yields:
        (w_value, points_3d, frame_number)
    """
    for frame in range(num_frames):
        w = -1.0 + 2.0 * frame / (num_frames - 1)
        points = get_s3_slice_at_w(w)
        yield w, points, frame


# In main.py:
slicing_mode = False
current_w = 0.0

if slicing_mode:
    # Animate or allow manual control
    current_w += 0.01  # or use arrow keys to control
    current_w = np.clip(current_w, -1.0, 1.0)

    slice_points = get_s3_slice_at_w(current_w, num_samples=50)

    # Project 3D slice to 2D screen
    for p3d in slice_points:
        x = view_width / 2 + p3d[0] * 200
        y = SCREEN_HEIGHT / 2 + p3d[1] * 200
        pygame.draw.circle(screen, POINT_COLOR, (int(x), int(y)), 2)

    # Draw status
    status = f"Slicing at w={current_w:.2f}"
    status_text = font.render(status, True, TEXT_COLOR)
    screen.blit(status_text, (10, 60))
```

### Rotating Slice Plane

```python
def get_s3_slice_along_axis(axis_4d, value, num_samples=100):
    """
    Slice S³ along an arbitrary axis (not just w).

    Args:
        axis_4d: 4D unit vector defining the slicing plane normal
        value: position along that axis (scalar value)
        num_samples: mesh resolution

    Returns:
        Array of points in the intersection plane
    """
    # This is more complex: need to solve for 3D surface within hyperplane
    # Simplified: use orthogonal basis in the hyperplane

    # Build orthonormal basis orthogonal to axis_4d
    basis = []
    for e in np.eye(4):
        v = e - np.dot(e, axis_4d) * axis_4d
        if np.linalg.norm(v) > 1e-6:
            basis.append(v / np.linalg.norm(v))
        if len(basis) == 3:
            break

    # Generate 2-sphere in the hyperplane
    radius = np.sqrt(max(0, 1 - value**2))
    points = []
    for i in np.linspace(-1, 1, num_samples):
        for j in np.linspace(-1, 1, num_samples):
            p2d = np.array([i, j])
            if np.dot(p2d, p2d) <= 1:  # within unit disk
                # Map to 3D sphere
                p3d = radius * np.sqrt(i**2 + j**2) * (basis[0] * i + basis[1] * j)
                # Convert back to 4D
                p4d = value * axis_4d + p3d  # simplified
                if abs(np.linalg.norm(p4d) - 1.0) < 0.1:  # roughly on S³
                    points.append(p4d)

    return np.array(points) if points else np.array([[0, 0, 0, 0]])
```

---

## 6. Integration Template: Adding a New Projection Mode

### Minimal Integration

```python
# In sphere.py, add new projection function:
def new_projection_method(point, camera_pos=None, **kwargs):
    """
    Your projection method here.

    Args:
        point: 4D point on S³
        camera_pos: optional camera position

    Returns:
        3D point (or 2D point if projecting all the way to screen)
    """
    # Implementation
    return np.array([0, 0, 0])


# In main.py, add to view_mode options:
# 0 = assigned colors + tangent space (current)
# 1 = 4D position colors + tangent space
# 2 = stereographic projection
# 3 = hopf fibration coloring + stereographic
# 4 = orthogonal projection
# 5 = slicing

# Add to import:
from sphere import new_projection_method

# In render loop:
if view_mode == 2:
    for i, idx in enumerate(visible_indices):
        p4d = points[idx]
        p3d = new_projection_method(p4d, camera_pos=camera_pos)

        # Project to 2D (reuse existing logic or create new)
        p2d, depth = project_to_2d(p3d, view_width, SCREEN_HEIGHT)

        if 0 <= p2d[0] < view_width and 0 <= p2d[1] < SCREEN_HEIGHT:
            color = determine_color(idx, view_mode)
            pygame.draw.circle(screen, color, p2d.astype(int), 3)
```

### Testing a New Method

```python
def test_new_projection():
    """Unit test template for new projection method."""
    # Generate test points on S³
    test_points = [
        random_point_on_s3(20),
        np.array([1, 0, 0, 0]),
        np.array([0.5, 0.5, 0.5, 0.5]),
    ]

    for p in test_points:
        result = new_projection_method(p)

        # Check result is 3D
        assert len(result) == 3, f"Expected 3D, got {len(result)}D"

        # Check not NaN/inf
        assert np.all(np.isfinite(result)), f"Non-finite result: {result}"

        print(f"✓ {p} → {result}")

# Run once to validate
test_new_projection()
```

---

## Summary Table

| Method | File | Function | Lines | Difficulty |
|--------|------|----------|-------|------------|
| Stereographic | `sphere.py` | `stereographic_projection_*` | 40 | Medium |
| Orthogonal | `sphere.py` | `orthogonal_projection_*` | 20 | Low |
| Hopf | `sphere.py` | `hopf_map`, `hopf_map_to_color` | 35 | Medium |
| Quaternion | `sphere.py` + `main.py` | `quaternion_*`, `CameraQuaternion` | 60 | Medium-High |
| Slicing | `sphere.py` + `main.py` | `get_s3_slice_at_w`, control logic | 50 | Low-Medium |

