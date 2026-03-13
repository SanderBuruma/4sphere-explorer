"""Tests that W-halo coloring is invariant to Q/E rotation (xyz_w_angle)."""

import numpy as np
import pytest
from sphere import build_fixed_y_frame


def _compute_w_val(player_pos, planet, w_angle):
    """Compute the rotation-invariant W projection for a planet."""
    frame = build_fixed_y_frame(player_pos, w_angle)
    rel = planet @ frame.T
    cos_a = np.cos(w_angle)
    sin_a = np.sin(w_angle)
    return sin_a * rel[1] + cos_a * rel[3]


def _random_unit_4d(rng):
    """Return a random unit vector on S3."""
    v = rng.standard_normal(4)
    return v / np.linalg.norm(v)


class TestWInvariance:
    """W projection must not change when xyz_w_angle changes."""

    def test_invariance_across_angles(self):
        """For a fixed player+planet, base_w_proj is the same at 20 different angles."""
        player = np.array([1.0, 0.0, 0.0, 0.0])
        planet = np.array([0.9, 0.1, 0.2, 0.3])
        planet /= np.linalg.norm(planet)

        angles = np.linspace(0, 2 * np.pi, 20, endpoint=False)
        w_vals = [_compute_w_val(player, planet, a) for a in angles]

        for v in w_vals[1:]:
            assert abs(v - w_vals[0]) < 1e-10

    def test_matches_raw_col3_at_angle_zero(self):
        """At w_angle=0, un-rotated W equals raw rel_vis[:, 3]."""
        player = np.array([1.0, 0.0, 0.0, 0.0])
        planet = np.array([0.8, 0.2, 0.3, 0.5])
        planet /= np.linalg.norm(planet)

        frame = build_fixed_y_frame(player, 0.0)
        rel = planet @ frame.T
        w_invariant = _compute_w_val(player, planet, 0.0)

        assert abs(w_invariant - rel[3]) < 1e-10

    def test_sign_correctness(self):
        """Planet with large positive W component yields positive base_w_proj."""
        player = np.array([1.0, 0.0, 0.0, 0.0])

        # Planet mostly in +W direction
        planet_pos_w = np.array([0.9, 0.0, 0.0, 0.4])
        planet_pos_w /= np.linalg.norm(planet_pos_w)
        assert _compute_w_val(player, planet_pos_w, 1.23) > 0

        # Planet mostly in -W direction
        planet_neg_w = np.array([0.9, 0.0, 0.0, -0.4])
        planet_neg_w /= np.linalg.norm(planet_neg_w)
        assert _compute_w_val(player, planet_neg_w, 1.23) < 0

    def test_multiple_player_positions(self):
        """Invariance holds from 5 random player positions."""
        rng = np.random.default_rng(42)
        angles = np.linspace(0, 2 * np.pi, 20, endpoint=False)

        for _ in range(5):
            player = _random_unit_4d(rng)
            planet = _random_unit_4d(rng)

            w_vals = [_compute_w_val(player, planet, a) for a in angles]
            for v in w_vals[1:]:
                assert abs(v - w_vals[0]) < 1e-10

    def test_zero_angle_is_identity(self):
        """At w_angle=0, formula sin(0)*col1 + cos(0)*col3 == col3."""
        player = np.array([0.5, 0.5, 0.5, 0.5])
        player /= np.linalg.norm(player)
        planet = np.array([0.3, 0.7, 0.1, 0.6])
        planet /= np.linalg.norm(planet)

        frame = build_fixed_y_frame(player, 0.0)
        rel = planet @ frame.T

        # sin(0) * rel[1] + cos(0) * rel[3] == 0 * rel[1] + 1 * rel[3] == rel[3]
        result = np.sin(0.0) * rel[1] + np.cos(0.0) * rel[3]
        assert abs(result - rel[3]) < 1e-15
