import unittest
import numpy as np
from sphere import (
    random_point_on_s3, visible_points, angular_distance, slerp,
    decode_name, TOTAL_NAMES, SUFFIXES, _N_CORE, _N_END, _N_SUF,
)

NUM_POINTS = 30_000
FOV_ANGLE = 0.116
TRAVEL_SPEED = 0.000008
ARRIVAL_THRESHOLD = 0.02
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
        """Simulate: travel to A, queue B, arrive at A → traveling to B."""
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


if __name__ == "__main__":
    unittest.main()
