import numpy as np
import pygame

SAMPLE_RATE = 44100
BUFFER_SECONDS = 15
CROSSFADE = 0.5  # seconds, for seamless loop boundary
AUDIO_RANGE = 0.010  # 10 mrad
MAX_CHANNELS = 8
MASTER_VOLUME = 0.7

SCALES = [
    [0, 3, 5, 7, 10],  # pentatonic minor
    [0, 2, 4, 7, 9],   # pentatonic major
    [0, 2, 5, 7, 10],  # suspended
]

_sound_cache: dict[int, pygame.mixer.Sound] = {}
_active_channels: dict[int, pygame.mixer.Channel] = {}


def init_audio():
    pygame.mixer.set_num_channels(MAX_CHANNELS)


def _synth_supersaw(f, t, rng):
    """Supersaw: 5 detuned sawtooth oscillators, slow filter sweep — classic trance pad."""
    phase = rng.uniform(0, 2 * np.pi)
    detunes = [1.0 + rng.uniform(-0.012, 0.012) for _ in range(5)]
    voice = np.zeros_like(t)
    for d in detunes:
        # Band-limited saw via harmonics, capped at 500 Hz
        for n in range(1, 10):
            h = f * d * n
            if h > 500:
                break
            voice += np.sin(2 * np.pi * h * t + phase * n) / n
    # Slow filter sweep via amplitude modulation of upper harmonics
    sweep = 0.4 + 0.6 * np.sin(2 * np.pi * rng.uniform(0.02, 0.08) * t + rng.uniform(0, 2 * np.pi))
    return voice / 5.0 * sweep


def _synth_acid(f, t, rng):
    """Acid bass: square wave + resonant filter sweep — TB-303 style."""
    phase = rng.uniform(0, 2 * np.pi)
    voice = np.zeros_like(t)
    # Square wave: odd harmonics only
    for n in range(1, 12, 2):
        h = f * n
        if h > 500:
            break
        voice += np.sin(2 * np.pi * h * t + phase * n) / n
    # Resonant filter sweep: modulate harmonic balance over time
    sweep_rate = rng.uniform(0.05, 0.15)
    sweep_phase = rng.uniform(0, 2 * np.pi)
    sweep = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * sweep_rate * t + sweep_phase))
    # Add a resonant peak (boosted sine at sweep frequency)
    res_freq = f * (1.5 + 1.5 * (0.5 + 0.5 * np.sin(2 * np.pi * sweep_rate * t + sweep_phase)))
    resonance = 0.4 * np.sin(2 * np.pi * np.clip(res_freq, 0, 500) * t)
    return (voice * sweep + resonance)


def _synth_pluck(f, t, rng):
    """Synth pluck: sharp attack, fast decay, repeating notes — arpeggiated stab."""
    phase = rng.uniform(0, 2 * np.pi)
    # Note repeats every 1.5–3 seconds
    note_len = rng.uniform(1.5, 3.0)
    # Sharp attack (5ms), fast exponential decay
    t_mod = t % note_len
    attack = np.minimum(t_mod / 0.005, 1.0)
    decay = np.exp(-t_mod / (note_len * 0.2))
    env = attack * decay
    voice = np.zeros_like(t)
    # Rich harmonics that decay with the envelope
    for n in range(1, 8):
        h = f * n
        if h > 500:
            break
        # Higher harmonics get extra-fast decay for that plucky brightness-then-mellow
        h_decay = np.exp(-t_mod / (note_len * 0.2 / (1 + 0.3 * n)))
        voice += np.sin(2 * np.pi * h * t + phase * n) * h_decay * attack / (n ** 0.5)
    return voice


def _synth_fm(f, t, rng):
    """FM bass: frequency modulation with slow mod index sweep — deep, evolving tone."""
    phase = rng.uniform(0, 2 * np.pi)
    # Modulator at ratio to carrier (1.0, 2.0, or 3.0 for harmonic FM)
    ratio = rng.choice([1.0, 2.0])
    mod_freq = f * ratio
    # Modulation index sweeps slowly for timbral movement
    mod_sweep_rate = rng.uniform(0.03, 0.1)
    mod_sweep_phase = rng.uniform(0, 2 * np.pi)
    mod_index = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * mod_sweep_rate * t + mod_sweep_phase))
    # FM synthesis: carrier + modulator
    modulator = mod_index * np.sin(2 * np.pi * mod_freq * t + phase)
    voice = np.sin(2 * np.pi * f * t + modulator + phase * 0.7)
    # Slow amplitude LFO
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(0.04, 0.12) * t + rng.uniform(0, 2 * np.pi))
    return voice * lfo


_TIMBRES = [_synth_supersaw, _synth_acid, _synth_pluck, _synth_fm]


def generate_signal(name_key: int) -> np.ndarray:
    """Generate normalized float64 audio signal for a point. Returns 1D array in [-1, 1]."""
    rng = np.random.default_rng(name_key)

    # Root frequency: MIDI 35–54 mapped to Hz (~58–185 Hz)
    midi = rng.integers(35, 55)
    root_hz = 440.0 * 2 ** ((midi - 69) / 12.0)

    # Pick timbre, scale, and 3–4 tones
    timbre = _TIMBRES[rng.integers(len(_TIMBRES))]
    scale = SCALES[rng.integers(len(SCALES))]
    n_tones = rng.integers(3, 5)
    tone_indices = rng.choice(len(scale), size=n_tones, replace=False)
    freqs = [root_hz * 2 ** (scale[i] / 12.0) for i in sorted(tone_indices)]

    # Generate buffer with extra tail for crossfade
    total_samples = int((BUFFER_SECONDS + CROSSFADE) * SAMPLE_RATE)
    t = np.arange(total_samples) / SAMPLE_RATE
    signal = np.zeros(total_samples, dtype=np.float64)

    for freq in freqs:
        signal += timbre(freq, t, rng)

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
