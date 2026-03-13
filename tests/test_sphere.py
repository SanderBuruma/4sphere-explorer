import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sphere import (
    angular_distance,
    build_fixed_y_frame,
    build_player_frame,
    build_visibility_kdtree,
    cross4,
    decode_name,
    project_to_tangent,
    query_visible_kdtree,
    random_point_on_s3,
    reorthogonalize_frame,
    rotate_frame,
    rotate_frame_tangent,
    slerp,
    tangent_basis,
    visible_points,
    TOTAL_NAMES,
    SUFFIXES,
    _N_CORE,
    _N_END,
    _N_SUF,
    w_to_color,
)

NUM_POINTS = 30_000
FOV_ANGLE = 0.116
TRAVEL_SPEED = 0.00008
ARRIVAL_THRESHOLD = 0.002
OLD_TRAVEL_SPEED = 0.00004


class TestScaleConstraints(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.points = random_point_on_s3(NUM_POINTS)

    def test_point_count(self):
        """Verify that 30,000 points are generated."""
        self.assertEqual(len(self.points), NUM_POINTS)

    def test_avg_visible_approx_10(self):
        """Average visible points across 200 random camera positions must be 8-12."""
        rng = np.random.default_rng(7)
        counts = []
        for _ in range(200):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            _, indices = visible_points(cam, self.points, FOV_ANGLE)
            counts.append(len(indices))
        avg = float(np.mean(counts))
        self.assertGreater(avg, 8.0, f"Average visible {avg:.2f} is below 8")
        self.assertLess(avg, 12.0, f"Average visible {avg:.2f} exceeds 12")

    def test_travel_speed_2x_faster(self):
        """Verify travel speed is 2x faster than old speed."""
        self.assertAlmostEqual(TRAVEL_SPEED, OLD_TRAVEL_SPEED * 2, places=8)


class TestNameGeneration(unittest.TestCase):
    """Test name format: suffix always between syllables and optional number."""

    def test_three_part_with_number(self):
        """First region: core+end Suffix NN."""
        name = decode_name(0)
        parts = name.split(" ")
        self.assertEqual(len(parts), 3)
        self.assertIn(parts[1], SUFFIXES)
        self.assertRegex(parts[2], r"^\d{2}$")

    def test_three_part_plain(self):
        """Second region: core+end Suffix (no number)."""
        from sphere import THREE_NUM
        name = decode_name(THREE_NUM)
        parts = name.split(" ")
        self.assertEqual(len(parts), 2)
        self.assertIn(parts[1], SUFFIXES)

    def test_two_part_with_number(self):
        """Third region: core Suffix NN."""
        from sphere import THREE_NUM, THREE_PLAIN
        name = decode_name(THREE_NUM + THREE_PLAIN)
        parts = name.split(" ")
        self.assertEqual(len(parts), 3)
        self.assertIn(parts[1], SUFFIXES)
        self.assertRegex(parts[2], r"^\d{2}$")

    def test_two_part_plain(self):
        """Fourth region: core Suffix (no number)."""
        from sphere import THREE_NUM, THREE_PLAIN, TWO_NUM
        name = decode_name(THREE_NUM + THREE_PLAIN + TWO_NUM)
        parts = name.split(" ")
        self.assertEqual(len(parts), 2)
        self.assertIn(parts[1], SUFFIXES)

    def test_total_names_sufficient(self):
        """Name space must accommodate 30k unique points."""
        self.assertGreater(TOTAL_NAMES, 30_000)

    def test_no_bare_numbers_as_suffix(self):
        """Numbers must never appear where the suffix word should be."""
        rng = np.random.default_rng(99)
        keys = rng.choice(TOTAL_NAMES, 500, replace=False)
        for k in keys:
            parts = decode_name(k).split(" ")
            # Second part (index 1) must always be a word suffix
            self.assertIn(parts[1], SUFFIXES, f"Key {k} has number as suffix: {parts}")


class TestTravelQueue(unittest.TestCase):
    """Test travel completes at proximity and queue activates."""

    def test_arrival_at_proximity(self):
        """Slerp travel must reach < ARRIVAL_THRESHOLD rad within reasonable progress."""
        player = np.array([1.0, 0.0, 0.0, 0.0])
        target = random_point_on_s3(1)
        for i in range(1, 10001):
            t = i * 0.0001
            pos = slerp(player, target, min(t, 1.0))
            if angular_distance(pos, target) < ARRIVAL_THRESHOLD:
                break
        self.assertLess(angular_distance(pos, target), ARRIVAL_THRESHOLD)

    def test_queue_activates_after_arrival(self):
        """Simulate: travel to A, queue B, arrive at A -> traveling to B."""
        player = np.array([1.0, 0.0, 0.0, 0.0])
        np.random.seed(7)
        pts = random_point_on_s3(2)
        target_a, target_b = pts[0], pts[1]

        traveling = True
        travel_target = target_a
        queued_target = target_b
        travel_progress = 0.0

        # Advance until proximity
        while True:
            travel_progress += 0.001
            pos = slerp(player, travel_target, min(travel_progress, 1.0))
            if angular_distance(pos, travel_target) < ARRIVAL_THRESHOLD:
                # Arrival: activate queue
                travel_target = queued_target
                queued_target = None
                travel_progress = 0.0
                player = pos
                break

        self.assertTrue(np.allclose(travel_target, target_b))
        self.assertIsNone(queued_target)
        self.assertTrue(traveling)


class TestRelativeRotation(unittest.TestCase):
    """Verify QWEADS relative rotations are smooth and consistent everywhere on S3."""

    ROTATION_SPEED = 0.02
    KEYS = "wasdeq"
    # axis_idx and sign for each key, matching main.py's rotate_frame calls
    KEY_MAP = {
        "w": (2, -1), "s": (2, 1),
        "a": (1, -1), "d": (1, 1),
        "q": (3, 1),  "e": (3, -1),
    }

    def _make_frame(self, cam):
        """Build initial orientation frame at camera position."""
        frame = np.eye(4)
        frame[0] = cam / np.linalg.norm(cam)
        basis = tangent_basis(frame[0])
        for i in range(3):
            frame[i + 1] = basis[i]
        return frame

    def _rotate_step(self, frame, keys):
        """Apply one frame of rotation for given key(s). Mirrors main.py logic."""
        from sphere import rotate_frame, reorthogonalize_frame
        for key in keys:
            axis_idx, sign = self.KEY_MAP[key]
            rotate_frame(frame, axis_idx, sign * self.ROTATION_SPEED)
        reorthogonalize_frame(frame)
        return frame[0].copy()

    def test_unit_norm_preserved(self):
        """Camera stays on S3 after 1000 single-key rotation steps."""
        for key in self.KEYS:
            frame = self._make_frame(np.array([1.0, 0.0, 0.0, 0.0]))
            for _ in range(1000):
                self._rotate_step(frame, key)
            self.assertAlmostEqual(np.linalg.norm(frame[0]), 1.0, places=10)

    def test_step_size_consistent(self):
        """Each single-key step moves camera by ~ROTATION_SPEED from various starts."""
        starts = [
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.5, 0.5, 0.5, 0.5]),
        ]
        for start in starts:
            start /= np.linalg.norm(start)
            for key in self.KEYS:
                frame = self._make_frame(start.copy())
                new_cam = self._rotate_step(frame, key)
                step = angular_distance(start, new_cam)
                self.assertAlmostEqual(
                    step, self.ROTATION_SPEED, places=5,
                    msg=f"Key '{key}' from {start}: step {step:.6f}",
                )

    def test_full_rotation_returns_to_start(self):
        """Rotating ~2pi with a single key returns close to start (great circle)."""
        steps = int(round(2 * np.pi / self.ROTATION_SPEED))
        for key in self.KEYS:
            start = np.array([1.0, 0.0, 0.0, 0.0])
            frame = self._make_frame(start.copy())
            for _ in range(steps):
                self._rotate_step(frame, key)
            dist = angular_distance(start, frame[0])
            self.assertLess(
                dist, 0.01,
                f"Key '{key}': after {steps} steps, dist from start = {dist:.4f}",
            )

    def test_no_jumps_through_full_rotation(self):
        """Every consecutive step has the same angular distance (no discontinuities)."""
        steps = int(round(2 * np.pi / self.ROTATION_SPEED))
        for key in self.KEYS:
            frame = self._make_frame(np.array([0.5, 0.5, 0.5, 0.5]))
            max_dev = 0.0
            for _ in range(steps):
                prev = frame[0].copy()
                self._rotate_step(frame, key)
                dev = abs(angular_distance(prev, frame[0]) - self.ROTATION_SPEED)
                max_dev = max(max_dev, dev)
            self.assertLess(
                max_dev, 1e-5,
                f"Key '{key}': max step deviation = {max_dev:.2e}",
            )

    def test_combination_two_keys_smooth(self):
        """Two simultaneous keys produce smooth, consistent step sizes."""
        combos = ["wa", "wd", "wq", "sa", "se", "dq", "ae"]
        for combo in combos:
            frame = self._make_frame(np.array([1.0, 0.0, 0.0, 0.0]))
            steps = []
            for _ in range(200):
                prev = frame[0].copy()
                self._rotate_step(frame, combo)
                steps.append(angular_distance(prev, frame[0]))
                self.assertAlmostEqual(np.linalg.norm(frame[0]), 1.0, places=10)
            self.assertLess(
                np.std(steps), 1e-4,
                f"Combo '{combo}': step std = {np.std(steps):.2e}",
            )

    def test_combination_three_keys_smooth(self):
        """Three simultaneous keys still produce smooth rotation."""
        combos = ["waq", "sde", "wdq", "sae"]
        for combo in combos:
            cam = np.array([0.3, 0.4, 0.5, 0.6])
            cam /= np.linalg.norm(cam)
            frame = self._make_frame(cam)
            steps = []
            for _ in range(200):
                prev = frame[0].copy()
                self._rotate_step(frame, combo)
                steps.append(angular_distance(prev, frame[0]))
                self.assertAlmostEqual(np.linalg.norm(frame[0]), 1.0, places=10)
            self.assertLess(
                np.std(steps), 1e-4,
                f"Combo '{combo}': step std = {np.std(steps):.2e}",
            )

    def test_from_random_starting_positions(self):
        """Single-key rotation is consistent from 20 random positions on S3."""
        rng = np.random.default_rng(123)
        for _ in range(20):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            for key in self.KEYS:
                frame = self._make_frame(cam.copy())
                new_cam = self._rotate_step(frame, key)
                step = angular_distance(cam, new_cam)
                self.assertAlmostEqual(
                    step, self.ROTATION_SPEED, places=4,
                    msg=f"Key '{key}' from {cam}: step {step:.6f}",
                )
                self.assertAlmostEqual(np.linalg.norm(new_cam), 1.0, places=10)


class TestSphereMath(unittest.TestCase):
    """Test core sphere math: angular distance and slerp."""

    def test_angular_distance_self_is_zero(self):
        """Distance from point to itself is approximately 0."""
        rng = np.random.default_rng(42)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            self.assertAlmostEqual(angular_distance(p, p), 0.0, places=6)

    def test_angular_distance_antipodal_is_pi(self):
        """Distance between p and -p is approximately pi."""
        rng = np.random.default_rng(43)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            self.assertAlmostEqual(angular_distance(p, -p), np.pi, places=6)

    def test_angular_distance_symmetric(self):
        """d(a,b) == d(b,a) for random pairs."""
        rng = np.random.default_rng(44)
        for _ in range(50):
            a = rng.standard_normal(4)
            a /= np.linalg.norm(a)
            b = rng.standard_normal(4)
            b /= np.linalg.norm(b)
            self.assertAlmostEqual(
                angular_distance(a, b), angular_distance(b, a), places=14
            )

    def test_angular_distance_triangle_inequality(self):
        """d(a,c) <= d(a,b) + d(b,c) for random triples."""
        rng = np.random.default_rng(45)
        for _ in range(50):
            pts = rng.standard_normal((3, 4))
            pts /= np.linalg.norm(pts, axis=1, keepdims=True)
            a, b, c = pts
            dac = angular_distance(a, c)
            dab = angular_distance(a, b)
            dbc = angular_distance(b, c)
            self.assertLessEqual(dac, dab + dbc + 1e-10)

    def test_slerp_t0_returns_start(self):
        """slerp(p, q, 0) is approximately p."""
        rng = np.random.default_rng(46)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            q = rng.standard_normal(4)
            q /= np.linalg.norm(q)
            result = slerp(p, q, 0.0)
            np.testing.assert_allclose(result, p, atol=1e-12)

    def test_slerp_t1_returns_end(self):
        """slerp(p, q, 1) is approximately q."""
        rng = np.random.default_rng(47)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            q = rng.standard_normal(4)
            q /= np.linalg.norm(q)
            result = slerp(p, q, 1.0)
            np.testing.assert_allclose(result, q, atol=1e-10)

    def test_slerp_unit_norm_along_path(self):
        """Norm is approximately 1 at t=0.25, 0.5, 0.75."""
        rng = np.random.default_rng(48)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            q = rng.standard_normal(4)
            q /= np.linalg.norm(q)
            for t in [0.25, 0.5, 0.75]:
                result = slerp(p, q, t)
                self.assertAlmostEqual(np.linalg.norm(result), 1.0, places=10)

    def test_slerp_midpoint_equidistant(self):
        """d(p, slerp(0.5)) is approximately d(slerp(0.5), q)."""
        rng = np.random.default_rng(49)
        for _ in range(20):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            q = rng.standard_normal(4)
            q /= np.linalg.norm(q)
            mid = slerp(p, q, 0.5)
            d1 = angular_distance(p, mid)
            d2 = angular_distance(mid, q)
            self.assertAlmostEqual(d1, d2, places=10)


class TestTangentProjection(unittest.TestCase):
    """Test tangent basis construction and projection."""

    def test_tangent_basis_orthonormal(self):
        """3 vectors, unit norm, mutually orthogonal, perpendicular to cam from 10+ random positions."""
        rng = np.random.default_rng(50)
        for _ in range(15):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            basis = tangent_basis(cam)
            self.assertEqual(len(basis), 3)
            # Unit norm
            for v in basis:
                self.assertAlmostEqual(np.linalg.norm(v), 1.0, places=10)
            # Perpendicular to cam
            for v in basis:
                self.assertAlmostEqual(np.dot(v, cam), 0.0, places=10)
            # Mutually orthogonal
            for i in range(3):
                for j in range(i + 1, 3):
                    self.assertAlmostEqual(
                        np.dot(basis[i], basis[j]), 0.0, places=10
                    )

    def test_project_to_tangent_degenerate(self):
        """Colocated returns zero, antipodal does not NaN."""
        cam = np.array([1.0, 0.0, 0.0, 0.0])
        basis = tangent_basis(cam)
        # Colocated
        result = project_to_tangent(cam, cam, basis)
        np.testing.assert_allclose(result, np.zeros(3), atol=1e-10)
        # Antipodal
        result = project_to_tangent(cam, -cam, basis)
        self.assertFalse(np.any(np.isnan(result)))

    def test_project_to_tangent_distance_proportional(self):
        """Output magnitude tracks angular distance."""
        rng = np.random.default_rng(51)
        cam = rng.standard_normal(4)
        cam /= np.linalg.norm(cam)
        basis = tangent_basis(cam)

        # Generate points at varying distances
        magnitudes = []
        distances = []
        for _ in range(30):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            d = angular_distance(cam, p)
            if d < 1e-4 or d > np.pi - 1e-4:
                continue
            proj = project_to_tangent(cam, p, basis)
            magnitudes.append(np.linalg.norm(proj))
            distances.append(d)

        # Correlation should be strongly positive
        if len(magnitudes) > 5:
            corr = np.corrcoef(distances, magnitudes)[0, 1]
            self.assertGreater(corr, 0.9, f"Correlation {corr:.3f} too low")

    def test_kdtree_visible_matches_brute_force(self):
        """Compare visible_points vs query_visible_kdtree for 20 random cameras."""
        np.random.seed(42)
        points = random_point_on_s3(NUM_POINTS)
        kdtree = build_visibility_kdtree(points)
        rng = np.random.default_rng(52)

        for _ in range(20):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            _, brute_idx = visible_points(cam, points, FOV_ANGLE)
            _, kd_idx = query_visible_kdtree(kdtree, cam, points, FOV_ANGLE)
            brute_set = set(brute_idx.tolist())
            kd_set = set(kd_idx.tolist())
            self.assertEqual(brute_set, kd_set)


class TestPlayerFrameProjection(unittest.TestCase):
    """Test that player projects to screen center in XYZ projection mode."""

    CAMERA_OFFSET = 0.08  # matches main.py

    def _make_orientation(self, cam):
        """Build a 4x4 orientation frame from camera position."""
        frame = np.zeros((4, 4))
        frame[0] = cam / np.linalg.norm(cam)
        # Use tangent_basis for rows 1-3
        basis = tangent_basis(frame[0])
        for i in range(3):
            frame[i + 1] = basis[i]
        return frame

    def _simulate_player_camera(self, player_pos):
        """Given player pos, create camera offset along an arbitrary tangent direction."""
        player_pos = player_pos / np.linalg.norm(player_pos)
        basis = tangent_basis(player_pos)
        # Camera is offset from player along first tangent direction
        cam = slerp(player_pos, basis[0] + player_pos, self.CAMERA_OFFSET / np.pi)
        cam /= np.linalg.norm(cam)
        return cam

    def test_player_projects_to_origin_from_standard_positions(self):
        """Player position must have near-zero components 1,2,3 in its own frame."""
        positions = [
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 0.0, 1.0]),
            np.array([0.5, 0.5, 0.5, 0.5]),
            np.array([-0.3, 0.7, -0.2, 0.6]),
        ]
        for pos in positions:
            pos = pos / np.linalg.norm(pos)
            cam = self._simulate_player_camera(pos)
            orientation = self._make_orientation(cam)
            frame = build_player_frame(pos, orientation)

            # Project player through frame
            proj = pos @ frame.T
            # Component 0 should be ~1 (aligned with self), components 1,2,3 should be ~0
            self.assertAlmostEqual(proj[0], 1.0, places=5,
                msg=f"Player {pos}: component 0 = {proj[0]:.6f}, expected ~1.0")
            for c in range(1, 4):
                self.assertAlmostEqual(proj[c], 0.0, places=5,
                    msg=f"Player {pos}: component {c} = {proj[c]:.6f}, expected ~0.0")

    def test_player_projects_to_origin_from_random_orientations(self):
        """Player maps to (1,0,0,0) in its frame from 50 random positions+orientations."""
        rng = np.random.default_rng(99)
        for _ in range(50):
            player = rng.standard_normal(4)
            player /= np.linalg.norm(player)
            cam = self._simulate_player_camera(player)
            orientation = self._make_orientation(cam)

            # Simulate rotations to get a non-trivial orientation
            for _ in range(rng.integers(1, 10)):
                axis = rng.integers(1, 4)
                angle = rng.uniform(-0.5, 0.5)
                rotate_frame(orientation, axis, angle)
            reorthogonalize_frame(orientation)

            frame = build_player_frame(player, orientation)
            proj = player @ frame.T
            self.assertAlmostEqual(proj[0], 1.0, places=4,
                msg=f"Component 0 = {proj[0]:.6f}")
            for c in range(1, 4):
                self.assertAlmostEqual(proj[c], 0.0, places=4,
                    msg=f"Component {c} = {proj[c]:.6f}")

    def test_frame_is_orthonormal(self):
        """Player frame must be orthonormal (4x4 orthogonal matrix)."""
        rng = np.random.default_rng(100)
        for _ in range(30):
            player = rng.standard_normal(4)
            player /= np.linalg.norm(player)
            cam = self._simulate_player_camera(player)
            orientation = self._make_orientation(cam)
            frame = build_player_frame(player, orientation)

            # Check orthonormality: frame @ frame.T should be identity
            product = frame @ frame.T
            np.testing.assert_allclose(product, np.eye(4), atol=1e-10,
                err_msg=f"Frame not orthonormal for player {player}")

    def test_nearby_points_project_near_center(self):
        """Points close to player should have small components 1,2,3."""
        rng = np.random.default_rng(101)
        for _ in range(20):
            player = rng.standard_normal(4)
            player /= np.linalg.norm(player)
            cam = self._simulate_player_camera(player)
            orientation = self._make_orientation(cam)
            frame = build_player_frame(player, orientation)

            # Generate a nearby point (small angular distance)
            tangent = rng.standard_normal(4)
            tangent -= np.dot(tangent, player) * player
            tangent /= np.linalg.norm(tangent)
            nearby = slerp(player, tangent + player, 0.01)  # ~0.01 rad away
            nearby /= np.linalg.norm(nearby)

            proj = nearby @ frame.T
            # Components 1,2,3 should be small (point is close)
            offset = np.sqrt(proj[1]**2 + proj[2]**2 + proj[3]**2)
            self.assertLess(offset, 0.1,
                msg=f"Nearby point offset {offset:.4f} too large")


class TestXYZProjectionColors(unittest.TestCase):
    """Test w_to_color gradient: blue(-1) → white(0) → red(+1)."""

    def test_w_minus1_is_blue(self):
        """w=-1 gives pure blue (0, 0, 255)."""
        self.assertEqual(w_to_color(-1.0), (0, 0, 255))

    def test_w_zero_is_white(self):
        """w=0 gives white (255, 255, 255)."""
        self.assertEqual(w_to_color(0.0), (255, 255, 255))

    def test_w_plus1_is_red(self):
        """w=+1 gives pure red (255, 0, 0)."""
        self.assertEqual(w_to_color(1.0), (255, 0, 0))

    def test_w_minus05_between_blue_and_white(self):
        """w=-0.5 is halfway between blue and white."""
        r, g, b = w_to_color(-0.5)
        # R and G should be ~127, B should be 255
        self.assertAlmostEqual(r, 127, delta=1)
        self.assertAlmostEqual(g, 127, delta=1)
        self.assertEqual(b, 255)

    def test_w_plus05_between_white_and_red(self):
        """w=+0.5 is halfway between white and red."""
        r, g, b = w_to_color(0.5)
        # R should be 255, G and B should be ~127
        self.assertEqual(r, 255)
        self.assertAlmostEqual(g, 127, delta=1)
        self.assertAlmostEqual(b, 127, delta=1)

    def test_r_channel_monotonically_nondecreasing(self):
        """R channel is monotonically non-decreasing as w goes from -1 to +1."""
        ws = [i / 100.0 for i in range(-100, 101)]
        rs = [w_to_color(w)[0] for w in ws]
        for i in range(1, len(rs)):
            self.assertGreaterEqual(rs[i], rs[i - 1],
                f"R decreased at w={ws[i]:.2f}: {rs[i]} < {rs[i-1]}")

    def test_b_channel_monotonically_nonincreasing(self):
        """B channel is monotonically non-increasing as w goes from -1 to +1."""
        ws = [i / 100.0 for i in range(-100, 101)]
        bs = [w_to_color(w)[2] for w in ws]
        for i in range(1, len(bs)):
            self.assertLessEqual(bs[i], bs[i - 1],
                f"B increased at w={ws[i]:.2f}: {bs[i]} > {bs[i-1]}")


class TestRotateFrameTangent(unittest.TestCase):
    """Test rotate_frame_tangent: rotates tangent basis without moving camera."""

    def _make_frame(self, cam):
        frame = np.eye(4)
        frame[0] = cam / np.linalg.norm(cam)
        basis = tangent_basis(frame[0])
        for i in range(3):
            frame[i + 1] = basis[i]
        return frame

    def test_row0_unchanged(self):
        """Row 0 (camera) must be identical before and after tangent rotation."""
        rng = np.random.default_rng(200)
        for _ in range(20):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            frame = self._make_frame(cam)
            row0_before = frame[0].copy()
            axis1, axis2 = rng.choice([1, 2, 3], 2, replace=False)
            angle = rng.uniform(-1.0, 1.0)
            rotate_frame_tangent(frame, axis1, axis2, angle)
            np.testing.assert_allclose(frame[0], row0_before, atol=1e-14,
                err_msg="Row 0 changed after tangent rotation")

    def test_orthonormality_preserved(self):
        """Frame remains orthonormal after tangent rotation."""
        rng = np.random.default_rng(201)
        for _ in range(20):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            frame = self._make_frame(cam)
            axis1, axis2 = rng.choice([1, 2, 3], 2, replace=False)
            angle = rng.uniform(-1.0, 1.0)
            rotate_frame_tangent(frame, axis1, axis2, angle)
            product = frame @ frame.T
            np.testing.assert_allclose(product, np.eye(4), atol=1e-10,
                err_msg="Frame not orthonormal after tangent rotation")

    def test_rotation_angle_matches(self):
        """Angle between original and rotated axis vectors matches input angle."""
        rng = np.random.default_rng(202)
        for _ in range(20):
            cam = rng.standard_normal(4)
            cam /= np.linalg.norm(cam)
            frame = self._make_frame(cam)
            axis1, axis2 = rng.choice([1, 2, 3], 2, replace=False)
            angle = rng.uniform(-0.5, 0.5)
            v1_before = frame[axis1].copy()
            rotate_frame_tangent(frame, axis1, axis2, angle)
            # The rotated v1 should make angle `angle` with original v1
            dot = np.clip(np.dot(frame[axis1], v1_before), -1.0, 1.0)
            measured = np.arccos(dot)
            self.assertAlmostEqual(measured, abs(angle), places=10,
                msg=f"Expected angle {abs(angle):.6f}, got {measured:.6f}")


class TestFixedYFrame(unittest.TestCase):
    """Test XYZ Fixed-Y mode: absolute Y axis [0,1,0,0] stays as frame row 2."""

    FIXED_UP = np.array([0.0, 1.0, 0.0, 0.0])

    def _make_frame(self, cam):
        frame = np.eye(4)
        frame[0] = cam / np.linalg.norm(cam)
        basis = tangent_basis(frame[0])
        for i in range(3):
            frame[i + 1] = basis[i]
        return frame

    def _build_mode3_frame(self, player_pos, w_angle=0.0):
        """Build mode 3 frame using build_fixed_y_frame."""
        return build_fixed_y_frame(player_pos, w_angle, self.FIXED_UP)

    def test_row2_parallel_to_absolute_y(self):
        """Frame row 2 is always parallel to [0,1,0,0] projected orthogonal to player."""
        rng = np.random.default_rng(300)
        for _ in range(20):
            # Avoid players aligned with Y axis (degenerate case)
            player = rng.standard_normal(4)
            player[1] *= 0.3  # reduce Y component to avoid degeneracy
            player /= np.linalg.norm(player)
            w_angle = rng.uniform(0, 2 * np.pi)

            player_frame = self._build_mode3_frame(player, w_angle)

            # Row 2 should be parallel to [0,1,0,0] projected orthogonal to player
            expected_up = self.FIXED_UP - np.dot(self.FIXED_UP, player_frame[0]) * player_frame[0]
            expected_up /= np.linalg.norm(expected_up)
            dot = abs(np.dot(player_frame[2], expected_up))
            self.assertAlmostEqual(dot, 1.0, places=8,
                msg=f"Row 2 not parallel to absolute Y: dot={dot:.10f}")

    def test_frame_orthonormal_after_override(self):
        """Frame remains orthonormal with build_fixed_y_frame."""
        rng = np.random.default_rng(301)
        for _ in range(20):
            player = rng.standard_normal(4)
            player[1] *= 0.3
            player /= np.linalg.norm(player)
            w_angle = rng.uniform(0, 2 * np.pi)

            player_frame = self._build_mode3_frame(player, w_angle)

            product = player_frame @ player_frame.T
            np.testing.assert_allclose(product, np.eye(4), atol=1e-8,
                err_msg="Frame not orthonormal from build_fixed_y_frame")

    def test_screen_y_stable_under_w_angle_change(self):
        """Screen Y coords don't change when changing w_angle."""
        rng = np.random.default_rng(302)
        player = np.array([1.0, 0.0, 0.0, 0.0])

        test_points = []
        for _ in range(10):
            p = rng.standard_normal(4)
            p /= np.linalg.norm(p)
            p = slerp(player, p, 0.05)
            p /= np.linalg.norm(p)
            test_points.append(p)

        def get_screen_y_values(w_angle):
            pf = self._build_mode3_frame(player, w_angle)
            return np.array([pt @ pf.T for pt in test_points])[:, 2]

        y_at_0 = get_screen_y_values(0.0)
        y_at_1 = get_screen_y_values(1.0)
        y_at_pi = get_screen_y_values(np.pi)

        np.testing.assert_allclose(y_at_0, y_at_1, atol=1e-10,
            err_msg="Screen Y changed with w_angle=1.0")
        np.testing.assert_allclose(y_at_0, y_at_pi, atol=1e-10,
            err_msg="Screen Y changed with w_angle=pi")


if __name__ == "__main__":
    unittest.main()
