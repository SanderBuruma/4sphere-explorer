"""
Compass widget for 4D orientation HUD.

Renders two great-circle rings projected from R^4 into 2D widget space:
  - NS ring: great circle in the XY plane of R^4 (passes through Y-axis poles)
  - W  ring: great circle in the XW plane of R^4 (passes through W-axis poles)

Each ring is sampled as 64 points on S3, projected through the camera
orientation frame, and drawn as a polyline. Arcs behind the camera are
rendered dimmer to convey depth.

Public API:
    render_compass(screen, orientation, x, y, size=120)
"""

import math
import pygame

# Font cache keyed by point size
_font_cache = {}

# Number of sample points per ring
_N = 64

# Fixed plane vectors for each ring (unit vectors in R^4 as plain tuples)
# NS ring: plane spanned by X=[1,0,0,0] and Y=[0,1,0,0]
_NS_A = (1.0, 0.0, 0.0, 0.0)   # X axis
_NS_B = (0.0, 1.0, 0.0, 0.0)   # Y axis (poles here)

# W ring: plane spanned by X=[1,0,0,0] and W=[0,0,0,1]
_W_A  = (1.0, 0.0, 0.0, 0.0)   # X axis
_W_B  = (0.0, 0.0, 0.0, 1.0)   # W axis (poles here)

# Ring colors
_NS_COLOR_BRIGHT = (100, 180, 255)    # blue-white, front arcs
_NS_COLOR_DIM    = (40,  80, 120)     # dimmed, back arcs
_W_COLOR_BRIGHT  = (255, 160, 80)     # amber, front arcs
_W_COLOR_DIM     = (120,  65, 25)     # dimmed, back arcs


# ---------------------------------------------------------------------------
# Math helpers (no numpy — plain Python)
# ---------------------------------------------------------------------------

def _dot4(a, b):
    """Dot product of two 4-element sequences."""
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]


def _sample_ring(a, b):
    """Return list of 64 points on the great circle cos(t)*a + sin(t)*b."""
    step = 2.0 * math.pi / _N
    pts = []
    for i in range(_N):
        t = i * step
        c, s = math.cos(t), math.sin(t)
        pts.append((
            c * a[0] + s * b[0],
            c * a[1] + s * b[1],
            c * a[2] + s * b[2],
            c * a[3] + s * b[3],
        ))
    return pts


def _project(p, orientation, cx, cy, scale):
    """Project a point p in R^4 to 2D widget coordinates.

    Returns (wx, wy, front) where front = dot(p, camera) — positive means
    the point is on the camera-facing hemisphere.
    """
    # orientation rows are numpy arrays; float() ensures plain Python arithmetic
    cam  = orientation[0]
    rgt  = orientation[1]
    up   = orientation[2]

    front = _dot4(p, cam)           # depth sign
    right = _dot4(p, rgt)           # widget X
    upv   = _dot4(p, up)            # widget Y

    wx = cx + right * scale
    wy = cy - upv   * scale
    return wx, wy, front


# ---------------------------------------------------------------------------
# Ring drawing
# ---------------------------------------------------------------------------

def _draw_ring(surf, pts, orientation, cx, cy, scale, color_bright, color_dim):
    """Draw a great-circle ring given its 64 sample points."""
    projected = [_project(p, orientation, cx, cy, scale) for p in pts]

    # Draw segments: each segment connects projected[i] to projected[(i+1) % N]
    # Segment depth sign = average of the two endpoint fronts
    dash_counter = 0
    for i in range(_N):
        wx0, wy0, f0 = projected[i]
        wx1, wy1, f1 = projected[(i + 1) % _N]
        avg_front = (f0 + f1) * 0.5

        if avg_front >= 0:
            pygame.draw.line(surf, color_bright,
                             (int(wx0), int(wy0)), (int(wx1), int(wy1)), 2)
        else:
            # Dashed: draw every other segment
            if dash_counter % 2 == 0:
                pygame.draw.line(surf, color_dim,
                                 (int(wx0), int(wy0)), (int(wx1), int(wy1)), 1)
            dash_counter += 1


def _draw_pole(surf, pole_vec, orientation, cx, cy, scale, color, label, font):
    """Draw a small circle and label at the projected position of a pole vector."""
    wx, wy, front = _project(pole_vec, orientation, cx, cy, scale)
    # Dim the dot when behind the camera
    dot_color = color if front >= 0 else tuple(max(0, c // 3) for c in color)
    pygame.draw.circle(surf, dot_color, (int(wx), int(wy)), 3)

    label_surf = font.render(label, True, dot_color)
    # Offset label slightly away from center
    dx = wx - cx
    dy = wy - cy
    dist = math.sqrt(dx*dx + dy*dy) or 1.0
    offset = 9
    lx = int(wx + (dx / dist) * offset)
    ly = int(wy + (dy / dist) * offset)
    surf.blit(label_surf, label_surf.get_rect(center=(lx, ly)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_compass(screen, orientation, x, y, size=120):
    """Draw the two-ring compass widget onto screen at (x, y).

    Parameters
    ----------
    screen : pygame.Surface
    orientation : np.ndarray, shape (4, 4)
        Row 0 = camera direction (unit vector in R^4).
        Rows 1-3 = tangent basis.
    x, y : int  Top-left position on screen.
    size : int  Widget width and height in pixels (default 120).
    """
    cx = size // 2
    cy = size // 2
    scale = size * 0.38

    # Pre-sample rings once (could be cached but 64*2 is trivial)
    ns_pts = _sample_ring(_NS_A, _NS_B)
    w_pts  = _sample_ring(_W_A,  _W_B)

    # Font
    font_size = max(9, size // 13)
    if font_size not in _font_cache:
        _font_cache[font_size] = pygame.font.Font(None, font_size)
    font = _font_cache[font_size]

    # -----------------------------------------------------------------------
    # Build widget surface
    # -----------------------------------------------------------------------
    widget_surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Background
    pygame.draw.rect(widget_surf, (30, 30, 50, 180), (0, 0, size, size), border_radius=6)
    # Border
    pygame.draw.rect(widget_surf, (100, 100, 130, 100), (0, 0, size, size), 1, border_radius=6)

    # Faint horizon reference circle
    pygame.draw.circle(widget_surf, (60, 65, 90), (cx, cy), int(scale), 1)

    # -----------------------------------------------------------------------
    # Draw NS ring (blue-white)
    # -----------------------------------------------------------------------
    _draw_ring(widget_surf, ns_pts, orientation, cx, cy, scale,
               _NS_COLOR_BRIGHT, _NS_COLOR_DIM)

    # NS pole markers: b = [0,1,0,0] -> "N" and -b -> "S"
    _draw_pole(widget_surf, _NS_B, orientation, cx, cy, scale,
               _NS_COLOR_BRIGHT, "N", font)
    _draw_pole(widget_surf, (0.0, -1.0, 0.0, 0.0), orientation, cx, cy, scale,
               _NS_COLOR_BRIGHT, "S", font)

    # -----------------------------------------------------------------------
    # Draw W ring (amber)
    # -----------------------------------------------------------------------
    _draw_ring(widget_surf, w_pts, orientation, cx, cy, scale,
               _W_COLOR_BRIGHT, _W_COLOR_DIM)

    # W pole markers: b = [0,0,0,1] -> "W+" and -b -> "W-"
    _draw_pole(widget_surf, _W_B, orientation, cx, cy, scale,
               _W_COLOR_BRIGHT, "W+", font)
    _draw_pole(widget_surf, (0.0, 0.0, 0.0, -1.0), orientation, cx, cy, scale,
               _W_COLOR_BRIGHT, "W-", font)

    # -----------------------------------------------------------------------
    # Blit to screen
    # -----------------------------------------------------------------------
    screen.blit(widget_surf, (x, y))
