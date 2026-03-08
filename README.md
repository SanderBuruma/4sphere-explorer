# 4-Sphere Explorer

**Navigate 30,000 worlds on the surface of a four-dimensional sphere.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pygame CE](https://img.shields.io/badge/Pygame--CE-2.x-green?logo=python&logoColor=white)](https://pyga.me/)
[![NumPy](https://img.shields.io/badge/NumPy-math-orange?logo=numpy&logoColor=white)](https://numpy.org/)

---

<!-- TODO: Add a screenshot or animated GIF here showing the main viewport with planets, sidebar, and tooltip. Recommended size: 900px wide. Example: ![Screenshot](assets/screenshot.png) -->

4-Sphere Explorer is a real-time interactive visualization of **S3** -- the three-dimensional surface of a four-dimensional ball. Fly between procedurally named worlds rendered as colorized planet sprites, each emitting its own unique synthesized ambient soundtrack. The entire experience runs in a single Python process with no external assets beyond 10 small sprite PNGs.

---

## Features

| | |
|---|---|
| **4D Navigation** | Rotate freely in six planes of 4D space using keyboard or mouse drag. Travel between points via spherical interpolation (slerp). |
| **30,000 Worlds** | Uniformly distributed on S3, each with a deterministic name, color, identicon, planet type, and audio signature. |
| **Procedural Music** | Every world has a unique techno/ambient loop -- 10 synth timbres, 15 scales, 5 tempo levels, melodic sequencing. Fades in as you approach. |
| **Planet Sprites** | 10 distinct planet types (Earth, Mars, Jupiter, Frost, Inferno, Desert, Jungle, Methane, Saturn, Void) assigned deterministically and colorized per-point. |
| **Lazy Everything** | Names, identicons, and audio are generated on demand with LRU caching. Startup is fast despite the 30k point count. |
| **Tangent Space Projection** | Points are projected from 4D through the camera's local tangent plane, then to screen -- a faithful representation of the local geometry of S3. |

---

## Controls

| Input | Action |
|-------|--------|
| **W / S** | Rotate up / down |
| **A / D** | Rotate left / right |
| **Q / E** | Rotate in 4D depth |
| **V** | Cycle view mode (Assigned / 4D Position / XYZ Projection / XYZ Fixed-Y) |
| **Up / Down** | Scroll the point list |
| **Ctrl +/-** or **scroll** | Zoom (XYZ modes only) |
| **Left click** (viewport) | Travel to nearest point |
| **Left click** (sidebar) | Travel to selected point |

All rotations are relative to the camera's current orientation frame, so controls always feel consistent regardless of where you are on the sphere.

---

## Quickstart

**Requirements:** Python 3.10+ on Windows, macOS, or Linux.

```bash
# Clone the repository
git clone https://github.com/your-username/4sphere-explorer.git
cd 4sphere-explorer

# Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

The `requirements.txt` installs:
- **pygame-ce** -- rendering and audio
- **numpy** -- all 4D math
- **scipy** -- KDTree for fast spatial queries
- **pydenticon** -- identicon generation

---

## How It Works

A regular sphere (the one you can hold) is a 2D surface curving through 3D space. Every point satisfies x^2 + y^2 + z^2 = 1. The **3-sphere (S3)** is the same idea one dimension up: a 3D surface curving through 4D space where x^2 + y^2 + z^2 + w^2 = 1.

You cannot see 4D directly, so the explorer uses a two-stage projection:

1. **4D to tangent space.** At the camera's position on S3, three orthonormal vectors span the local tangent hyperplane. Nearby points are projected onto these vectors, with distance equal to the great-circle (angular) distance on the sphere.

2. **Tangent space to screen.** The 3D tangent coordinates map to 2D screen position (x, y) plus a depth value (z) used for rendering order and brightness.

Navigation works by rotating a persistent **4x4 orientation frame** -- row 0 is the camera position, rows 1-3 are the tangent basis. Keyboard and mouse inputs apply planar rotations within this frame, and Gram-Schmidt reorthogonalization corrects numerical drift without flipping directions.

<details>
<summary><strong>Deeper: Orientation and Rotation</strong></summary>

The orientation frame is a 4x4 orthogonal matrix maintained across frames. Each rotation input (say, "rotate left") applies an exact rotation in the (camera, basis_i) plane:

```
camera'  =  cos(a) * camera + sin(a) * basis[i]
basis[i]' = -sin(a) * camera + cos(a) * basis[i]
```

This is mathematically equivalent to a rotation in one of the six planes of 4D space (xy, xz, xw, yz, yw, zw), but expressed in the camera's own coordinate system. The frame is periodically reorthogonalized using modified Gram-Schmidt starting from the current vectors, preserving orientation continuity.

Travel between points uses **slerp** (spherical linear interpolation), which traces the shortest great-circle arc on S3 -- the 4D equivalent of flying along a geodesic.

</details>

---

## Procedural Audio

Each of the 30,000 worlds generates a unique 15-second seamless loop built from:

- **10 timbres** -- supersaw pad, acid bass, synth pluck, FM bass, noise drone, ring mod, PWM, organ, wavefold, stutter
- **15 scales** -- major/minor triads, pentatonic, dorian, lydian, harmonic minor, and more
- **5 tempo levels** -- from ambient drones (5s cycles) to glitchy stutter (80ms gates)
- **Melodic sequencing** -- 12-24 note patterns with varied durations, rests, and step movement

Audio is spatially mixed: sounds fade in as you approach within 10 mrad and fade out as you leave. Up to 8 simultaneous channels play at once. All signals are RMS-normalized for consistent perceived loudness.

<details>
<summary><strong>Deeper: Synthesis Details</strong></summary>

Each timbre is an additive/FM synthesis function that generates raw float64 sample arrays. Harmonics are capped at 700 Hz with a linear rolloff above 580 Hz, keeping the sound warm regardless of root pitch (MIDI 25-70, ~33-466 Hz). Notable techniques:

- **Acid bass** uses proper phase accumulation (`np.cumsum`) for the resonant sweep, avoiding runaway harmonics from naive `freq * t`.
- **Ring modulation** filters carrier/modulator ratios so both sum and difference frequencies stay below 580 Hz, with full sideband suppression when they would exceed the threshold.
- **Wavefold** scales drive inversely with root frequency to prevent harsh upper partials on higher notes.

Seamless looping is achieved by generating 15.5 seconds and crossfading the last 0.5s tail into the head. DC offset is removed before RMS normalization to a target of 0.25.

</details>

---

## Project Structure

```
4sphere-explorer/
  main.py           Game loop, rendering, UI, input handling
  sphere.py         S3 math: point generation, distance, slerp, projection, names
  audio.py          Procedural audio synthesis and spatial mixing
  tests/
    test_sphere.py  22 tests for sphere math and navigation
    test_audio.py   17 tests for audio signal quality
  assets/planets/   10 planet sprite PNGs (64x64) + manifest
  requirements.txt  Python dependencies
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

The test suite covers 4D rotation correctness, tangent space projection, name generation uniqueness, slerp interpolation, audio signal RMS levels, frequency content, and seamless loop boundaries.
