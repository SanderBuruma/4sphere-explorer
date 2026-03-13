"""Tests for compute_planet_size() smooth sizing function."""

from lib.constants import compute_planet_size, SIZE_FOV as FOV_ANGLE


def test_closest_planet_max_radius():
    """Planet at angular_dist=0, w_dist=0 should get max radius."""
    radius, sprite_size, glow_radius = compute_planet_size(0.0, 0.0)
    assert radius > 7.0


def test_farthest_planet_min_radius():
    """Planet at FOV edge with max W offset should get min radius."""
    radius, sprite_size, glow_radius = compute_planet_size(FOV_ANGLE, FOV_ANGLE)
    assert radius <= 2.0


def test_monotonic_decrease_angular():
    """Radius should decrease monotonically with angular distance."""
    prev_radius = float("inf")
    for i in range(100):
        ang = FOV_ANGLE * i / 99
        radius, _, _ = compute_planet_size(ang, 0.0)
        assert radius <= prev_radius, f"Radius increased at angular step {i}"
        prev_radius = radius


def test_monotonic_decrease_w_dist():
    """Radius should decrease monotonically with W distance."""
    prev_radius = float("inf")
    for i in range(50):
        w = FOV_ANGLE * i / 49
        radius, _, _ = compute_planet_size(0.0, w)
        assert radius <= prev_radius, f"Radius increased at W step {i}"
        prev_radius = radius


def test_w_distance_reduces_size():
    """Same angular distance, larger W distance should give smaller radius."""
    r_near, _, _ = compute_planet_size(FOV_ANGLE * 0.3, 0.0)
    r_far, _, _ = compute_planet_size(FOV_ANGLE * 0.3, FOV_ANGLE * 0.8)
    assert r_far < r_near


def test_zoom_scales_linearly():
    """Doubling zoom should approximately double radius (above the floor)."""
    r1, _, _ = compute_planet_size(0.0, 0.0, zoom=1.0)
    r2, _, _ = compute_planet_size(0.0, 0.0, zoom=2.0)
    assert abs(r2 / r1 - 2.0) < 0.1


def test_sprite_size_ge_double_radius():
    """sprite_size should be >= max(4, 2*radius)."""
    for ang_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for w_frac in [0.0, 0.5, 1.0]:
            ang = FOV_ANGLE * ang_frac
            w = FOV_ANGLE * w_frac
            radius, sprite_size, _ = compute_planet_size(ang, w)
            assert sprite_size >= max(4.0, 2.0 * radius)


def test_glow_radius_gt_radius():
    """glow_radius should always be larger than radius."""
    for ang_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for w_frac in [0.0, 0.5, 1.0]:
            ang = FOV_ANGLE * ang_frac
            w = FOV_ANGLE * w_frac
            radius, _, glow_radius = compute_planet_size(ang, w)
            assert glow_radius > radius


def test_minimum_floors():
    """Worst-case inputs should still respect minimum floors."""
    radius, sprite_size, glow_radius = compute_planet_size(FOV_ANGLE * 10, FOV_ANGLE * 10)
    assert radius >= 1.5
    assert sprite_size >= 4.0
    assert glow_radius >= 3.0


def test_many_distinct_radii():
    """Across the distance range, there should be at least 5 distinct integer radii."""
    int_radii = set()
    for i in range(100):
        ang = FOV_ANGLE * i / 99
        radius, _, _ = compute_planet_size(ang, 0.0)
        int_radii.add(int(round(radius)))
    assert len(int_radii) >= 5, f"Only {len(int_radii)} distinct int radii: {sorted(int_radii)}"
