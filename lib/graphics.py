"""Identicon generation and rendering helpers."""

from io import BytesIO
import pygame
from pydenticon import Generator


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
