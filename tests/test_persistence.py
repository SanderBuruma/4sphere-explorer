"""Tests for save/load persistence system."""
import json
import os
import unittest
from collections import deque

import numpy as np

from lib.persistence import (
    SAVE_VERSION, _serialize_state, _deserialize_state, save_game, load_game,
)


def _make_state():
    """Return a representative game state tuple."""
    player_pos = np.array([0.5, 0.5, 0.5, 0.5])
    player_pos /= np.linalg.norm(player_pos)
    orientation = np.eye(4)
    reputation_store = {
        42: {"score": 5, "visits": 3, "talked_this_visit": False},
        127: {"score": 1, "visits": 1, "talked_this_visit": True},
    }
    visited_planets = {0, 42, 127}
    visit_history = deque([0, 42, 127], maxlen=50)
    return player_pos, orientation, reputation_store, visited_planets, visit_history


class TestSerializeDeserialize(unittest.TestCase):

    def test_round_trip(self):
        """serialize -> deserialize produces identical state."""
        pos, ori, rep, vis, hist = _make_state()
        data = _serialize_state(pos, ori, rep, vis, hist, 1.5, 0.75)
        result = _deserialize_state(data)
        np.testing.assert_array_almost_equal(result["player_pos"], pos)
        np.testing.assert_array_almost_equal(result["orientation"], ori)
        self.assertEqual(result["reputation_store"], rep)
        self.assertEqual(result["visited_planets"], vis)
        self.assertEqual(list(result["visit_history"]), list(hist))
        self.assertAlmostEqual(result["view_zoom"], 1.5)
        self.assertAlmostEqual(result["xyz_w_angle"], 0.75)

    def test_reputation_key_conversion(self):
        """Int keys -> string keys -> int keys survives round-trip."""
        pos, ori, rep, vis, hist = _make_state()
        data = _serialize_state(pos, ori, rep, vis, hist)
        # JSON keys are strings
        for k in data["reputation_store"]:
            self.assertIsInstance(k, str)
        result = _deserialize_state(data)
        for k in result["reputation_store"]:
            self.assertIsInstance(k, int)

    def test_numpy_precision(self):
        """float64 values survive JSON round-trip."""
        pos = np.array([0.123456789012345, 0.987654321098765, 0.111111111111111, 0.222222222222222])
        pos /= np.linalg.norm(pos)
        ori = np.eye(4) * 0.999999999999999
        data = _serialize_state(pos, ori, {}, set(), deque(maxlen=50))
        # Simulate JSON round-trip
        json_str = json.dumps(data)
        data2 = json.loads(json_str)
        result = _deserialize_state(data2)
        np.testing.assert_array_almost_equal(result["player_pos"], pos, decimal=12)

    def test_empty_state(self):
        """Empty reputation, visited, history serializes correctly."""
        pos = np.array([1.0, 0.0, 0.0, 0.0])
        ori = np.eye(4)
        data = _serialize_state(pos, ori, {}, set(), deque(maxlen=50))
        result = _deserialize_state(data)
        self.assertEqual(result["reputation_store"], {})
        self.assertEqual(result["visited_planets"], set())
        self.assertEqual(len(result["visit_history"]), 0)

    def test_large_reputation_store(self):
        """1000-entry reputation_store round-trips."""
        pos = np.array([1.0, 0.0, 0.0, 0.0])
        ori = np.eye(4)
        rep = {i: {"score": i % 11, "visits": i, "talked_this_visit": False} for i in range(1000)}
        data = _serialize_state(pos, ori, rep, set(), deque(maxlen=50))
        result = _deserialize_state(data)
        self.assertEqual(len(result["reputation_store"]), 1000)
        self.assertEqual(result["reputation_store"][999]["score"], 999 % 11)

    def test_version_field(self):
        """Save data includes version field."""
        pos, ori, rep, vis, hist = _make_state()
        data = _serialize_state(pos, ori, rep, vis, hist)
        self.assertEqual(data["version"], SAVE_VERSION)

    def test_deserialize_missing_keys(self):
        """Missing required keys returns None."""
        result = _deserialize_state({"version": 1, "player_pos": [1, 0, 0, 0]})
        self.assertIsNone(result)

    def test_visit_history_maxlen(self):
        """Deserialized visit_history has maxlen=50."""
        pos = np.array([1.0, 0.0, 0.0, 0.0])
        ori = np.eye(4)
        data = _serialize_state(pos, ori, {}, set(), deque(range(50), maxlen=50))
        result = _deserialize_state(data)
        self.assertEqual(result["visit_history"].maxlen, 50)


class TestFileIO(unittest.TestCase):

    def test_save_and_load(self, tmp_path=None):
        """save_game creates file, load_game reads it back."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            pos, ori, rep, vis, hist = _make_state()
            save_game(pos, ori, rep, vis, hist, view_zoom=1.5, save_file=path)
            self.assertTrue(os.path.exists(path))
            result = load_game(save_file=path)
            self.assertIsNotNone(result)
            np.testing.assert_array_almost_equal(result["player_pos"], pos)
            self.assertEqual(result["reputation_store"], rep)

    def test_missing_file(self):
        """load_game returns None for nonexistent file."""
        result = load_game(save_file="/tmp/nonexistent_4sphere_save.json")
        self.assertIsNone(result)

    def test_corrupt_file(self):
        """load_game returns None on invalid JSON."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            result = load_game(save_file=path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_partial_save(self):
        """load_game returns None when required keys missing."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": 1, "player_pos": [1, 0, 0, 0]}, f)
            path = f.name
        try:
            result = load_game(save_file=path)
            self.assertIsNone(result)
        finally:
            os.unlink(path)

    def test_directory_creation(self):
        """save_game creates directory if it doesn't exist."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "subdir", "test.json")
            pos = np.array([1.0, 0.0, 0.0, 0.0])
            ori = np.eye(4)
            save_game(pos, ori, {}, set(), deque(maxlen=50), save_file=path)
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
