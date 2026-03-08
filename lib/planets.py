"""Procedural rotating planets — equirectangular UV-mapped spheres.

Generates a rectangular texture per planet (like unrolling a globe).
Each frame, shift the longitude to rotate — pure numpy indexing, no noise at runtime.
"""

import numpy as np
import pygame
from scipy.ndimage import map_coordinates

try:
    from noise import snoise3
except ImportError:
    import math as _math

    _PERM = None

    def _init_perm():
        global _PERM
        p = list(range(256))
        import random
        r = random.Random(0)
        r.shuffle(p)
        _PERM = np.array(p + p, dtype=np.int32)

    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(a, b, t):
        return a + t * (b - a)

    def _grad3(h, x, y, z):
        g = h & 15
        u = np.where(g < 8, x, y)
        v = np.where(g < 4, y, np.where((g == 12) | (g == 14), x, z))
        return np.where(g & 1, -u, u) + np.where(g & 2, -v, v)

    def snoise3(x, y, z, octaves=1, persistence=0.5, lacunarity=2.0):
        if _PERM is None:
            _init_perm()
        val = 0.0
        amp = 1.0
        freq = 1.0
        for _ in range(octaves):
            xi, yi, zi = x * freq, y * freq, z * freq
            X = int(_math.floor(xi)) & 255
            Y = int(_math.floor(yi)) & 255
            Z = int(_math.floor(zi)) & 255
            xf = xi - _math.floor(xi)
            yf = yi - _math.floor(yi)
            zf = zi - _math.floor(zi)
            u, v, w = _fade(xf), _fade(yf), _fade(zf)
            p = _PERM
            A = p[X] + Y; AA = p[A] + Z; AB = p[A + 1] + Z
            B = p[X + 1] + Y; BA = p[B] + Z; BB = p[B + 1] + Z
            val += amp * _lerp(
                _lerp(_lerp(_grad3(p[AA], xf, yf, zf), _grad3(p[BA], xf - 1, yf, zf), u),
                      _lerp(_grad3(p[AB], xf, yf - 1, zf), _grad3(p[BB], xf - 1, yf - 1, zf), u), v),
                _lerp(_lerp(_grad3(p[AA + 1], xf, yf, zf - 1), _grad3(p[BA + 1], xf - 1, yf, zf - 1), u),
                      _lerp(_grad3(p[AB + 1], xf, yf - 1, zf - 1), _grad3(p[BB + 1], xf - 1, yf - 1, zf - 1), u), v), w)
            amp *= persistence
            freq *= lacunarity
        return val


# --- Color gradients ---
GRADIENTS = [
    # 0: Sunset — magma sea → obsidian shore → amber desert → golden dunes → pale sky
    [(0.0, (40, 10, 60)), (0.25, (120, 30, 50)), (0.4, (210, 100, 30)),
     (0.42, (180, 130, 60)), (0.65, (230, 170, 70)), (0.85, (250, 210, 130)),
     (1.0, (255, 240, 200))],
    # 1: Deep Sea — trench → reef → shallow → sand island
    [(0.0, (5, 5, 15)), (0.3, (10, 40, 90)), (0.5, (10, 130, 120)),
     (0.7, (40, 180, 160)), (0.72, (180, 170, 120)), (1.0, (220, 245, 250))],
    # 2: Aurora — dark polar sea → ice edge → tundra → aurora green → bright shimmer
    [(0.0, (10, 5, 30)), (0.3, (15, 30, 60)), (0.38, (20, 80, 70)),
     (0.40, (30, 120, 50)), (0.55, (20, 180, 80)), (0.75, (60, 220, 160)),
     (1.0, (100, 240, 230))],
    # 3: Ember — dark crust → lava river → hot rock → cooling basalt → ash
    [(0.0, (10, 5, 5)), (0.3, (40, 8, 5)), (0.32, (220, 60, 10)),
     (0.38, (170, 30, 15)), (0.4, (60, 15, 8)), (0.7, (140, 50, 20)),
     (1.0, (255, 210, 60))],
    # 4: Arctic — frozen ocean → ice shelf → tundra → snow
    [(0.0, (10, 15, 45)), (0.35, (30, 70, 130)), (0.44, (50, 110, 160)),
     (0.46, (160, 180, 170)), (0.6, (120, 140, 130)), (0.8, (200, 210, 210)),
     (1.0, (240, 248, 255))],
    # 5: Terran — deep ocean → shallow water | land → forest → highland → snow
    [(0.0, (10, 20, 80)), (0.35, (20, 60, 150)), (0.43, (50, 110, 180)),
     (0.45, (35, 110, 40)), (0.6, (50, 130, 35)), (0.8, (120, 100, 60)),
     (1.0, (210, 200, 190))],
    # 6: Nebula — void → dark nebula → emission pink → bright core → stellar white
    [(0.0, (8, 2, 20)), (0.2, (30, 10, 60)), (0.4, (100, 20, 90)),
     (0.55, (160, 30, 120)), (0.7, (200, 80, 160)), (0.85, (230, 160, 200)),
     (1.0, (250, 220, 240))],
    # 7: Desert Dusk — canyon shadow → red rock → mesa → sand → salt flat → pale horizon
    [(0.0, (30, 20, 18)), (0.2, (80, 35, 25)), (0.4, (170, 80, 50)),
     (0.55, (200, 140, 80)), (0.58, (210, 180, 140)), (0.8, (225, 205, 170)),
     (1.0, (240, 230, 210))],
    # 8: Toxic — dark swamp → acid pool → neon shore → sickly plains → pale haze
    [(0.0, (8, 18, 8)), (0.25, (15, 60, 15)), (0.42, (40, 160, 20)),
     (0.44, (120, 200, 30)), (0.6, (160, 220, 60)), (0.8, (200, 240, 120)),
     (1.0, (230, 250, 180))],
    # 9: Abyssal — void → deep trench → biolum vents → dark purple → faint glow
    [(0.0, (3, 3, 8)), (0.3, (8, 10, 40)), (0.45, (20, 30, 100)),
     (0.47, (50, 60, 180)), (0.52, (30, 35, 120)), (0.75, (80, 70, 160)),
     (1.0, (180, 170, 220))],
    # 10: Rust — iron core → oxidized plains → weathered ridge → dust → pale crust
    [(0.0, (25, 18, 15)), (0.2, (60, 30, 20)), (0.4, (140, 60, 25)),
     (0.6, (180, 95, 40)), (0.62, (170, 120, 70)), (0.8, (210, 175, 120)),
     (1.0, (245, 230, 200))],
    # 11: Coral Reef — deep blue → reef wall → coral pink → shallow sand → bright surface
    [(0.0, (8, 8, 45)), (0.3, (15, 40, 100)), (0.45, (40, 80, 140)),
     (0.47, (180, 70, 60)), (0.6, (220, 100, 80)), (0.75, (230, 170, 140)),
     (1.0, (255, 220, 195))],
]

GRADIENT_NAMES = [
    "Sunset", "Deep Sea", "Aurora", "Ember", "Arctic", "Terran",
    "Nebula", "Desert Dusk", "Toxic", "Abyssal", "Rust", "Coral Reef",
]

# Gradient index → polar bias strength (0-1). Pushes noise toward 1.0 at poles.
# Only useful for gradients where high end = snow/ice.
POLAR_BIAS = {4: 0.6, 5: 0.7}

# Equirect texture dimensions
EQUIRECT_H = 128
EQUIRECT_W = 256

# Rotation period (ms for full 360°)
ROTATION_PERIOD_MS = 60_000

# Cache budget per frame
MAX_TEXTURES_PER_FRAME = 2

# Module-level caches
_equirect_cache = {}   # point_idx -> (EQUIRECT_H, EQUIRECT_W, 3) uint8
_uv_cache = {}         # render_size -> (inside, lat_idx, lon_idx, shade)
_frame_budget = 0


def _gradient_color(t, stops):
    """Smoothly interpolate color at position t in [0, 1] across gradient stops."""
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if t <= p1:
            frac = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            frac = frac * frac * (3.0 - 2.0 * frac)  # smoothstep
            return (
                c0[0] + (c1[0] - c0[0]) * frac,
                c0[1] + (c1[1] - c0[1]) * frac,
                c0[2] + (c1[2] - c0[2]) * frac,
            )
    return stops[-1][1]


def _build_gradient_lut(gradient):
    """Build a 256-entry color lookup table from gradient stops."""
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        r, g, b = _gradient_color(i / 255.0, gradient)
        lut[i] = (int(r), int(g), int(b))
    return lut


def generate_equirect_texture(seed):
    """Generate an equirectangular texture for a planet.

    Args:
        seed: Integer controlling noise offset and gradient selection.

    Returns:
        (EQUIRECT_H, EQUIRECT_W, 3) uint8 ndarray.
    """
    rng = np.random.RandomState(seed & 0xFFFFFFFF)
    ox, oy, oz = rng.uniform(-1000, 1000, 3)
    gradient = GRADIENTS[seed % len(GRADIENTS)]
    base_scale = 0.8 + rng.uniform(-0.1, 0.3)

    lat = np.linspace(-np.pi / 2, np.pi / 2, EQUIRECT_H)
    lon = np.linspace(0, 2 * np.pi, EQUIRECT_W, endpoint=False)
    LON, LAT = np.meshgrid(lon, lat)

    cos_lat = np.cos(LAT)
    sx = cos_lat * np.cos(LON)
    sy = cos_lat * np.sin(LON)
    sz = np.sin(LAT)

    noise_map = np.zeros((EQUIRECT_H, EQUIRECT_W))
    for y in range(EQUIRECT_H):
        for x in range(EQUIRECT_W):
            noise_map[y, x] = snoise3(
                sx[y, x] * base_scale + ox,
                sy[y, x] * base_scale + oy,
                sz[y, x] * base_scale + oz,
                octaves=5, persistence=0.45, lacunarity=2.0,
            )

    lo, hi = noise_map.min(), noise_map.max()
    if hi - lo > 1e-9:
        noise_map = (noise_map - lo) / (hi - lo)
    else:
        noise_map[:] = 0.5

    grad_idx = seed % len(GRADIENTS)
    polar_strength = POLAR_BIAS.get(grad_idx, 0.0)
    if polar_strength > 0:
        # abs(sin(lat))^2 gives smooth polar caps; blend toward 1.0 (snow end)
        polar = np.sin(LAT) ** 2
        noise_map = noise_map * (1 - polar * polar_strength) + polar * polar_strength

    lut = _build_gradient_lut(gradient)
    indices = np.clip((noise_map * 255).astype(int), 0, 255)
    return lut[indices]


def _precompute_uv(render_size):
    """Precompute UV mapping arrays for hemisphere rendering at a given size."""
    half = render_size / 2.0
    radius = half - 0.5

    ys, xs = np.mgrid[0:render_size, 0:render_size]
    nx = (xs - half + 0.5) / radius
    ny = (ys - half + 0.5) / radius
    dist_sq = nx * nx + ny * ny
    inside = dist_sq <= 1.0

    nz = np.sqrt(np.clip(1.0 - dist_sq, 0, None))
    # lat: arcsin(-ny) because screen Y points down
    lat = np.arcsin(np.clip(-ny, -1, 1))
    lon = np.arctan2(nx, nz)  # [-pi, pi]

    # Map to equirect pixel coords (float for interpolation)
    lat_idx = (lat + np.pi / 2) / np.pi * (EQUIRECT_H - 1)
    lon_idx = (lon + np.pi) / (2 * np.pi) * EQUIRECT_W

    # Shading: edge darkening + top-left highlight
    dist = np.sqrt(np.clip(dist_sq, 0, 1))
    shade = np.ones((render_size, render_size))
    shade[inside] = 1.0 - 0.6 * dist[inside] ** 1.8

    hx = nx + 0.4
    hy = ny + 0.4
    hdist = np.sqrt(hx ** 2 + hy ** 2)
    highlight = np.clip(1.0 - hdist * 0.6, 0, 1) * 0.25
    shade[inside] += highlight[inside]
    shade = np.clip(shade, 0.15, 1.2)

    return inside, lat_idx, lon_idx, shade


def render_planet_frame(equirect, render_size, rotation_angle, tint_color=None):
    """Render a hemisphere from an equirectangular texture.

    Args:
        equirect: (EQUIRECT_H, EQUIRECT_W, 3) uint8 texture.
        render_size: Output square pixel size.
        rotation_angle: Rotation in radians (0 to 2*pi).
        tint_color: Optional (r, g, b) tuple to multiply onto the result.

    Returns:
        pygame.Surface with SRCALPHA.
    """
    if render_size not in _uv_cache:
        _uv_cache[render_size] = _precompute_uv(render_size)
    inside, lat_idx, lon_idx, shade = _uv_cache[render_size]

    rotation_offset = (rotation_angle / (2 * np.pi)) * EQUIRECT_W
    shifted_lon = (lon_idx + rotation_offset) % EQUIRECT_W

    iy, ix = np.where(inside)
    lat_vals = lat_idx[iy, ix]
    lon_vals = shifted_lon[iy, ix]

    pixels = np.zeros((render_size, render_size, 3), dtype=np.uint8)

    if render_size >= 48:
        # Bilinear interpolation for large sizes
        for c in range(3):
            sampled = map_coordinates(
                equirect[:, :, c].astype(np.float64),
                [lat_vals, lon_vals], order=1, mode='wrap',
            )
            pixels[iy, ix, c] = np.clip(sampled, 0, 255).astype(np.uint8)
    else:
        # Nearest-neighbor for small sizes (faster)
        lat_int = np.clip(lat_vals.astype(int), 0, EQUIRECT_H - 1)
        lon_int = lon_vals.astype(int) % EQUIRECT_W
        pixels[iy, ix] = equirect[lat_int, lon_int]

    # Apply shading
    for c in range(3):
        pixels[:, :, c] = np.clip(
            pixels[:, :, c].astype(np.float64) * shade, 0, 255
        ).astype(np.uint8)

    # Build SRCALPHA surface — pixelcopy expects (W, H, 3), our array is (H, W, 3)
    surf = pygame.Surface((render_size, render_size), pygame.SRCALPHA)
    pygame.pixelcopy.array_to_surface(surf, pixels.transpose(1, 0, 2))
    alpha_arr = pygame.surfarray.pixels_alpha(surf)
    alpha = np.zeros((render_size, render_size), dtype=np.uint8)
    alpha[inside] = 255
    alpha_arr[:] = alpha.T
    del alpha_arr

    if tint_color is not None:
        color_surf = pygame.Surface((render_size, render_size))
        color_surf.fill(tint_color)
        surf.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)

    return surf


def get_planet_rotation_angle(point_idx, elapsed_ms):
    """Get current rotation angle for a planet.

    20s full rotation period with per-planet phase offset.
    """
    phase = ((point_idx * 137) % 360) * np.pi / 180.0
    return phase + (elapsed_ms % ROTATION_PERIOD_MS) / ROTATION_PERIOD_MS * 2 * np.pi


def get_planet_equirect(point_idx, name_key):
    """Get equirect texture for a point, generating if budget allows.

    Args:
        point_idx: Index into the points array (cache key).
        name_key: Name key used as seed for texture generation.

    Returns:
        (EQUIRECT_H, EQUIRECT_W, 3) uint8 ndarray, or None if over budget.
    """
    global _frame_budget
    if point_idx in _equirect_cache:
        return _equirect_cache[point_idx]
    if _frame_budget <= 0:
        return None
    _frame_budget -= 1
    tex = generate_equirect_texture(int(name_key))
    _equirect_cache[point_idx] = tex
    return tex


def reset_frame_budget():
    """Reset per-frame texture generation budget. Call once per frame."""
    global _frame_budget
    _frame_budget = MAX_TEXTURES_PER_FRAME


def evict_planet_cache(indices):
    """Remove cached textures for points that left the view."""
    for idx in indices:
        _equirect_cache.pop(idx, None)
