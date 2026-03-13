#!/usr/bin/env python3
"""Headless screenshot tool for 4-Sphere Explorer.

Runs the game without a display, executes scripted actions, and saves
screenshots to output/. Uses SDL dummy drivers for headless operation.

Usage:
    ./venv/bin/python screenshot.py [script]

Available scripts (default: default):
    default     - Initial view + rotate + change view modes
    viewmodes   - Screenshot all 4 view modes
    travel      - Click nearest planet, travel, screenshot arrival
    custom      - Define actions in ACTIONS list below

Actions are lists of (action_type, *args) tuples:
    ("screenshot", "filename")       - Save screenshot to output/filename.png
    ("keys", {K_w: True, ...}, N)    - Hold keys for N frames
    ("wait", N)                      - Run N frames with no input
    ("set_view_mode", 0-3)           - Set view mode directly
    ("click_nearest",)               - Start travel to nearest visible planet
    ("travel_complete",)             - Wait until travel finishes
    ("rotate", "wasd_key", frames)   - Rotate in a direction for N frames
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import numpy as np

pygame.mixer.pre_init(44100, -16, 2)
pygame.init()

from sphere import (
    random_point_on_s3,
    angular_distance,
    build_visibility_kdtree,
    query_visible_kdtree,
    tangent_basis,
    rotate_frame,
    rotate_frame_tangent,
    reorthogonalize_frame,
    build_player_frame,
    build_fixed_y_frame,
    project_to_tangent,
    project_tangent_to_screen,
    slerp,
    w_to_color,
    random_color,
    decode_name,
    TOTAL_NAMES,
)

# ── Constants (mirror main.py) ──────────────────────────────────────────
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
NUM_PLANETS = 30_000
FOV_ANGLE = 0.116
GAME_SEED = 42
CAMERA_OFFSET = 0.08
ROTATION_SPEED = 0.02
TRAVEL_SPEED = 0.00008

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
font = pygame.font.Font(None, 14)
start_time = pygame.time.get_ticks()

BG_COLOR = (20, 20, 30)
TEXT_COLOR = (200, 200, 200)
LIST_BG = (40, 40, 60)

# ── Game state ──────────────────────────────────────────────────────────
player_pos = np.array([1.0, 0.0, 0.0, 0.0])
camera_pos = np.array([np.cos(CAMERA_OFFSET), 0.0, np.sin(CAMERA_OFFSET), 0.0])
orientation = np.eye(4)
orientation[0] = camera_pos.copy()
_init_basis = tangent_basis(camera_pos)
for _i in range(3):
    orientation[_i + 1] = _init_basis[_i]

planets = random_point_on_s3(NUM_PLANETS)
visibility_kdtree = build_visibility_kdtree(planets)
_name_keys = np.random.default_rng(GAME_SEED).choice(TOTAL_NAMES, NUM_PLANETS, replace=False)
planet_name_cache = {}

def get_name(idx):
    if idx not in planet_name_cache:
        planet_name_cache[idx] = decode_name(_name_keys[idx])
    return planet_name_cache[idx]

planet_colors = random_color(NUM_PLANETS)
view_mode = 3  # only XYZ Fixed-Y
view_zoom = 1.0

# Travel state
traveling = False
travel_target = None
travel_target_idx = None
travel_progress = 0.0

visible_indices = []
visible_distances = []

# Planet sprites
planet_sprites = {}
planet_names = []
def load_planet_sprites():
    planet_dir = "assets/planets"
    if not os.path.isdir(planet_dir):
        return
    planet_files = [f"planet_{i:02d}.png" for i in range(1, 11)]
    index_path = os.path.join(planet_dir, "planet_index.txt")
    if os.path.isfile(index_path):
        with open(index_path) as f:
            for line in f:
                parts = line.strip().split("=")
                if len(parts) == 2:
                    fname = parts[0].strip()
                    pname = parts[1].strip()
                    path = os.path.join(planet_dir, fname)
                    if os.path.isfile(path):
                        planet_sprites[fname] = pygame.image.load(path).convert_alpha()
                        planet_names.append(fname)

load_planet_sprites()


def update_visible():
    global visible_indices, visible_distances
    vis_planets, indices = query_visible_kdtree(visibility_kdtree, player_pos, planets, FOV_ANGLE)
    distances = [angular_distance(player_pos, planets[i]) for i in indices]
    sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
    visible_indices = [p[0] for p in sorted_pairs]
    visible_distances = [p[1] for p in sorted_pairs]


def format_dist(rad):
    if rad < 1.0:
        return f"{rad * 1000:.0f} mrad"
    return f"{rad:.2f} rad"


def render_frame():
    """Render one frame to screen surface (mirrors main.py rendering)."""
    global start_time
    view_width = SCREEN_WIDTH - 300
    center_x = view_width // 2
    center_y = SCREEN_HEIGHT // 2
    now = pygame.time.get_ticks()

    screen.fill(BG_COLOR)

    # Build planet display colors dict for sidebar
    planet_display_colors = {}

    if True:
        player_frame = build_fixed_y_frame(player_pos, 0.0)

        vis_pts = planets[visible_indices]
        rel_vis = vis_pts @ player_frame.T
        xyz_scale = min(view_width, SCREEN_HEIGHT) * 0.4 * view_zoom
        screen_x = (center_x + rel_vis[:, 1] * xyz_scale).astype(int)
        screen_y = (center_y + rel_vis[:, 2] * xyz_scale).astype(int)
        w_vals = rel_vis[:, 3]
        sort_order = np.argsort(rel_vis[:, 0])

        for vi in sort_order:
            idx = visible_indices[vi]
            sx, sy = screen_x[vi], screen_y[vi]
            if not (0 <= sx < view_width and 0 <= sy < SCREEN_HEIGHT):
                continue
            w_norm = np.clip(w_vals[vi] / FOV_ANGLE, -1.0, 1.0)
            r, g, b = w_to_color(w_norm)
            angular_dist = visible_distances[vi]
            normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / FOV_ANGLE)))
            radius = max(1, int(2 + normalized_dist * 4))
            color = (min(255, r), min(255, g), min(255, b))
            planet_display_colors[idx] = color
            pygame.draw.circle(screen, color, (sx, sy), radius)
    else:
        basis = [orientation[1], orientation[2], orientation[3]]
        player_screen_offset = project_to_tangent(camera_pos, player_pos, basis)

        for i, idx in enumerate(visible_indices):
            p4d = planets[idx]
            tangent_xyz = project_to_tangent(camera_pos, p4d, basis)
            tangent_xyz[0] -= player_screen_offset[0]
            tangent_xyz[1] -= player_screen_offset[1]
            p2d, depth = project_tangent_to_screen(tangent_xyz, view_width, SCREEN_HEIGHT)

            if depth <= 0 or not (0 <= p2d[0] < view_width and 0 <= p2d[1] < SCREEN_HEIGHT):
                continue

            angular_dist = visible_distances[i]
            normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / FOV_ANGLE)))
            radius = max(1, int(2 + normalized_dist * 6))

            color = tuple(int(c) for c in planet_colors[idx])

            planet_display_colors[idx] = color

            # Try planet sprite, fall back to circle
            rendered = False
            if planet_sprites and planet_names:
                sprite_idx = hash(idx) % len(planet_names)
                fname = planet_names[sprite_idx]
                sprite = planet_sprites.get(fname)
                if sprite:
                    scale_size = max(8, int(radius * 4))
                    scaled = pygame.transform.scale(sprite, (scale_size, scale_size))
                    tinted = scaled.copy()
                    color_surf = pygame.Surface((scale_size, scale_size))
                    color_surf.fill(color)
                    tinted.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)
                    draw_pos = (int(p2d[0]) - scale_size // 2, int(p2d[1]) - scale_size // 2)
                    screen.blit(tinted, draw_pos)
                    rendered = True
            if not rendered:
                pygame.draw.circle(screen, color, (int(p2d[0]), int(p2d[1])), radius)

    # Crosshair
    cx, cy = center_x, center_y
    pygame.draw.line(screen, (100, 100, 100), (cx - 10, cy), (cx + 10, cy))
    pygame.draw.line(screen, (100, 100, 100), (cx, cy - 10), (cx, cy + 10))

    # Player dot
    if not traveling:
        pygame.draw.circle(screen, (255, 100, 100), (cx, cy), 3)

    # Sidebar
    sidebar_x = SCREEN_WIDTH - 300
    pygame.draw.rect(screen, LIST_BG, (sidebar_x, 0, 300, SCREEN_HEIGHT))

    # View mode label
    mode_label = "XYZ Fixed-Y"
    mode_text = font.render(f"View: {mode_label}", True, TEXT_COLOR)
    screen.blit(mode_text, (sidebar_x + 10, 10))

    # Planet count
    count_text = font.render(f"Visible: {len(visible_indices)} planets", True, TEXT_COLOR)
    screen.blit(count_text, (sidebar_x + 10, 30))

    # Travel indicator
    if traveling and travel_target_idx is not None:
        name = get_name(travel_target_idx)
        dist = angular_distance(player_pos, travel_target)
        travel_text = font.render(f"Traveling to {name} ({format_dist(dist)})", True, (100, 200, 255))
        screen.blit(travel_text, (sidebar_x + 10, 50))

    # Planet list
    item_height = 40
    list_y = 100
    max_items = (SCREEN_HEIGHT - list_y) // item_height
    for li, idx in enumerate(visible_indices[:max_items]):
        y = list_y + li * item_height
        color = planet_display_colors.get(idx, (200, 200, 255))
        name = get_name(idx)
        dist = visible_distances[li] if li < len(visible_distances) else 0
        item_bg = (60, 60, 90)
        pygame.draw.rect(screen, item_bg, (sidebar_x, y, 300, item_height - 2))
        # Color dot
        pygame.draw.circle(screen, color, (sidebar_x + 15, y + item_height // 2), 5)
        # Name + distance
        name_text = font.render(f"{name}  {format_dist(dist)}", True, TEXT_COLOR)
        screen.blit(name_text, (sidebar_x + 30, y + 12))


def step_travel():
    """Advance travel by one frame."""
    global player_pos, camera_pos, traveling, travel_target, travel_target_idx, travel_progress
    if not traveling or travel_target is None:
        return
    travel_progress += TRAVEL_SPEED
    if travel_progress >= 1.0 or angular_distance(player_pos, travel_target) < 0.0005:
        player_pos = travel_target / np.linalg.norm(travel_target)
        traveling = False
        travel_target = None
        travel_target_idx = None
        travel_progress = 0.0
    else:
        player_pos = slerp(player_pos, travel_target, travel_progress)
        player_pos /= np.linalg.norm(player_pos)

    # Update camera to follow player
    cam_dir = orientation[0]
    offset_dir = orientation[2]
    camera_pos = np.cos(CAMERA_OFFSET) * player_pos + np.sin(CAMERA_OFFSET) * offset_dir
    camera_pos /= np.linalg.norm(camera_pos)
    orientation[0] = camera_pos
    reorthogonalize_frame(orientation)
    update_visible()


def start_travel_to_nearest():
    """Begin travel to nearest visible planet."""
    global traveling, travel_target, travel_target_idx, travel_progress
    if not visible_indices:
        return
    travel_target_idx = visible_indices[0]
    travel_target = planets[travel_target_idx]
    traveling = True
    travel_progress = 0.0
    print(f"  Travel to {get_name(travel_target_idx)} ({format_dist(visible_distances[0])})")


def do_rotate(key, frames):
    """Apply rotation for N frames."""
    for _ in range(frames):
        if key == "w":
            rotate_frame(orientation, 1, -ROTATION_SPEED)
        elif key == "s":
            rotate_frame(orientation, 1, ROTATION_SPEED)
        elif key == "a":
            rotate_frame(orientation, 2, -ROTATION_SPEED)
        elif key == "d":
            rotate_frame(orientation, 2, ROTATION_SPEED)
        elif key == "q":
            rotate_frame(orientation, 3, ROTATION_SPEED)
        elif key == "e":
            rotate_frame(orientation, 3, -ROTATION_SPEED)
        reorthogonalize_frame(orientation)
        camera_pos_local = orientation[0]
        update_visible()


def save_screenshot(name):
    """Save current screen to output/name.png"""
    path = f"output/{name}.png"
    pygame.image.save(screen, path)
    print(f"  Saved: {path}")


# ── Built-in scripts ────────────────────────────────────────────────────

def script_default():
    """Initial view, rotate a bit, show all view modes."""
    update_visible()
    render_frame()
    save_screenshot("01_initial")

    do_rotate("d", 30)
    render_frame()
    save_screenshot("02_rotated_right")

    do_rotate("w", 20)
    render_frame()
    save_screenshot("03_rotated_up")

    do_rotate("q", 25)
    render_frame()
    save_screenshot("04_rotated_4d")


def script_viewmodes():
    """Screenshot the view."""
    update_visible()
    render_frame()
    save_screenshot("view_xyz_fixed_y")


def script_travel():
    """Travel to nearest planet and screenshot."""
    update_visible()
    render_frame()
    save_screenshot("travel_01_before")

    start_travel_to_nearest()
    render_frame()
    save_screenshot("travel_02_started")

    # Run frames until travel completes (max 50000)
    for i in range(50000):
        step_travel()
        if not traveling:
            break
    render_frame()
    save_screenshot("travel_03_arrived")


def script_fixed_y_rotation_test():
    """Verify Fixed-Y colors don't change when rotating. Takes before/after screenshots."""
    update_visible()
    render_frame()
    save_screenshot("fixedy_01_initial")

    do_rotate("d", 40)
    render_frame()
    save_screenshot("fixedy_02_after_rotate_d")

    do_rotate("a", 80)
    render_frame()
    save_screenshot("fixedy_03_after_rotate_a")


SCRIPTS = {
    "default": script_default,
    "viewmodes": script_viewmodes,
    "travel": script_travel,
    "fixedy": script_fixed_y_rotation_test,
}


if __name__ == "__main__":
    script_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    if script_name == "all":
        for name, func in SCRIPTS.items():
            print(f"\n=== Running script: {name} ===")
            func()
    elif script_name in SCRIPTS:
        print(f"Running script: {script_name}")
        SCRIPTS[script_name]()
    else:
        print(f"Unknown script: {script_name}")
        print(f"Available: {', '.join(SCRIPTS.keys())}, all")
        sys.exit(1)

    pygame.quit()
    print("\nDone.")
