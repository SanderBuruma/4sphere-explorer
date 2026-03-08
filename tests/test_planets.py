"""Tests for procedural rotating planet generation and rendering."""
import unittest
import numpy as np
import pygame

from lib.planets import (
    generate_equirect_texture,
    render_planet_frame,
    get_planet_rotation_angle,
    get_planet_equirect,
    reset_frame_budget,
    evict_planet_cache,
    EQUIRECT_H,
    EQUIRECT_W,
    _equirect_cache,
)


class TestEquirectTexture(unittest.TestCase):
    """Tests for generate_equirect_texture."""

    def test_shape_and_dtype(self):
        tex = generate_equirect_texture(0)
        self.assertEqual(tex.shape, (EQUIRECT_H, EQUIRECT_W, 3))
        self.assertEqual(tex.dtype, np.uint8)

    def test_deterministic(self):
        a = generate_equirect_texture(42)
        b = generate_equirect_texture(42)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_differ(self):
        a = generate_equirect_texture(0)
        b = generate_equirect_texture(1)
        self.assertFalse(np.array_equal(a, b))

    def test_pixel_range(self):
        tex = generate_equirect_texture(7)
        self.assertTrue(tex.max() > 0, "Texture should have non-zero pixels")
        self.assertTrue(tex.max() <= 255)


class TestRenderPlanetFrame(unittest.TestCase):
    """Tests for render_planet_frame."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
        cls.equirect = generate_equirect_texture(0)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_returns_srcalpha_surface(self):
        surf = render_planet_frame(self.equirect, 32, 0.0)
        self.assertEqual(surf.get_size(), (32, 32))
        self.assertTrue(surf.get_flags() & pygame.SRCALPHA)

    def test_small_size(self):
        surf = render_planet_frame(self.equirect, 8, 0.0)
        self.assertEqual(surf.get_size(), (8, 8))

    def test_large_size_bilinear(self):
        surf = render_planet_frame(self.equirect, 64, 0.0)
        self.assertEqual(surf.get_size(), (64, 64))

    def test_rotation_changes_pixels(self):
        arr_a = pygame.surfarray.array3d(render_planet_frame(self.equirect, 32, 0.0))
        arr_b = pygame.surfarray.array3d(render_planet_frame(self.equirect, 32, np.pi))
        self.assertFalse(np.array_equal(arr_a, arr_b))

    def test_tint_color(self):
        untinted = pygame.surfarray.array3d(render_planet_frame(self.equirect, 32, 0.0))
        tinted = pygame.surfarray.array3d(
            render_planet_frame(self.equirect, 32, 0.0, tint_color=(255, 0, 0))
        )
        # Green and blue channels should be zeroed by red tint
        self.assertEqual(tinted[:, :, 1].max(), 0)
        self.assertEqual(tinted[:, :, 2].max(), 0)


class TestRotationAngle(unittest.TestCase):
    """Tests for get_planet_rotation_angle."""

    def test_different_points_different_phase(self):
        a = get_planet_rotation_angle(0, 0)
        b = get_planet_rotation_angle(1, 0)
        self.assertNotAlmostEqual(a, b)

    def test_advances_with_time(self):
        a = get_planet_rotation_angle(0, 0)
        b = get_planet_rotation_angle(0, 5000)
        self.assertNotAlmostEqual(a, b)

    def test_full_rotation_period(self):
        a = get_planet_rotation_angle(0, 0)
        b = get_planet_rotation_angle(0, 60000)
        # Should be back to same angle after 60s (ROTATION_PERIOD_MS)
        self.assertAlmostEqual(a % (2 * np.pi), b % (2 * np.pi), places=5)


class TestCacheManagement(unittest.TestCase):
    """Tests for get_planet_equirect, cache eviction, and frame budget."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1), pygame.NOFRAME)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        _equirect_cache.clear()

    def test_generates_and_caches(self):
        reset_frame_budget()
        tex = get_planet_equirect(0, 42)
        self.assertIsNotNone(tex)
        self.assertIn(0, _equirect_cache)

    def test_returns_cached(self):
        reset_frame_budget()
        a = get_planet_equirect(0, 42)
        # Even with zero budget, cached value is returned
        b = get_planet_equirect(0, 42)
        self.assertIs(a, b)

    def test_budget_limits_generation(self):
        reset_frame_budget()  # budget = 2
        get_planet_equirect(0, 0)
        get_planet_equirect(1, 1)
        result = get_planet_equirect(2, 2)
        self.assertIsNone(result, "Should return None when budget exhausted")

    def test_eviction(self):
        reset_frame_budget()
        get_planet_equirect(10, 100)
        self.assertIn(10, _equirect_cache)
        evict_planet_cache([10])
        self.assertNotIn(10, _equirect_cache)

    def test_eviction_ignores_missing(self):
        evict_planet_cache([999])  # should not raise


if __name__ == "__main__":
    unittest.main()
