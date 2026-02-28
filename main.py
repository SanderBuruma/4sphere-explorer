import pygame
import numpy as np
from io import BytesIO
from pydenticon import Generator
from sphere import (
    random_point_on_s3,
    angular_distance,
    visible_points,
    tangent_basis,
    project_to_tangent,
    project_tangent_to_screen,
    slerp,
    random_color,
    decode_name,
    TOTAL_NAMES,
)

pygame.init()

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
_t = 0.08  # camera distance from player (tuned for narrower FOV)
camera_pos = np.array([np.cos(_t), 0.0, np.sin(_t), 0.0])
points = random_point_on_s3(NUM_POINTS)

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

traveling = False
travel_target = None
travel_target_idx = None
travel_progress = 0.0
travel_speed = 0.000008  # per frame, 5x slower than before
queued_target = None
queued_target_idx = None
pop_animation_idx = None
pop_animation_start_time = None

# UI state
list_scroll = 0
visible_indices = []
visible_distances = []
hovered_item = None
view_mode = 0  # 0 = assigned colors, 1 = relative 4D position colors
last_projected_points = []  # store for click detection
dragging = False
drag_start = None

# Precompute visible points and distances
def update_visible():
    global visible_indices, visible_distances, point_identicon_cache
    prev_set = set(visible_indices)  # cache state before update
    vis_points, indices = visible_points(player_pos, points, FOV_ANGLE)
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

running = True
while running:
    clock.tick(60)

    # Handle input
    keys = pygame.key.get_pressed()

    # Camera rotation (6 degrees of freedom in 4D)
    rotation_speed = 0.02
    if keys[pygame.K_w]:  # rotate in xy plane
        angle = rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[1],
            sin_a * camera_pos[0] + cos_a * camera_pos[1],
            camera_pos[2],
            camera_pos[3]
        ])
    if keys[pygame.K_s]:  # rotate in xy plane (opposite)
        angle = -rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[1],
            sin_a * camera_pos[0] + cos_a * camera_pos[1],
            camera_pos[2],
            camera_pos[3]
        ])
    if keys[pygame.K_a]:  # rotate in xz plane
        angle = rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[2],
            camera_pos[1],
            sin_a * camera_pos[0] + cos_a * camera_pos[2],
            camera_pos[3]
        ])
    if keys[pygame.K_d]:  # rotate in xz plane (opposite)
        angle = -rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[2],
            camera_pos[1],
            sin_a * camera_pos[0] + cos_a * camera_pos[2],
            camera_pos[3]
        ])
    if keys[pygame.K_q]:  # rotate in xw plane
        angle = rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[3],
            camera_pos[1],
            camera_pos[2],
            sin_a * camera_pos[0] + cos_a * camera_pos[3]
        ])
    if keys[pygame.K_e]:  # rotate in xw plane (opposite)
        angle = -rotation_speed
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        camera_pos = np.array([
            cos_a * camera_pos[0] - sin_a * camera_pos[3],
            camera_pos[1],
            camera_pos[2],
            sin_a * camera_pos[0] + cos_a * camera_pos[3]
        ])

    # Handle drag rotation
    if dragging and drag_start is not None:
        mx, my = pygame.mouse.get_pos()
        dx = (mx - drag_start[0]) * 0.005  # horizontal drag → xy rotation
        dy = (my - drag_start[1]) * 0.005  # vertical drag → xz rotation

        # Apply rotation in xy plane from horizontal drag
        if abs(dx) > 1e-6:
            cos_a, sin_a = np.cos(dx), np.sin(dx)
            camera_pos = np.array([
                cos_a * camera_pos[0] - sin_a * camera_pos[1],
                sin_a * camera_pos[0] + cos_a * camera_pos[1],
                camera_pos[2],
                camera_pos[3]
            ])

        # Apply rotation in xz plane from vertical drag
        if abs(dy) > 1e-6:
            cos_a, sin_a = np.cos(dy), np.sin(dy)
            camera_pos = np.array([
                cos_a * camera_pos[0] - sin_a * camera_pos[2],
                camera_pos[1],
                sin_a * camera_pos[0] + cos_a * camera_pos[2],
                camera_pos[3]
            ])

    camera_pos /= np.linalg.norm(camera_pos)
    update_visible()

    # List scrolling
    item_height = 40
    max_items = (SCREEN_HEIGHT - 100) // item_height
    if keys[pygame.K_UP]:
        list_scroll = max(0, list_scroll - 1)
    if keys[pygame.K_DOWN]:
        list_scroll = min(max(0, len(visible_indices) - max_items), list_scroll + 1)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_v:
                view_mode = 1 - view_mode  # toggle 0/1
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mx, my = event.pos
                dragging = True
                drag_start = (mx, my)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click release
                if dragging and drag_start is not None:
                    # Only trigger click-to-travel if drag distance was minimal
                    mx, my = event.pos
                    drag_dist_sq = (mx - drag_start[0]) ** 2 + (my - drag_start[1]) ** 2
                    if drag_dist_sq < 100:  # within 10px threshold
                        # Resolve clicked point index
                        clicked_idx = None
                        if mx > SCREEN_WIDTH - 300:
                            item_idx = (my - 100) // 40 + list_scroll
                            if 0 <= item_idx < len(visible_indices):
                                clicked_idx = visible_indices[item_idx]
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
                dragging = False
                drag_start = None
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if not dragging and mx > SCREEN_WIDTH - 300:
                item_idx = (my - 100) // 40 + list_scroll
                hovered_item = item_idx if 0 <= item_idx < len(visible_indices) else None
            elif dragging:
                hovered_item = None

    # Update travel
    if traveling and travel_target is not None:
        travel_progress += travel_speed
        old_player = player_pos.copy()
        player_pos = slerp(player_pos, travel_target, min(travel_progress, 1.0))
        camera_pos = (camera_pos + (player_pos - old_player))
        camera_pos /= np.linalg.norm(camera_pos)

        # Complete travel at proximity threshold (snap to target)
        if angular_distance(player_pos, travel_target) < 0.02:
            old_player = player_pos.copy()
            player_pos = travel_target / np.linalg.norm(travel_target)
            camera_pos = (camera_pos + (player_pos - old_player))
            camera_pos /= np.linalg.norm(camera_pos)
            pop_animation_idx = travel_target_idx
            pop_animation_start_time = pygame.time.get_ticks()

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

    # Project visible points into camera's tangent space
    view_width = SCREEN_WIDTH - 300
    basis = tangent_basis(camera_pos)
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

            brightness_factor = 0.3 + normalized_dist * 0.7
            color = tuple(int(c * brightness_factor) for c in base_color)
            pygame.draw.circle(screen, color, p2d.astype(int), radius)

            # Check if mouse is near this point (within radius + margin)
            dx, dy = mx - p2d[0], my - p2d[1]
            dist_sq = dx * dx + dy * dy
            hit_radius = max(radius + 6, 10)
            if dist_sq < hit_radius * hit_radius and dist_sq < hover_dist_sq_min:
                hover_dist_sq_min = dist_sq
                hover_point = (p2d, angular_dist, idx)

    # Draw white circle around hovered list item point
    if hovered_item is not None and 0 <= hovered_item < len(visible_indices):
        hovered_point_idx = visible_indices[hovered_item]
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
        pop_duration = 400  # milliseconds
        if elapsed_pop >= pop_duration:
            pop_animation_idx = None
            pop_animation_start_time = None
        else:
            progress = elapsed_pop / pop_duration
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

    # Draw rotating blue triangles around travel target (hide once pop starts)
    if traveling and travel_target_idx is not None and pop_animation_idx is None:
        for p2d, angular_dist, depth, idx in projected_points:
            if idx == travel_target_idx:
                elapsed_ms = pygame.time.get_ticks() - start_time
                rotation_angle = (elapsed_ms / 6000.0) * 2 * np.pi  # Full rotation every 6 seconds (3x slower)
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

    # Draw camera position crosshair at center of view area
    center_x, center_y = view_width // 2, SCREEN_HEIGHT // 2
    crosshair_radius = 12
    crosshair_size = 8

    # Hollow circle
    pygame.draw.circle(screen, CAMERA_COLOR, (center_x, center_y), crosshair_radius, 2)

    # Crosshair lines (+ shape)
    pygame.draw.line(screen, CAMERA_COLOR, (center_x - crosshair_size, center_y), (center_x + crosshair_size, center_y), 2)
    pygame.draw.line(screen, CAMERA_COLOR, (center_x, center_y - crosshair_size), (center_x, center_y + crosshair_size), 2)

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
        pygame.draw.rect(screen, point_colors[h_idx], bg_rect, 1)

        # Draw identicon and label
        screen.blit(identicon, (tx, ty + (tooltip_height - 32) // 2))
        screen.blit(label_surface, (tx + 32 + 4, ty + (tooltip_height - label_rect.height) // 2))

    # Draw divider line
    pygame.draw.line(
        screen, (100, 100, 100), (SCREEN_WIDTH - 300, 0), (SCREEN_WIDTH - 300, SCREEN_HEIGHT), 2
    )

    # Draw list header
    header = font.render("Nearby Points (Distance)", True, TEXT_COLOR)
    screen.blit(header, (SCREEN_WIDTH - 290, 10))

    # Draw list items
    item_height = 40
    max_items = (SCREEN_HEIGHT - 100) // item_height
    for i in range(max_items):
        item_idx = list_scroll + i
        if item_idx >= len(visible_indices):
            break

        y = 100 + i * item_height
        point_idx = visible_indices[item_idx]
        dist = visible_distances[item_idx]
        name = get_name(point_idx)
        label = f"{name} ({dist:.2f})"

        # Highlight hovered
        item_bg = LIST_ITEM_HOVER if hovered_item == item_idx else LIST_ITEM_BG
        pygame.draw.rect(screen, item_bg, (SCREEN_WIDTH - 290, y, 290, item_height))

        # Identicon from point name
        identicon = get_identicon(point_idx)
        screen.blit(identicon, (SCREEN_WIDTH - 285, y + 4))

        # Render name and distance separately with distance colored by gradient
        name_text = font.render(name, True, TEXT_COLOR)
        dist_color = distance_to_color(dist)
        dist_text = font.render(f"({format_dist(dist)})", True, dist_color)
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
        "WASD: Rotate XY/XZ planes | Q/E: Rotate XW plane | Drag: Rotate camera",
        "UP/DOWN: Scroll list | Click: Travel to point | V: Toggle view",
    ]
    for i, ctrl in enumerate(controls):
        ctrl_text = font.render(ctrl, True, (150, 150, 150))
        screen.blit(ctrl_text, (10, 30 + i * 20))

    pygame.display.flip()

pygame.quit()
