# Plan 01: Save/Load System

**Phase:** 6 — Persistence
**Requirements:** SAVE-01
**Goal:** Game state (reputation, visit counts, player position, orientation) saves to disk on quit and loads on startup

---

## Tasks

### 1. Create `lib/persistence.py` — save/load module

New file with:

```python
import json
import os
import numpy as np

SAVE_DIR = "saves"
SAVE_FILE = os.path.join(SAVE_DIR, "autosave.json")
SAVE_VERSION = 1

def save_game(player_pos, orientation, reputation_store, visited_planets, visit_history, view_mode=0, view_zoom=1.0):
    """Serialize game state to JSON file."""

def load_game():
    """Deserialize game state from JSON file.
    Returns dict with all saved fields, or None if no save exists / load fails."""

def _serialize_state(player_pos, orientation, reputation_store, visited_planets, visit_history, view_mode, view_zoom) -> dict:
    """Build save dict. Separated for testability."""

def _deserialize_state(data: dict) -> dict:
    """Parse save dict back into game types. Separated for testability."""
```

**Serialization details:**
- `player_pos`: `np.ndarray` → list of 4 floats via `.tolist()`
- `orientation`: `np.ndarray` (4x4) → nested list via `.tolist()`
- `reputation_store`: `dict[int, dict]` → JSON dict with string keys (JSON requirement); convert back to int keys on load
- `visited_planets`: `set[int]` → sorted list; convert back to `set()` on load
- `visit_history`: `deque[int]` → list; convert back to `deque(maxlen=50)` on load
- `view_mode`: `int` → stored directly
- `view_zoom`: `float` → stored directly

**Save file structure:**
```json
{
  "version": 1,
  "player_pos": [1.0, 0.0, 0.0, 0.0],
  "orientation": [[...], [...], [...], [...]],
  "reputation_store": {
    "42": {"score": 5, "visits": 3, "talked_this_visit": false},
    "127": {"score": 1, "visits": 1, "talked_this_visit": false}
  },
  "visited_planets": [0, 42, 127],
  "visit_history": [0, 42, 127],
  "view_mode": 0,
  "view_zoom": 1.0
}
```

**Error handling:**
- `save_game`: create `saves/` dir if missing (`os.makedirs`). Write to temp file then rename (atomic write) to prevent corruption on crash during write.
- `load_game`: return `None` on missing file, invalid JSON, or missing required keys. Print warning to stderr. Never raise.

### 2. Add `.gitignore` entry for saves directory

Append `saves/` to `.gitignore` if not already present.

### 3. Hook save into quit handler (`main.py`)

In the `pygame.QUIT` event handler:
```python
from lib.persistence import save_game
save_game(player_pos, orientation, reputation_store, visited_planets, visit_history, view_mode, view_zoom)
```

Also hook save on `KeyboardInterrupt` (Ctrl+C) in the outer try/finally of the game loop.

### 4. Hook load into startup (`main.py`)

After all state variables are initialized (defaults), before the game loop:
```python
from lib.persistence import load_game
save_data = load_game()
if save_data:
    player_pos = save_data["player_pos"]
    orientation = save_data["orientation"]
    reputation_store = save_data["reputation_store"]
    visited_planets = save_data["visited_planets"]
    visit_history = save_data["visit_history"]
    view_mode = save_data.get("view_mode", 0)
    view_zoom = save_data.get("view_zoom", 1.0)
```

After loading position/orientation, recompute `camera_pos` from `orientation[0]` and trigger `update_visible()` to populate the view with the restored position.

### 5. Add tests (`tests/test_persistence.py`)

Test `_serialize_state` and `_deserialize_state` (pure functions, no disk I/O needed for most tests):

- **Round-trip**: serialize → deserialize produces identical game state (numpy array equality, set equality, deque equality)
- **Reputation key conversion**: int keys → string keys → int keys survives round-trip
- **Numpy precision**: player_pos and orientation values survive JSON serialization without unacceptable drift (float64 → JSON float → float64)
- **Empty state**: empty reputation_store, empty visited_planets, empty visit_history serializes and deserializes correctly
- **Large state**: 1000-entry reputation_store round-trips correctly
- **Version field**: save data includes `"version": 1`
- **Missing file**: `load_game()` returns `None` when no save file exists
- **Corrupt file**: `load_game()` returns `None` on invalid JSON (use tmp file with garbage)
- **Partial save**: `load_game()` returns `None` when required keys are missing
- **Atomic write**: save creates file that exists after completion (basic existence check)
- **Directory creation**: `save_game` creates `saves/` dir if it doesn't exist

Use `tmp_path` pytest fixture for file I/O tests to avoid polluting the project directory.

### 6. Update Gamepedia

Add a "Saving" topic under the "Controls" or "UI" group in `lib/gamepedia.py` `GAMEPEDIA_CONTENT`:

```
"Saving": "Your progress saves automatically when you close the game. This includes your position, orientation, reputation with creatures, and visit history. The next time you launch, you'll resume exactly where you left off."
```

Update `tests/test_gamepedia.py` topic count if the group count changes.

---

## Acceptance Criteria

- [SAVE-01] Game state saves to disk on quit — `saves/autosave.json` created
- [SAVE-01] Game state loads from disk on startup — player resumes at saved position with saved reputation
- Missing/corrupt save file does not crash the game — starts fresh with defaults
- Reputation store, visited set, and visit history persist across sessions
- All tests pass

---

## Files Modified

| File | Change |
|------|--------|
| `lib/persistence.py` | **NEW** — save/load/serialize/deserialize functions |
| `main.py` | Import persistence, save on quit, load on startup, recompute derived state after load |
| `.gitignore` | Add `saves/` |
| `lib/gamepedia.py` | Add "Saving" topic |
| `tests/test_persistence.py` | **NEW** — round-trip, error handling, edge case tests |
| `tests/test_gamepedia.py` | Update topic count if needed |
