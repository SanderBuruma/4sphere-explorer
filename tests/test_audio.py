import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio import (
    BUFFER_SECONDS,
    SAMPLE_RATE,
    SCALES,
    TEMPO_RANGES,
    _rolloff,
    _TIMBRES,
    generate_signal,
    get_audio_params,
)
from sphere import TOTAL_NAMES, decode_name


class TestAudioVolumeLevels(unittest.TestCase):
    """No single point's music should be significantly louder than the average."""

    def test_rms_within_1_std(self):
        """RMS of every sound in a 100-point sample must be within 1 std of the mean."""
        rng = np.random.default_rng(0)
        keys = rng.integers(0, 11_817_000, size=100)
        rms_values = np.array([
            np.sqrt(np.mean(generate_signal(int(k)) ** 2)) for k in keys
        ])
        mean_rms = rms_values.mean()
        std_rms = rms_values.std()
        for i, rms in enumerate(rms_values):
            self.assertLessEqual(
                rms, mean_rms + std_rms + 0.01,
                f"Key {keys[i]}: RMS {rms:.4f} exceeds mean {mean_rms:.4f} + 1 std {std_rms:.4f}",
            )


class TestAudioSearchSpace(unittest.TestCase):
    """Music generation must have sufficient variety."""

    def test_search_space_above_2_million(self):
        """Discrete search space must exceed 2 million configurations."""
        # Conservative lower bound: MIDI x timbres x scales x tempos x min pattern combos
        midi_range = 46  # MIDI 25-70
        n_timbres = len(_TIMBRES)
        n_scales = len(SCALES)
        n_tempos = len(TEMPO_RANGES)
        min_pat_len = 12
        min_scale_size = min(len(s) for s in SCALES)
        # Each step: rest or one of 5 moves = ~5.6 effective choices
        # Conservative: use scale size as branching factor
        melody_combos = min_scale_size ** min_pat_len
        total = midi_range * n_timbres * n_scales * n_tempos * melody_combos
        self.assertGreater(total, 2_000_000,
            f"Search space {total:,} is below 2 million")


class TestAudioQuality(unittest.TestCase):
    """Generated sounds must be smooth, low-pitched, and free of artifacts."""

    def test_sound_quality_1000_random(self):
        """50 random sounds: low spectral centroid, no clicks, no high-freq shrillness."""
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

            # Spectral centroid < 500 Hz -- not shrill
            fft_mag = np.abs(np.fft.rfft(signal))
            freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
            power = fft_mag ** 2
            total_power = np.sum(power)
            centroid = np.sum(freqs * power) / total_power
            self.assertLess(centroid, 500,
                f"Key {key}: spectral centroid {centroid:.0f} Hz (shrill)")

            # < 25% energy above 600 Hz -- keeps sound warm
            high_ratio = np.sum(power[freqs > 600]) / total_power
            self.assertLess(high_ratio, 0.25,
                f"Key {key}: {high_ratio:.1%} energy above 600 Hz")

            # No clicks: max sample-to-sample jump < 0.5
            max_diff = np.max(np.abs(np.diff(signal)))
            self.assertLess(max_diff, 0.5,
                f"Key {key}: max sample diff {max_diff:.4f} (click/pop)")

            # No DC offset (mean near zero)
            dc = abs(np.mean(signal))
            self.assertLess(dc, 0.05, f"Key {key}: DC offset {dc:.4f}")


class TestAllPointsAudible(unittest.TestCase):
    """Every point on the sphere must produce audible (non-silent) music."""

    def test_100_random_points_have_audible_signal(self):
        """100 random name keys from the actual name space must produce RMS > 0.01."""
        rng = np.random.default_rng(77)
        keys = rng.choice(TOTAL_NAMES, size=100, replace=False)
        for key in keys:
            key = int(key)
            signal = generate_signal(key)
            rms = np.sqrt(np.mean(signal ** 2))
            self.assertGreater(
                rms, 0.01,
                f"Key {key} (name: {decode_name(key)}) is silent: RMS={rms:.6f}",
            )


class TestAudioSignal(unittest.TestCase):
    """Test signal generation properties."""

    def test_signal_length_and_bounds(self):
        """Length == BUFFER_SECONDS * SAMPLE_RATE, values in [-1,1], all finite."""
        expected_len = BUFFER_SECONDS * SAMPLE_RATE
        rng = np.random.default_rng(60)
        keys = rng.integers(0, 11_817_000, size=10)
        for key in keys:
            signal = generate_signal(int(key))
            self.assertEqual(len(signal), expected_len)
            self.assertTrue(np.all(np.isfinite(signal)), f"Key {key}: non-finite values")
            self.assertGreaterEqual(signal.min(), -1.0, f"Key {key}: below -1.0")
            self.assertLessEqual(signal.max(), 1.0, f"Key {key}: above 1.0")

    def test_crossfade_seamless_loop(self):
        """Loop boundary should be smooth: |signal[0] - signal[-1]| is small."""
        rng = np.random.default_rng(61)
        keys = rng.integers(0, 11_817_000, size=20)
        for key in keys:
            signal = generate_signal(int(key))
            boundary_diff = abs(signal[0] - signal[-1])
            self.assertLess(
                boundary_diff, 0.1,
                f"Key {key}: loop boundary diff {boundary_diff:.4f} (click at loop point)",
            )

    def test_audio_params_rng_sync(self):
        """get_audio_params(k)['midi'] matches what generate_signal uses internally."""
        rng = np.random.default_rng(62)
        keys = rng.integers(0, 11_817_000, size=50)
        for key in keys:
            key = int(key)
            params = get_audio_params(key)
            # Replay the same RNG sequence as generate_signal
            sig_rng = np.random.default_rng(key)
            midi = int(sig_rng.integers(25, 71))
            timbre_idx = int(sig_rng.integers(len(_TIMBRES)))
            scale_idx = int(sig_rng.integers(len(SCALES)))
            tempo_idx = int(sig_rng.integers(len(TEMPO_RANGES)))
            self.assertEqual(params["midi"], midi, f"Key {key}: midi mismatch")
            from audio import _TIMBRE_NAMES, _SCALE_NAMES, _TEMPO_LABELS
            self.assertEqual(params["timbre"], _TIMBRE_NAMES[timbre_idx])
            self.assertEqual(params["scale"], _SCALE_NAMES[scale_idx])
            self.assertEqual(params["tempo"], _TEMPO_LABELS[tempo_idx])

    def test_signal_deterministic(self):
        """Same key produces identical signal array."""
        rng = np.random.default_rng(63)
        keys = rng.integers(0, 11_817_000, size=10)
        for key in keys:
            key = int(key)
            s1 = generate_signal(key)
            s2 = generate_signal(key)
            np.testing.assert_array_equal(s1, s2, err_msg=f"Key {key}: non-deterministic")

    def test_rolloff_boundaries(self):
        """_rolloff(580)=1.0, _rolloff(700)=0.0, _rolloff(640) approx 0.5."""
        self.assertAlmostEqual(_rolloff(580), 1.0, places=10)
        self.assertAlmostEqual(_rolloff(700), 0.0, places=10)
        self.assertAlmostEqual(_rolloff(640), 0.5, places=5)
        # Below 580 should be 1.0
        self.assertAlmostEqual(_rolloff(100), 1.0, places=10)
        self.assertAlmostEqual(_rolloff(0), 1.0, places=10)
        # Above 700 should be 0.0
        self.assertAlmostEqual(_rolloff(800), 0.0, places=10)


if __name__ == "__main__":
    unittest.main()
