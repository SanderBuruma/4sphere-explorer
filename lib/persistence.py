"""Save/load game state to JSON file."""
import json
import os
import sys
import tempfile
from collections import deque

import numpy as np

SAVE_DIR = "saves"
SAVE_FILE = os.path.join(SAVE_DIR, "autosave.json")
SAVE_VERSION = 1

REQUIRED_KEYS = {"version", "player_pos", "orientation", "reputation_store",
                 "visited_planets", "visit_history"}


def _serialize_state(player_pos, orientation, reputation_store, visited_planets,
                     visit_history, view_zoom=1.0, xyz_w_angle=0.0):
    """Build save dict from game state."""
    return {
        "version": SAVE_VERSION,
        "player_pos": player_pos.tolist(),
        "orientation": orientation.tolist(),
        "reputation_store": {str(k): v for k, v in reputation_store.items()},
        "visited_planets": sorted(visited_planets),
        "visit_history": list(visit_history),
        "view_zoom": view_zoom,
        "xyz_w_angle": xyz_w_angle,
    }


def _deserialize_state(data):
    """Parse save dict back into game types. Returns dict or None on failure."""
    if not REQUIRED_KEYS.issubset(data.keys()):
        return None
    return {
        "player_pos": np.array(data["player_pos"], dtype=np.float64),
        "orientation": np.array(data["orientation"], dtype=np.float64),
        "reputation_store": {int(k): v for k, v in data["reputation_store"].items()},
        "visited_planets": set(data["visited_planets"]),
        "visit_history": deque(data["visit_history"], maxlen=50),
        "view_zoom": data.get("view_zoom", 1.0),
        "xyz_w_angle": data.get("xyz_w_angle", 0.0),
    }


def save_game(player_pos, orientation, reputation_store, visited_planets,
              visit_history, view_zoom=1.0, xyz_w_angle=0.0, save_file=None):
    """Serialize game state to JSON file. Atomic write via temp file + rename."""
    save_file = save_file or SAVE_FILE
    save_dir = os.path.dirname(save_file)
    os.makedirs(save_dir, exist_ok=True)
    data = _serialize_state(player_pos, orientation, reputation_store,
                            visited_planets, visit_history, view_zoom,
                            xyz_w_angle)
    fd, tmp_path = tempfile.mkstemp(dir=save_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, save_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_game(save_file=None):
    """Deserialize game state from JSON file.
    Returns dict with all saved fields, or None if no save / load fails."""
    save_file = save_file or SAVE_FILE
    try:
        with open(save_file, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"[persistence] Could not load save: {e}", file=sys.stderr)
        return None
    result = _deserialize_state(data)
    if result is None:
        print("[persistence] Save file missing required keys", file=sys.stderr)
    return result
