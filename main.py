import pygame
import numpy as np
from sphere import (
    random_point_on_s3,
    angular_distance,
    visible_points,
    tangent_basis,
    project_to_tangent,
    project_tangent_to_screen,
    slerp,
    random_color,
    generate_futuristic_name,
)

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("4-Sphere Explorer")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 14)

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
NUM_POINTS = 300
FOV_ANGLE = np.pi / 2  # 90 degrees

camera_pos = np.array([1.0, 0.0, 0.0, 0.0])
points = random_point_on_s3(NUM_POINTS)

# Generate unique names
point_names = set()
while len(point_names) < NUM_POINTS:
    point_names.add(generate_futuristic_name())
point_names = list(point_names)

point_colors = random_color(NUM_POINTS)  # Assign random colors
traveling = False
travel_target = None
travel_progress = 0.0
travel_speed = 0.0002  # per frame

# UI state
list_scroll = 0
visible_indices = []
visible_distances = []
hovered_item = None
view_mode = 0  # 0 = assigned colors, 1 = relative 4D position colors
last_projected_points = []  # store for click detection

# Precompute visible points and distances
def update_visible():
    global visible_indices, visible_distances
    vis_points, indices = visible_points(camera_pos, points, FOV_ANGLE)
    distances = [angular_distance(camera_pos, points[i]) for i in indices]
    sorted_pairs = sorted(zip(indices, distances), key=lambda x: x[1])
    visible_indices = [p[0] for p in sorted_pairs]
    visible_distances = [p[1] for p in sorted_pairs]


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

    camera_pos /= np.linalg.norm(camera_pos)
    update_visible()

    # List scrolling
    if keys[pygame.K_UP]:
        list_scroll = max(0, list_scroll - 1)
    if keys[pygame.K_DOWN]:
        list_scroll = min(max(0, len(visible_indices) - 10), list_scroll + 1)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_v:
                view_mode = 1 - view_mode  # toggle 0/1
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mx, my = event.pos
                if mx > SCREEN_WIDTH - 300:
                    # Click in list area
                    item_idx = (my - 100) // 25 + list_scroll
                    if 0 <= item_idx < len(visible_indices):
                        travel_target = points[visible_indices[item_idx]]
                        traveling = True
                        travel_progress = 0.0
                elif last_projected_points:
                    # Click in visual area — find nearest point
                    best_dist_sq = float("inf")
                    best_idx = None
                    for p2d, ang, dep, idx in last_projected_points:
                        dx, dy = mx - p2d[0], my - p2d[1]
                        d_sq = dx * dx + dy * dy
                        if d_sq < best_dist_sq:
                            best_dist_sq = d_sq
                            best_idx = idx
                    if best_idx is not None and best_dist_sq < 400:  # within 20px
                        travel_target = points[best_idx]
                        traveling = True
                        travel_progress = 0.0
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if mx > SCREEN_WIDTH - 300:
                item_idx = (my - 100) // 25 + list_scroll
                hovered_item = item_idx if 0 <= item_idx < len(visible_indices) else None

    # Update travel
    if traveling and travel_target is not None:
        travel_progress += travel_speed
        if travel_progress >= 1.0:
            camera_pos = travel_target / np.linalg.norm(travel_target)
            traveling = False
            travel_target = None
            update_visible()
        else:
            camera_pos = slerp(camera_pos, travel_target, travel_progress)

    # Render
    screen.fill(BG_COLOR)

    # Project visible points into camera's tangent space
    view_width = SCREEN_WIDTH - 300
    basis = tangent_basis(camera_pos)

    projected_points = []
    for i, idx in enumerate(visible_indices):
        p4d = points[idx]
        tangent_xyz = project_to_tangent(camera_pos, p4d, basis)
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
                # Color from relative 4D position (point - camera)
                rel = points[idx] - camera_pos
                # Map xyzw to RGB: x→R, y→G, z→B, w modulates brightness
                r = int(np.clip((rel[0] + 1.0) * 127.5, 0, 255))
                g = int(np.clip((rel[1] + 1.0) * 127.5, 0, 255))
                b = int(np.clip((rel[2] + 1.0) * 127.5, 0, 255))
                w_factor = 0.5 + 0.5 * np.clip((rel[3] + 1.0) / 2.0, 0, 1)  # 0.5-1.0
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
        name = point_names[h_idx]
        label = f"{name} ({h_dist:.2f} rad)"
        label_surface = font.render(label, True, TEXT_COLOR)
        label_rect = label_surface.get_rect()

        # Position tooltip above and to the right of cursor
        tx = int(hp2d[0]) + 12
        ty = int(hp2d[1]) - 20

        # Keep tooltip on screen
        if tx + label_rect.width > view_width:
            tx = int(hp2d[0]) - label_rect.width - 12
        if ty < 0:
            ty = int(hp2d[1]) + 12

        # Background
        padding = 4
        bg_rect = pygame.Rect(tx - padding, ty - padding, label_rect.width + padding * 2, label_rect.height + padding * 2)
        pygame.draw.rect(screen, (30, 30, 50), bg_rect)
        pygame.draw.rect(screen, point_colors[h_idx], bg_rect, 1)
        screen.blit(label_surface, (tx, ty))

    # Draw divider line
    pygame.draw.line(
        screen, (100, 100, 100), (SCREEN_WIDTH - 300, 0), (SCREEN_WIDTH - 300, SCREEN_HEIGHT), 2
    )

    # Draw list header
    header = font.render("Nearby Points (Distance)", True, TEXT_COLOR)
    screen.blit(header, (SCREEN_WIDTH - 290, 10))

    # Draw list items
    for i in range(10):
        item_idx = list_scroll + i
        if item_idx >= len(visible_indices):
            break

        y = 100 + i * 25
        point_idx = visible_indices[item_idx]
        dist = visible_distances[item_idx]
        name = point_names[point_idx]
        label = f"{name} ({dist:.2f})"

        # Highlight hovered
        item_bg = LIST_ITEM_HOVER if hovered_item == item_idx else LIST_ITEM_BG
        pygame.draw.rect(screen, item_bg, (SCREEN_WIDTH - 290, y, 290, 24))

        # Color swatch
        color_swatch = point_colors[point_idx]
        pygame.draw.rect(screen, color_swatch, (SCREEN_WIDTH - 285, y + 4, 14, 16))

        text = font.render(label, True, TEXT_COLOR)
        screen.blit(text, (SCREEN_WIDTH - 265, y + 5))

    # Draw status and controls
    mode_label = "Assigned" if view_mode == 0 else "4D Position"
    status = f"Visible: {len(visible_indices)} | View: {mode_label}"
    status_text = font.render(status, True, TEXT_COLOR)
    screen.blit(status_text, (10, 10))

    controls = [
        "WASD: Rotate XY/XZ planes | Q/E: Rotate XW plane",
        "UP/DOWN: Scroll list | Click: Travel to point | V: Toggle view",
    ]
    for i, ctrl in enumerate(controls):
        ctrl_text = font.render(ctrl, True, (150, 150, 150))
        screen.blit(ctrl_text, (10, 30 + i * 20))

    pygame.display.flip()

pygame.quit()
