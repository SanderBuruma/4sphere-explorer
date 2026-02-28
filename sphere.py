import numpy as np
import colorsys


SYLLABLES_CORE = [
    "no", "qua", "ste", "nex", "void", "flux", "chro", "apex", "aeon", "cy",
    "vor", "para", "zen", "pris", "neb", "sing", "infi", "casc", "rad", "dy",
    "eth", "lum", "obsi", "arc", "plas", "spec", "res", "cel", "harm", "vel",
    "hor", "aur", "tem", "crys", "mag", "pho", "meta", "ech", "quan", "fluc",
    "thro", "aster", "cosm", "dimen", "syn", "holo", "vir", "ultra", "cyber", "omni",
]

SYLLABLES_END = [
    "va", "tum", "ter", "sar", "dor", "nis", "lex", "trix", "tron", "plex",
    "lis", "ris", "sis", "tis", "mas", "tas", "nus", "dus", "mus", "lus",
]

SUFFIXES = [
    "Prime", "Core", "Gate", "Hub", "Echo", "Station", "Nexus", "Realm", "Tower", "Node",
    "Sphere", "Spire", "Peak", "Port", "Vault", "Loop", "Threshold", "Sanctum", "Fortress", "Haven",
    "Citadel", "Edge", "Abyss", "Bridge", "Sanctuary", "Ridge", "Field", "Zone", "Sector", "Star",
    "Dawn", "Dusk", "Light", "Wave", "Stream", "Flow", "Pulse", "Surge", "Path", "Way",
    "Drift", "Void", "Deep", "High", "Rise", "Fall", "Mark", "Call", "Veil", "Shade",
]


def generate_futuristic_name(rng=None):
    """Generate a random futuristic name: (Core+End) + Suffix, with 10% chance of just Core+Suffix."""
    if rng is None:
        rng = np.random

    if rng.random() < 0.1:
        # 10%: 2-part name (Core + Suffix)
        core = rng.choice(SYLLABLES_CORE)
        suffix = rng.choice(SUFFIXES)
        return core[0].upper() + core[1:] + " " + suffix
    else:
        # 90%: 3-part name (Core + End + Suffix)
        core = rng.choice(SYLLABLES_CORE)
        end = rng.choice(SYLLABLES_END)
        suffix = rng.choice(SUFFIXES)
        word = core + end
        return word[0].upper() + word[1:] + " " + suffix


def random_point_on_s3(count=1):
    """Generate random points uniformly on S³ (unit sphere in ℝ⁴)."""
    points = np.random.randn(count, 4)
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    return points if count > 1 else points[0]


def random_color(count=1):
    """Generate random RGB colors with consistent brightness (varying hue only)."""
    colors = []
    for _ in range(count):
        hue = np.random.random()  # 0-1 for full hue range
        saturation = 0.7  # Good saturation for vibrant colors
        brightness = 0.85  # Consistent brightness (0.85 ≈ 217/255)
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, brightness)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors if count > 1 else colors[0]


def angular_distance(p1, p2):
    """Angular distance between two points on S³ (in radians)."""
    # Clamp dot product to [-1, 1] to avoid numerical issues
    dot = np.clip(np.dot(p1, p2), -1.0, 1.0)
    return np.arccos(dot)


def slerp(p1, p2, t):
    """Spherical linear interpolation between two S³ points (0 ≤ t ≤ 1)."""
    angle = angular_distance(p1, p2)
    if angle < 1e-6:  # points are very close
        return p1 + t * (p2 - p1)
    sin_angle = np.sin(angle)
    return (np.sin((1 - t) * angle) / sin_angle) * p1 + (np.sin(t * angle) / sin_angle) * p2


def visible_points(camera_pos, points, fov_angle=np.pi / 2):
    """Filter points visible from camera position within FOV angle."""
    # Dot product with camera position gives cos(angle)
    dots = np.dot(points, camera_pos)
    cos_fov = np.cos(fov_angle)
    visible = dots > cos_fov
    return points[visible], np.where(visible)[0]


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
    """Project a point on S³ into camera's tangent space.

    Returns (x, y, z) where distance from origin = angular distance,
    and direction = direction on the sphere toward the point.
    """
    dot = np.clip(np.dot(cam, point), -1.0, 1.0)
    angle = np.arccos(dot)
    if angle < 1e-6:
        return np.zeros(3)

    # Direction in ℝ⁴ tangent to sphere, pointing toward point
    direction = point - dot * cam
    direction_norm = np.linalg.norm(direction)
    if direction_norm < 1e-6:
        return np.zeros(3)
    direction /= direction_norm

    # Project direction onto the 3 basis vectors
    coords = np.array([np.dot(direction, b) for b in basis])
    return coords * angle


def project_tangent_to_screen(tangent_xyz, screen_width, screen_height, scale=250):
    """Project tangent space (x, y, z) to 2D screen coordinates."""
    cx, cy = screen_width / 2, screen_height / 2
    x = cx + tangent_xyz[0] * scale
    y = cy + tangent_xyz[1] * scale
    depth = tangent_xyz[2]
    return np.array([x, y]), depth
