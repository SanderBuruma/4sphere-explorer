"""Tests for Q/E rotation uniformity and frame stability.

Tests the angle-based build_fixed_y_frame() approach for mode 3,
which guarantees uniform screen-space angular velocity for Q/E rotation.
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sphere import (
    build_fixed_y_frame,
    build_player_frame,
    reorthogonalize_frame,
    rotate_frame,
    tangent_basis,
)

CAMERA_OFFSET = 0.08
ROTATION_SPEED = 0.02


def make_initial_orientation():
    """Create the same initial orientation as main.py."""
    camera_pos = np.array([np.cos(CAMERA_OFFSET), 0.0, np.sin(CAMERA_OFFSET), 0.0])
    orientation = np.eye(4)
    orientation[0] = camera_pos.copy()
    basis = tangent_basis(camera_pos)
    for i in range(3):
        orientation[i + 1] = basis[i]
    return orientation


class TestOrientationFrameStability(unittest.TestCase):
    """Test that repeated Q/E rotation keeps the orientation frame well-behaved."""

    def test_qe_rotation_preserves_orthonormality(self):
        """After many Q rotations + reorthogonalize, frame stays orthonormal."""
        orientation = make_initial_orientation()
        for _ in range(500):
            rotate_frame(orientation, 3, ROTATION_SPEED)
            reorthogonalize_frame(orientation)

        for i in range(4):
            self.assertAlmostEqual(np.linalg.norm(orientation[i]), 1.0, places=10)
            for j in range(i + 1, 4):
                self.assertAlmostEqual(
                    np.dot(orientation[i], orientation[j]), 0.0, places=10
                )

    def test_qe_rotation_preserves_determinant(self):
        """Determinant stays +1 throughout Q/E rotation (no handedness flip)."""
        orientation = make_initial_orientation()
        for step in range(500):
            rotate_frame(orientation, 3, ROTATION_SPEED)
            reorthogonalize_frame(orientation)
            det = np.linalg.det(orientation)
            self.assertAlmostEqual(
                det, 1.0, places=8,
                msg=f"Determinant flipped to {det:.6f} at step {step}"
            )

    def test_qe_rotation_rows12_stable(self):
        """Rows 1 and 2 (screen X/Y basis) should not flip during Q/E rotation."""
        orientation = make_initial_orientation()
        prev_row1 = orientation[1].copy()
        prev_row2 = orientation[2].copy()

        for step in range(500):
            rotate_frame(orientation, 3, ROTATION_SPEED)
            reorthogonalize_frame(orientation)

            dot1 = np.dot(orientation[1], prev_row1)
            dot2 = np.dot(orientation[2], prev_row2)
            self.assertGreater(
                dot1, 0.99,
                msg=f"Row 1 flipped at step {step}: dot with prev = {dot1:.6f}"
            )
            self.assertGreater(
                dot2, 0.99,
                msg=f"Row 2 flipped at step {step}: dot with prev = {dot2:.6f}"
            )
            prev_row1 = orientation[1].copy()
            prev_row2 = orientation[2].copy()


class TestMode2FrameContinuity(unittest.TestCase):
    """Mode 2 uses standard build_player_frame -- should be stable."""

    def test_mode2_screen_axes_continuous(self):
        """In mode 2, frame[1] and frame[2] (screen X/Y) stay continuous during Q/E."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        orientation = make_initial_orientation()

        prev_frame = build_player_frame(player_pos, orientation)

        for step in range(500):
            rotate_frame(orientation, 3, ROTATION_SPEED)
            reorthogonalize_frame(orientation)
            frame = build_player_frame(player_pos, orientation)

            dot1 = np.dot(frame[1], prev_frame[1])
            dot2 = np.dot(frame[2], prev_frame[2])
            self.assertGreater(
                dot1, 0.99,
                msg=f"Mode 2 frame[1] flipped at step {step}: dot = {dot1:.6f}"
            )
            self.assertGreater(
                dot2, 0.99,
                msg=f"Mode 2 frame[2] flipped at step {step}: dot = {dot2:.6f}"
            )
            prev_frame = frame.copy()


class TestMode3UniformRotation(unittest.TestCase):
    """Test that build_fixed_y_frame produces uniform angular velocity for Q/E."""

    def test_mode3_uniform_angular_velocity(self):
        """Increment w_angle by equal steps, measure inter-frame angle -- must be constant."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        step_size = ROTATION_SPEED
        angles = []

        prev_frame = build_fixed_y_frame(player_pos, 0.0)
        for i in range(1, 500):
            w_angle = i * step_size
            frame = build_fixed_y_frame(player_pos, w_angle)
            # Measure angular change in frame[1] between consecutive steps
            dot = np.clip(np.dot(frame[1], prev_frame[1]), -1.0, 1.0)
            angle = np.arccos(dot)
            angles.append(angle)
            prev_frame = frame.copy()

        angles = np.array(angles)
        # All inter-frame angles should be identical (std ≈ 0)
        self.assertLess(
            np.std(angles), 1e-10,
            msg=f"Angular velocity not uniform: std={np.std(angles):.2e}, "
                f"mean={np.mean(angles):.6f}"
        )

    def test_mode3_full_rotation_returns(self):
        """w_angle=0 and w_angle=2*pi produce the same frame."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        frame_0 = build_fixed_y_frame(player_pos, 0.0)
        frame_2pi = build_fixed_y_frame(player_pos, 2 * np.pi)

        for i in range(4):
            dot = np.dot(frame_0[i], frame_2pi[i])
            self.assertAlmostEqual(
                dot, 1.0, places=10,
                msg=f"frame[{i}] diverged after full rotation: dot = {dot:.10f}"
            )

    def test_mode3_frame_orthonormal_at_all_angles(self):
        """Orthonormality check at many angles."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        for i in range(100):
            w_angle = i * 2 * np.pi / 100
            frame = build_fixed_y_frame(player_pos, w_angle)

            product = frame @ frame.T
            np.testing.assert_array_almost_equal(
                product, np.eye(4), decimal=10,
                err_msg=f"Frame not orthonormal at w_angle={w_angle:.4f}"
            )

    def test_mode3_fixed_y_preserved(self):
        """frame[2] always parallel to fixed_up at all angles."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        fixed_up = np.array([0.0, 1.0, 0.0, 0.0])

        first_frame = build_fixed_y_frame(player_pos, 0.0)
        expected_up = first_frame[2].copy()

        for i in range(100):
            w_angle = i * 2 * np.pi / 100
            frame = build_fixed_y_frame(player_pos, w_angle)

            dot = np.dot(frame[2], expected_up)
            self.assertAlmostEqual(
                dot, 1.0, places=10,
                msg=f"frame[2] changed at w_angle={w_angle:.4f}: dot = {dot:.10f}"
            )

    def test_mode3_angle_zero_matches_convention(self):
        """At w_angle=0 with player [1,0,0,0], verify expected frame vectors."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        frame = build_fixed_y_frame(player_pos, 0.0)

        # frame[0] = player = [1,0,0,0]
        np.testing.assert_array_almost_equal(frame[0], [1, 0, 0, 0], decimal=10)
        # frame[2] = fixed Y projected = [0,1,0,0]
        np.testing.assert_array_almost_equal(frame[2], [0, 1, 0, 0], decimal=10)

    def test_mode3_determinant_positive(self):
        """det(frame) = +1 at all angles."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        for i in range(100):
            w_angle = i * 2 * np.pi / 100
            frame = build_fixed_y_frame(player_pos, w_angle)
            det = np.linalg.det(frame)
            self.assertAlmostEqual(
                det, 1.0, places=8,
                msg=f"Determinant = {det:.8f} at w_angle={w_angle:.4f}"
            )

    def test_mode3_from_various_positions(self):
        """Uniform rotation works from non-trivial player positions."""
        rng = np.random.default_rng(42)
        for _ in range(10):
            player_pos = rng.standard_normal(4)
            player_pos[1] *= 0.3  # avoid Y-axis degeneracy
            player_pos /= np.linalg.norm(player_pos)

            angles = []
            prev_frame = build_fixed_y_frame(player_pos, 0.0)
            for i in range(1, 100):
                w_angle = i * ROTATION_SPEED
                frame = build_fixed_y_frame(player_pos, w_angle)
                dot = np.clip(np.dot(frame[1], prev_frame[1]), -1.0, 1.0)
                angles.append(np.arccos(dot))
                prev_frame = frame.copy()

            self.assertLess(
                np.std(angles), 1e-10,
                msg=f"Non-uniform from pos {player_pos}: std={np.std(angles):.2e}"
            )

    def test_mode3_screen_x_continuous(self):
        """frame[1] (screen X) changes smoothly -- no sudden flips."""
        player_pos = np.array([1.0, 0.0, 0.0, 0.0])
        prev_frame = build_fixed_y_frame(player_pos, 0.0)

        for step in range(500):
            w_angle = (step + 1) * ROTATION_SPEED
            frame = build_fixed_y_frame(player_pos, w_angle)

            dot1 = np.dot(frame[1], prev_frame[1])
            self.assertGreater(
                dot1, 0.99,
                msg=f"frame[1] flipped at step {step} "
                    f"(w_angle={w_angle:.3f}): dot = {dot1:.6f}"
            )
            prev_frame = frame.copy()


if __name__ == "__main__":
    unittest.main()
