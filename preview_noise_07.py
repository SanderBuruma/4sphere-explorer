#!/usr/bin/env python3
"""Procedural planet preview — live rotation demo.

Shows planets at multiple sizes, spinning in real-time.
A/D to cycle seeds, ESC to quit.
"""

import os
os.environ['SDL_VIDEO_WINDOW_POS'] = '0,100'
import pygame
from lib.planets import (
    generate_equirect_texture, render_planet_frame,
    get_planet_rotation_angle, GRADIENT_NAMES, GRADIENTS,
    ROTATION_PERIOD_MS,
)


def main():
    pygame.init()
    pygame.display.set_caption("Planet Preview: Rotating")
    screen = pygame.display.set_mode((700, 340))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)
    small_font = pygame.font.SysFont("monospace", 14)

    seed = 0
    cached_seed = None
    equirect = None

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_d:
                    seed += 1
                elif ev.key == pygame.K_a:
                    seed = max(0, seed - 1)

        if seed != cached_seed:
            cached_seed = seed
            equirect = generate_equirect_texture(seed)

        screen.fill((0, 0, 0))

        ms = pygame.time.get_ticks()
        rot = get_planet_rotation_angle(seed, ms)

        y_center = 180
        x = 20

        # 64px
        surf64 = render_planet_frame(equirect, 64, rot)
        screen.blit(surf64, (x, y_center - 32))
        label = small_font.render("64x64", True, (160, 160, 160))
        screen.blit(label, (x + 32 - label.get_width() // 2, y_center + 40))
        x += 64 + 20

        # 128px
        surf128 = render_planet_frame(equirect, 128, rot)
        screen.blit(surf128, (x, y_center - 64))
        label = small_font.render("128x128", True, (160, 160, 160))
        screen.blit(label, (x + 64 - label.get_width() // 2, y_center + 72))
        x += 128 + 20

        # 256px
        surf256 = render_planet_frame(equirect, 256, rot)
        screen.blit(surf256, (x, y_center - 128))
        label = small_font.render("256x256", True, (160, 160, 160))
        screen.blit(label, (x + 128 - label.get_width() // 2, y_center + 132))

        seed_text = font.render(f"Seed: {seed}", True, (255, 255, 255))
        screen.blit(seed_text, (20, 12))

        hint = small_font.render("A/D: change seed   ESC: quit", True, (120, 120, 120))
        screen.blit(hint, (20, 38))

        gname = GRADIENT_NAMES[seed % len(GRADIENT_NAMES)]
        gtext = small_font.render(f"Gradient: {gname}", True, (180, 180, 100))
        screen.blit(gtext, (20, 56))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
