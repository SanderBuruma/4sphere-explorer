# S³ Projection Methods: Visual Comparison Guide

ASCII diagrams and visual explanations for understanding each projection method.

---

## 1. Tangent Space Projection (Current Implementation)

### Visual Concept

```
4D SPHERE (S³)                  3D TANGENT SPACE              2D SCREEN
┌─────────────┐
│   ╱╲╱╲      │ Camera            Basis vectors              Camera at center
│  ╱  ╲  ╲    │ looking out       b1 ┌───┐                   ⊕ crosshair
│ ╱ [⊕] ╲  ╲  │ into S³           b2 │ P │ Angular           Nearby points
│ ╲      ╲  ╱ │                  b3 └───┘ distance           cluster around
│  ╲  ╱╱  ╱   │                         θ = arccos(P·cam)
│   ╲╱╱╱╱     │                  Local projection:           Points fade
└─────────────┘                  P_local = θ × basis_coeff  with distance

  Each point projected         3D local coords            2D screen coords
  into tangent plane at        scaled by distance         (standard 3D→2D)
  camera position                                         projection
```

### Mathematical Essence

1. **Establish local coordinates**: At camera position, create 3 orthonormal basis vectors perpendicular to camera direction
2. **Measure distance**: Angular distance θ between camera and point
3. **Project direction**: Compute which direction (in tangent space) the point lies
4. **Scale and render**: Scale direction by angle, project to 2D

### Example: How a Point Moves

```
Camera at [1, 0, 0, 0]   →   Point at [0.9, 0.3, 0.3, 0]
Angular distance = arccos(0.9) ≈ 0.45 rad
Direction in tangent space = (0.3, 0.3, 0) normalized
Final 3D = 0.45 × (0.3, 0.3, 0) = (0.135, 0.135, 0)
Screen position = center + (0.135, 0.135) × scale
                = (600, 400) + (135, 135)
                = (735, 535)   [assuming 1200×800, scale=1000]
```

### Strengths & Weaknesses

```
✓ STRENGTHS                          ✗ WEAKNESSES
─────────────────────────────────────────────────────────────
✓ Interactive real-time              ✗ Can't see opposite side
✓ Points cluster around camera       ✗ Only FOV cone visible
✓ Angular distances preserved        ✗ Distortion at FOV edges
✓ No singularities (in view)          ✗ Hard to see global structure
✓ Intuitive navigation               ✗ Antipodal point always hidden
✓ Fast computation
```

---

## 2. Stereographic Projection

### Visual Concept

```
4D SPHERE (S³)                  PROJECTION PROCESS           3D RESULT

                                 Pole (light)                Plane w=0
Light source                          ●                      (3D space)
at north pole             ╱ ray      ╱ │ ╲
                        ╱ from      ╱  │  ╲                  Points near
        ●────────────────pole      ╱   │   ╲ ray             pole project
       ╱│╲                        ╱    P    ╲ to plane        far away
      ╱ │ ╲  Points on S³       ╱     (on  ╲                 (toward ∞)
     │  │  ╱ cast shadows      │      sphere) ╲
     │  ├─╱ onto plane         │            ╲ ╱              Points near
     │ ╱│  (at w=0)            │          ●──●               equator
     ├─ │   far from pole      │    Intersection            cluster
     │  │   project close      │    (projected point)
     │ ╱    to origin          │                           Points at
     ├─                        └────────────────────       pole = ∞
     │
  Points near pole
  (top of sphere)
```

### Mathematical Essence

```
Forward: S³ → ℝ³
─────────────────
For point P = (p₀, p₁, p₂, p₃) on S³:
  If p₀ ≈ 1 (near north pole):
    Projection → ∞ (points blow up)

  Projection = (p₁, p₂, p₃) / (1 - p₀)
  (Divide by distance from pole)

Example:
  P = (0.95, 0.2, 0.1, 0.15)  [normalized]
  Projection = (0.2, 0.1, 0.15) / (1 - 0.95)
             = (0.2, 0.1, 0.15) / 0.05
             = (4.0, 2.0, 3.0)
             [far from origin]

  P = (0.5, 0.5, 0.5, 0)  [at equator w.r.t. w-axis]
  Projection = (0.5, 0.5, 0) / (1 - 0.5)
             = (0.5, 0.5, 0) / 0.5
             = (1.0, 1.0, 0)
             [closer to origin]

Backward: ℝ³ → S³
──────────────────
For 3D point (x, y, z):
  r² = x² + y² + z²
  P = [(r² - 1)/(r² + 1), 2x/(r² + 1), 2y/(r² + 1), 2z/(r² + 1)]

Example:
  (x, y, z) = (1, 0, 0)
  r² = 1
  P = [(1-1)/(1+1), 2/(1+1), 0, 0]
    = [0, 1, 0, 0]
```

### Key Properties

```
CONFORMAL (angle-preserving):
  Two curves intersecting at 90° on S³
  → Still intersect at 90° in 3D projection

  This is mathematically beautiful but makes
  interpretation tricky: "distances wrong, angles right"

CIRCLES → CIRCLES or LINES:
  A circle on S³ projects to either:
  • A circle in 3D (if not parallel to pole)
  • A line in 3D (if perpendicular to pole direction)

VISUALIZATION CHALLENGE:
  Points near pole need special handling:

  Option 1: Clip them (don't render beyond distance D)
  Option 2: Color them differently ("at infinity")
  Option 3: Use hyperbolic geometry to render properly
```

### Visual Example: Rotating Through Pole Region

```
Frame 1: Camera far from pole
         Normal projection, points clustered

Frame 2: Camera approaching pole (p₀ → 1)
         Visible points spread out
         Points become darker/dimmer (visual cue)

Frame 3: Camera at pole
         Everything projects to ∞
         (Nothing visible or only clipped region)

Frame 4: Camera retreating
         Points converge back to clustered view
```

---

## 3. Orthogonal Projection

### Visual Concept

```
4D SPHERE (S³)              PROJECTION PROCESS           3D RESULT
All 4 coordinates           "Look along" one axis       Just 3 coordinates

  w axis
  ↑
  │   ◀────────────────────
  │  /                     \ Looking along the
  │ /  [point]             \ z-axis (perpendicular)
  │/   on S³               │
  └─────────────────────▶   │ Drop z-coordinate
  z axis                    │ Keep x, y, w
                            └─▶ (x, y, w) in 3D


Simple formula:
  3D = (p₀, p₁, p₂)    [drop p₃, the w-coordinate]

or any combination: (p₀, p₁, p₃), (p₀, p₂, p₃), etc.
```

### Visual Effect: What You See

```
AXIS-ALIGNED PROJECTION (drop w):

  Original S³ "shape"        What you see in 3D

      ●●●●●●●●                 ●●●●●●●●
    ●●●●●●●●●●●●●            ●●●●●●●●●●●●●
   ●●●●●●●●●●●●●●●●  →       ●●●●●●●●●●●●●●●●
    ●●●●●●●●●●●●●             ●●●●●●●●●●●●●
      ●●●●●●●●               ●●●●●●●●

  (Removing w removes the "depth" entirely—
   all points project to the (x,y,z) plane)

ROTATED PROJECTION (rotate in 4D, then drop):

  1. Rotate all points in 4D space
  2. Then drop one coordinate

  Effect: different axis is "dropped"
         Creates different viewpoint of S³
```

### Strengths & Weaknesses

```
✓ FAST: Just array slicing or 1 multiplication
✓ NO SINGULARITIES: Works everywhere
✓ SIMPLE: Easiest to understand & code
✓ INTUITIVE: "Which 3 of 4 axes do you want?"

✗ NOT CONFORMAL: Angles get distorted
✗ LOSES INFORMATION: Entire dimension discarded
✗ NO DEPTH CUE: Can't tell near from far in dropped axis
✗ ASYMMETRIC: Result depends heavily on which axis dropped
✗ CIRCLES BECOME ELLIPSES: Geometric distortion
```

### Variant: Include W as Color or Depth

```
Instead of just dropping w, use it:

Option A: w → Brightness
  color = base_color × (0.5 + 0.5 * w)
  Points with w=1 are bright
  Points with w=-1 are dark

Option B: w → Hue
  hue = (w + 1) / 2 * 360°
  w=1 → red, w=0 → green, w=-1 → blue

Option C: w → Perspective
  scale = 1 / (1 + w)
  Points with w=1 appear large
  Points with w=-1 appear small
```

---

## 4. Hopf Fibration

### Visual Concept

```
S³ has hidden structure: it's a bundle of circles

HOPF MAP (S³ → S²):
"What if every point on S³ is colored by its Hopf coordinate?"

    S³ points colored by Hopf value

    ●(Red)   ●(Blue)  ●(Green)    ← All project to
    ↓        ↓        ↓              different points on S²

    ┌────S²────────┐
    │ ●R ●B ●G    │
    │  ╲│╱         │  Hopf map groups
    │   ●          │  circles into S²
    └──────────────┘


FIBER STRUCTURE:

All points that map to the same S² location form a circle!

  S² point #1 ──Hopf map←── Circle of S³ points
  S² point #2 ──Hopf map←── Another circle
  S² point #3 ──Hopf map←── Another circle
  ...

  (Every point on S³ belongs to exactly one fiber circle)
```

### Mathematical Visualization

```
Hopf Map Formula (for quaternions):

Input: q = [w, x, y, z] (point on S³)

Output:
  s₁ = x² + y² - w² - z²
  s₂ = 2(wx + yz)
  s₃ = 2(wy - xz)

Result: (s₁, s₂, s₃) is a point on S² (always unit length!)

GEOMETRIC INSIGHT:
─────────────────
The Hopf map is "non-trivial" because:
• Not every point on S³ gets its own point on S²
• Instead, circles of points map to single S² points
• This creates nested, linked torus structures when visualized

This reveals that S³ is NOT just S² × S¹ (simple product)
but has a TWISTED product structure (non-trivial bundle).
```

### Visual Rendering

```
STEP 1: Color by Hopf coordinate
        (Each S³ point gets color based on S² location)

        [Colorful sphere-like shape]

STEP 2: Apply stereographic projection
        to visualize in 3D

        [Colored, contorted 3D structure]

STEP 3: Render fibers as tubes/curves
        to see the circle structure

        [Linked tori, woven patterns]

This reveals the most abstract property of S³:
its fiber bundle structure over S².
```

---

## 5. Quaternion Representation

### Visual Concept

```
S³ AS A ROTATION SPACE:

Each point on S³ = a unit quaternion = a 3D rotation!

    S³ point: q = [w, x, y, z]
         ↓
    Interpret as: 3D rotation
         ↓
    Apply rotation to canonical object (tetrahedron, frame, etc.)
         ↓
    Render the rotated object


EXAMPLE:

    Quaternion [1, 0, 0, 0]  = Identity rotation (no rotation)
               [0, 1, 0, 0]  = 180° rotation about X-axis
               [√2/2, √2/2, 0, 0]  = 90° rotation about X-axis

    Visualize by rendering a rotated tetrahedron at each point!
```

### Interpolation Advantage

```
SLERP on quaternions gives the shortest path on S³:

    q_start ────────── q_path ────────── q_end
       (start)       (interpolate)      (end)

    Path on S³:  great circle arc

    In visualization: smooth camera motion along S³ surface

    Color can represent:
    • Rotation angle (brightness)
    • Rotation axis (hue)
    • Resulting orientation (display rotated object)
```

### Double Cover Property

```
Important geometric fact:

    Each 3D rotation has TWO quaternion representations:

    q and -q both represent the same 3D rotation!

    [0.707, 0.707, 0, 0]  →  180° about X-axis
    [-0.707, -0.707, 0, 0] →  Same 180° about X-axis

    This is why S³ is the "double cover" of SO(3).

    Visualizing this requires showing antipodal points
    have the same visual interpretation.
```

---

## 6. Slicing Method

### Visual Concept

```
ANIMATE S³ by showing cross-sections:

    w = -1.0         w = -0.5        w = 0.0
    ●●●●●●●●         ●●●●●●●●●●●●    ●●●●●●●●●●●●●●●
    (point)          (small sphere)   (large sphere)

    w = 0.5          w = 1.0
    ●●●●●●●●●●●●     ●●●●●●●●
    (shrinking)      (point)

    Animation shows: point → growing sphere → shrinking → point
```

### Mathematical Explanation

```
CROSS-SECTION AT w = w₀:

All points satisfying:
  x² + y² + z² + w₀² = 1
    ↓
  x² + y² + z² = 1 - w₀²
    ↓
  3D sphere of radius r = √(1 - w₀²)

VOLUME BEHAVIOR:

  Volume(w) = (4π/3) × [1 - w²]^(3/2)

  At w = 0:    Vol = 4π/3  (maximum)
  At w = ±0.5: Vol ≈ 4.05  (smaller)
  At w = ±1:   Vol = 0     (point)

  Graph:  V
          │      ●●●●●
          │    ●       ●
          │  ●           ●
          │●               ●
          └─────────────────── w
           -1   -0.5   0   0.5   1

  Counter-intuitive: volume peaks at CENTER, not spread out!
  (This is a feature of 4D geometry, not 3D)
```

### Visualization Variants

```
VARIANT 1: Single animated slice
  ┌─────────────────┐
  │                 │
  │     ○○○○○○      │  Time → w changes
  │    ○ ← ○○○○    │  Sphere grows/shrinks
  │     ○○○○○○      │
  │                 │
  └─────────────────┘

VARIANT 2: Multiple simultaneous slices
  ┌─────────────────┐
  │    ○○○○ (w=1)   │
  │   ○○○○○○ (w=0.5)│  See how
  │  ○○○○○○○○ (w=0) │  cross-sections
  │   ○○○○○○ (w=-0.5)│ relate
  │    ○○○○ (w=-1)  │
  └─────────────────┘

VARIANT 3: Rotating slice plane
  ┌─────────────────┐
  │      ╱○○○╲      │  Instead of slicing at w=const,
  │    ╱○○●○○○╲    │  slice along rotated axis
  │   ╱ ○○ ○○  ╲   │
  │  ╱   ○ ○    ╲  │  See different structures
  │ ╱           ╲ │
  └─────────────────┘
```

---

## 7. Side-by-Side Comparison

### What Each Method Shows Best

```
Tangent Space:
└─ ✓ Local neighborhoods       ✓ Interactive exploration
   ✓ Angular relationships     ✗ Global topology

Stereographic:
└─ ✓ Conformal structure       ✓ Global view (except pole)
   ✓ Circle preservation       ✗ Foreshortening

Orthogonal:
└─ ✓ Speed                     ✓ Multiple simultaneous views
   ✓ No singularities          ✗ Angle distortion

Hopf Fibration:
└─ ✓ Fiber bundle structure    ✓ Beautiful visuals
   ✓ Reveals hidden topology   ✗ Complex to compute

Quaternion:
└─ ✓ Rotation interpretation   ✓ Natural SLERP interpolation
   ✓ Physics connection        ✗ Requires extra layer

Slicing:
└─ ✓ Intuitive dimension reduction  ✓ Animated sequences
   ✓ No singularities               ✗ Loses continuity
```

---

## 8. "How Would This Look?" Scenarios

### Scenario 1: A Point at [0.9, 0.3, 0.2, 0.1]

**Tangent Space (camera at origin [1,0,0,0])**
```
Angular distance = 0.45 rad
Projects to nearby screen position (all points nearby)
Appears as bright dot near crosshair
```

**Stereographic**
```
Divides by (1 - 0.9) = 0.1
Result = [3, 2, 1] / 0.1 = [30, 20, 10]
Very far from origin (near the projection plane edge)
```

**Orthogonal**
```
Just [0.9, 0.3, 0.2] in 3D
Projects normally, not far from origin
```

**Hopf Fibration**
```
Hopf value = (0.3² + 0.2² - 0.9² - 0.1²) ≈ -0.76
(on the S² sphere, this is in the negative hemisphere)
Colored according to S² location
```

---

## 9. Decision Guide: "I See [This], I Want [That]"

```
I see: Cluster of points around center
I want: Global view without cluster
→ Try: Stereographic or Orthogonal

I see: Beautiful linked tori structure
I want: To understand it
→ Read: Hopf fibration explanation

I see: Smooth animation of rotation
I want: To know what rotation it is
→ Use: Quaternion rendering of rotated object

I see: Static point cloud
I want: To understand topology
→ Try: Hopf coloring or slicing

I see: Distorted circles become ellipses
I want: To preserve shapes
→ Try: Stereographic (conformal)

I see: Everything projecting to infinity
I want: To see those points
→ Use: Clipping, coloring, or different projection

I see: Only one axis missing (w direction)
I want: To visualize that axis
→ Try: Coloring by w or perspective scaling
```

---

## 10. Color Coding Reference

When implementing, consider:

```
VIEW MODE 0 (Current): Assigned Colors
└─ Each point has fixed random color
   Brightness modulated by distance
   Shows: Point identity and neighborhood

VIEW MODE 1 (Current): 4D Position Colors
└─ R = (x+1)×127.5, G = (y+1)×127.5, B = (z+1)×127.5, W=brightness
   Shows: Which "quadrant" of S³ each point is in
   Useful for orientation

NEW MODE: Hopf Fibration Colors
└─ Color by S² value from Hopf map
   Hue = azimuth on S²
   Brightness = distance from south pole
   Shows: Fiber structure

NEW MODE: Distance from Camera
└─ Hue = angular distance
   Saturation = relative direction
   Shows: Neighborhood topology

NEW MODE: W-coordinate
└─ Color palette from w=-1 (red) to w=+1 (blue)
   Shows: Fourth dimension as color
```

