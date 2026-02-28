import numpy as np
import colorsys


SYLLABLES_CORE = [
    "no", "qua", "ste", "nex", "void", "flux", "chro", "apex", "aeon", "cy",
    "vor", "para", "zen", "pris", "neb", "sing", "infi", "casc", "rad", "dy",
    "eth", "lum", "obsi", "arc", "plas", "spec", "res", "cel", "harm", "vel",
    "hor", "aur", "tem", "crys", "mag", "pho", "meta", "ech", "quan", "fluc",
    "thro", "aster", "cosm", "dimen", "syn", "holo", "vir", "ultra", "cyber", "omni",
    "zeph", "lux", "astr", "vex", "sol", "iris", "mer", "pax", "volt", "rift",
    "ion", "zap", "nova", "frac", "stra",
]

SYLLABLES_END = [
    "va", "tum", "ter", "sar", "dor", "nis", "lex", "trix", "tron", "plex",
    "lis", "ris", "sis", "tis", "mas", "tas", "nus", "dus", "mus", "lus",
    "kir", "zex", "vor", "keth", "nix", "ath", "orm", "yx", "eth", "ism",
    "ada", "ora", "ina", "ura", "ess",
]

SUFFIXES = [
    "Prime", "Core", "Gate", "Hub", "Echo", "Station", "Nexus", "Realm", "Tower", "Node",
    "Sphere", "Spire", "Peak", "Port", "Vault", "Loop", "Threshold", "Sanctum", "Fortress", "Haven",
    "Citadel", "Edge", "Abyss", "Bridge", "Sanctuary", "Ridge", "Field", "Zone", "Sector", "Star",
    "Dawn", "Dusk", "Light", "Wave", "Stream", "Flow", "Pulse", "Surge", "Path", "Way",
    "Drift", "Void", "Deep", "High", "Rise", "Fall", "Mark", "Call", "Veil", "Shade",
]

# Name space: 4 regions (numbers always after suffix, never replacing)
# 1. core+end Suffix NN  (65*35*50*100 = 11,375,000)
# 2. core+end Suffix      (65*35*50    =    113,750)
# 3. core Suffix NN       (65*50*100   =    325,000)
# 4. core Suffix           (65*50      =      3,250)
_N_CORE = len(SYLLABLES_CORE)
_N_END = len(SYLLABLES_END)
_N_SUF = len(SUFFIXES)
THREE_NUM = _N_CORE * _N_END * _N_SUF * 100
THREE_PLAIN = _N_CORE * _N_END * _N_SUF
TWO_NUM = _N_CORE * _N_SUF * 100
TWO_PLAIN = _N_CORE * _N_SUF
TOTAL_NAMES = THREE_NUM + THREE_PLAIN + TWO_NUM + TWO_PLAIN


def decode_name(key):
    """Decode an integer 0..TOTAL_NAMES-1 into a deterministic futuristic name."""
    if key < THREE_NUM:
        num = key % 100
        key //= 100
        suf = key % _N_SUF
        key //= _N_SUF
        end = key % _N_END
        core = key // _N_END
        word = SYLLABLES_CORE[core] + SYLLABLES_END[end]
        return f"{word[0].upper()}{word[1:]} {SUFFIXES[suf]} {num:02d}"
    key -= THREE_NUM
    if key < THREE_PLAIN:
        suf = key % _N_SUF
        key //= _N_SUF
        end = key % _N_END
        core = key // _N_END
        word = SYLLABLES_CORE[core] + SYLLABLES_END[end]
        return f"{word[0].upper()}{word[1:]} {SUFFIXES[suf]}"
    key -= THREE_PLAIN
    if key < TWO_NUM:
        num = key % 100
        key //= 100
        suf = key % _N_SUF
        core = key // _N_SUF
        c = SYLLABLES_CORE[core]
        return f"{c[0].upper()}{c[1:]} {SUFFIXES[suf]} {num:02d}"
    key -= TWO_NUM
    suf = key % _N_SUF
    core = key // _N_SUF
    c = SYLLABLES_CORE[core]
    return f"{c[0].upper()}{c[1:]} {SUFFIXES[suf]}"


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


def rotate_frame(frame, axis_idx, angle):
    """Rotate orientation frame in plane (row 0, row axis_idx) by angle.

    frame: 4x4 array, row 0 = camera pos, rows 1-3 = tangent basis.
    Modifies frame in-place.
    """
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    cam = frame[0].copy()
    axis = frame[axis_idx].copy()
    frame[0] = cos_a * cam + sin_a * axis
    frame[axis_idx] = -sin_a * cam + cos_a * axis


def reorthogonalize_frame(frame):
    """Re-orthogonalize frame to correct numerical drift.

    Uses modified Gram-Schmidt starting from current vectors to
    preserve orientation as much as possible.
    """
    frame[0] /= np.linalg.norm(frame[0])
    for i in range(1, 4):
        v = frame[i].copy()
        v -= np.dot(v, frame[0]) * frame[0]
        for j in range(1, i):
            v -= np.dot(v, frame[j]) * frame[j]
        frame[i] = v / np.linalg.norm(v)


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


def project_tangent_to_screen(tangent_xyz, screen_width, screen_height, scale=2500):
    """Project tangent space (x, y, z) to 2D screen coordinates."""
    cx, cy = screen_width / 2, screen_height / 2
    x = cx + tangent_xyz[0] * scale
    y = cy + tangent_xyz[1] * scale
    depth = tangent_xyz[2]
    return np.array([x, y]), depth
