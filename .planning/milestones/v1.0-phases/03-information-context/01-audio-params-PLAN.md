---
phase: 03-information-context
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [audio.py]
autonomous: true
requirements: [INFO-01]

must_haves:
  truths:
    - "Audio parameters for any point can be extracted by name_key without generating the full audio signal"
  artifacts:
    - path: "audio.py"
      provides: "get_audio_params() function and timbre/scale friendly name mappings"
      section: "New function after generate_signal()"
  key_links:
    - from: "audio.py:get_audio_params"
      to: "audio.py:generate_signal"
      via: "Replays same RNG sequence to extract parameters without synthesis"
      pattern: "rng = np.random.default_rng\\(name_key\\)"
---

<objective>
Add a function to extract audio parameters (timbre name, scale name, root note, tempo description) from a name_key without synthesizing the full signal.

Purpose: The detail panel (Plan 02) needs human-readable audio summary text for each point.

Output:
- `get_audio_params(name_key)` function returning a dict with friendly labels (audio.py)
- Timbre and scale name lookup constants
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

The `generate_signal()` function (audio.py:234-279) uses a seeded RNG that deterministically selects:
1. `midi = rng.integers(25, 71)` → root frequency
2. `timbre = _TIMBRES[rng.integers(len(_TIMBRES))]` → one of 10 synth functions
3. `scale = SCALES[rng.integers(len(SCALES))]` → one of 12 scales
4. `tempo_range = TEMPO_RANGES[rng.integers(len(TEMPO_RANGES))]` → one of 5 tempo ranges

The same RNG calls in the same order will reproduce identical parameter selections.

Timbre functions are:
```python
_TIMBRES = [
    _synth_supersaw, _synth_acid, _synth_pluck, _synth_fm,
    _synth_noise_drone, _synth_ring_mod, _synth_pwm, _synth_organ,
    _synth_wavefold, _synth_stutter,
]
```

Scale names (in order of SCALES list):
pentatonic minor, pentatonic major, suspended, dorian, phrygian, whole tone, blues, harmonic minor, lydian, mixolydian, locrian, japanese in-sen
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add timbre and scale name constants and get_audio_params function</name>
  <files>audio.py</files>
  <action>
    Add two name-mapping tuples and `get_audio_params()` to audio.py.

    After the `_TIMBRES` list (line 228), add:

    ```python
    _TIMBRE_NAMES = (
        "Supersaw pad", "Acid bass", "Synth pluck", "FM bass",
        "Noise drone", "Ring mod", "PWM synth", "Organ",
        "Wavefold", "Stutter",
    )

    _SCALE_NAMES = (
        "Pentatonic minor", "Pentatonic major", "Suspended", "Dorian",
        "Phrygian", "Whole tone", "Blues", "Harmonic minor",
        "Lydian", "Mixolydian", "Locrian", "Japanese in-sen",
    )

    _TEMPO_LABELS = ("Ambient", "Slow", "Medium", "Fast", "Glitchy")
    ```

    Then after `generate_sound()` (after line 286), add:

    ```python
    def get_audio_params(name_key: int) -> dict:
        """Extract audio parameters for a point without generating the signal.

        Replays the same RNG sequence as generate_signal() to extract
        timbre, scale, root note, and tempo selections.
        """
        rng = np.random.default_rng(name_key)
        midi = int(rng.integers(25, 71))
        timbre_idx = int(rng.integers(len(_TIMBRES)))
        scale_idx = int(rng.integers(len(SCALES)))
        tempo_idx = int(rng.integers(len(TEMPO_RANGES)))
        root_hz = 440.0 * 2 ** ((midi - 69) / 12.0)
        return {
            "timbre": _TIMBRE_NAMES[timbre_idx],
            "scale": _SCALE_NAMES[scale_idx],
            "tempo": _TEMPO_LABELS[tempo_idx],
            "root_hz": round(root_hz, 1),
            "midi": midi,
            "summary": f"{_TIMBRE_NAMES[timbre_idx]} in {_SCALE_NAMES[scale_idx].lower()}",
        }
    ```

    The key correctness requirement: the first 4 RNG calls must match `generate_signal()` exactly (integers(25,71), integers(10), integers(12), integers(5)) so the extracted params match the actual generated audio.
  </action>
  <verify>
    <manual>
      Quick smoke test in Python REPL:
      ```python
      from audio import get_audio_params
      p = get_audio_params(42)
      print(p)  # Should show timbre, scale, tempo, root_hz, midi, summary
      # Verify summary is human-readable like "Acid bass in blues"
      ```
    </manual>
  </verify>
  <done>
    - `get_audio_params()` extracts timbre/scale/tempo/root without synthesis
    - Name mappings align with `_TIMBRES` and `SCALES` list order
    - RNG replay matches `generate_signal()` parameter selection sequence
  </done>
</task>

</tasks>

<verification>
After completion, verify:

1. **RNG sequence match:** `get_audio_params(key)` extracts the same timbre/scale as `generate_signal(key)` would use (verify by adding a temporary print in generate_signal)
2. **All 10 timbres named:** `_TIMBRE_NAMES` has exactly 10 entries matching `_TIMBRES` order
3. **All 12 scales named:** `_SCALE_NAMES` has exactly 12 entries matching `SCALES` order
4. **Summary format:** Returns "Timbre name in scale name" string ready for display
</verification>

<success_criteria>
- `get_audio_params(name_key)` returns correct timbre/scale/tempo for any valid name_key
- RNG sequence is identical to the first 4 calls in `generate_signal()`
- Summary string is human-readable (e.g., "Acid bass in blues")
- No audio synthesis performed (function is fast)
</success_criteria>

<output>
After completion, create `.planning/phases/03-information-context/01-SUMMARY.md`
</output>
