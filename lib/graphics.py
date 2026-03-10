"""Procedural creature generation — low-poly faceted sprites with accent markings."""

import math
import numpy as np
import pygame
from scipy.spatial import Delaunay
from scipy.ndimage import distance_transform_edt, binary_dilation

# --- Eye wander/tracking constants ---
_DECAY_RATE = 4.0          # /s — delta accumulator decay
_ATTENTION_LOW = 2.0       # px — below = full wander
_ATTENTION_HIGH = 30.0     # px — above = full tracking
_ATTENTION_SMOOTH = 3.0    # /s — transition smoothing rate
_WANDER_BASE_SPEED = 0.8   # rad/s — ~8s per full orbit
_WANDER_REACH = 0.7        # fraction of max_offset for wander

# Module-level eye tracking state (shared across all creatures)
_eye_state = {
    "prev_mouse": (0, 0),
    "delta_accum": 0.0,
    "attention": 0.0,
    "wander_phase": 0.0,
    "wander_speed": _WANDER_BASE_SPEED,
    "_speed_timer": 0.0,       # seconds until next speed reseed
    "last_update_ms": 0,
    "_rng": np.random.RandomState(7),
}


def _wander_offset(phase):
    """Compute a wandering (wx, wy) offset in [-1, 1] from the current phase.

    Uses multiple incommensurate harmonics for an organic, non-repeating path.
    Both eyes share the same offset so they stay synced.
    """
    wx = (math.sin(phase)
          + 0.5 * math.sin(phase * 1.618 + 1.0)
          + 0.3 * math.sin(phase * 2.879 + 3.7))
    wy = (math.cos(phase * 1.2 + 0.5)
          + 0.5 * math.cos(phase * 2.1 + 2.3)
          + 0.3 * math.cos(phase * 3.37 + 5.1))
    # Normalize to roughly [-1, 1] range (max theoretical ~1.8)
    wx /= 1.8
    wy /= 1.8
    return wx, wy


def update_eye_tracking(mouse_pos, current_ms):
    """Update shared eye wander/tracking state. Call once per frame.

    Args:
        mouse_pos: (mx, my) current mouse position in screen coords.
        current_ms: Current time in milliseconds (e.g. pygame.time.get_ticks()).
    """
    s = _eye_state
    dt = min((current_ms - s["last_update_ms"]) / 1000.0, 0.1)
    if dt <= 0:
        s["prev_mouse"] = mouse_pos
        s["last_update_ms"] = current_ms
        return

    # Mouse movement delta
    dx = mouse_pos[0] - s["prev_mouse"][0]
    dy = mouse_pos[1] - s["prev_mouse"][1]
    raw_delta = math.sqrt(dx * dx + dy * dy)

    # Decay + inject
    s["delta_accum"] = s["delta_accum"] * math.exp(-_DECAY_RATE * dt) + raw_delta

    # Raw attention from accumulator
    raw_att = max(0.0, min(1.0,
        (s["delta_accum"] - _ATTENTION_LOW) / (_ATTENTION_HIGH - _ATTENTION_LOW)))

    # Smooth attention
    s["attention"] += (raw_att - s["attention"]) * min(1.0, _ATTENTION_SMOOTH * dt)

    # Advance wander phase; periodically reseed speed for variety
    s["_speed_timer"] -= dt
    if s["_speed_timer"] <= 0:
        s["wander_speed"] = s["_rng"].uniform(0.4, 1.6)
        s["_speed_timer"] = s["_rng"].uniform(2.0, 6.0)
    s["wander_phase"] += s["wander_speed"] * dt

    s["prev_mouse"] = mouse_pos
    s["last_update_ms"] = current_ms


def _color_from_seed(rng):
    """Generate a vivid HSV color from an RNG state."""
    h = rng.uniform(0, 360)
    s = rng.uniform(0.5, 1.0)
    v = rng.uniform(0.6, 1.0)
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60: r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else: r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def _accent_color(rng, color):
    """Derive a visibly different accent color from the primary."""
    accent = (
        int(np.clip(color[1] * 0.6 + color[2] * 0.8, 0, 255)),
        int(np.clip(color[2] * 0.6 + color[0] * 0.8, 0, 255)),
        int(np.clip(color[0] * 0.6 + color[1] * 0.8, 0, 255)),
    )
    if sum(abs(a - b) for a, b in zip(accent, color)) < 80:
        accent = (
            min(255, color[0] + 80),
            max(0, color[1] - 60),
            min(255, color[2] + 40),
        )
    return accent


def _generate_body_outline(rng, size):
    """Generate a symmetric creature body outline as polygon vertices."""
    cx = size / 2.0
    n_ctrl = rng.randint(6, 12)
    ctrl_y = np.sort(rng.uniform(0.08, 0.92, n_ctrl)) * size
    ctrl_w = rng.uniform(0.06, 0.32, n_ctrl) * size
    ctrl_y = np.concatenate([[size * 0.03], ctrl_y, [size * 0.97]])
    ctrl_w = np.concatenate([[size * 0.01], ctrl_w, [size * 0.01]])
    ctrl_w += rng.uniform(-size * 0.03, size * 0.03, len(ctrl_w))
    ctrl_w = np.clip(ctrl_w, size * 0.01, size * 0.4)

    right_verts = [(cx + w, y) for y, w in zip(ctrl_y, ctrl_w)]
    left_verts = [(cx - w, y) for y, w in zip(ctrl_y[::-1], ctrl_w[::-1])]
    return right_verts + left_verts


def _generate_appendages(rng, outline_verts, size):
    """Generate angular appendage polygons (horns, fins, limbs, spikes)."""
    cx = size / 2.0
    appendages = []
    n_appendages = rng.randint(1, 5)

    for _ in range(n_appendages):
        atype = rng.choice(["horn", "fin", "limb", "spike"])
        attach_y = rng.uniform(0.1, 0.85) * size

        body_w = 0
        for vx, vy in outline_verts:
            if abs(vy - attach_y) < size * 0.08:
                body_w = max(body_w, abs(vx - cx))
        if body_w < size * 0.03:
            continue

        if atype == "horn":
            horn_h = size * rng.uniform(0.06, 0.15)
            horn_w = size * rng.uniform(0.02, 0.06)
            for side in [-1, 1]:
                base_x = cx + side * body_w * rng.uniform(0.3, 0.8)
                tip_x = base_x + side * rng.uniform(-horn_w, horn_w)
                appendages.append([
                    (base_x - horn_w * 0.5, attach_y),
                    (tip_x, attach_y - horn_h),
                    (base_x + horn_w * 0.5, attach_y),
                ])
        elif atype == "fin":
            fin_len = size * rng.uniform(0.08, 0.18)
            fin_h = size * rng.uniform(0.04, 0.1)
            for side in [-1, 1]:
                base_x = cx + side * body_w
                appendages.append([
                    (base_x, attach_y - fin_h * 0.5),
                    (base_x + side * fin_len, attach_y + rng.uniform(-fin_h, fin_h) * 0.3),
                    (base_x, attach_y + fin_h * 0.5),
                ])
        elif atype == "limb":
            limb_len1 = size * rng.uniform(0.06, 0.14)
            limb_len2 = size * rng.uniform(0.04, 0.1)
            limb_thick = size * rng.uniform(0.015, 0.035)
            angle1 = rng.uniform(0.3, 1.0)
            angle2 = rng.uniform(-0.5, 0.8)
            for side in [-1, 1]:
                base_x = cx + side * body_w
                joint_x = base_x + side * limb_len1 * np.cos(angle1)
                joint_y = attach_y + limb_len1 * np.sin(angle1)
                tip_x = joint_x + side * limb_len2 * np.cos(angle2)
                tip_y = joint_y + limb_len2 * np.sin(angle2)
                perp_x = -np.sin(angle1) * limb_thick
                perp_y = np.cos(angle1) * limb_thick
                appendages.append([
                    (base_x - perp_x, attach_y - perp_y),
                    (base_x + perp_x, attach_y + perp_y),
                    (joint_x + perp_x, joint_y + perp_y),
                    (tip_x, tip_y),
                    (joint_x - perp_x, joint_y - perp_y),
                ])
        elif atype == "spike":
            spike_len = size * rng.uniform(0.04, 0.1)
            spike_w = size * rng.uniform(0.01, 0.025)
            for side in [-1, 1]:
                base_x = cx + side * body_w
                appendages.append([
                    (base_x, attach_y - spike_w),
                    (base_x + side * spike_len, attach_y),
                    (base_x, attach_y + spike_w),
                ])

    return appendages


def _rasterize_polygon(verts, size):
    """Rasterize a polygon to a binary mask via scanline fill."""
    mask = np.zeros((size, size), dtype=bool)
    n = len(verts)
    if n < 3:
        return mask
    min_y = max(0, int(min(v[1] for v in verts)))
    max_y = min(size - 1, int(max(v[1] for v in verts)))
    for y in range(min_y, max_y + 1):
        intersections = []
        for i in range(n):
            x0, y0 = verts[i]
            x1, y1 = verts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                if abs(y1 - y0) > 0.001:
                    t = (y - y0) / (y1 - y0)
                    intersections.append(x0 + t * (x1 - x0))
        intersections.sort()
        for j in range(0, len(intersections) - 1, 2):
            x_start = max(0, int(intersections[j]))
            x_end = min(size - 1, int(intersections[j + 1]))
            mask[y, x_start:x_end + 1] = True
    return mask


def _triangulate_and_shade(body_mask, rng, color, size, _return_mesh=False):
    """Apply low-poly faceted shading via Delaunay triangulation.

    If _return_mesh is True, returns (rgba, mesh_data) where mesh_data is
    (points, simplices, tri_colors) for use in morph animation.
    """
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    _no_mesh = (rgba, (np.zeros((0, 2)), np.zeros((0, 3), dtype=int), [])) if _return_mesh else rgba
    if body_mask.sum() == 0:
        return _no_mesh

    body_ys, body_xs = np.where(body_mask)
    n_samples = min(len(body_ys), rng.randint(40, 80))
    if n_samples < 4:
        rgba[body_mask, 0] = color[0]
        rgba[body_mask, 1] = color[1]
        rgba[body_mask, 2] = color[2]
        rgba[body_mask, 3] = 255
        return _no_mesh

    indices = rng.choice(len(body_ys), n_samples, replace=False)
    points = np.column_stack([body_xs[indices], body_ys[indices]])

    edge_mask = binary_dilation(body_mask, iterations=1) & ~body_mask
    edge_ys, edge_xs = np.where(edge_mask)
    if len(edge_ys) > 10:
        edge_idx = rng.choice(len(edge_ys), min(len(edge_ys), 30), replace=False)
        points = np.vstack([points, np.column_stack([edge_xs[edge_idx], edge_ys[edge_idx]])])

    try:
        tri = Delaunay(points)
    except Exception:
        rgba[body_mask, 0] = color[0]
        rgba[body_mask, 1] = color[1]
        rgba[body_mask, 2] = color[2]
        rgba[body_mask, 3] = 255
        return _no_mesh

    light_dir = np.array([rng.uniform(-0.4, 0.1), rng.uniform(-0.6, -0.2), 1.0])
    light_dir /= np.linalg.norm(light_dir)
    YS, XS = np.mgrid[0:size, 0:size]
    cx, cy = size / 2.0, size / 2.0

    tri_colors = []
    for simplex in tri.simplices:
        v0, v1, v2 = points[simplex]
        centroid = (v0 + v1 + v2) / 3.0
        dist_from_center = np.sqrt((centroid[0] - cx)**2 + (centroid[1] - cy)**2) / (size * 0.5)
        nx = (centroid[0] - cx) / (size * 0.5)
        ny = (centroid[1] - cy) / (size * 0.5)
        nz = max(0.3, 1.0 - dist_from_center)
        normal = np.array([nx, ny, nz])
        norm_len = np.linalg.norm(normal)
        if norm_len > 0:
            normal /= norm_len
        diffuse = max(0.15, np.dot(normal, light_dir))
        brightness = np.clip(0.5 + 0.5 * diffuse + rng.uniform(-0.04, 0.04), 0.3, 1.2)
        tri_color = tuple(int(np.clip(c * brightness, 0, 255)) for c in color)
        tri_colors.append(tri_color)

        min_x = max(0, int(min(v0[0], v1[0], v2[0])))
        max_x = min(size - 1, int(max(v0[0], v1[0], v2[0])))
        min_y = max(0, int(min(v0[1], v1[1], v2[1])))
        max_y = min(size - 1, int(max(v0[1], v1[1], v2[1])))
        if max_x <= min_x or max_y <= min_y:
            continue

        px = XS[min_y:max_y+1, min_x:max_x+1].astype(np.float64) + 0.5
        py = YS[min_y:max_y+1, min_x:max_x+1].astype(np.float64) + 0.5
        d00 = (v1[0]-v0[0])**2 + (v1[1]-v0[1])**2
        d01 = (v1[0]-v0[0])*(v2[0]-v0[0]) + (v1[1]-v0[1])*(v2[1]-v0[1])
        d11 = (v2[0]-v0[0])**2 + (v2[1]-v0[1])**2
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            continue
        d20 = (px - v0[0]) * (v1[0]-v0[0]) + (py - v0[1]) * (v1[1]-v0[1])
        d21 = (px - v0[0]) * (v2[0]-v0[0]) + (py - v0[1]) * (v2[1]-v0[1])
        bv = (d11 * d20 - d01 * d21) / denom
        bw = (d00 * d21 - d01 * d20) / denom
        bu = 1.0 - bv - bw
        inside = (bu >= -0.001) & (bv >= -0.001) & (bw >= -0.001)
        body_region = body_mask[min_y:max_y+1, min_x:max_x+1]
        fill = inside & body_region
        if fill.any():
            for c_idx in range(3):
                rgba[min_y:max_y+1, min_x:max_x+1, c_idx][fill] = tri_color[c_idx]
            rgba[min_y:max_y+1, min_x:max_x+1, 3][fill] = 255

    # Outline
    dilated = binary_dilation(body_mask, iterations=max(1, size // 50))
    outline = dilated & ~body_mask
    dark = tuple(max(0, c // 5) for c in color)
    for c_idx in range(3):
        rgba[:, :, c_idx][outline] = dark[c_idx]
    rgba[:, :, 3][outline] = 255

    if _return_mesh:
        return rgba, (points.copy(), tri.simplices.copy(), tri_colors)
    return rgba


def _apply_markings(rgba, body_mask, rng, seed, color, accent, size):
    """Apply accent-colored markings (spots, ridge, belly, patches)."""
    YS, XS = np.mgrid[0:size, 0:size]
    mark_type = seed % 5

    if mark_type == 0:
        # Accent spots
        n_spots = rng.randint(3, 8)
        body_ys, body_xs = np.where(body_mask)
        if len(body_ys) > 0:
            for _ in range(n_spots):
                idx = rng.randint(len(body_ys))
                sy, sx = body_ys[idx], body_xs[idx]
                sr = rng.uniform(2, size * 0.05)
                spot = ((YS - sy)**2 + (XS - sx)**2 < sr**2) & body_mask
                for c in range(3):
                    rgba[:, :, c][spot] = accent[c]
    elif mark_type == 1:
        # Accent dorsal ridge
        cx = size / 2.0
        ridge_w = size * rng.uniform(0.03, 0.07)
        ridge = (np.abs(XS - cx) < ridge_w) & body_mask
        for c in range(3):
            rgba[:, :, c][ridge] = accent[c]
    elif mark_type == 2:
        # Accent belly
        belly_start = size * 0.45
        belly = (YS > belly_start) & body_mask
        belly_color = tuple(int(np.clip(a * 0.6 + c * 0.4, 0, 255)) for a, c in zip(accent, color))
        for c in range(3):
            rgba[:, :, c][belly] = belly_color[c]
    elif mark_type == 3:
        # Accent patches
        n_patches = rng.randint(2, 4)
        body_ys, body_xs = np.where(body_mask)
        if len(body_ys) > 0:
            for _ in range(n_patches):
                idx = rng.randint(len(body_ys))
                py, px = body_ys[idx], body_xs[idx]
                pr = rng.uniform(size * 0.04, size * 0.09)
                patch = ((YS - py)**2 + (XS - px)**2 < pr**2) & body_mask
                for c in range(3):
                    rgba[:, :, c][patch] = accent[c]
    # mark_type == 4: no extra markings


def _apply_eyes(rgba, body_mask, rng, size):
    """Draw white eye sclera and return normalized eye positions.

    Returns list of (norm_x, norm_y, norm_r) in [0,1] coordinates.
    Pupils are drawn separately at render time by draw_creature_eyes().
    """
    YS, XS = np.mgrid[0:size, 0:size]
    body_ys, _ = np.where(body_mask)
    if len(body_ys) == 0:
        return []
    top_y = body_ys.min()
    cx = size / 2.0
    eye_y = top_y + size * 0.12
    eye_spacing = size * rng.uniform(0.08, 0.16)
    eye_r = size * rng.uniform(0.055, 0.085)

    eyes = []
    for side in [-1, 1]:
        ex = cx + side * eye_spacing
        d = (YS - eye_y)**2 + (XS - ex)**2
        eye_mask = d < eye_r**2
        rgba[:, :, :3][eye_mask] = 255
        rgba[:, :, 3][eye_mask] = 255
        eyes.append((ex / size, eye_y / size, eye_r / size))
    return eyes


def generate_creature(seed, size=32):
    """Generate a low-poly faceted creature sprite.

    Args:
        seed: Integer seed for deterministic generation.
        size: Output square pixel size (default 32).

    Returns:
        (pygame.Surface with SRCALPHA, eye_info) where eye_info is a list
        of (norm_x, norm_y, norm_r) for each eye in [0,1] coordinates.
    """
    rng = np.random.RandomState(seed & 0xFFFFFFFF)
    color = _color_from_seed(rng)
    accent = _accent_color(rng, color)

    # Body outline + rasterize
    outline_verts = _generate_body_outline(rng, size)
    body_mask = _rasterize_polygon(outline_verts, size)

    # Appendages
    for app_verts in _generate_appendages(rng, outline_verts, size):
        clipped = [(np.clip(x, 0, size - 1), np.clip(y, 0, size - 1)) for x, y in app_verts]
        body_mask |= _rasterize_polygon(clipped, size)

    # Minimum body size fallback
    if body_mask.sum() < size * size * 0.02:
        ys, xs = np.mgrid[0:size, 0:size]
        d = ((xs - size / 2) / (size * 0.2))**2 + ((ys - size / 2) / (size * 0.35))**2
        body_mask = d <= 1.0

    # Faceted shading
    rgba = _triangulate_and_shade(body_mask, rng, color, size)
    _apply_markings(rgba, body_mask, rng, seed, color, accent, size)
    eye_info = _apply_eyes(rgba, body_mask, rng, size)

    # Convert to pygame surface
    h, w = rgba.shape[:2]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.pixelcopy.array_to_surface(surf, rgba[:, :, :3].transpose(1, 0, 2))
    alpha_arr = pygame.surfarray.pixels_alpha(surf)
    alpha_arr[:] = rgba[:, :, 3].T
    del alpha_arr
    return surf, eye_info


def draw_creature_eyes(screen, x, y, size, eye_info, mouse_pos, seed=0):
    """Draw tracking/wandering pupils on a creature already blitted to screen.

    Args:
        screen: pygame display surface.
        x, y: Top-left screen coords where the creature was blitted.
        size: Pixel size the creature was drawn at.
        eye_info: List of (norm_x, norm_y, norm_r) from generate_creature.
        mouse_pos: (mx, my) current mouse position in screen coords.
        seed: Per-creature seed to offset wander phase (so creatures wander independently).
    """
    if not eye_info:
        return
    mx, my = mouse_pos
    s = _eye_state
    attention = s["attention"]
    # Per-creature phase offset from seed (large prime multiplier for good spread)
    phase = s["wander_phase"] + (seed * 2.6537) % (2 * math.pi * 100)
    wx, wy = _wander_offset(phase)

    for (nx, ny, nr) in eye_info:
        eye_cx = x + nx * size
        eye_cy = y + ny * size
        eye_r = nr * size
        pupil_r = max(1, int(eye_r * 0.5))
        max_offset = max(0.0, eye_r - pupil_r)

        # Mouse-tracking offset (clamped inside sclera)
        mdx = mx - eye_cx
        mdy = my - eye_cy
        dist = max(1e-6, (mdx * mdx + mdy * mdy) ** 0.5)
        if dist > max_offset:
            mdx = mdx / dist * max_offset
            mdy = mdy / dist * max_offset

        # Wander offset scaled to fraction of max_offset
        wander_r = max_offset * _WANDER_REACH
        wdx = wx * wander_r
        wdy = wy * wander_r

        # Blend mouse tracking and wander
        fdx = attention * mdx + (1 - attention) * wdx
        fdy = attention * mdy + (1 - attention) * wdy

        # Re-clamp blended result inside sclera
        fdist = math.sqrt(fdx * fdx + fdy * fdy)
        if fdist > max_offset and fdist > 1e-6:
            fdx = fdx / fdist * max_offset
            fdy = fdy / fdist * max_offset

        # pygame.draw.circle pixel centroid is at (px-0.5, py-0.5) due to
        # integer rasterization spanning [px-r, px+r-1]; +0.5 compensates
        px = round(eye_cx + fdx + 0.5)
        py = round(eye_cy + fdy + 0.5)
        pygame.draw.circle(screen, (0, 0, 0), (px, py), pupil_r)


def get_creature(idx, cache, name_key):
    """Get or generate creature sprite for a point, with lazy caching.

    Args:
        idx: Point index (cache key).
        cache: Dict mapping idx -> (pygame.Surface, eye_info).
        name_key: Integer seed for generation.

    Returns:
        (32x32 pygame.Surface with SRCALPHA, eye_info).
    """
    if idx not in cache:
        cache[idx] = generate_creature(int(name_key), size=32)
    return cache[idx]


# --- Morph animation system ---

# Pre-rendered morph frame settings
_MORPH_FRAMES = 16        # frames per animation cycle
_MORPH_CYCLE_MS = 8000.0  # cycle duration in ms (~8 seconds, non-repeating due to incommensurate freqs)

def generate_morph_data(seed, size=64):
    """Generate mesh data for animated creature morphing.

    Runs the same generation pipeline as generate_creature but captures
    the Delaunay mesh (points, simplices, per-triangle colors) needed
    to re-render deformed frames without re-triangulating.

    Args:
        seed: Integer seed for deterministic generation.
        size: Output square pixel size (default 64).

    Returns:
        dict with keys: points, simplices, tri_colors, eye_info, color,
        accent, outline_color, seed, size, displace_phases, displace_freqs.
    """
    rng = np.random.RandomState(seed & 0xFFFFFFFF)
    color = _color_from_seed(rng)
    accent = _accent_color(rng, color)

    outline_verts = _generate_body_outline(rng, size)
    body_mask = _rasterize_polygon(outline_verts, size)

    for app_verts in _generate_appendages(rng, outline_verts, size):
        clipped = [(np.clip(x, 0, size - 1), np.clip(y, 0, size - 1)) for x, y in app_verts]
        body_mask |= _rasterize_polygon(clipped, size)

    if body_mask.sum() < size * size * 0.02:
        ys, xs = np.mgrid[0:size, 0:size]
        d = ((xs - size / 2) / (size * 0.2))**2 + ((ys - size / 2) / (size * 0.35))**2
        body_mask = d <= 1.0

    # Get mesh data from triangulation
    result = _triangulate_and_shade(body_mask, rng, color, size, _return_mesh=True)
    _rgba, (mesh_points, simplices, tri_colors) = result

    # Advance RNG through markings (to keep eye positions consistent)
    _apply_markings(_rgba, body_mask, rng, seed, color, accent, size)

    # Eye positions
    eye_info = _apply_eyes(_rgba, body_mask, rng, size)

    # Pre-compute per-vertex displacement parameters (separate RNG)
    disp_rng = np.random.RandomState((seed * 7919) & 0xFFFFFFFF)
    n_pts = len(mesh_points)

    return {
        'points': mesh_points.astype(np.float64),
        'simplices': simplices,
        'tri_colors': tri_colors,
        'eye_info': eye_info,
        'color': color,
        'accent': accent,
        'outline_color': tuple(max(0, c // 5) for c in color),
        'seed': seed,
        'size': size,
        'displace_phases': disp_rng.uniform(0, 2 * np.pi, n_pts),
        'displace_freqs': disp_rng.uniform(0.8, 2.0, n_pts),
    }


def _displace_vertices(morph_data, elapsed_ms):
    """Displace mesh vertices using harmonic oscillators for organic morphing.

    Combines radial breathing, y-axis wave ripple, and tangential wobble
    with incommensurate frequencies for non-repeating motion.
    """
    points = morph_data['points']
    size = morph_data['size']
    phases = morph_data['displace_phases']
    freqs = morph_data['displace_freqs']
    t = elapsed_ms / 1000.0
    cx, cy = size / 2.0, size / 2.0

    displaced = points.copy()

    dx = points[:, 0] - cx
    dy = points[:, 1] - cy
    dist = np.sqrt(dx * dx + dy * dy)
    dist_safe = np.maximum(dist, 0.5)

    # Normalized y-position for wave propagation along body
    y_norm = points[:, 1] / size

    # Amplitude: proportional to distance from center, capped at ~3.5% of size
    amplitude = np.minimum(size * 0.035, dist * 0.06)

    # Multi-component radial oscillation (incommensurate frequencies)
    breathing = 0.6 * np.sin(1.2 * t + phases)
    ripple = 0.3 * np.sin(2.5 * t + y_norm * 4.0 + phases * 0.7)
    organic = 0.1 * np.sin(3.7 * t + phases * 1.3 + 2.0)
    radial = amplitude * (breathing + ripple + organic)

    # Tangential wobble (perpendicular to radial direction)
    tangential = amplitude * 0.4 * np.cos(1.8 * t + phases + 0.5)

    # Unit vectors: radial and tangential
    nx = dx / dist_safe
    ny = dy / dist_safe
    tx = -ny
    ty = nx

    # Apply displacement only to points away from center
    mask = dist > 1.0
    displaced[mask, 0] += nx[mask] * radial[mask] + tx[mask] * tangential[mask]
    displaced[mask, 1] += ny[mask] * radial[mask] + ty[mask] * tangential[mask]

    return displaced


def render_morph_frame(morph_data, elapsed_ms):
    """Render one morphed creature frame using displaced triangle mesh.

    Uses pygame.draw.polygon for fast C-level triangle rasterization
    instead of numpy-based scanline fill.

    Args:
        morph_data: Dict from generate_morph_data().
        elapsed_ms: Current time in milliseconds.

    Returns:
        (pygame.Surface with SRCALPHA, eye_info).
    """
    size = morph_data['size']
    points = _displace_vertices(morph_data, elapsed_ms)

    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Render filled triangles via pygame (C-level, fast)
    for idx, simplex in enumerate(morph_data['simplices']):
        tri_pts = points[simplex]
        color = morph_data['tri_colors'][idx]
        verts = [(round(float(p[0])), round(float(p[1]))) for p in tri_pts]
        pygame.draw.polygon(surf, (*color, 255), verts)

    # Compute outline from filled pixels
    alpha = pygame.surfarray.array_alpha(surf)  # copy, no surface lock
    filled = alpha > 0
    if filled.any():
        dil_iter = max(1, size // 50)
        dilated = binary_dilation(filled, iterations=dil_iter)
        outline = dilated & ~filled
        dark = morph_data['outline_color']
        px3d = pygame.surfarray.pixels3d(surf)
        px_a = pygame.surfarray.pixels_alpha(surf)
        px3d[outline] = dark
        px_a[outline] = 255
        del px3d, px_a

    # Draw eye sclera
    for (nx, ny, nr) in morph_data['eye_info']:
        ecx = round(nx * size)
        ecy = round(ny * size)
        er = max(1, round(nr * size))
        pygame.draw.circle(surf, (255, 255, 255, 255), (ecx, ecy), er)

    return surf, morph_data['eye_info']


def generate_morph_frames(seed, size=32):
    """Pre-render a cycle of morph animation frames for cheap playback.

    Generates _MORPH_FRAMES surfaces by rendering the morphed mesh at
    evenly spaced time offsets. At render time, pick a frame based on
    elapsed_ms for near-free animated blitting.

    Args:
        seed: Integer seed for deterministic generation.
        size: Output square pixel size (default 32).

    Returns:
        (frames, eye_info) where frames is a list of pygame.Surfaces
        and eye_info is the normalized eye position list.
    """
    md = generate_morph_data(seed, size)
    frames = []
    for i in range(_MORPH_FRAMES):
        t_ms = i * _MORPH_CYCLE_MS / _MORPH_FRAMES
        surf, eye_info = render_morph_frame(md, t_ms)
        frames.append(surf)
    return frames, eye_info


def get_morph_frame(frames, elapsed_ms):
    """Pick the appropriate pre-rendered morph frame for the current time.

    Args:
        frames: List of pre-rendered pygame.Surfaces from generate_morph_frames.
        elapsed_ms: Current time in milliseconds.

    Returns:
        pygame.Surface for the current animation frame.
    """
    t = (elapsed_ms % _MORPH_CYCLE_MS) / _MORPH_CYCLE_MS
    idx = int(t * len(frames)) % len(frames)
    return frames[idx]


def get_creature_animated(idx, cache, name_key):
    """Get or generate animated creature frames for a point, with lazy caching.

    Args:
        idx: Point index (cache key).
        cache: Dict mapping idx -> (frames_list, eye_info).
        name_key: Integer seed for generation.

    Returns:
        (frames_list, eye_info) where frames_list has _MORPH_FRAMES surfaces.
    """
    if idx not in cache:
        cache[idx] = generate_morph_frames(int(name_key), size=32)
    return cache[idx]
