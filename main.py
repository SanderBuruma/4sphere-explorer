import pygame
import numpy as np
import math
from collections import deque
from io import BytesIO
from pydenticon import Generator
from audio import init_audio, update_audio, cleanup_audio, get_audio_params
from sphere import (
    random_point_on_s3,
    angular_distance,
    visible_points,
    build_visibility_kdtree,
    query_visible_kdtree,
    tangent_basis,
    rotate_frame,
    reorthogonalize_frame,
    project_to_tangent,
    project_tangent_to_screen,
    slerp,
    random_color,
    decode_name,
    TOTAL_NAMES,
)

pygame.mixer.pre_init(44100, -16, 2)
pygame.init()
init_audio()

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("4-Sphere Explorer")

# Generate window icon from game name
icon_generator = Generator(8, 8, foreground=["#3498db", "#e74c3c", "#2ecc71"], background="#000000")
icon_bytes = icon_generator.generate("4-Sphere", 64, 64, inverted=False)
icon_surface = pygame.image.load(BytesIO(icon_bytes))
pygame.display.set_icon(icon_surface)

clock = pygame.time.Clock()
font = pygame.font.Font(None, 14)
start_time = pygame.time.get_ticks()  # milliseconds since pygame init

# Colors
BG_COLOR = (20, 20, 30)
POINT_COLOR = (200, 200, 255)
CAMERA_COLOR = (255, 100, 100)
SELECTED_COLOR = (255, 255, 100)
TEXT_COLOR = (200, 200, 200)
LIST_BG = (40, 40, 60)
LIST_ITEM_BG = (60, 60, 90)
LIST_ITEM_HOVER = (80, 80, 120)

# Game state
NUM_POINTS = 30_000
FOV_ANGLE = 0.116  # radians, tuned for ~10 visible points
GAME_SEED = 42
ARRIVAL_THRESHOLD = 0.0005  # radians (0.5 mrad) — snap to target when this close
CAMERA_OFFSET = 0.08  # radians — camera orbital distance from player
ROTATION_SPEED = 0.02  # radians per frame for WASD/QE
TRAVEL_SPEED = 0.000008  # slerp progress per frame
POP_DURATION = 400  # milliseconds for arrival pop animation
TRIANGLE_PERIOD = 6000.0  # milliseconds for one full triangle rotation

# Starfield: random 4D directions for parallax background
NUM_STARS = 200
_star_rng = np.random.default_rng(seed=123)
_star_dirs = _star_rng.standard_normal((NUM_STARS, 4))
_star_dirs /= np.linalg.norm(_star_dirs, axis=1, keepdims=True)
_star_brightness = _star_rng.uniform(0.15, 0.6, NUM_STARS)
_star_sizes = _star_rng.choice([1, 1, 1, 2], NUM_STARS)

# Distance color mapping: green (near) -> yellow (mid) -> red (far)
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
point_identicon_cache = {}

def get_identicon(idx):
    """Get or generate identicon for a point, with lazy caching."""
    if idx not in point_identicon_cache:
        name = get_name(idx)
        r, g, b = point_colors[idx]
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        generator = Generator(12, 12, foreground=[hex_color], background="#000000")
        png_bytes = generator.generate(name, 24, 24, inverted=False)
        identicon_surface = pygame.image.load(BytesIO(png_bytes))
        identicon_with_margin = pygame.Surface((32, 32))
        identicon_with_margin.fill((0, 0, 0))
        identicon_with_margin.blit(identicon_surface, (4, 4))
        point_identicon_cache[idx] = identicon_with_margin
    return point_identicon_cache[idx]

def draw_googly_eyes(surface, x, y, mouse_pos, scale=1):
    """Draw googly eyes on top of an identicon at screen pos (x, y). scale=1 for 32px, scale=4 for 128px."""
    eye_radius = 4 * scale
    pupil_radius = 2 * scale
    eye_y = y + 10 * scale
    left_eye_x = x + 10 * scale
    right_eye_x = x + 22 * scale
    max_offset = eye_radius - pupil_radius

    for ex in (left_eye_x, right_eye_x):
        pygame.draw.circle(surface, (255, 255, 255), (ex, eye_y), eye_radius)
        dx = mouse_pos[0] - ex
        dy = mouse_pos[1] - eye_y
        dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
        ox = int(dx / dist * max_offset)
        oy = int(dy / dist * max_offset)
        pygame.draw.circle(surface, (0, 0, 0), (ex + ox, eye_y + oy), pupil_radius)

# Planet sprite loader
planet_sprites = {}  # filename -> pygame.Surface

def load_planet_sprites():
    """Load all 10 planet sprites from assets/planets/ directory."""
    import os
    planet_dir = "assets/planets"
    if not os.path.isdir(planet_dir):
        print(f"WARNING: Planet directory not found at {planet_dir}")
        return False

    planet_files = [f"planet_{i:02d}.png" for i in range(1, 11)]
    loaded_count = 0

    for filename in planet_files:
        filepath = os.path.join(planet_dir, filename)
        try:
            if os.path.exists(filepath):
                img = pygame.image.load(filepath)
                planet_sprites[filename] = img
                loaded_count += 1
            else:
                print(f"WARNING: {filename} not found at {filepath}")
        except Exception as e:
            print(f"ERROR loading {filename}: {e}")

    success = loaded_count == len(planet_files)
    print(f"Loaded {loaded_count}/{len(planet_files)} planet sprites")
    return success

def get_planet_sprite(point_idx):
    """Get a planet sprite for a point, deterministically based on its index.

    Args:
        point_idx: Point index (0 to NUM_POINTS-1)

    Returns:
        pygame.Surface or None if sprites not loaded
    """
    if not planet_sprites:
        return None
    # Hash-based selection: deterministic mapping of point to sprite
    sprite_idx = (point_idx * 73) % 10  # Use prime multiplier for distribution
    filename = f"planet_{sprite_idx + 1:02d}.png"
    return planet_sprites.get(filename)

def render_point_sprite(screen, sprite, p2d, radius, color):
    """Render a colorized planet sprite at screen position.

    Args:
        screen: pygame.Surface to draw to
        sprite: pygame.Surface sprite to render
        p2d: (x, y) screen position
        radius: Approximate sprite size (will scale sprite to ~2*radius)
        color: (r, g, b) color to multiply sprite by
    """
    if sprite is None:
        return False

    # Scale sprite to match desired radius (sprite is 64x64)
    scale_size = max(4, int(2 * radius))
    try:
        scaled_sprite = pygame.transform.scale(sprite, (scale_size, scale_size))

        # Colorize by multiplying the sprite colors
        # Create a new surface with the color tint applied
        tinted = scaled_sprite.copy()
        # Use a color surface to multiply
        color_surf = pygame.Surface((scale_size, scale_size))
        color_surf.fill(color)
        color_surf.set_colorkey((0, 0, 0))
        tinted.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)

        # Draw at position
        draw_pos = (int(p2d[0]) - scale_size // 2, int(p2d[1]) - scale_size // 2)
        screen.blit(tinted, draw_pos)
        return True
    except Exception as e:
        print(f"ERROR rendering sprite: {e}")
        return False

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
HOLD_THRESHOLD = 200  # ms before radial menu opens
MENU_RADIUS = 50  # pixel radius of radial menu
WEDGE_INNER = 15  # inner dead zone radius
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
view_mode = 0  # 0 = assigned colors, 1 = relative 4D position colors
last_projected_points = []  # store for click detection
list_start_y = 100  # Y coordinate where point list items begin (updated each frame)

# Search/filter state
search_text = ""
search_active = False


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

# Bookmark system: list of (player_pos, orientation, name) tuples
bookmarks = []


def save_bookmark(name_str=None):
    """Save current position and orientation as a bookmark."""
    global bookmarks
    if name_str is None:
        name_str = f"Bookmark {len(bookmarks) + 1}"
    bookmark = (player_pos.copy(), orientation.copy(), name_str)
    bookmarks.append(bookmark)


def restore_bookmark(bookmark_idx):
    """Restore player position and orientation from a saved bookmark."""
    global player_pos, orientation, camera_pos, traveling, travel_target, travel_target_idx
    if 0 <= bookmark_idx < len(bookmarks):
        pos, frame, name = bookmarks[bookmark_idx]
        player_pos = pos.copy()
        orientation = frame.copy()
        camera_pos = orientation[0]
        traveling = False
        travel_target = None
        travel_target_idx = None
        update_visible()


# Precompute visible points and distances
def update_visible():
    global visible_indices, visible_distances, point_identicon_cache
    prev_set = set(visible_indices)  # cache state before update

    # Use KDTree for sub-linear visibility query
    vis_points, indices = query_visible_kdtree(visibility_kdtree, player_pos, points, FOV_ANGLE)
    distances = [angular_distance(player_pos, points[i]) for i in indices]
    sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
    visible_indices = [p[0] for p in sorted_pairs]
    visible_distances = [p[1] for p in sorted_pairs]

    # Evict caches for points no longer visible
    new_set = set(visible_indices)
    for idx in prev_set - new_set:
        point_identicon_cache.pop(idx, None)
        point_name_cache.pop(idx, None)


update_visible()
load_planet_sprites()

running = True
while running:
    clock.tick(60)

    # Handle input
    keys = pygame.key.get_pressed()

    # Camera rotation via persistent orientation frame
    rotation_speed = ROTATION_SPEED
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
            if search_active:
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
                    view_mode = 1 - view_mode  # toggle 0/1
                elif event.key == pygame.K_b:
                    save_bookmark()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    restore_bookmark(event.key - pygame.K_1)
                elif event.key == pygame.K_SLASH or event.key == pygame.K_f:
                    search_active = True
                    search_text = ""
                elif event.key == pygame.K_TAB:
                    auto_travel_to_nearest_unvisited()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
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
        elif event.type == pygame.MOUSEBUTTONUP:
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
        elif event.type == pygame.MOUSEMOTION:
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

    # Project visible points into camera's tangent space
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

    # Check mouse position for hover tooltip
    mx, my = pygame.mouse.get_pos()
    hover_point = None
    hover_dist_sq_min = float("inf")

    # Store computed display colors per point for reuse in tooltip/panel/sidebar
    point_display_colors = {}

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

            # Try to render sprite; fall back to circle if sprite not available
            sprite = get_planet_sprite(idx)
            if sprite and render_point_sprite(screen, sprite, p2d, radius, color):
                pass  # Sprite rendered successfully
            else:
                # Fallback to circle if sprite missing
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
                    center_x = p2d[0] + arrow_distance * np.cos(angle)
                    center_y = p2d[1] + arrow_distance * np.sin(angle)

                    # Triangle points inward toward the target
                    # Tip points toward center of target
                    tip_x = center_x - triangle_size * np.cos(angle)
                    tip_y = center_y - triangle_size * np.sin(angle)

                    # Two base points perpendicular to the radial direction
                    perp_x = -np.sin(angle)
                    perp_y = np.cos(angle)
                    base_left_x = center_x + perp_x * triangle_size * 0.7
                    base_left_y = center_y + perp_y * triangle_size * 0.7
                    base_right_x = center_x - perp_x * triangle_size * 0.7
                    base_right_y = center_y - perp_y * triangle_size * 0.7

                    tri_verts = [
                        (int(tip_x), int(tip_y)),
                        (int(base_left_x), int(base_left_y)),
                        (int(base_right_x), int(base_right_y))
                    ]
                    pygame.draw.polygon(screen, (100, 150, 255), tri_verts)
                break

    # Draw player position dot at center of view area
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
        identicon = get_identicon(h_idx)

        # Total width: identicon (32px) + gap (4px) + label
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

        # Draw identicon and label
        ident_y = ty + (tooltip_height - 32) // 2
        screen.blit(identicon, (tx, ident_y))
        draw_googly_eyes(screen, tx, ident_y, pygame.mouse.get_pos())
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
            identicon_size = 64
            top_row_h = identicon_size
            max_w = max(font.size(line)[0] for line in lines)
            panel_w = max(max_w + padding * 2, identicon_size + padding * 3 + sprite_size)
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

            # Draw large sprite at top of panel
            sprite = get_planet_sprite(inspected_point_idx)
            if sprite is not None:
                scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))

                # Use same color as 3D view (hue from point, brightness from distance)
                point_color = point_display_colors.get(inspected_point_idx, point_colors[inspected_point_idx])

                # Colorize sprite using BLEND_MULT (same method as 3D viewport)
                colorized = scaled_sprite.copy()
                color_surf = pygame.Surface((sprite_size, sprite_size))
                color_surf.fill(point_color)
                color_surf.set_colorkey((0, 0, 0))
                colorized.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)

                # Apply random rotation and mirroring based on point hash
                sprite_seed = (inspected_point_idx * 73) % 360  # Deterministic rotation per point
                rotation_angle = sprite_seed % 360
                should_flip = (inspected_point_idx * 157) % 2 == 0  # Deterministic 50% flip per point

                # Apply transformations
                rotated = pygame.transform.rotate(colorized, rotation_angle)
                if should_flip:
                    rotated = pygame.transform.flip(rotated, True, False)

                # Center the rotated sprite (may be larger due to rotation)
                rotated_rect = rotated.get_rect(center=(sprite_size // 2, sprite_size // 2))
                sprite_display = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                sprite_display.blit(rotated, rotated_rect)

                sprite_x = identicon_size + padding * 2
                panel_surf.blit(sprite_display, (sprite_x, padding))

            # Draw large identicon in top-left with googly eyes
            large_identicon = pygame.transform.scale(get_identicon(inspected_point_idx), (identicon_size, identicon_size))
            ident_x = padding
            ident_y = padding
            panel_surf.blit(large_identicon, (ident_x, ident_y))

            # Draw text below sprite/identicon area
            text_y = top_row_h + padding * 2
            # Brighten panel_color for title readability (ensure min 150 per channel)
            title_color = tuple(min(255, c + 80) for c in panel_color)
            for li, line in enumerate(lines):
                text_color = title_color if li == 0 else TEXT_COLOR
                lbl = font.render(line, True, text_color)
                panel_surf.blit(lbl, (padding, text_y + li * line_height))

            screen.blit(panel_surf, (px, py))

            # Googly eyes on the large identicon
            draw_googly_eyes(screen, px + padding, py + ident_y, pygame.mouse.get_pos(), scale=2)
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

    # Draw bookmark section
    bm_y = 35
    pygame.draw.line(screen, (100, 100, 120), (SCREEN_WIDTH - 300, bm_y), (SCREEN_WIDTH, bm_y))
    bm_label = font.render("BOOKMARKS  B=save  1-5=restore", True, (160, 160, 200))
    screen.blit(bm_label, (SCREEN_WIDTH - 290, bm_y + 5))
    bm_y += 24
    for bm_i, (_, _, bm_name) in enumerate(bookmarks[:5]):
        bm_rect = pygame.Rect(SCREEN_WIDTH - 290, bm_y, 280, 22)
        pygame.draw.rect(screen, LIST_ITEM_BG, bm_rect)
        bm_text = font.render(f"{bm_i + 1}: {bm_name}", True, TEXT_COLOR)
        screen.blit(bm_text, (SCREEN_WIDTH - 283, bm_y + 5))
        bm_y += 24
    pygame.draw.line(screen, (100, 100, 120), (SCREEN_WIDTH - 300, bm_y + 4), (SCREEN_WIDTH, bm_y + 4))

    # Search field and list header (between bookmark divider and point list)
    search_y = bm_y + 8

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

        # Identicon from point name
        identicon = get_identicon(point_idx)
        screen.blit(identicon, (SCREEN_WIDTH - 285, y + 4))
        draw_googly_eyes(screen, SCREEN_WIDTH - 285, y + 4, pygame.mouse.get_pos())

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
    mode_label = "Assigned" if view_mode == 0 else "4D Position"
    status = f"Visible: {len(visible_indices)} | View: {mode_label}"
    status_text = font.render(status, True, TEXT_COLOR)
    screen.blit(status_text, (10, 10))

    controls = [
        "WASD: Rotate camera | Q/E: Rotate 4D depth | Drag: Rotate camera",
        "UP/DOWN: Scroll list | Click: Travel | Tab: Auto-travel unvisited | V: Toggle view",
    ]
    for i, ctrl in enumerate(controls):
        ctrl_text = font.render(ctrl, True, (150, 150, 150))
        screen.blit(ctrl_text, (10, 30 + i * 20))

    pygame.display.flip()

cleanup_audio()
pygame.quit()
