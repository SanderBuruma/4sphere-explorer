import numpy as np
import pygame

SAMPLE_RATE = 44100
BUFFER_SECONDS = 15
CROSSFADE = 0.5  # seconds, for seamless loop boundary
AUDIO_RANGE = 0.010  # 10 mrad
MAX_CHANNELS = 8
MASTER_VOLUME = 0.7
HARMONIC_CAP = 700  # Hz, max frequency for explicit harmonic synthesis

SCALES = [
    [0, 4, 7],                 # major triad
    [0, 4, 7, 11],             # major 7th
    [0, 4, 7, 11, 14],         # major 9th
    [0, 2, 4, 7, 9],           # major pentatonic
    [0, 2, 4, 5, 7, 9, 11],    # ionian (major scale)
    [0, 2, 4, 6, 7, 9, 11],    # lydian
    [0, 2, 4, 5, 7, 9, 10],    # mixolydian
    [0, 4, 7, 10],             # dominant 7th
    [0, 4, 7, 9],              # major 6th
    [0, 2, 4, 7, 9, 11],       # major hexatonic
    [0, 4, 7, 14, 16],         # major triad + high 9th/10th
    [0, 2, 4, 7, 11],          # major add9
    [0, 3, 7],                 # minor triad
    [0, 3, 7, 10],             # minor 7th
    [0, 2, 3, 5, 7, 8, 11],    # harmonic minor
]

TEMPO_RANGES = [
    (2.5, 5.0),   # very slow / ambient
    (1.2, 2.5),   # slow
    (0.5, 1.2),   # medium
    (0.2, 0.5),   # fast
    (0.08, 0.2),  # very fast / glitchy
]

_sound_cache: dict[int, pygame.mixer.Sound] = {}
_active_channels: dict[int, pygame.mixer.Channel] = {}


def init_audio():
    pygame.mixer.set_num_channels(MAX_CHANNELS)


def _rolloff(h):
    """Gain for harmonic at freq h: full below 580, linear fade to 0 at HARMONIC_CAP."""
    if h <= 580:
        return 1.0
    return max(0.0, (HARMONIC_CAP - h) / (HARMONIC_CAP - 580))


def _synth_supersaw(f, t, rng, tempo_range):
    """5 detuned sawtooths, filter sweep — trance pad."""
    phase = rng.uniform(0, 2 * np.pi)
    detunes = [1.0 + rng.uniform(-0.015, 0.015) for _ in range(5)]
    voice = np.zeros_like(t)
    for d in detunes:
        for n in range(1, 12):
            h = f * d * n
            if h > HARMONIC_CAP:
                break
            voice += _rolloff(h) * np.sin(2 * np.pi * h * t + phase * n) / n
    sweep_period = rng.uniform(*tempo_range)
    sweep = 0.4 + 0.6 * np.sin(2 * np.pi / sweep_period * t + rng.uniform(0, 2 * np.pi))
    return voice / 5.0 * sweep


def _synth_acid(f, t, rng, tempo_range):
    """Square wave + resonant sweep — TB-303."""
    phase = rng.uniform(0, 2 * np.pi)
    voice = np.zeros_like(t)
    for n in range(1, 16, 2):
        h = f * n
        if h > HARMONIC_CAP:
            break
        voice += _rolloff(h) * np.sin(2 * np.pi * h * t + phase * n) / n
    sweep_period = rng.uniform(*tempo_range)
    sweep_phase = rng.uniform(0, 2 * np.pi)
    sweep = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi / sweep_period * t + sweep_phase))
    res_freq = f * (1.5 + 1.5 * (0.5 + 0.5 * np.sin(2 * np.pi / sweep_period * t + sweep_phase)))
    # Proper phase accumulation (not freq*t which creates runaway harmonics)
    res_phase = 2 * np.pi * np.cumsum(np.clip(res_freq, 0, 500)) / SAMPLE_RATE
    resonance = 0.4 * np.sin(res_phase)
    return voice * sweep + resonance


def _synth_pluck(f, t, rng, tempo_range):
    """Sharp attack, fast decay — arpeggiated stab."""
    phase = rng.uniform(0, 2 * np.pi)
    note_len = rng.uniform(*tempo_range)
    t_mod = t % note_len
    attack_time = max(0.003, note_len * 0.03)
    attack = np.minimum(t_mod / attack_time, 1.0)
    voice = np.zeros_like(t)
    for n in range(1, 10):
        h = f * n
        if h > HARMONIC_CAP:
            break
        h_decay = np.exp(-t_mod / (note_len * 0.2 / (1 + 0.3 * n)))
        voice += _rolloff(h) * np.sin(2 * np.pi * h * t + phase * n) * h_decay * attack / n**0.5
    return voice


def _synth_fm(f, t, rng, tempo_range):
    """Frequency modulation — deep evolving tone."""
    phase = rng.uniform(0, 2 * np.pi)
    max_ratio = max(1.0, HARMONIC_CAP / (f * 1.5))
    possible = [r for r in [1.0, 1.5, 2.0, 3.0] if r <= max_ratio]
    ratio = rng.choice(possible if possible else [1.0])
    mod_freq = f * ratio
    mod_period = rng.uniform(*tempo_range)
    mod_phase = rng.uniform(0, 2 * np.pi)
    mod_index = 0.2 + 0.4 * (0.5 + 0.5 * np.sin(2 * np.pi / mod_period * t + mod_phase))
    modulator = mod_index * np.sin(2 * np.pi * mod_freq * t + phase)
    voice = np.sin(2 * np.pi * f * t + modulator + phase * 0.7)
    lfo_period = rng.uniform(*tempo_range)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi / lfo_period * t + rng.uniform(0, 2 * np.pi))
    return voice * lfo


def _synth_noise_drone(f, t, rng, tempo_range):
    """Inharmonic cluster — dense shimmering drone."""
    voice = np.zeros_like(t)
    n_partials = rng.integers(6, 12)
    for _ in range(n_partials):
        partial_f = f * rng.uniform(0.5, 3.0)
        if partial_f > 580:
            continue
        phase = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.1, 0.4)
        voice += amp * np.sin(2 * np.pi * partial_f * t + phase)
    period = rng.uniform(*tempo_range)
    env = 0.5 + 0.5 * np.sin(2 * np.pi / period * t + rng.uniform(0, 2 * np.pi))
    return voice / max(n_partials * 0.15, 1) * env


def _synth_ring_mod(f, t, rng, tempo_range):
    """Ring modulation — metallic bell-like tones."""
    phase1 = rng.uniform(0, 2 * np.pi)
    phase2 = rng.uniform(0, 2 * np.pi)
    # Filter ratios so difference frequency stays below 580 Hz
    valid = [r for r in [1.1, 1.25, 1.5, 1.618, 2.0, 2.5, 3.0] if f * (r - 1) <= 580]
    ratio = rng.choice(valid if valid else [1.1])
    carrier = np.sin(2 * np.pi * f * t + phase1)
    modulator = np.sin(2 * np.pi * f * ratio * t + phase2)
    voice = carrier * modulator
    # Suppress upper sideband when it exceeds warm-sound threshold
    if f * (1 + ratio) > 580:
        voice = np.cos(2 * np.pi * abs(f - f * ratio) * t + (phase1 - phase2))
    period = rng.uniform(*tempo_range)
    env = 0.5 + 0.5 * np.sin(2 * np.pi / period * t + rng.uniform(0, 2 * np.pi))
    return voice * env


def _synth_pwm(f, t, rng, tempo_range):
    """Pulse width modulation — analog synth character."""
    phase = rng.uniform(0, 2 * np.pi)
    pwm_period = rng.uniform(*tempo_range)
    pwm_phase = rng.uniform(0, 2 * np.pi)
    duty = 0.3 + 0.4 * (0.5 + 0.5 * np.sin(2 * np.pi / pwm_period * t + pwm_phase))
    voice = np.zeros_like(t)
    for n in range(1, 16):
        h = f * n
        if h > HARMONIC_CAP:
            break
        coeff = 2 * np.sin(n * np.pi * duty) / (n * np.pi)
        voice += _rolloff(h) * coeff * np.sin(2 * np.pi * h * t + phase * n)
    return voice


def _synth_organ(f, t, rng, tempo_range):
    """Additive harmonics — warm organ tone."""
    phase = rng.uniform(0, 2 * np.pi)
    n_harmonics = rng.integers(4, 9)
    voice = np.zeros_like(t)
    active = 0
    for n in range(1, n_harmonics + 1):
        h = f * n
        if h > HARMONIC_CAP:
            break
        amp = rng.uniform(0.2, 1.0) / n**0.3
        voice += _rolloff(h) * amp * np.sin(2 * np.pi * h * t + phase * n)
        active += 1
    trem_period = rng.uniform(*tempo_range)
    trem = 0.7 + 0.3 * np.sin(2 * np.pi / trem_period * t + rng.uniform(0, 2 * np.pi))
    return voice / max(active**0.5, 1) * trem


def _synth_wavefold(f, t, rng, tempo_range):
    """Soft saturation — warm overdrive with evolving drive."""
    phase = rng.uniform(0, 2 * np.pi)
    base = np.sin(2 * np.pi * f * t + phase)
    # Scale drive inversely with frequency to keep harmonics in check
    max_drive = min(2.5, 580 / f)
    drive_range = max(0.3, max_drive - 1.0)
    drive_period = rng.uniform(*tempo_range)
    drive_phase = rng.uniform(0, 2 * np.pi)
    drive = 1.0 + drive_range * (0.5 + 0.5 * np.sin(2 * np.pi / drive_period * t + drive_phase))
    voice = np.tanh(base * drive)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(0.03, 0.12) * t + rng.uniform(0, 2 * np.pi))
    return voice * lfo


def _synth_stutter(f, t, rng, tempo_range):
    """Rhythmic gate — chopped tone."""
    phase = rng.uniform(0, 2 * np.pi)
    voice = np.zeros_like(t)
    for n in range(1, 10):
        h = f * n
        if h > HARMONIC_CAP:
            break
        voice += _rolloff(h) * np.sin(2 * np.pi * h * t + phase * n) / n**0.7
    voice /= 4.0
    gate_period = rng.uniform(*tempo_range)
    duty = rng.uniform(0.3, 0.7)
    gate_offset = rng.uniform(0, 1)
    gate_phase = (t / gate_period + gate_offset) % 1.0
    fade = 0.05
    gate = np.minimum(
        np.clip(gate_phase / fade, 0, 1),
        np.clip((duty - gate_phase) / fade, 0, 1),
    )
    return voice * gate


_TIMBRES = [
    _synth_supersaw, _synth_acid, _synth_pluck, _synth_fm,
    _synth_noise_drone, _synth_ring_mod, _synth_pwm, _synth_organ,
    _synth_wavefold, _synth_stutter,
]

_TIMBRE_NAMES = (
    "Supersaw pad", "Acid bass", "Synth pluck", "FM bass",
    "Noise drone", "Ring mod", "PWM synth", "Organ",
    "Wavefold", "Stutter",
)

_SCALE_NAMES = (
    "Major triad", "Major 7th", "Major 9th", "Major pentatonic",
    "Ionian", "Lydian", "Mixolydian", "Dominant 7th",
    "Major 6th", "Major hexatonic", "Major wide", "Major add9",
    "Minor triad", "Minor 7th", "Harmonic minor",
)

_TEMPO_LABELS = ("Ambient", "Slow", "Medium", "Fast", "Glitchy")

# Discrete search space (conservative lower bound):
# 46 MIDI x 10 timbres x 15 scales x 5 tempos x 13 pattern lengths
# x 6 avg starting notes x 5.6^12 min melody combos ≈ 50B+
# x ~80 avg tone combos = 2,208,000+ unique configurations


def _timbre_harmonics(timbre_idx, rng):
    """Return (harmonics_list, attack_seconds, release_fraction) for timbre.

    harmonics_list: [(harmonic_ratio, relative_amplitude), ...]
    attack_seconds: note attack time
    release_fraction: fraction of step duration used for release
    """
    if timbre_idx == 0:  # supersaw — rich sawtooth
        return [(n, 1.0 / n) for n in range(1, 10)], 0.02, 0.4
    if timbre_idx == 1:  # acid — square (odd harmonics)
        return [(n, 1.0 / n) for n in range(1, 12, 2)], 0.005, 0.2
    if timbre_idx == 2:  # pluck — fast decay, fewer harmonics
        return [(n, 1.0 / n ** 1.5) for n in range(1, 8)], 0.002, 0.7
    if timbre_idx == 3:  # FM — fundamental + sidebands
        r = int(rng.choice([2, 3, 4]))
        return [(1, 1.0), (r, 0.4), (r + 1, 0.15)], 0.008, 0.35
    if timbre_idx == 4:  # noise drone — fundamental + close detuned
        d = float(rng.uniform(1.005, 1.02))
        return [(1, 0.7), (d, 0.5), (2, 0.3), (3, 0.15)], 0.03, 0.5
    if timbre_idx == 5:  # ring mod — sum/difference tones
        r = float(rng.choice([1.5, 2.0, 2.5]))
        return [(1, 0.6), (r, 0.4), (r - 1, 0.2)], 0.008, 0.3
    if timbre_idx == 6:  # PWM — all harmonics, weighted
        return [(n, 0.8 / n) for n in range(1, 10)], 0.01, 0.35
    if timbre_idx == 7:  # organ — drawbar-like
        return [(1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (6, 0.2), (8, 0.1)], 0.01, 0.25
    if timbre_idx == 8:  # wavefold — odd harmonics from saturation
        return [(1, 1.0), (3, 0.4), (5, 0.15), (7, 0.05)], 0.01, 0.4
    if timbre_idx == 9:  # stutter — sharp, rhythmic
        return [(n, 1.0 / n ** 0.7) for n in range(1, 7)], 0.002, 0.1
    return [(1, 1.0)], 0.01, 0.3


def generate_signal(name_key: int) -> np.ndarray:
    """Generate normalized float64 audio signal with melodic sequencing."""
    rng = np.random.default_rng(name_key)

    # Root frequency: MIDI 25–70 mapped to Hz (~33–370 Hz)
    midi = rng.integers(25, 71)
    root_hz = 440.0 * 2 ** ((midi - 69) / 12.0)

    # Pick timbre, scale, tempo (same RNG sequence as get_audio_params)
    timbre_idx = int(rng.integers(len(_TIMBRES)))
    scale = SCALES[int(rng.integers(len(SCALES)))]
    tempo_idx = int(rng.integers(len(TEMPO_RANGES)))
    tempo_range = TEMPO_RANGES[tempo_idx]

    # Timbre characteristics
    harmonics, attack_s, release_frac = _timbre_harmonics(timbre_idx, rng)

    # Step duration clamped to musical range (120-500 BPM in note terms)
    step_dur = float(np.clip(rng.uniform(*tempo_range), 0.12, 0.5))

    # Available note frequencies from scale (octave-folded to stay warm)
    note_pool = []
    for deg in scale:
        f = root_hz * 2 ** (deg / 12.0)
        while f > 500:
            f /= 2
        while f < 30:
            f *= 2
        note_pool.append(f)

    # Melody: repeating pattern of 12-24 notes with varied durations
    # Durations are beat subdivisions/multiples (powers of 2)
    _DURATIONS = [0.25, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 4.0]
    bar_len = int(rng.choice([3, 4, 4, 4]))  # beats per bar (mostly 4/4)
    pat_len = int(rng.integers(12, 25))
    pattern = []  # list of (freq, duration_multiplier)
    note_idx = int(rng.integers(len(note_pool)))
    beat_pos = 0.0  # current position within bar in beats
    for _ in range(pat_len):
        dur_mult = float(rng.choice(_DURATIONS))
        # Cap duration so it doesn't cross a bar boundary
        beats_left = bar_len - beat_pos
        if dur_mult > beats_left:
            dur_mult = beats_left if beats_left >= 0.25 else dur_mult
        beat_pos = (beat_pos + dur_mult) % bar_len
        if rng.random() < 0.12:
            pattern.append((0.0, dur_mult))  # rest
        else:
            move = int(rng.integers(-2, 3))
            note_idx = (note_idx + move) % len(note_pool)
            pattern.append((note_pool[note_idx], dur_mult))

    # Build per-sample frequency track and note envelope
    total_samples = int((BUFFER_SECONDS + CROSSFADE) * SAMPLE_RATE)

    freq_track = np.zeros(total_samples)
    envelope = np.zeros(total_samples)

    att_samples = max(1, int(attack_s * SAMPLE_RATE))
    pos = 0
    pat_idx = 0
    while pos < total_samples:
        freq, dur_mult = pattern[pat_idx % pat_len]
        note_samples = max(1, int(step_dur * dur_mult * SAMPLE_RATE))
        s = pos
        e = min(s + note_samples, total_samples)
        n = e - s
        pos = e
        pat_idx += 1
        if freq == 0.0:
            continue
        freq_track[s:e] = freq
        rel_samples = max(1, int(step_dur * dur_mult * release_frac * SAMPLE_RATE))
        env = np.ones(n)
        a = min(att_samples, n // 4)
        r = min(rel_samples, n // 2)
        if a > 1:
            env[:a] = np.linspace(0, 1, a)
        if r > 1:
            env[-r:] = np.linspace(1, 0, r)
        envelope[s:e] = env

    # Phase accumulation for pitch-accurate melody
    phase = 2 * np.pi * np.cumsum(freq_track) / SAMPLE_RATE

    # Render harmonics — filter by max note freq to keep energy below 600 Hz
    max_note_freq = max((f for f, _ in pattern if f > 0), default=root_hz)
    signal = np.zeros(total_samples, dtype=np.float64)
    for h_num, h_amp in harmonics:
        if max_note_freq * h_num > 580:
            continue
        signal += _rolloff(root_hz * h_num) * h_amp * np.sin(phase * h_num)

    signal *= envelope

    # Crossfade tail into head for seamless loop
    cf = int(CROSSFADE * SAMPLE_RATE)
    buf = int(BUFFER_SECONDS * SAMPLE_RATE)
    fade_in = np.linspace(0, 1, cf)
    fade_out = np.linspace(1, 0, cf)
    signal[:cf] = signal[:cf] * fade_in + signal[buf:buf + cf] * fade_out
    signal = signal[:buf]

    # Remove DC offset
    signal -= np.mean(signal)

    # Normalize to consistent RMS (perceived loudness), clip peaks
    TARGET_RMS = 0.25
    rms = np.sqrt(np.mean(signal ** 2))
    if rms > 0:
        signal *= TARGET_RMS / rms
    np.clip(signal, -1.0, 1.0, out=signal)
    return signal


def generate_sound(name_key: int) -> pygame.mixer.Sound:
    signal = generate_signal(name_key)
    samples = (signal * 32767).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    return pygame.sndarray.make_sound(stereo)


def get_audio_params(name_key: int) -> dict:
    """Extract audio parameters for a planet without generating the signal.

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


def update_audio(visible_indices, visible_distances, name_keys):
    # Build wanted: planet_idx -> volume for planets within audio range
    wanted = {}
    for idx, dist in zip(visible_indices, visible_distances):
        if dist < AUDIO_RANGE:
            wanted[idx] = (1.0 - dist / AUDIO_RANGE) * MASTER_VOLUME

    # Stop and evict planets no longer in range
    for idx in list(_active_channels):
        if idx not in wanted:
            _active_channels.pop(idx).stop()
            _sound_cache.pop(idx, None)

    # Start or update wanted planets (visible_indices is already sorted closest-first)
    for idx, vol in wanted.items():
        if idx not in _active_channels:
            if idx not in _sound_cache:
                _sound_cache[idx] = generate_sound(int(name_keys[idx]))
            channel = _sound_cache[idx].play(loops=-1)
            if channel is not None:
                channel.set_volume(vol)
                _active_channels[idx] = channel
        else:
            _active_channels[idx].set_volume(vol)


def cleanup_audio():
    for ch in _active_channels.values():
        ch.stop()
    _active_channels.clear()
    _sound_cache.clear()
