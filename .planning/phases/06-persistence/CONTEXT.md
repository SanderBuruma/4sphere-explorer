# Phase 6 Context: Persistence

**Phase Goal**: Game state saves automatically on quit and loads on startup, so the player resumes where they left off
**Requirements**: SAVE-01

---

## Decisions

### 1. Save Format: JSON

**Why JSON over pickle**: Human-readable, debuggable, no security risk from untrusted deserialization. Numpy arrays convert via `.tolist()`.

**Why not SQLite**: Overkill for a single save file with ~30k max entries in reputation store.

### 2. Save Location

`saves/autosave.json` in the project directory. Simple, visible, gitignored.

### 3. Auto-save on Quit Only

Save triggers on pygame QUIT event (window close). No periodic auto-save — the game state is small and quit is the natural save point.

Load triggers on startup before the game loop.

### 4. What Gets Saved

**Critical** (required by SAVE-01):
- `player_pos` — 4D position on S3
- `orientation` — 4x4 orthogonal frame
- `reputation_store` — sparse dict (score, visits per creature)
- `visited_planets` — set of visited indices
- `visit_history` — deque of recent 50 visits

**Convenience** (nice to have):
- `view_mode` — which color mode was active
- `view_zoom` — zoom level

**Not saved** (regenerated deterministically):
- `planets`, `_name_keys`, `planet_colors` — from GAME_SEED
- Caches (creatures, names, textures) — rebuilt on demand
- Travel state — resume stationary at last position
- Transient UI state (menu, hover, gamepedia scroll)

### 5. Version Field

Save file includes `"version": 1` for future migration if the format changes.

### 6. Graceful Degradation

Missing or corrupt save file → start fresh (default position, empty reputation). Log a warning, never crash.

---

## Code Context

**Game loop quit**: `main.py` — `pygame.QUIT` event handler triggers cleanup
**State initialization**: `main.py` lines 65-113 — all mutable state declared here
**Reputation store**: `lib/reputation.py` — pure data functions, store is a plain dict
**Numpy arrays**: `player_pos` (4-vector), `orientation` (4x4 matrix) — convert with `.tolist()`/`np.array()`

---

## Deferred Ideas

- Multiple save slots — unnecessary for single-player explorer
- Cloud saves — local-only project
- Periodic auto-save — quit-only is sufficient for now
- Save file compression — JSON is small enough

---
*Created: 2026-03-11*
