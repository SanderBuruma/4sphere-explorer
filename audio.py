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
    [0, 3, 5, 7, 10],         # pentatonic minor
    [0, 2, 4, 7, 9],          # pentatonic major
    [0, 2, 5, 7, 10],         # suspended
    [0, 2, 3, 5, 7, 9, 10],   # dorian
    [0, 1, 3, 5, 7, 8, 10],   # phrygian
    [0, 2, 4, 6, 8, 10],      # whole tone
    [0, 3, 5, 6, 7, 10],      # blues
    [0, 2, 3, 5, 7, 8, 11],   # harmonic minor
    [0, 2, 4, 6, 7, 9, 11],   # lydian
    [0, 2, 4, 5, 7, 9, 10],   # mixolydian
    [0, 1, 3, 5, 6, 8, 10],   # locrian
    [0, 2, 3, 7, 9],          # japanese in-sen
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

# Discrete search space: 46 MIDI x 10 timbres x 12 scales x 5 tempos
# x ~80 avg tone combos = 2,208,000+ unique configurations


def generate_signal(name_key: int) -> np.ndarray:
    """Generate normalized float64 audio signal. Returns 1D array in [-1, 1]."""
    rng = np.random.default_rng(name_key)

    # Root frequency: MIDI 25–70 mapped to Hz (~33–370 Hz)
    midi = rng.integers(25, 71)
    root_hz = 440.0 * 2 ** ((midi - 69) / 12.0)

    # Pick timbre, scale, tempo, and tones
    timbre = _TIMBRES[rng.integers(len(_TIMBRES))]
    scale = SCALES[rng.integers(len(SCALES))]
    tempo_range = TEMPO_RANGES[rng.integers(len(TEMPO_RANGES))]

    max_tones = min(6, len(scale))
    n_tones = rng.integers(2, max_tones + 1)
    tone_indices = rng.choice(len(scale), size=n_tones, replace=False)
    freqs = [root_hz * 2 ** (scale[i] / 12.0) for i in sorted(tone_indices)]
    # Octave-fold any tone above 580 Hz to keep fundamentals warm
    freqs = [f / 2 if f > 580 else f for f in freqs]

    # Generate buffer with extra tail for crossfade
    total_samples = int((BUFFER_SECONDS + CROSSFADE) * SAMPLE_RATE)
    t = np.arange(total_samples) / SAMPLE_RATE
    signal = np.zeros(total_samples, dtype=np.float64)

    for freq in freqs:
        signal += timbre(freq, t, rng, tempo_range)

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


def update_audio(visible_indices, visible_distances, name_keys):
    # Build wanted: point_idx -> volume for points within audio range
    wanted = {}
    for idx, dist in zip(visible_indices, visible_distances):
        if dist < AUDIO_RANGE:
            wanted[idx] = (1.0 - dist / AUDIO_RANGE) * MASTER_VOLUME

    # Stop and evict points no longer in range
    for idx in list(_active_channels):
        if idx not in wanted:
            _active_channels.pop(idx).stop()
            _sound_cache.pop(idx, None)

    # Start or update wanted points (visible_indices is already sorted closest-first)
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
