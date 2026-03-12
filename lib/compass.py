"""
Compass widget for 4D orientation HUD.

Calculates heading (XZ plane), tilt (Y axis), and W-depth alignment
from a fixed standard basis frame, then renders a three-indicator
widget onto a pygame surface.

Public API:
    render_compass(screen, orientation, x, y, size=120)
    calculate_heading(camera_pos) -> float in [-pi, pi]
    calculate_tilt(camera_pos) -> float in [0, pi/2]
    calculate_w_alignment(camera_pos) -> float in [-1, 1]
"""

import math
import pygame
import numpy as np

# ---------------------------------------------------------------------------
# Fixed standard basis axes — never modified
# ---------------------------------------------------------------------------
_AXIS_X = np.array([1.0, 0.0, 0.0, 0.0])
_AXIS_Y = np.array([0.0, 1.0, 0.0, 0.0])
_AXIS_Z = np.array([0.0, 0.0, 1.0, 0.0])
_AXIS_W = np.array([0.0, 0.0, 0.0, 1.0])

# ---------------------------------------------------------------------------
# Lerp animation state (module-level)
# ---------------------------------------------------------------------------
_needle_angle = 0.0
_target_angle = 0.0
_lerp_progress = 1.0      # start at completion so first frame snaps cleanly
_LERP_DURATION_MS = 200.0

# Timing state for dt calculation
_last_render_ms = None    # None = not yet called


# ---------------------------------------------------------------------------
# Calculation functions
# ---------------------------------------------------------------------------

def calculate_heading(camera_pos):
    """Return heading angle in [-pi, pi] from fixed X and Z axes.

    Camera pointing along +X -> 0.
    Camera pointing along +Z -> -pi/2.
    """
    x_comp = float(np.dot(camera_pos, _AXIS_X))
    z_comp = float(np.dot(camera_pos, _AXIS_Z))
    return math.atan2(-z_comp, x_comp)


def calculate_tilt(camera_pos):
    """Return tilt relative to Y axis in [0, pi/2].

    0 = camera aligned with Y axis.
    pi/2 = camera perpendicular to Y axis.
    """
    y_comp = float(np.dot(camera_pos, _AXIS_Y))
    y_comp = float(np.clip(y_comp, -1.0, 1.0))
    return float(np.arccos(abs(y_comp)))


def calculate_w_alignment(camera_pos):
    """Return W-axis depth alignment in [-1, 1].

    +1 = camera pointing along +W.
    -1 = camera pointing along -W.
    """
    w_comp = float(np.dot(camera_pos, _AXIS_W))
    return float(np.clip(w_comp, -1.0, 1.0))


# ---------------------------------------------------------------------------
# Needle Lerp animation
# ---------------------------------------------------------------------------

def _update_needle(target_heading, dt_ms):
    """Update module-level Lerp state for smooth needle animation."""
    global _needle_angle, _target_angle, _lerp_progress

    if abs(target_heading - _target_angle) > 0.001:
        _target_angle = target_heading
        _lerp_progress = 0.0

    if _lerp_progress < 1.0:
        _lerp_progress = min(1.0, _lerp_progress + dt_ms / _LERP_DURATION_MS)

        # Shortest-path wraparound
        delta = _target_angle - _needle_angle
        if delta > math.pi:
            delta -= 2 * math.pi
        elif delta < -math.pi:
            delta += 2 * math.pi

        _needle_angle += delta * _lerp_progress

        if _lerp_progress >= 1.0:
            _needle_angle = _target_angle


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_compass(screen, orientation, x, y, size=120):
    """Draw the compass widget onto screen at (x, y).

    Parameters
    ----------
    screen : pygame.Surface
    orientation : np.ndarray, shape (4, 4)
        Row 0 = camera direction (unit vector in R^4).
        Rows 1-3 = tangent basis.
    x, y : int  Top-left position on screen.
    size : int  Widget width and height in pixels (default 120).
    """
    global _last_render_ms

    # Delta time
    now_ms = pygame.time.get_ticks()
    if _last_render_ms is None:
        _last_render_ms = now_ms
        dt_ms = 16.0
    else:
        dt_ms = float(np.clip(now_ms - _last_render_ms, 1, 100))
        _last_render_ms = now_ms

    # Extract camera direction from orientation frame
    camera = orientation[0]

    heading = calculate_heading(camera)
    tilt = calculate_tilt(camera)
    w_align = calculate_w_alignment(camera)

    _update_needle(heading, dt_ms)

    # -----------------------------------------------------------------------
    # Build widget surface
    # -----------------------------------------------------------------------
    widget_surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Background
    pygame.draw.rect(widget_surf, (30, 30, 50, 180), (0, 0, size, size), border_radius=6)
    # Border
    pygame.draw.rect(widget_surf, (100, 100, 130, 100), (0, 0, size, size), 1, border_radius=6)

    # -----------------------------------------------------------------------
    # Compass rose (left-centre area)
    # -----------------------------------------------------------------------
    cx = int(size * 0.42)
    cy = int(size * 0.50)
    rose_radius = int(size * 0.30)

    # Rose circle outline
    pygame.draw.circle(widget_surf, (60, 65, 90), (cx, cy), rose_radius, 1)

    # Cardinal tick marks
    tick_outer = rose_radius
    tick_inner = rose_radius - max(3, size // 25)
    for angle_deg in (0, 90, 180, 270):
        a = math.radians(angle_deg)
        cos_a = math.cos(a)
        sin_a = math.sin(a)
        px_outer = cx + int(tick_outer * cos_a)
        py_outer = cy - int(tick_outer * sin_a)
        px_inner = cx + int(tick_inner * cos_a)
        py_inner = cy - int(tick_inner * sin_a)
        pygame.draw.line(widget_surf, (90, 95, 120), (px_inner, py_inner), (px_outer, py_outer), 1)

    # Cardinal labels: X+ at 0, Z+ at 90 (pi/2), X- at 180 (pi), Z- at 270 (3*pi/2)
    label_font = pygame.font.Font(None, max(10, size // 12))
    label_offset = rose_radius + max(6, size // 16)
    labels = [
        (0,           "X+"),
        (math.pi / 2, "Z+"),
        (math.pi,     "X-"),
        (3 * math.pi / 2, "Z-"),
    ]
    for angle, text in labels:
        lx = cx + int(label_offset * math.cos(angle))
        ly = cy - int(label_offset * math.sin(angle))
        surf = label_font.render(text, True, (160, 165, 190))
        rect = surf.get_rect(center=(lx, ly))
        widget_surf.blit(surf, rect)

    # -----------------------------------------------------------------------
    # Needle
    # -----------------------------------------------------------------------
    needle_len = rose_radius * 0.85
    nx = cx + int(needle_len * math.cos(_needle_angle))
    ny = cy - int(needle_len * math.sin(_needle_angle))

    # Back stub (opposite direction, 1/4 length)
    stub_len = needle_len / 4
    sx = cx - int(stub_len * math.cos(_needle_angle))
    sy = cy + int(stub_len * math.sin(_needle_angle))
    pygame.draw.line(widget_surf, (120, 60, 40), (cx, cy), (sx, sy), 1)

    # Main needle
    pygame.draw.line(widget_surf, (255, 110, 80), (cx, cy), (nx, ny), 2)
    # Tip dot
    pygame.draw.circle(widget_surf, (255, 110, 80), (nx, ny), 3)

    # -----------------------------------------------------------------------
    # Tilt bar (right side)
    # -----------------------------------------------------------------------
    bar_cx = int(size * 0.83)
    bar_top = int(size * 0.20)
    bar_bottom = int(size * 0.80)
    bar_h = bar_bottom - bar_top
    bar_w = max(6, size // 18)
    bar_left = bar_cx - bar_w // 2

    # Track outline
    pygame.draw.rect(widget_surf, (60, 65, 90), (bar_left, bar_top, bar_w, bar_h), 1)

    # Indicator position: tilt=0 (aligned with Y) = center, tilt=pi/2 = bottom
    indicator_y = bar_top + int((tilt / (math.pi / 2)) * bar_h)
    indicator_y = int(np.clip(indicator_y, bar_top, bar_bottom))
    pygame.draw.circle(widget_surf, (150, 160, 255), (bar_cx, indicator_y), 4)

    # "Y" label above bar
    y_label_font = pygame.font.Font(None, max(9, size // 14))
    y_surf = y_label_font.render("Y", True, (150, 160, 255))
    y_rect = y_surf.get_rect(center=(bar_cx, bar_top - max(6, size // 16)))
    widget_surf.blit(y_surf, y_rect)

    # -----------------------------------------------------------------------
    # W gauge (top-left corner)
    # -----------------------------------------------------------------------
    w_cx = int(size * 0.17)
    w_cy = int(size * 0.20)
    w_radius = max(7, size // 15)

    # Interpolate color: -1 = blue (80,80,220), 0 = neutral (140,140,140), +1 = red (220,80,80)
    t = (w_align + 1.0) / 2.0   # map [-1,1] -> [0,1]
    if t <= 0.5:
        # blue to neutral
        f = t / 0.5
        w_color = (
            int(80 + f * (140 - 80)),
            int(80 + f * (140 - 80)),
            int(220 + f * (140 - 220)),
        )
    else:
        # neutral to red
        f = (t - 0.5) / 0.5
        w_color = (
            int(140 + f * (220 - 140)),
            int(140 + f * (80 - 140)),
            int(140 + f * (80 - 140)),
        )

    pygame.draw.circle(widget_surf, w_color, (w_cx, w_cy), w_radius)
    pygame.draw.circle(widget_surf, (100, 100, 130), (w_cx, w_cy), w_radius, 1)

    # "W" label below gauge
    w_label_font = pygame.font.Font(None, max(9, size // 14))
    w_surf = w_label_font.render("W", True, (160, 165, 190))
    w_rect = w_surf.get_rect(center=(w_cx, w_cy + w_radius + max(5, size // 18)))
    widget_surf.blit(w_surf, w_rect)

    # -----------------------------------------------------------------------
    # Blit to screen
    # -----------------------------------------------------------------------
    screen.blit(widget_surf, (x, y))
