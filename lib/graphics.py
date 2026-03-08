"""Sprite loading, identicon generation, and rendering helpers."""

import os
from io import BytesIO
import pygame
from pydenticon import Generator

# Planet sprites: filename -> pygame.Surface (populated by load_planet_sprites)
planet_sprites = {}


def load_planet_sprites():
    """Load all 10 planet sprites from assets/planets/ directory."""
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
    sprite_idx = (point_idx * 73) % 10
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

    scale_size = max(4, int(2 * radius))
    try:
        scaled_sprite = pygame.transform.scale(sprite, (scale_size, scale_size))

        tinted = scaled_sprite.copy()
        color_surf = pygame.Surface((scale_size, scale_size))
        color_surf.fill(color)
        color_surf.set_colorkey((0, 0, 0))
        tinted.blit(color_surf, (0, 0), special_flags=pygame.BLEND_MULT)

        draw_pos = (int(p2d[0]) - scale_size // 2, int(p2d[1]) - scale_size // 2)
        screen.blit(tinted, draw_pos)
        return True
    except Exception as e:
        print(f"ERROR rendering sprite: {e}")
        return False


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


def get_identicon(idx, cache, name, color):
    """Get or generate identicon for a point, with lazy caching.

    Args:
        idx: Point index
        cache: Dict mapping idx -> pygame.Surface (read/written by this function)
        name: Point name string
        color: (r, g, b) tuple for the point
    """
    if idx not in cache:
        r, g, b = color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        generator = Generator(12, 12, foreground=[hex_color], background="#000000")
        png_bytes = generator.generate(name, 24, 24, inverted=False)
        identicon_surface = pygame.image.load(BytesIO(png_bytes))
        identicon_with_margin = pygame.Surface((32, 32))
        identicon_with_margin.fill((0, 0, 0))
        identicon_with_margin.blit(identicon_surface, (4, 4))
        cache[idx] = identicon_with_margin
    return cache[idx]
