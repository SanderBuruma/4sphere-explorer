"""Game constants, colors, and utility functions."""

import math

# Display
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800

# Colors
BG_COLOR = (20, 20, 30)
PLANET_COLOR = (200, 200, 255)
CAMERA_COLOR = (255, 100, 100)
SELECTED_COLOR = (255, 255, 100)
TEXT_COLOR = (200, 200, 200)
LIST_BG = (40, 40, 60)
LIST_ITEM_BG = (60, 60, 90)
LIST_ITEM_HOVER = (80, 80, 120)

# Game
NUM_PLANETS = 30_000
FOV_ANGLE = 0.116  # radians, tuned for ~10 visible planets
SIZE_FOV = math.pi / 4  # 45 degrees — reference angle for planet sizing (wider than visibility FOV)
GAME_SEED = 42
ARRIVAL_THRESHOLD = 0.0005  # radians (0.5 mrad) — snap to target when this close
CAMERA_OFFSET = 0.08  # radians — camera orbital distance from player
ROTATION_SPEED = 0.02  # radians per frame for WASD/QE
TRAVEL_SPEED = 0.00008  # slerp progress per frame
POP_DURATION = 400  # milliseconds for arrival pop animation
TRIANGLE_PERIOD = 6000.0  # milliseconds for one full triangle rotation

# Radial menu
HOLD_THRESHOLD = 200  # ms before radial menu opens
MENU_RADIUS = 50  # pixel radius of radial menu
WEDGE_INNER = 15  # inner dead zone radius

# Dialogue
DIALOGUE_DURATION = 5000  # ms speech bubble display
DIALOGUE_FADE = 1000      # ms fade-out at end


def distance_to_color(dist):
    """Map angular distance to RGB color gradient, scaled to FOV_ANGLE."""
    t = min(1.0, dist / FOV_ANGLE)  # 0 = at camera, 1 = at edge of LoS
    if t <= 0.6:
        # Green to yellow: 0–60% of LoS
        f = t / 0.6
        return (int(255 * f), 255, 0)
    else:
        # Yellow to red: 60–100% of LoS
        f = (t - 0.6) / 0.4
        return (255, int(255 * (1 - f)), 0)


def format_dist(rad):
    """Format angular distance: mrad if < 1 rad, else rad."""
    if rad < 1.0:
        return f"{rad * 1000:.0f} mrad"
    return f"{rad:.2f} rad"


def compute_planet_size(angular_dist, w_dist, fov_angle=SIZE_FOV, zoom=1.0):
    """Compute planet display sizes from angular and W distances.

    Returns (radius, sprite_size, glow_radius) as floats.
    """
    # Angular proximity: 1.0 at camera, 0.0 at FOV edge
    t = max(0.0, 1.0 - (angular_dist / fov_angle))

    # W-depth factor: 1.0 at same W, 0.4 at max W offset within FOV
    w_norm = min(1.0, w_dist / math.sin(fov_angle))
    w_factor = 1.0 - 0.6 * w_norm

    size_factor = t * w_factor

    radius = max(1.5, (1.5 + size_factor * 6.5) * zoom)
    sprite_size = max(4.0, 2.0 * radius)
    glow_radius = max(3.0, radius * 1.6 + size_factor * 5.0)

    return radius, sprite_size, glow_radius
