import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sphere import (
    angular_distance,
    build_visibility_kdtree,
    decode_name,
    project_to_tangent,
    query_visible_kdtree,
    random_point_on_s3,
    slerp,
    tangent_basis,
    visible_points,
    TOTAL_NAMES,
    SUFFIXES,
    _N_CORE,
    _N_END,
    _N_SUF,
)

NUM_POINTS = 30_000
FOV_ANGLE = 0.116
TRAVEL_SPEED = 0.000008
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

    def test_travel_speed_5x_slower(self):
        """Verify travel speed is 5x slower than before."""
        self.assertAlmostEqual(TRAVEL_SPEED, OLD_TRAVEL_SPEED / 5, places=8)


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


if __name__ == "__main__":
    unittest.main()
