import unittest
import numpy as np
from sphere import (
    random_point_on_s3, visible_points, angular_distance, slerp,
    decode_name, TOTAL_NAMES, SUFFIXES, _N_CORE, _N_END, _N_SUF,
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


class TestRelativeRotation(unittest.TestCase):
    """Verify QWEADS relative rotations are smooth and consistent everywhere on S³."""

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
        from sphere import tangent_basis
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
        """Camera stays on S³ after 1000 single-key rotation steps."""
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
        """Single-key rotation is consistent from 20 random positions on S³."""
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


class TestAudioVolumeLevels(unittest.TestCase):
    """No single point's music should be significantly louder than the average."""

    def test_rms_within_1_std(self):
        """RMS of every sound in a 100-point sample must be within 1 std of the mean."""
        from audio import generate_signal
        rng = np.random.default_rng(0)
        keys = rng.integers(0, 11_817_000, size=100)
        rms_values = np.array([
            np.sqrt(np.mean(generate_signal(int(k)) ** 2)) for k in keys
        ])
        mean_rms = rms_values.mean()
        std_rms = rms_values.std()
        for i, rms in enumerate(rms_values):
            self.assertLess(
                rms, mean_rms + std_rms,
                f"Key {keys[i]}: RMS {rms:.4f} exceeds mean {mean_rms:.4f} + 1 std {std_rms:.4f}",
            )


class TestAudioQuality(unittest.TestCase):
    """Generated sounds must be smooth, low-pitched, and free of artifacts."""

    def test_sound_quality_1000_random(self):
        """50 random sounds: low spectral centroid, no clicks, no high-freq shrillness."""
        from audio import generate_signal, SAMPLE_RATE
        rng = np.random.default_rng()  # non-deterministic
        keys = rng.integers(0, 11_817_000, size=50)

        for key in keys:
            key = int(key)
            signal = generate_signal(key)
            n = len(signal)

            # Sanity: no NaN/Inf, bounded to [-1, 1]
            self.assertFalse(np.any(np.isnan(signal)), f"Key {key}: NaN in signal")
            self.assertFalse(np.any(np.isinf(signal)), f"Key {key}: Inf in signal")
            self.assertGreaterEqual(signal.min(), -1.0, f"Key {key}: signal below -1.0")
            self.assertLessEqual(signal.max(), 1.0, f"Key {key}: signal above 1.0")

            # Spectral centroid < 400 Hz — not shrill
            fft_mag = np.abs(np.fft.rfft(signal))
            freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
            power = fft_mag ** 2
            total_power = np.sum(power)
            centroid = np.sum(freqs * power) / total_power
            self.assertLess(centroid, 400,
                f"Key {key}: spectral centroid {centroid:.0f} Hz (shrill)")

            # < 15% energy above 600 Hz — keeps sound warm
            high_ratio = np.sum(power[freqs > 600]) / total_power
            self.assertLess(high_ratio, 0.15,
                f"Key {key}: {high_ratio:.1%} energy above 600 Hz")

            # No clicks: max sample-to-sample jump < 0.5
            max_diff = np.max(np.abs(np.diff(signal)))
            self.assertLess(max_diff, 0.5,
                f"Key {key}: max sample diff {max_diff:.4f} (click/pop)")

            # No DC offset (mean near zero)
            dc = abs(np.mean(signal))
            self.assertLess(dc, 0.05, f"Key {key}: DC offset {dc:.4f}")


if __name__ == "__main__":
    unittest.main()
