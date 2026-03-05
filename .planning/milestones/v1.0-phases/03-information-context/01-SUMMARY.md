---
phase: 03-information-context
plan: 01
subsystem: audio
tags: [audio-params, parameter-extraction, info-panel-prep]
dependency_graph:
  requires: []
  provides: [get_audio_params-function, timbre-scale-tempo-names]
  affects: [03-02-detail-panel]
tech_stack:
  patterns: [RNG-replay, deterministic-parameter-selection]
  added: [name-mapping-tuples, parameter-extraction-function]
key_files:
  created: []
  modified: [audio.py]
decisions: []
metrics:
  duration: "5 min"
  completed_date: 2026-03-05
---

# Phase 3 Plan 1: Audio Parameter Extraction Summary

**One-liner:** Parameter extraction function for audio without synthesis, enabling human-readable audio metadata for the detail panel.

## What Was Built

Added `get_audio_params(name_key)` function to `audio.py` that extracts audio parameters (timbre, scale, tempo, root frequency) from any point's name_key by replaying the same RNG sequence as `generate_signal()`, but without the expensive audio synthesis.

### Components Added

1. **Name mapping tuples** (lines 230–242):
   - `_TIMBRE_NAMES`: 10 friendly names for synth timbres (Supersaw pad, Acid bass, etc.)
   - `_SCALE_NAMES`: 12 friendly names for scales (Pentatonic minor, Dorian, etc.)
   - `_TEMPO_LABELS`: 5 friendly labels for tempo ranges (Ambient, Slow, Medium, Fast, Glitchy)

2. **`get_audio_params(name_key: int) -> dict`** (lines 303–322):
   - Instantiates RNG with name_key
   - Extracts 4 parameters in exact same order as `generate_signal()`:
     1. MIDI note (25–70)
     2. Timbre index → friendly name
     3. Scale index → friendly name
     4. Tempo index → friendly label
   - Computes root frequency in Hz from MIDI
   - Returns dict with keys: `timbre`, `scale`, `tempo`, `root_hz`, `midi`, `summary`
   - Summary string: "Timbre name in scale name" (e.g., "Organ in harmonic minor")

## Verification

### RNG Sequence Correctness
Tested that the first 4 RNG calls in `get_audio_params()` perfectly match those in `generate_signal()`:
- Both use `np.random.default_rng(name_key)` with same key
- Both call `integers(25, 71)` for MIDI
- Both call `integers(len(_TIMBRES))` for timbre
- Both call `integers(len(SCALES))` for scale
- Both call `integers(len(TEMPO_RANGES))` for tempo
- Verified for key=42: both extract MIDI=29, Organ (idx 7), Harmonic minor (idx 7), Medium (idx 2)

### Name Mapping Counts
All mappings have correct counts:
- 10 timbres → 10 names ✓
- 12 scales → 12 names ✓
- 5 tempo ranges → 5 labels ✓

### Output Format
Sample output from `get_audio_params(42)`:
```python
{
    'timbre': 'Organ',
    'scale': 'Harmonic minor',
    'tempo': 'Medium',
    'root_hz': 43.7,
    'midi': 29,
    'summary': 'Organ in harmonic minor'
}
```

## Deviations from Plan

None — plan executed exactly as written.

## Success Criteria

- [x] `get_audio_params(name_key)` extracts timbre/scale/tempo/root without synthesis
- [x] Name mappings align with `_TIMBRES` and `SCALES` list order
- [x] RNG replay matches `generate_signal()` parameter selection sequence
- [x] Function is fast (no audio generation, pure parameter extraction)
- [x] Summary string is human-readable

## What This Enables

Plan 02 (Detail Panel) now has a lightweight function to display audio metadata for any point without triggering audio synthesis. Enables the detail panel to show "This point plays an Organ in harmonic minor at 43.7 Hz with Medium tempo" without sound generation overhead.

## Files Modified

- `audio.py`: Added name mappings (14 lines) and `get_audio_params()` function (20 lines)

## Commits

- `f158f08`: feat(03-01): add get_audio_params function for parameter extraction
