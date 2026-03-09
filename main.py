import pygame
import numpy as np
import math
from collections import deque
from audio import init_audio, update_audio, cleanup_audio, get_audio_params
from lib.constants import *
from lib.graphics import get_creature, generate_creature, draw_creature_eyes, update_eye_tracking
from lib.planets import (
    get_planet_equirect, get_planet_equirect_hires, request_hires_preload,
    update_hires_preload_queue, render_planet_frame, get_planet_rotation_angle,
    reset_frame_budget, evict_planet_cache,
)
from lib.gamepedia import (
    GP_LEFT_X, GP_LEFT_W, GP_TOP_Y, GP_LINE_H,
    GAMEPEDIA_CONTENT, _gamepedia_flat, word_wrap_text,
)
from sphere import (
    random_point_on_s3,
    angular_distance,
    visible_points,
    build_visibility_kdtree,
    query_visible_kdtree,
    tangent_basis,
    rotate_frame,
    rotate_frame_tangent,
    reorthogonalize_frame,
    build_player_frame,
    project_to_tangent,
    project_tangent_to_screen,
    slerp,
    w_to_color,
    random_color,
    decode_name,
    TOTAL_NAMES,
)

pygame.mixer.pre_init(44100, -16, 2)
pygame.init()
init_audio()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("4-Sphere Explorer")

# Generate window icon
pygame.display.set_icon(generate_creature(42, size=64)[0])

clock = pygame.time.Clock()
font = pygame.font.Font(None, 14)
start_time = pygame.time.get_ticks()  # milliseconds since pygame init

# Starfield: random 4D directions for parallax background
_star_rng = np.random.default_rng(seed=123)
_star_dirs = _star_rng.standard_normal((NUM_STARS, 4))
_star_dirs /= np.linalg.norm(_star_dirs, axis=1, keepdims=True)
_star_brightness = _star_rng.uniform(0.15, 0.6, NUM_STARS)
_star_sizes = _star_rng.choice([1, 1, 1, 2], NUM_STARS)

player_pos = np.array([1.0, 0.0, 0.0, 0.0])
camera_pos = np.array([np.cos(CAMERA_OFFSET), 0.0, np.sin(CAMERA_OFFSET), 0.0])

# Persistent orientation frame: row 0 = camera, rows 1-3 = tangent basis
orientation = np.eye(4)
orientation[0] = camera_pos.copy()
_init_basis = tangent_basis(camera_pos)
for _i in range(3):
    orientation[_i + 1] = _init_basis[_i]

points = random_point_on_s3(NUM_POINTS)

# Build spatial index for fast visibility queries
visibility_kdtree = build_visibility_kdtree(points)

# Name keys: map each point index to a unique name via combinatorial index
_name_keys = np.random.default_rng(GAME_SEED).choice(TOTAL_NAMES, NUM_POINTS, replace=False)
point_name_cache = {}

def get_name(idx):
    """Lazily decode the name for point idx."""
    if idx not in point_name_cache:
        point_name_cache[idx] = decode_name(_name_keys[idx])
    return point_name_cache[idx]

point_colors = random_color(NUM_POINTS)  # Assign random colors

# Lazy identicon cache: idx -> pygame Surface
point_creature_cache = {}

traveling = False
travel_target = None
travel_target_idx = None
travel_progress = 0.0
travel_speed = TRAVEL_SPEED
queued_target = None
queued_target_idx = None
pop_animation_idx = None
pop_animation_start_time = None

# Auto-travel (Tab key) system
visited_points = set()  # Indices of points already traveled-to
visit_history = deque(maxlen=50)  # Ordered trail of visited point indices
auto_travel_feedback = None  # (message, timestamp) or None
auto_travel_feedback_duration = 2000  # milliseconds

# Radial menu state
menu_state = "idle"  # idle | hold_pending | menu_open
menu_hold_start = 0  # tick when mouse went down on a point
menu_point_idx = None  # point index the menu is for
menu_center = None  # (x, y) screen position of menu

# Detail panel state
inspected_point_idx = None  # point currently inspected (panel open)


def find_nearest_unvisited(visible_idx_list, visible_dist_list):
    """Find the nearest unvisited point from visible list.

    Args:
        visible_idx_list: List of visible point indices (from visible_indices)
        visible_dist_list: List of distances (from visible_distances), parallel to idx_list

    Returns:
        (index, distance) tuple for nearest unvisited point, or (None, None) if all visited
    """
    for idx, dist in zip(visible_idx_list, visible_dist_list):
        if idx not in visited_points:
            return idx, dist
    return None, None


def auto_travel_to_nearest_unvisited():
    """Start travel to nearest unvisited visible point if one exists."""
    global traveling, travel_target, travel_target_idx, travel_progress
    global queued_target, queued_target_idx

    nearest_idx, nearest_dist = find_nearest_unvisited(visible_indices, visible_distances)

    if nearest_idx is not None:
        request_hires_preload(nearest_idx, _name_keys[nearest_idx])
        if traveling:
            # Queue the auto-travel target
            queued_target_idx = nearest_idx
            queued_target = points[nearest_idx]
            print(f"Queued auto-travel to {get_name(nearest_idx)} ({format_dist(nearest_dist)})")
        else:
            # Start travel immediately
            travel_target_idx = nearest_idx
            travel_target = points[nearest_idx]
            traveling = True
            travel_progress = 0.0
            print(f"Auto-traveling to {get_name(nearest_idx)} ({format_dist(nearest_dist)})")
    else:
        print("No unvisited points visible. Explore more!")


# UI state
list_scroll = 0
visible_indices = []
visible_distances = []
hovered_item = None
view_mode = 0  # 0 = assigned colors, 1 = relative 4D position colors, 2 = XYZ projection (W→color), 3 = XYZ Fixed-Y
xyz_zoom = 1.0  # zoom level for XYZ projection view
XYZ_FIXED_UP = np.array([0.0, 1.0, 0.0, 0.0])  # absolute Y axis for mode 3
last_projected_points = []  # store for click detection
list_start_y = 100  # Y coordinate where point list items begin (updated each frame)

# Search/filter state
search_text = ""
search_active = False

# Gamepedia state
gamepedia_open = False
gamepedia_selected_topic = 0
gamepedia_scroll = 0

def apply_search_filter(search_query):
    """Filter visible_indices by name prefix match.

    Args:
        search_query: String to match against point names (case-insensitive prefix)

    Returns:
        List of indices from visible_indices whose names start with search_query
    """
    if not search_query:
        return visible_indices[:]
    query_lower = search_query.lower()
    return [idx for idx in visible_indices if get_name(idx).lower().startswith(query_lower)]

# Precompute visible points and distances
def update_visible():
    global visible_indices, visible_distances, point_creature_cache
    prev_set = set(visible_indices)  # cache state before update

    # Use KDTree for sub-linear visibility query
    vis_points, indices = query_visible_kdtree(visibility_kdtree, player_pos, points, FOV_ANGLE)
    distances = [angular_distance(player_pos, points[i]) for i in indices]
    sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
    visible_indices = [p[0] for p in sorted_pairs]
    visible_distances = [p[1] for p in sorted_pairs]

    # Evict caches for points no longer visible
    new_set = set(visible_indices)
    evicted = prev_set - new_set
    for idx in evicted:
        point_creature_cache.pop(idx, None)
        point_name_cache.pop(idx, None)
    evict_planet_cache(evicted)

    # Queue hires texture generation for all visible points
    update_hires_preload_queue(visible_indices, _name_keys)


update_visible()

running = True
while running:
    clock.tick(60)
    reset_frame_budget()
    elapsed_ms = pygame.time.get_ticks()

    # Handle input
    keys = pygame.key.get_pressed()

    if not gamepedia_open:
        # Camera rotation via persistent orientation frame
        rotation_speed = ROTATION_SPEED
        if view_mode == 3:
            # XYZ Fixed-Y: only horizontal pan (A/D), Y stays locked to absolute [0,1,0,0]
            if keys[pygame.K_a]:
                rotate_frame_tangent(orientation, 1, 3, -rotation_speed)
            if keys[pygame.K_d]:
                rotate_frame_tangent(orientation, 1, 3, rotation_speed)
        elif view_mode == 2:
            # XYZ view: rotate tangent basis only (camera stays fixed)
            if keys[pygame.K_w]:  # tilt up (row 1, row 2 plane)
                rotate_frame_tangent(orientation, 1, 2, -rotation_speed)
            if keys[pygame.K_s]:  # tilt down
                rotate_frame_tangent(orientation, 1, 2, rotation_speed)
            if keys[pygame.K_a]:  # pan left (row 1, row 3 plane)
                rotate_frame_tangent(orientation, 1, 3, -rotation_speed)
            if keys[pygame.K_d]:  # pan right
                rotate_frame_tangent(orientation, 1, 3, rotation_speed)
            if keys[pygame.K_q]:  # roll (row 2, row 3 plane)
                rotate_frame_tangent(orientation, 2, 3, rotation_speed)
            if keys[pygame.K_e]:  # roll opposite
                rotate_frame_tangent(orientation, 2, 3, -rotation_speed)
        else:
            if keys[pygame.K_w]:  # rotate up (screen Y)
                rotate_frame(orientation, 2, -rotation_speed)
            if keys[pygame.K_s]:  # rotate down
                rotate_frame(orientation, 2, rotation_speed)
            if keys[pygame.K_a]:  # rotate left (screen X)
                rotate_frame(orientation, 1, -rotation_speed)
            if keys[pygame.K_d]:  # rotate right
                rotate_frame(orientation, 1, rotation_speed)
            if keys[pygame.K_q]:  # rotate in 4D depth
                rotate_frame(orientation, 3, rotation_speed)
            if keys[pygame.K_e]:  # rotate in 4D depth (opposite)
                rotate_frame(orientation, 3, -rotation_speed)

    reorthogonalize_frame(orientation)
    camera_pos = orientation[0]
    update_visible()
    update_audio(visible_indices, visible_distances, _name_keys)

    # Compute filtered list once per frame (used by event handlers and renderer)
    filtered_indices = apply_search_filter(search_text)
    vis_dist_map = {idx: dist for idx, dist in zip(visible_indices, visible_distances)}
    filtered_distances = [vis_dist_map[idx] for idx in filtered_indices]

    # List scrolling
    if not gamepedia_open:
        item_height = 40
        max_items = (SCREEN_HEIGHT - list_start_y) // item_height
        if keys[pygame.K_UP]:
            list_scroll = max(0, list_scroll - 1)
        if keys[pygame.K_DOWN]:
            list_scroll = min(max(0, len(filtered_indices) - max_items), list_scroll + 1)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if gamepedia_open:
                if event.key == pygame.K_F1 or event.key == pygame.K_ESCAPE:
                    gamepedia_open = False
                elif event.key == pygame.K_UP:
                    gamepedia_selected_topic = max(0, gamepedia_selected_topic - 1)
                    gamepedia_scroll = 0
                elif event.key == pygame.K_DOWN:
                    gamepedia_selected_topic = min(len(_gamepedia_flat) - 1, gamepedia_selected_topic + 1)
                    gamepedia_scroll = 0
            elif event.key == pygame.K_F1:
                gamepedia_open = True
            elif search_active:
                if event.key == pygame.K_ESCAPE:
                    search_text = ""
                    search_active = False
                elif event.key == pygame.K_BACKSPACE:
                    search_text = search_text[:-1]
                elif event.unicode and (event.unicode.isalnum() or event.unicode in " -"):
                    search_text += event.unicode
                # Allow UP/DOWN to scroll list even while searching (fall through handled by keys[] above)
            else:
                if event.key == pygame.K_ESCAPE:
                    if inspected_point_idx is not None:
                        inspected_point_idx = None
                    elif menu_state != "idle":
                        menu_state = "idle"
                        menu_point_idx = None
                        menu_center = None
                elif event.key == pygame.K_v:
                    view_mode = (view_mode + 1) % 4  # cycle 0/1/2/3
                elif event.key == pygame.K_SLASH or event.key == pygame.K_f:
                    search_active = True
                    search_text = ""
                elif event.key == pygame.K_TAB:
                    auto_travel_to_nearest_unvisited()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    if pygame.key.get_mods() & pygame.KMOD_CTRL and view_mode in (2, 3):
                        xyz_zoom *= 1.25
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if pygame.key.get_mods() & pygame.KMOD_CTRL and view_mode in (2, 3):
                        xyz_zoom = max(0.1, xyz_zoom / 1.25)
        elif event.type == pygame.MOUSEWHEEL:
            if gamepedia_open:
                gamepedia_scroll = max(0, gamepedia_scroll - event.y * 3)
            elif view_mode in (2, 3):
                if event.y > 0:
                    xyz_zoom *= 1.15
                elif event.y < 0:
                    xyz_zoom = max(0.1, xyz_zoom / 1.15)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if gamepedia_open:
                if event.button == 1:
                    mx, my = event.pos
                    # Left panel click: select topic
                    if GP_LEFT_X <= mx <= GP_LEFT_X + GP_LEFT_W and my >= GP_TOP_Y:
                        y_cursor = GP_TOP_Y
                        flat_idx = 0
                        for gname, topics in GAMEPEDIA_CONTENT:
                            y_cursor += GP_LINE_H  # group header
                            for title, _text in topics:
                                if y_cursor <= my < y_cursor + GP_LINE_H:
                                    gamepedia_selected_topic = flat_idx
                                    gamepedia_scroll = 0
                                y_cursor += GP_LINE_H
                                flat_idx += 1
            elif event.button == 1:  # Left click
                mx, my = event.pos
                # Dismiss detail panel on click outside it
                if inspected_point_idx is not None and menu_state == "idle":
                    # Simple dismiss: any new click clears the panel
                    # (unless it leads to a new inspection via radial menu)
                    inspected_point_idx = None
                # Check if click is on a viewport point for potential radial menu
                if mx <= SCREEN_WIDTH - 300 and last_projected_points:
                    best_dist_sq = float("inf")
                    best_idx = None
                    best_p2d = None
                    for p2d, ang, dep, idx in last_projected_points:
                        dx, dy = mx - p2d[0], my - p2d[1]
                        d_sq = dx * dx + dy * dy
                        if d_sq < best_dist_sq:
                            best_dist_sq = d_sq
                            best_idx = idx
                            best_p2d = p2d
                    if best_idx is not None and best_dist_sq < 400:
                        menu_state = "hold_pending"
                        menu_hold_start = pygame.time.get_ticks()
                        menu_point_idx = best_idx
                        menu_center = best_p2d.astype(int)
        elif event.type == pygame.MOUSEBUTTONUP and not gamepedia_open:
            if event.button == 1:  # Left click release
                mx, my = event.pos
                if menu_state == "menu_open":
                    # Check which wedge the mouse is in
                    dx = mx - menu_center[0]
                    dy = my - menu_center[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                    if WEDGE_INNER < dist < MENU_RADIUS:
                        angle = math.atan2(-dy, dx)  # negative dy for screen coords
                        wedge = int((angle + math.pi + math.pi / 4) / (math.pi / 2) + 2) % 4
                        if wedge == 0:  # Info wedge (right)
                            inspected_point_idx = menu_point_idx
                            request_hires_preload(menu_point_idx, _name_keys[menu_point_idx])
                        # wedges 1,2,3 are placeholders — no action
                    menu_state = "idle"
                    menu_point_idx = None
                    menu_center = None
                elif menu_state == "hold_pending":
                    # Released before threshold — treat as normal click
                    menu_state = "idle"
                    clicked_idx = None
                    if mx > SCREEN_WIDTH - 300:
                        item_idx = (my - list_start_y) // 40 + list_scroll
                        if 0 <= item_idx < len(filtered_indices):
                            clicked_idx = filtered_indices[item_idx]
                    elif last_projected_points:
                        best_dist_sq = float("inf")
                        best_idx = None
                        for p2d, ang, dep, idx in last_projected_points:
                            dx, dy = mx - p2d[0], my - p2d[1]
                            d_sq = dx * dx + dy * dy
                            if d_sq < best_dist_sq:
                                best_dist_sq = d_sq
                                best_idx = idx
                        if best_idx is not None and best_dist_sq < 400:
                            clicked_idx = best_idx
                    if clicked_idx is not None:
                        request_hires_preload(clicked_idx, _name_keys[clicked_idx])
                        if traveling:
                            queued_target_idx = clicked_idx
                            queued_target = points[clicked_idx]
                        else:
                            travel_target_idx = clicked_idx
                            travel_target = points[clicked_idx]
                            traveling = True
                            travel_progress = 0.0
                            pop_animation_idx = None
                            pop_animation_start_time = None
                    menu_point_idx = None
                    menu_center = None
                else:
                    # Normal release (no menu involved) — resolve clicked point index
                    clicked_idx = None
                    if mx > SCREEN_WIDTH - 300:
                        item_idx = (my - list_start_y) // 40 + list_scroll
                        if 0 <= item_idx < len(filtered_indices):
                            clicked_idx = filtered_indices[item_idx]
                    elif last_projected_points:
                        best_dist_sq = float("inf")
                        best_idx = None
                        for p2d, ang, dep, idx in last_projected_points:
                            dx, dy = mx - p2d[0], my - p2d[1]
                            d_sq = dx * dx + dy * dy
                            if d_sq < best_dist_sq:
                                best_dist_sq = d_sq
                                best_idx = idx
                        if best_idx is not None and best_dist_sq < 400:
                            clicked_idx = best_idx

                    if clicked_idx is not None:
                        request_hires_preload(clicked_idx, _name_keys[clicked_idx])
                        if traveling:
                            # Queue — will start after current travel completes
                            queued_target_idx = clicked_idx
                            queued_target = points[clicked_idx]
                        else:
                            travel_target_idx = clicked_idx
                            travel_target = points[clicked_idx]
                            traveling = True
                            travel_progress = 0.0
                            pop_animation_idx = None
                            pop_animation_start_time = None
        elif event.type == pygame.MOUSEMOTION and not gamepedia_open:
            mx, my = event.pos
            if mx > SCREEN_WIDTH - 300:
                item_idx = (my - list_start_y) // 40 + list_scroll
                hovered_item = item_idx if 0 <= item_idx < len(filtered_indices) else None
            else:
                hovered_item = None

    # Check hold threshold for radial menu
    if menu_state == "hold_pending":
        if pygame.time.get_ticks() - menu_hold_start >= HOLD_THRESHOLD:
            menu_state = "menu_open"

    # Update travel
    if traveling and travel_target is not None:
        travel_progress += travel_speed
        old_player = player_pos.copy()
        player_pos = slerp(player_pos, travel_target, min(travel_progress, 1.0))
        delta = player_pos - old_player
        orientation[0] += delta
        reorthogonalize_frame(orientation)
        camera_pos = orientation[0]

        # Complete travel at proximity threshold (snap to target)
        if angular_distance(player_pos, travel_target) < ARRIVAL_THRESHOLD:
            old_player = player_pos.copy()
            player_pos = travel_target / np.linalg.norm(travel_target)
            delta = player_pos - old_player
            orientation[0] += delta
            reorthogonalize_frame(orientation)
            camera_pos = orientation[0]
            pop_animation_idx = travel_target_idx
            pop_animation_start_time = pygame.time.get_ticks()

            # Travel complete — mark as visited
            if travel_target_idx is not None:
                visited_points.add(travel_target_idx)
                visit_history.append(travel_target_idx)
                auto_travel_feedback = (f"Visited: {get_name(travel_target_idx)}", pygame.time.get_ticks())
                print(f"Visited: {get_name(travel_target_idx)} ({len(visited_points)} total)")

            if queued_target is not None:
                # Start queued travel
                travel_target = queued_target
                travel_target_idx = queued_target_idx
                travel_progress = 0.0
                queued_target = None
                queued_target_idx = None
            else:
                traveling = False
                travel_target = None
                travel_target_idx = None

            update_visible()

    # Render
    screen.fill(BG_COLOR)

    # Render starfield with parallax from camera orientation
    view_width = SCREEN_WIDTH - 300
    star_parallax_scale = 300
    for si in range(NUM_STARS):
        sx = np.dot(_star_dirs[si], orientation[1]) * star_parallax_scale
        sy = np.dot(_star_dirs[si], orientation[2]) * star_parallax_scale
        px = int((sx % view_width + view_width) % view_width)
        py = int((sy % SCREEN_HEIGHT + SCREEN_HEIGHT) % SCREEN_HEIGHT)
        if px < view_width:
            c = int(_star_brightness[si] * 255)
            pygame.draw.circle(screen, (c, c, int(c * 0.9)), (px, py), int(_star_sizes[si]))

    center_x, center_y = view_width // 2, SCREEN_HEIGHT // 2

    # Check mouse position for hover tooltip
    mx, my = pygame.mouse.get_pos()
    update_eye_tracking((mx, my), elapsed_ms)
    hover_point = None
    hover_dist_sq_min = float("inf")

    # Store computed display colors per point for reuse in tooltip/panel/sidebar
    point_display_colors = {}

    if view_mode in (2, 3):
        # XYZ Projection view: visible points rendered by XYZ position relative to player, W→color
        # Build proper orthonormal frame centered on player (not camera)
        player_frame = build_player_frame(player_pos, orientation)

        if view_mode == 3:
            # Override Y axis with absolute Y direction (orthogonalized against player)
            up = XYZ_FIXED_UP.copy()
            up -= np.dot(up, player_frame[0]) * player_frame[0]
            up_norm = np.linalg.norm(up)
            if up_norm > 1e-8:
                up /= up_norm
                player_frame[2] = up
                # Re-derive row 3: orthogonalize orientation[3] against rows 0 and 2
                v3 = orientation[3].copy()
                v3 -= np.dot(v3, player_frame[0]) * player_frame[0]
                v3 -= np.dot(v3, player_frame[2]) * player_frame[2]
                v3 /= np.linalg.norm(v3)
                player_frame[3] = v3
                # Row 1 completes the orthonormal basis
                v1 = orientation[1].copy()
                v1 -= np.dot(v1, player_frame[0]) * player_frame[0]
                v1 -= np.dot(v1, player_frame[2]) * player_frame[2]
                v1 -= np.dot(v1, player_frame[3]) * player_frame[3]
                v1 /= np.linalg.norm(v1)
                player_frame[1] = v1

        vis_points = points[visible_indices]  # (M, 4)
        rel_vis = vis_points @ player_frame.T  # columns: [along_player, basis1, basis2, basis3]

        # Screen mapping: basis1→X, basis2→Y, basis3(W-like)→color
        xyz_scale = min(view_width, SCREEN_HEIGHT) * 0.4 * xyz_zoom
        screen_x = (center_x + rel_vis[:, 1] * xyz_scale).astype(int)
        screen_y = (center_y + rel_vis[:, 2] * xyz_scale).astype(int)
        w_vals = rel_vis[:, 3]  # the 4th dimension relative to player

        # Sort by distance from player (farthest first for painter's algorithm)
        sort_order = np.argsort(rel_vis[:, 0])  # ascending = farthest first

        projected_points = []
        for vi in sort_order:
            idx = visible_indices[vi]
            sx, sy = screen_x[vi], screen_y[vi]
            if not (0 <= sx < view_width and 0 <= sy < SCREEN_HEIGHT):
                continue

            # W→color: -1 to +1 maps blue→white→red
            r, g, b = w_to_color(np.clip(w_vals[vi] / FOV_ANGLE, -1.0, 1.0))

            # Size by angular proximity
            angular_dist = visible_distances[vi]
            normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / FOV_ANGLE)))
            radius = max(1, int(2 + normalized_dist * 4))

            color = (min(255, r), min(255, g), min(255, b))
            point_display_colors[idx] = color
            pygame.draw.circle(screen, color, (sx, sy), radius)

            p2d = np.array([float(sx), float(sy)])
            projected_points.append((p2d, angular_dist, 0.0, idx))

            # Hover detection
            dx, dy = mx - sx, my - sy
            dist_sq = dx * dx + dy * dy
            hit_radius = max(radius + 6, 10)
            if dist_sq < hit_radius * hit_radius and dist_sq < hover_dist_sq_min:
                hover_dist_sq_min = dist_sq
                hover_point = (p2d, angular_dist, idx)

        last_projected_points = projected_points

    else:
        # Standard tangent space projection (modes 0 and 1)
        basis = [orientation[1], orientation[2], orientation[3]]
        player_screen_offset = project_to_tangent(camera_pos, player_pos, basis)

        projected_points = []
        for i, idx in enumerate(visible_indices):
            p4d = points[idx]
            tangent_xyz = project_to_tangent(camera_pos, p4d, basis)
            tangent_xyz[0] -= player_screen_offset[0]
            tangent_xyz[1] -= player_screen_offset[1]
            p2d, depth = project_tangent_to_screen(tangent_xyz, view_width, SCREEN_HEIGHT)
            angular_dist = visible_distances[i]
            projected_points.append((p2d, angular_dist, depth, idx))

        # Sort by angular distance for painter's algorithm (farther first)
        projected_points.sort(key=lambda x: x[1], reverse=True)
        last_projected_points = projected_points

        for p2d, angular_dist, depth, idx in projected_points:
            if 0 <= p2d[0] < view_width and 0 <= p2d[1] < SCREEN_HEIGHT:
                # Size and brightness based on angular distance from camera
                max_distance = FOV_ANGLE
                normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
                radius = int(2 + normalized_dist * 5)

                if view_mode == 0:
                    # Assigned color, modulate brightness by distance
                    base_color = point_colors[idx]
                else:
                    # Color from relative 4D direction (normalized for narrow FOV)
                    rel = points[idx] - camera_pos
                    rel_norm = np.linalg.norm(rel)
                    if rel_norm > 1e-8:
                        rel = rel / rel_norm
                    # Map unit direction xyzw to RGB: x→R, y→G, z→B, w→brightness
                    r = int(np.clip((rel[0] + 1.0) * 127.5, 0, 255))
                    g = int(np.clip((rel[1] + 1.0) * 127.5, 0, 255))
                    b = int(np.clip((rel[2] + 1.0) * 127.5, 0, 255))
                    w_factor = 0.5 + 0.5 * np.clip((rel[3] + 1.0) / 2.0, 0, 1)
                    base_color = (int(r * w_factor), int(g * w_factor), int(b * w_factor))

                color = base_color
                point_display_colors[idx] = color

                # Glow halo behind point
                glow_radius = int(radius * 2.5 + normalized_dist * 8)
                glow_surf = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color, 60), (glow_radius + 2, glow_radius + 2), glow_radius)
                screen.blit(glow_surf, (int(p2d[0]) - glow_radius - 2, int(p2d[1]) - glow_radius - 2))

                # Render rotating planet; fall back to circle if not yet cached
                equirect = get_planet_equirect(idx, _name_keys[idx])
                if equirect is not None:
                    rot = get_planet_rotation_angle(idx, elapsed_ms)
                    sz = max(4, int(2 * radius))
                    surf = render_planet_frame(equirect, sz, rot, tint_color=color)
                    screen.blit(surf, (int(p2d[0]) - sz // 2, int(p2d[1]) - sz // 2))
                else:
                    pygame.draw.circle(screen, color, p2d.astype(int), radius)

                # Inspection ring on currently inspected point
                if idx == inspected_point_idx:
                    ring_radius = radius + 10
                    ring_surf = pygame.Surface((ring_radius * 2 + 4, ring_radius * 2 + 4), pygame.SRCALPHA)
                    ring_color = (*color, 160)
                    pygame.draw.circle(ring_surf, ring_color, (ring_radius + 2, ring_radius + 2), ring_radius, 2)
                    screen.blit(ring_surf, (int(p2d[0]) - ring_radius - 2, int(p2d[1]) - ring_radius - 2))

                # Check if mouse is near this point (within radius + margin)
                dx, dy = mx - p2d[0], my - p2d[1]
                dist_sq = dx * dx + dy * dy
                hit_radius = max(radius + 6, 10)
                if dist_sq < hit_radius * hit_radius and dist_sq < hover_dist_sq_min:
                    hover_dist_sq_min = dist_sq
                    hover_point = (p2d, angular_dist, idx)

        # Draw breadcrumb trail: fading dots for recently visited points
        if visit_history:
            trail_len = len(visit_history)
            for trail_i, trail_idx in enumerate(visit_history):
                trail_p4d = points[trail_idx]
                trail_tangent = project_to_tangent(camera_pos, trail_p4d, basis)
                trail_tangent[0] -= player_screen_offset[0]
                trail_tangent[1] -= player_screen_offset[1]
                trail_p2d, trail_depth = project_tangent_to_screen(trail_tangent, view_width, SCREEN_HEIGHT)
                tx, ty = int(trail_p2d[0]), int(trail_p2d[1])
                if 0 <= tx < view_width and 0 <= ty < SCREEN_HEIGHT:
                    fade = (trail_i + 1) / trail_len
                    alpha = int(30 + fade * 100)
                    dot_radius = 3 if fade > 0.5 else 2
                    dot_surf = pygame.Surface((dot_radius * 2 + 4, dot_radius * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surf, (180, 220, 255, alpha), (dot_radius + 2, dot_radius + 2), dot_radius)
                    screen.blit(dot_surf, (tx - dot_radius - 2, ty - dot_radius - 2))

    # Draw white circle around hovered list item point
    if hovered_item is not None and 0 <= hovered_item < len(filtered_indices):
        hovered_point_idx = filtered_indices[hovered_item]
        for p2d, angular_dist, depth, idx in projected_points:
            if idx == hovered_point_idx:
                # Draw 50% transparent white circle outline around the point
                max_distance = FOV_ANGLE
                normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
                radius = int(2 + normalized_dist * 5)
                circle_radius = radius + 8
                # Create temporary surface for transparent circle
                temp_surf = pygame.Surface((circle_radius * 2 + 4, circle_radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, (255, 255, 255, 128), (circle_radius + 2, circle_radius + 2), circle_radius, 2)
                screen.blit(temp_surf, (int(p2d[0]) - circle_radius - 2, int(p2d[1]) - circle_radius - 2))
                break

    # Draw pop animation
    if pop_animation_idx is not None:
        elapsed_pop = pygame.time.get_ticks() - pop_animation_start_time
        if elapsed_pop >= POP_DURATION:
            pop_animation_idx = None
            pop_animation_start_time = None
        else:
            progress = elapsed_pop / POP_DURATION
            for p2d, angular_dist, depth, idx in projected_points:
                if idx == pop_animation_idx:
                    max_distance = FOV_ANGLE
                    normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
                    base_radius = int(2 + normalized_dist * 5)
                    expand_radius = base_radius + int(progress * 20)
                    alpha = int(255 * (1 - progress))
                    temp_surf = pygame.Surface((expand_radius * 2 + 4, expand_radius * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, (100, 150, 255, alpha), (expand_radius + 2, expand_radius + 2), expand_radius)
                    screen.blit(temp_surf, (int(p2d[0]) - expand_radius - 2, int(p2d[1]) - expand_radius - 2))
                    break

    # Draw animated travel line from crosshair to target
    if traveling and travel_target_idx is not None and pop_animation_idx is None:
        target_screen = None
        for p2d, angular_dist, depth, idx in projected_points:
            if idx == travel_target_idx:
                target_screen = p2d.astype(int)
                break
        if target_screen is not None:
            line_start = np.array([center_x, center_y])
            line_end = target_screen
            diff = line_end - line_start
            line_length = np.linalg.norm(diff)
            if line_length > 5:
                direction = diff / line_length
                dash_len, gap_len = 8, 6
                cycle = dash_len + gap_len
                offset = (pygame.time.get_ticks() * 0.05) % cycle
                travel_line_surf = pygame.Surface((view_width, SCREEN_HEIGHT), pygame.SRCALPHA)
                pos = -offset
                while pos < line_length:
                    seg_start = max(0.0, pos)
                    seg_end = min(line_length, pos + dash_len)
                    if seg_end > seg_start:
                        p1 = line_start + direction * seg_start
                        p2_line = line_start + direction * seg_end
                        mid_t = (seg_start + seg_end) / (2 * line_length)
                        alpha = max(30, min(120, int(120 * (1 - abs(mid_t - 0.5) * 1.5))))
                        pygame.draw.line(travel_line_surf, (100, 150, 255, alpha),
                                        p1.astype(int), p2_line.astype(int), 2)
                    pos += cycle
                screen.blit(travel_line_surf, (0, 0))

    # Draw rotating blue triangles around travel target (hide once pop starts)
    if traveling and travel_target_idx is not None and pop_animation_idx is None:
        for p2d, angular_dist, depth, idx in projected_points:
            if idx == travel_target_idx:
                elapsed_ms = pygame.time.get_ticks() - start_time
                rotation_angle = (elapsed_ms / TRIANGLE_PERIOD) * 2 * np.pi
                max_distance = FOV_ANGLE
                normalized_dist = max(0.1, min(1.0, 1.0 - (angular_dist / max_distance)))
                radius = int(2 + normalized_dist * 5)
                arrow_distance = radius + 12
                triangle_size = 5

                # Draw 3 blue triangles radially around the point
                for arrow_idx in range(3):
                    angle = rotation_angle + (arrow_idx * 2 * np.pi / 3)
                    tri_cx = p2d[0] + arrow_distance * np.cos(angle)
                    tri_cy = p2d[1] + arrow_distance * np.sin(angle)

                    # Triangle points inward toward the target
                    # Tip points toward center of target
                    tip_x = tri_cx - triangle_size * np.cos(angle)
                    tip_y = tri_cy - triangle_size * np.sin(angle)

                    # Two base points perpendicular to the radial direction
                    perp_x = -np.sin(angle)
                    perp_y = np.cos(angle)
                    base_left_x = tri_cx + perp_x * triangle_size * 0.7
                    base_left_y = tri_cy + perp_y * triangle_size * 0.7
                    base_right_x = tri_cx - perp_x * triangle_size * 0.7
                    base_right_y = tri_cy - perp_y * triangle_size * 0.7

                    tri_verts = [
                        (int(tip_x), int(tip_y)),
                        (int(base_left_x), int(base_left_y)),
                        (int(base_right_x), int(base_right_y))
                    ]
                    pygame.draw.polygon(screen, (100, 150, 255), tri_verts)
                break

    # Draw player position dot at center of view area (hide when parked at a point)
    parked = not traveling and visible_distances and visible_distances[0] < ARRIVAL_THRESHOLD
    if not parked:
        pygame.draw.circle(screen, CAMERA_COLOR, (center_x, center_y), 3)

    # Draw auto-travel feedback message
    if auto_travel_feedback is not None:
        msg, ts = auto_travel_feedback
        elapsed_fb = pygame.time.get_ticks() - ts
        if elapsed_fb > auto_travel_feedback_duration:
            auto_travel_feedback = None
        else:
            feedback_surface = font.render(msg, True, (100, 255, 100))
            screen.blit(feedback_surface, (10, 70))

    # Draw hover tooltip
    if hover_point is not None:
        hp2d, h_dist, h_idx = hover_point
        name = get_name(h_idx)
        label = f"{name} ({format_dist(h_dist)})"
        label_surface = font.render(label, True, TEXT_COLOR)
        label_rect = label_surface.get_rect()
        creature, creature_eyes = get_creature(h_idx, point_creature_cache, _name_keys[h_idx])

        # Total width: creature (32px) + gap (4px) + label
        tooltip_width = 32 + 4 + label_rect.width
        tooltip_height = max(32, label_rect.height)

        # Position tooltip above and to the right of cursor
        tx = int(hp2d[0]) + 12
        ty = int(hp2d[1]) - 20

        # Keep tooltip on screen
        if tx + tooltip_width > view_width:
            tx = int(hp2d[0]) - tooltip_width - 12
        if ty < 0:
            ty = int(hp2d[1]) + 12

        # Background
        padding = 4
        bg_rect = pygame.Rect(tx - padding, ty - padding, tooltip_width + padding * 2, tooltip_height + padding * 2)
        pygame.draw.rect(screen, (30, 30, 50), bg_rect)
        pygame.draw.rect(screen, point_display_colors.get(h_idx, TEXT_COLOR), bg_rect, 1)

        # Draw creature and label
        ident_y = ty + (tooltip_height - 32) // 2
        screen.blit(creature, (tx, ident_y))
        draw_creature_eyes(screen, tx, ident_y, 32, creature_eyes, (mx, my), seed=_name_keys[h_idx])
        screen.blit(label_surface, (tx + 32 + 4, ty + (tooltip_height - label_rect.height) // 2))

    # Draw radial menu
    if menu_state == "menu_open" and menu_center is not None:
        mx_now, my_now = pygame.mouse.get_pos()
        dx_menu = mx_now - menu_center[0]
        dy_menu = my_now - menu_center[1]
        hover_dist = (dx_menu * dx_menu + dy_menu * dy_menu) ** 0.5
        hover_angle = math.atan2(-dy_menu, dx_menu)
        hover_wedge = int((hover_angle + math.pi + math.pi / 4) / (math.pi / 2) + 2) % 4 if hover_dist > WEDGE_INNER else -1

        menu_surf = pygame.Surface((MENU_RADIUS * 2 + 4, MENU_RADIUS * 2 + 4), pygame.SRCALPHA)
        mc = MENU_RADIUS + 2  # center of surface

        # Draw background circle
        pygame.draw.circle(menu_surf, (20, 20, 40, 180), (mc, mc), MENU_RADIUS)

        # Draw wedge labels
        wedge_labels = ["Info", "A", "B", "C"]
        wedge_colors = [(100, 200, 255), (100, 100, 120), (100, 100, 120), (100, 100, 120)]
        wedge_angles = [0, math.pi / 2, math.pi, 3 * math.pi / 2]  # right, down-ish, left, up-ish (screen coords inverted)
        for wi, (label, color, wa) in enumerate(zip(wedge_labels, wedge_colors, wedge_angles)):
            # Highlight hovered wedge with filled pie sector
            if wi == hover_wedge:
                # Build polygon: inner arc -> outer arc -> close
                a_start = wa - math.pi / 4
                a_end = wa + math.pi / 4
                n_seg = 12
                pts = []
                for si in range(n_seg + 1):
                    a = a_start + (a_end - a_start) * si / n_seg
                    pts.append((mc + WEDGE_INNER * math.cos(a), mc - WEDGE_INNER * math.sin(a)))
                for si in range(n_seg, -1, -1):
                    a = a_start + (a_end - a_start) * si / n_seg
                    pts.append((mc + MENU_RADIUS * math.cos(a), mc - MENU_RADIUS * math.sin(a)))
                pygame.draw.polygon(menu_surf, (*color, 60), pts)
            # Wedge center position for label
            wr = (WEDGE_INNER + MENU_RADIUS) / 2
            wx = mc + int(wr * math.cos(wa))
            wy = mc - int(wr * math.sin(wa))  # invert y for screen
            lbl = font.render(label, True, color if wi == 0 else (80, 80, 100))
            menu_surf.blit(lbl, (wx - lbl.get_width() // 2, wy - lbl.get_height() // 2))

        # Inner dead zone circle
        pygame.draw.circle(menu_surf, (30, 30, 50, 200), (mc, mc), WEDGE_INNER)

        screen.blit(menu_surf, (menu_center[0] - mc, menu_center[1] - mc))

    # Draw detail panel for inspected point
    if inspected_point_idx is not None:
        # Find screen position of inspected point
        panel_anchor = None
        for p2d, angular_dist, depth, idx in last_projected_points:
            if idx == inspected_point_idx:
                panel_anchor = p2d.astype(int)
                panel_dist = angular_dist
                break

        if panel_anchor is not None:
            name = get_name(inspected_point_idx)
            coords = points[inspected_point_idx]
            audio_info = get_audio_params(int(_name_keys[inspected_point_idx]))

            lines = [
                name,
                f"Dist: {format_dist(panel_dist)}",
                f"4D: ({coords[0]:+.3f}, {coords[1]:+.3f}, {coords[2]:+.3f}, {coords[3]:+.3f})",
                f"Audio: {audio_info['summary']}",
                f"Root: {audio_info['root_hz']} Hz | Tempo: {audio_info['tempo']}",
            ]

            # Measure panel size (including sprite area at top)
            line_height = 16
            padding = 8
            sprite_size = 64
            creature_size = 64
            top_row_h = creature_size
            max_w = max(font.size(line)[0] for line in lines)
            panel_w = max(max_w + padding * 2, creature_size + padding * 3 + sprite_size)
            panel_h = top_row_h + padding * 3 + len(lines) * line_height

            # Position: offset right and above the anchor point
            px = panel_anchor[0] + 20
            py = panel_anchor[1] - panel_h - 10
            # Keep on screen
            if px + panel_w > SCREEN_WIDTH - 300:
                px = panel_anchor[0] - panel_w - 20
            if py < 0:
                py = panel_anchor[1] + 20

            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            pygame.draw.rect(panel_surf, (20, 20, 40, 200), (0, 0, panel_w, panel_h), border_radius=4)
            panel_color = point_display_colors.get(inspected_point_idx, point_colors[inspected_point_idx])
            pygame.draw.rect(panel_surf, (*panel_color, 120), (0, 0, panel_w, panel_h), 1, border_radius=4)

            # Draw rotating planet at top of panel
            point_color = point_display_colors.get(inspected_point_idx, point_colors[inspected_point_idx])
            equirect = get_planet_equirect_hires(inspected_point_idx, _name_keys[inspected_point_idx])
            if equirect is not None:
                rot = get_planet_rotation_angle(inspected_point_idx, elapsed_ms)
                planet_surf = render_planet_frame(equirect, sprite_size, rot, tint_color=point_color)
                panel_surf.blit(planet_surf, (creature_size + padding * 2, padding))

            # Draw large creature sprite in top-left
            large_creature, large_eyes = generate_creature(int(_name_keys[inspected_point_idx]), size=creature_size)
            ident_x = padding
            ident_y = padding
            panel_surf.blit(large_creature, (ident_x, ident_y))

            # Draw text below sprite/identicon area
            text_y = top_row_h + padding * 2
            # Brighten panel_color for title readability (ensure min 150 per channel)
            title_color = tuple(min(255, c + 80) for c in panel_color)
            for li, line in enumerate(lines):
                text_color = title_color if li == 0 else TEXT_COLOR
                lbl = font.render(line, True, text_color)
                panel_surf.blit(lbl, (padding, text_y + li * line_height))

            screen.blit(panel_surf, (px, py))
            draw_creature_eyes(screen, px + ident_x, py + ident_y, creature_size, large_eyes, (mx, my), seed=_name_keys[inspected_point_idx])
        else:
            # Inspected point not visible — keep panel state but skip render
            pass

    # Draw divider line
    pygame.draw.line(
        screen, (100, 100, 100), (SCREEN_WIDTH - 300, 0), (SCREEN_WIDTH - 300, SCREEN_HEIGHT), 2
    )

    # Draw sidebar header
    header = font.render("Nearby Points (Distance)", True, TEXT_COLOR)
    screen.blit(header, (SCREEN_WIDTH - 290, 10))

    # Search field and list header
    search_y = 35

    # Count label
    if search_text:
        count_str = f"POINTS ({len(filtered_indices)}/{len(visible_indices)}) | VISITED ({len(visited_points)})"
    else:
        count_str = f"POINTS ({len(visible_indices)}) | VISITED ({len(visited_points)})"
    count_label = font.render(count_str, True, TEXT_COLOR)
    screen.blit(count_label, (SCREEN_WIDTH - 290, search_y))
    search_y += 16

    # Search field
    search_field_rect = pygame.Rect(SCREEN_WIDTH - 290, search_y, 280, 22)
    if search_active:
        pygame.draw.rect(screen, (40, 70, 90), search_field_rect)
        pygame.draw.rect(screen, (100, 200, 255), search_field_rect, 1)
    else:
        pygame.draw.rect(screen, LIST_ITEM_BG, search_field_rect)
        pygame.draw.rect(screen, (100, 100, 100), search_field_rect, 1)
    display_query = search_text + ("|" if search_active else "")
    search_label = font.render(f"/{display_query}", True, TEXT_COLOR if search_active else (130, 130, 130))
    screen.blit(search_label, (SCREEN_WIDTH - 285, search_y + 5))

    list_start_y = search_y + 28

    # Draw list items
    item_height = 40
    max_items = (SCREEN_HEIGHT - list_start_y) // item_height
    for i in range(max_items):
        item_idx = list_scroll + i
        if item_idx >= len(filtered_indices):
            break

        y = list_start_y + i * item_height
        point_idx = filtered_indices[item_idx]
        dist = filtered_distances[item_idx]
        name = get_name(point_idx)

        # Highlight hovered; dim visited
        if hovered_item == item_idx:
            item_bg = LIST_ITEM_HOVER
        elif point_idx in visited_points:
            item_bg = (50, 50, 70)
        else:
            item_bg = LIST_ITEM_BG
        pygame.draw.rect(screen, item_bg, (SCREEN_WIDTH - 290, y, 290, item_height))

        # Creature sprite from point seed
        creature, creature_eyes = get_creature(point_idx, point_creature_cache, _name_keys[point_idx])
        screen.blit(creature, (SCREEN_WIDTH - 285, y + 4))
        draw_creature_eyes(screen, SCREEN_WIDTH - 285, y + 4, 32, creature_eyes, (mx, my), seed=_name_keys[point_idx])

        # Render name and distance with point's display color
        sidebar_color = point_display_colors.get(point_idx, point_colors[point_idx])
        name_text = font.render(name, True, sidebar_color)
        dist_text = font.render(f"({format_dist(dist)})", True, sidebar_color)
        x_offset = SCREEN_WIDTH - 250
        screen.blit(name_text, (x_offset, y + 12))
        x_offset += name_text.get_width() + 4
        screen.blit(dist_text, (x_offset, y + 12))
        if traveling and point_idx == travel_target_idx:
            x_offset += dist_text.get_width() + 4
            screen.blit(font.render("<", True, SELECTED_COLOR), (x_offset, y + 12))
        elif queued_target_idx is not None and point_idx == queued_target_idx:
            x_offset += dist_text.get_width() + 4
            screen.blit(font.render("<<", True, (150, 150, 255)), (x_offset, y + 12))

    # Draw status and controls
    mode_label = ["Assigned", "4D Position", "XYZ Projection", "XYZ Fixed-Y"][view_mode]
    status = f"Visible: {len(visible_indices)} | View: {mode_label}"
    status_text = font.render(status, True, TEXT_COLOR)
    screen.blit(status_text, (10, 10))

    # Gamepedia overlay
    if gamepedia_open:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 230))
        screen.blit(overlay, (0, 0))

        # Group accent colors
        _gp_group_colors = {
            "Controls": (100, 180, 255),
            "Navigation": (100, 220, 160),
            "World": (220, 180, 100),
            "Audio": (200, 130, 220),
            "4D Geometry": (255, 130, 120),
            "UI": (140, 200, 220),
        }

        # Title
        title_font = pygame.font.Font(None, 28)
        title_surf = title_font.render("GAMEPEDIA", True, (200, 220, 255))
        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 16))

        # Subtle divider under title
        pygame.draw.line(screen, (60, 70, 100), (40, 46), (SCREEN_WIDTH - 40, 46))

        # Layout (uses GP_ constants for left panel)
        left_x = GP_LEFT_X
        left_w = GP_LEFT_W
        right_x = left_x + left_w + 20
        right_w = SCREEN_WIDTH - right_x - 40
        top_y = GP_TOP_Y
        line_h = GP_LINE_H

        # Left panel background
        left_bg = pygame.Surface((left_w + 8, SCREEN_HEIGHT - top_y - 36), pygame.SRCALPHA)
        left_bg.fill((20, 22, 35, 120))
        screen.blit(left_bg, (left_x - 4, top_y))

        # Vertical divider between panels
        pygame.draw.line(screen, (50, 55, 80), (left_x + left_w + 10, top_y), (left_x + left_w + 10, SCREEN_HEIGHT - 36))

        # Left panel: grouped topic list
        y_cursor = top_y
        flat_idx = 0
        for gname, topics in GAMEPEDIA_CONTENT:
            accent = _gp_group_colors.get(gname, (140, 160, 200))
            # Group header with darkened accent bg + bar
            header_bg = (accent[0] // 6 + 10, accent[1] // 6 + 10, accent[2] // 6 + 15)
            pygame.draw.rect(screen, header_bg, (left_x - 4, y_cursor, left_w, line_h))
            pygame.draw.line(screen, accent, (left_x - 4, y_cursor), (left_x - 4, y_cursor + line_h - 1), 3)
            header_surf = font.render(gname.upper(), True, accent)
            screen.blit(header_surf, (left_x + 4, y_cursor + 5))
            y_cursor += line_h
            for title, _text in topics:
                if flat_idx == gamepedia_selected_topic:
                    # Selected: accent-tinted highlight
                    sel_color = (accent[0] // 4 + 20, accent[1] // 4 + 20, accent[2] // 4 + 30)
                    sel_rect = pygame.Rect(left_x - 4, y_cursor, left_w, line_h)
                    pygame.draw.rect(screen, sel_color, sel_rect, border_radius=3)
                    pygame.draw.rect(screen, accent, sel_rect, 1, border_radius=3)
                    color = (255, 255, 255)
                else:
                    color = (180, 180, 200)
                topic_surf = font.render(f"  {title}", True, color)
                screen.blit(topic_surf, (left_x, y_cursor + 4))
                y_cursor += line_h
                flat_idx += 1

        # Right panel: selected topic content
        if 0 <= gamepedia_selected_topic < len(_gamepedia_flat):
            gname, title, text = _gamepedia_flat[gamepedia_selected_topic]
            accent = _gp_group_colors.get(gname, (180, 200, 255))

            # Topic title with accent
            topic_title_font = pygame.font.Font(None, 22)
            tt_surf = topic_title_font.render(title, True, accent)
            group_surf = font.render(f"{gname}  >", True, (100, 110, 140))
            screen.blit(group_surf, (right_x, top_y + 3))
            screen.blit(tt_surf, (right_x + group_surf.get_width() + 6, top_y))
            # Accent underline
            pygame.draw.line(screen, (*accent, 80), (right_x, top_y + 22), (right_x + right_w, top_y + 22))

            # Word-wrapped content
            content_y = top_y + 32
            wrapped = word_wrap_text(text, right_w, font)
            content_line_h = 18
            visible_lines = (SCREEN_HEIGHT - content_y - 36) // content_line_h

            # Clamp scroll
            max_scroll = max(0, len(wrapped) - visible_lines)
            gamepedia_scroll = min(gamepedia_scroll, max_scroll)

            # Tint for emphasis lines (lines that look like "Key  Value" or start with a keyword)
            body_color = (200, 200, 210)
            emphasis_color = (accent[0] // 2 + 100, accent[1] // 2 + 100, accent[2] // 2 + 100)

            for li, line in enumerate(wrapped[gamepedia_scroll:gamepedia_scroll + visible_lines]):
                # Highlight lines that are key-value style (contain multiple consecutive spaces)
                if "  " in line and not line.startswith(" "):
                    # Render key part in accent, value part in body
                    parts = line.split("  ", 1)
                    key_surf = font.render(parts[0], True, emphasis_color)
                    val_surf = font.render("  " + parts[1], True, body_color)
                    screen.blit(key_surf, (right_x, content_y + li * content_line_h))
                    screen.blit(val_surf, (right_x + key_surf.get_width(), content_y + li * content_line_h))
                else:
                    line_surf = font.render(line, True, body_color)
                    screen.blit(line_surf, (right_x, content_y + li * content_line_h))

            # Scroll indicator
            if len(wrapped) > visible_lines:
                indicator = f"[{gamepedia_scroll + 1}-{min(gamepedia_scroll + visible_lines, len(wrapped))}/{len(wrapped)}]"
                ind_surf = font.render(indicator, True, (120, 120, 140))
                screen.blit(ind_surf, (right_x + right_w - ind_surf.get_width(), SCREEN_HEIGHT - 24))

        # Help hint
        hint = font.render("F1/ESC: Close | UP/DOWN: Topics | Scroll: Content", True, (100, 100, 120))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 24))

    pygame.display.flip()

cleanup_audio()
pygame.quit()
