"""Tests for eye wander/tracking and morph animation in lib/graphics.py."""

import math
import pytest
import numpy as np
import pygame

# Import the eye tracking functions (pygame is available in test env)
from lib.graphics import (
    _eye_state, _wander_offset, _WANDER_REACH,
    update_eye_tracking, draw_creature_eyes,
    generate_morph_data, render_morph_frame, _displace_vertices,
    generate_morph_frames, get_morph_frame, _MORPH_FRAMES,
)


def _reset_eye_state():
    """Reset module-level eye state to defaults."""
    _eye_state.update({
        "prev_mouse": (0, 0),
        "delta_accum": 0.0,
        "attention": 0.0,
        "wander_phase": 0.0,
        "wander_speed": 0.8,
        "_speed_timer": 0.0,
        "last_update_ms": 0,
        "_rng": np.random.RandomState(7),
    })


class TestWanderOffset:
    def test_bounded(self):
        """Wander offset stays roughly in [-1, 1]."""
        for phase in [0, 1, 2, 3, 5, 10, 100]:
            wx, wy = _wander_offset(phase)
            assert -1.1 <= wx <= 1.1
            assert -1.1 <= wy <= 1.1

    def test_varies_with_phase(self):
        """Different phases produce different offsets."""
        a = _wander_offset(0.0)
        b = _wander_offset(1.0)
        assert a != b

    def test_smooth(self):
        """Nearby phases produce nearby offsets (no jumps)."""
        wx0, wy0 = _wander_offset(5.0)
        wx1, wy1 = _wander_offset(5.001)
        assert abs(wx1 - wx0) < 0.01
        assert abs(wy1 - wy0) < 0.01

    def test_visits_all_quadrants(self):
        """Over a full cycle, wander visits all four quadrants."""
        quadrants = set()
        for i in range(1000):
            phase = i * 0.05  # 0 to 50 rad
            wx, wy = _wander_offset(phase)
            q = (wx > 0, wy > 0)
            quadrants.add(q)
        assert len(quadrants) == 4, f"Only visited quadrants: {quadrants}"

    def test_no_directional_bias(self):
        """Mean wander offset over many samples is near zero (no bias)."""
        wxs, wys = [], []
        for i in range(5000):
            phase = i * 0.1
            wx, wy = _wander_offset(phase)
            wxs.append(wx)
            wys.append(wy)
        assert abs(np.mean(wxs)) < 0.05, f"wx mean bias: {np.mean(wxs):.4f}"
        assert abs(np.mean(wys)) < 0.05, f"wy mean bias: {np.mean(wys):.4f}"

    def test_uses_full_range(self):
        """Wander reaches at least 60% of the [-1,1] range on each axis."""
        wxs, wys = [], []
        for i in range(5000):
            phase = i * 0.1
            wx, wy = _wander_offset(phase)
            wxs.append(wx)
            wys.append(wy)
        assert min(wxs) < -0.6, f"wx never goes below -0.6: min={min(wxs):.3f}"
        assert max(wxs) > 0.6, f"wx never goes above 0.6: max={max(wxs):.3f}"
        assert min(wys) < -0.6, f"wy never goes below -0.6: min={min(wys):.3f}"
        assert max(wys) > 0.6, f"wy never goes above 0.6: max={max(wys):.3f}"

    def test_per_seed_quadrant_spread(self):
        """Different creature seeds at the same wander_phase cover all quadrants."""
        rng = np.random.RandomState(42)
        seeds = rng.choice(11_800_000, 100, replace=False)
        quadrants = set()
        base_phase = 5.0  # arbitrary mid-game phase
        for seed in seeds:
            phase = base_phase + (seed * 2.6537) % (2 * math.pi * 100)
            wx, wy = _wander_offset(phase)
            quadrants.add((wx > 0, wy > 0))
        assert len(quadrants) == 4, f"Seeds only cover quadrants: {quadrants}"

    def test_per_seed_no_directional_bias(self):
        """Mean offset across many seeds is near zero (no seed-correlated bias)."""
        rng = np.random.RandomState(42)
        seeds = rng.choice(11_800_000, 500, replace=False)
        wxs, wys = [], []
        for base_phase in [0.0, 3.0, 10.0]:
            for seed in seeds:
                phase = base_phase + (seed * 2.6537) % (2 * math.pi * 100)
                wx, wy = _wander_offset(phase)
                wxs.append(wx)
                wys.append(wy)
        assert abs(np.mean(wxs)) < 0.05, f"wx seed bias: {np.mean(wxs):.4f}"
        assert abs(np.mean(wys)) < 0.05, f"wy seed bias: {np.mean(wys):.4f}"


class TestUpdateEyeTracking:
    def setup_method(self):
        _reset_eye_state()

    def test_idle_stays_wandering(self):
        """No mouse movement keeps attention near 0."""
        for t in range(0, 2000, 16):
            update_eye_tracking((400, 300), t)
        assert _eye_state["attention"] < 0.05

    def test_movement_raises_attention(self):
        """Rapid mouse movement raises attention toward 1."""
        update_eye_tracking((400, 300), 0)
        for i in range(1, 60):
            update_eye_tracking((400 + i * 5, 300), i * 16)
        assert _eye_state["attention"] > 0.5

    def test_attention_decays(self):
        """After movement stops, attention decays back toward 0."""
        update_eye_tracking((400, 300), 0)
        for i in range(1, 30):
            update_eye_tracking((400 + i * 10, 300), i * 16)
        peak = _eye_state["attention"]
        pos = (400 + 290, 300)
        for t in range(30 * 16, 30 * 16 + 3000, 16):
            update_eye_tracking(pos, t)
        assert _eye_state["attention"] < peak * 0.5

    def test_wander_phase_advances(self):
        """Wander phase increases over time."""
        update_eye_tracking((0, 0), 0)
        update_eye_tracking((0, 0), 1000)
        assert _eye_state["wander_phase"] > 0

    def test_dt_clamped(self):
        """Large time gap doesn't cause huge jumps."""
        update_eye_tracking((0, 0), 0)
        update_eye_tracking((0, 0), 100000)
        assert _eye_state["wander_phase"] < 2.0


class TestDrawCreatureEyes:
    """Test draw_creature_eyes blending logic.

    Uses a real pygame.Surface (no display needed) to verify no crashes.
    """

    @classmethod
    def setup_class(cls):
        pygame.init()
        cls.screen = pygame.Surface((200, 200), pygame.SRCALPHA)

    @classmethod
    def teardown_class(cls):
        pygame.quit()

    def setup_method(self):
        _reset_eye_state()

    def test_no_crash_empty_eyes(self):
        """Empty eye_info doesn't crash."""
        draw_creature_eyes(self.screen, 0, 0, 32, [], (100, 100))

    def test_different_seeds_different_wander(self):
        """Different seeds produce different wander directions."""
        update_eye_tracking((400, 300), 0)
        for t in range(16, 5000, 16):
            update_eye_tracking((400, 300), t)

        phase_a = _eye_state["wander_phase"] + (42 * 2.6537) % (2 * math.pi * 100)
        phase_b = _eye_state["wander_phase"] + (99 * 2.6537) % (2 * math.pi * 100)
        wa = _wander_offset(phase_a)
        wb = _wander_offset(phase_b)
        assert wa != wb

    def test_full_attention_follows_mouse(self):
        """At attention=1, no crash with mouse tracking."""
        _eye_state["attention"] = 1.0
        draw_creature_eyes(self.screen, 50, 50, 64, [(0.5, 0.3, 0.1)], (500, 100))

    def test_zero_attention_uses_wander(self):
        """At attention=0, no crash with wander."""
        _eye_state["attention"] = 0.0
        _eye_state["wander_phase"] = 2.0
        draw_creature_eyes(self.screen, 50, 50, 64, [(0.5, 0.3, 0.1)], (100, 100), seed=123)


def _find_pupil_offset(screen, eye_cx, eye_cy, surf_size):
    """Read back rendered pixels and find the black pupil centroid offset from eye center.

    Returns (dx, dy) offset in pixels from eye center, or None if no pupil found.
    """
    arr = pygame.surfarray.array3d(screen)  # (w, h, 3), axes are (x, y, rgb)
    # Black pupil pixels: all RGB channels < 10
    black_mask = (arr[:, :, 0] < 10) & (arr[:, :, 1] < 10) & (arr[:, :, 2] < 10)
    xs, ys = np.where(black_mask)  # surfarray is (x, y) indexed
    if len(xs) == 0:
        return None
    pupil_cx = xs.mean()
    pupil_cy = ys.mean()
    return (pupil_cx - eye_cx, pupil_cy - eye_cy)


class TestRenderedPupilWander:
    """Render actual googly eyes and measure where the black pupil dot lands.

    Uses a large eye (128px surface, big sclera) for sub-pixel centroid accuracy.
    Varies wander_phase across many values and asserts:
    - Mean pupil position is near eye center (no directional bias)
    - Pupils visit all four quadrants
    - Pupils use a significant fraction of available range
    """

    SURF_SIZE = 128
    # Single centered eye: norm coords (0.5, 0.5) with radius 0.25
    # This gives eye_r = 32px, pupil_r = 16px, max_offset = 16px
    EYE_INFO = [(0.5, 0.5, 0.25)]

    @classmethod
    def setup_class(cls):
        pygame.init()

    @classmethod
    def teardown_class(cls):
        pygame.quit()

    def _render_pupil_at_phase(self, phase, seed=0):
        """Set wander_phase, render eye, return pupil offset from center."""
        _reset_eye_state()
        _eye_state["attention"] = 0.0  # pure wander, no mouse tracking
        _eye_state["wander_phase"] = phase

        surf = pygame.Surface((self.SURF_SIZE, self.SURF_SIZE), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))  # white background = sclera

        # mouse_pos at eye center so mouse component is zero offset
        eye_cx = 0.5 * self.SURF_SIZE
        eye_cy = 0.5 * self.SURF_SIZE
        draw_creature_eyes(surf, 0, 0, self.SURF_SIZE, self.EYE_INFO,
                           (eye_cx, eye_cy), seed=seed)

        return _find_pupil_offset(surf, eye_cx, eye_cy, self.SURF_SIZE)

    def test_wander_visits_all_quadrants_rendered(self):
        """Rendered pupil visits all four quadrants over varying phases."""
        quadrants = set()
        for i in range(200):
            phase = i * 0.25  # 0 to 50 rad
            offset = self._render_pupil_at_phase(phase)
            assert offset is not None, f"No pupil found at phase={phase}"
            dx, dy = offset
            quadrants.add((dx > 0, dy > 0))
            if len(quadrants) == 4:
                break
        assert len(quadrants) == 4, f"Pupil only visited quadrants: {quadrants}"

    def test_wander_mean_near_center_over_phases(self):
        """Mean rendered pupil position over many phases is near eye center."""
        dxs, dys = [], []
        for i in range(300):
            phase = i * 0.17  # ~51 rad range, incommensurate step
            offset = self._render_pupil_at_phase(phase)
            assert offset is not None
            dxs.append(offset[0])
            dys.append(offset[1])
        mean_dx = np.mean(dxs)
        mean_dy = np.mean(dys)
        # Max offset is 16px; mean should be within 2px of center
        assert abs(mean_dx) < 2.0, f"Rendered dx mean bias: {mean_dx:.2f}px"
        assert abs(mean_dy) < 2.0, f"Rendered dy mean bias: {mean_dy:.2f}px"

    def test_wander_mean_near_center_over_seeds(self):
        """Mean rendered pupil position across many seeds at fixed phase is near center."""
        dxs, dys = [], []
        rng = np.random.RandomState(42)
        seeds = rng.choice(11_800_000, 200, replace=False)
        for seed in seeds:
            offset = self._render_pupil_at_phase(phase=5.0, seed=int(seed))
            assert offset is not None
            dxs.append(offset[0])
            dys.append(offset[1])
        mean_dx = np.mean(dxs)
        mean_dy = np.mean(dys)
        assert abs(mean_dx) < 2.0, f"Rendered dx seed-mean bias: {mean_dx:.2f}px"
        assert abs(mean_dy) < 2.0, f"Rendered dy seed-mean bias: {mean_dy:.2f}px"

    def test_wander_uses_significant_range(self):
        """Rendered pupil travels at least 40% of max_offset in each direction."""
        dxs, dys = [], []
        for i in range(300):
            phase = i * 0.17
            offset = self._render_pupil_at_phase(phase)
            assert offset is not None
            dxs.append(offset[0])
            dys.append(offset[1])
        # max_offset = eye_r - pupil_r = 32 - 16 = 16px
        # wander_reach = 0.7, so max wander = 11.2px
        # require at least 40% of that = 4.5px in each direction
        assert min(dxs) < -4.5, f"Pupil never goes far left: min dx={min(dxs):.1f}"
        assert max(dxs) > 4.5, f"Pupil never goes far right: max dx={max(dxs):.1f}"
        assert min(dys) < -4.5, f"Pupil never goes far up: min dy={min(dys):.1f}"
        assert max(dys) > 4.5, f"Pupil never goes far down: max dy={max(dys):.1f}"

    def test_seeds_visit_all_quadrants_rendered(self):
        """Different seeds at a single wander_phase spread across all quadrants."""
        rng = np.random.RandomState(99)
        seeds = rng.choice(11_800_000, 200, replace=False)
        quadrants = set()
        for seed in seeds:
            offset = self._render_pupil_at_phase(phase=3.0, seed=int(seed))
            assert offset is not None
            dx, dy = offset
            quadrants.add((dx > 0, dy > 0))
            if len(quadrants) == 4:
                break
        assert len(quadrants) == 4, f"Seeds only cover quadrants: {quadrants}"

    def test_mouse_tracking_symmetric(self):
        """Pupil displacement is symmetric: opposite mouse directions yield equal magnitude.

        Moves the mouse to extreme opposite corners and verifies the pupil
        centroid is equidistant from eye center in both cases.
        """
        _reset_eye_state()
        _eye_state["attention"] = 1.0  # full mouse tracking

        size = self.SURF_SIZE
        eye_cx = 0.5 * size
        eye_cy = 0.5 * size
        far = 500  # far enough that offset clamps to max

        # Mouse bottom-right → measure pupil offset
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        draw_creature_eyes(surf, 0, 0, size, self.EYE_INFO,
                           (eye_cx + far, eye_cy + far), seed=0)
        off_br = _find_pupil_offset(surf, eye_cx, eye_cy, size)

        # Mouse top-left → measure pupil offset
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        draw_creature_eyes(surf, 0, 0, size, self.EYE_INFO,
                           (eye_cx - far, eye_cy - far), seed=0)
        off_tl = _find_pupil_offset(surf, eye_cx, eye_cy, size)

        assert off_br is not None and off_tl is not None

        dist_br = math.sqrt(off_br[0]**2 + off_br[1]**2)
        dist_tl = math.sqrt(off_tl[0]**2 + off_tl[1]**2)

        # Magnitudes should be within 1px of each other
        assert abs(dist_br - dist_tl) < 1.0, (
            f"Asymmetric pupil displacement: bottom-right={dist_br:.2f}px, "
            f"top-left={dist_tl:.2f}px, diff={abs(dist_br - dist_tl):.2f}px"
        )


# --- Morph animation tests ---

class TestMorphDataGeneration:
    """Tests for generate_morph_data() mesh extraction."""

    def test_morph_data_keys(self):
        """Morph data contains all required keys."""
        md = generate_morph_data(42, size=32)
        required = {'points', 'simplices', 'tri_colors', 'eye_info', 'color',
                     'accent', 'outline_color', 'seed', 'size',
                     'displace_phases', 'displace_freqs'}
        assert required.issubset(md.keys())

    def test_morph_data_deterministic(self):
        """Same seed produces identical morph data."""
        md1 = generate_morph_data(12345, size=32)
        md2 = generate_morph_data(12345, size=32)
        np.testing.assert_array_equal(md1['points'], md2['points'])
        np.testing.assert_array_equal(md1['simplices'], md2['simplices'])
        assert md1['tri_colors'] == md2['tri_colors']
        assert md1['eye_info'] == md2['eye_info']

    def test_mesh_has_triangles(self):
        """Mesh should have a reasonable number of triangles."""
        md = generate_morph_data(42, size=64)
        assert len(md['simplices']) > 10
        assert len(md['tri_colors']) == len(md['simplices'])

    def test_points_within_bounds(self):
        """All mesh points should be within [0, size] bounds."""
        md = generate_morph_data(99, size=64)
        assert np.all(md['points'] >= -1)
        assert np.all(md['points'] <= 65)

    def test_displacement_params_shape(self):
        """Displacement parameters have one entry per mesh point."""
        md = generate_morph_data(42, size=32)
        n = len(md['points'])
        assert md['displace_phases'].shape == (n,)
        assert md['displace_freqs'].shape == (n,)


class TestVertexDisplacement:
    """Tests for _displace_vertices() harmonic oscillator system."""

    def test_zero_time_minimal_displacement(self):
        """At t=0, displacement should be small but non-zero (phases vary)."""
        md = generate_morph_data(42, size=64)
        displaced = _displace_vertices(md, 0)
        diff = np.linalg.norm(displaced - md['points'], axis=1)
        # Mean displacement at t=0 should be moderate (not all phases are 0)
        assert diff.mean() < md['size'] * 0.05

    def test_displacement_changes_over_time(self):
        """Vertices should be at different positions at different times."""
        md = generate_morph_data(42, size=64)
        d1 = _displace_vertices(md, 0)
        d2 = _displace_vertices(md, 2000)
        assert not np.allclose(d1, d2)

    def test_displacement_bounded(self):
        """No vertex should move more than ~5% of size from its base position."""
        md = generate_morph_data(42, size=64)
        max_disp = 0
        for t_ms in range(0, 10000, 500):
            displaced = _displace_vertices(md, t_ms)
            diff = np.linalg.norm(displaced - md['points'], axis=1)
            max_disp = max(max_disp, diff.max())
        # amplitude capped at size * 0.035, with radial+tangential ~1.4x max
        assert max_disp < md['size'] * 0.06

    def test_center_points_stable(self):
        """Points near the center should not be displaced."""
        md = generate_morph_data(42, size=64)
        cx, cy = 32.0, 32.0
        dist_from_center = np.sqrt(
            (md['points'][:, 0] - cx)**2 + (md['points'][:, 1] - cy)**2)
        near_center = dist_from_center < 1.0
        if near_center.any():
            displaced = _displace_vertices(md, 5000)
            center_diff = np.linalg.norm(
                displaced[near_center] - md['points'][near_center], axis=1)
            assert np.allclose(center_diff, 0)


class TestMorphFrameRendering:
    """Tests for render_morph_frame() output."""

    @classmethod
    def setup_class(cls):
        pygame.init()

    @classmethod
    def teardown_class(cls):
        pygame.quit()

    def test_returns_surface_and_eyes(self):
        """render_morph_frame returns (Surface, eye_info)."""
        md = generate_morph_data(42, size=64)
        surf, eyes = render_morph_frame(md, 1000)
        assert isinstance(surf, pygame.Surface)
        assert surf.get_size() == (64, 64)
        assert isinstance(eyes, list)
        assert len(eyes) >= 1

    def test_surface_has_content(self):
        """Rendered surface should have non-transparent pixels."""
        md = generate_morph_data(42, size=64)
        surf, _ = render_morph_frame(md, 1000)
        alpha = pygame.surfarray.array_alpha(surf)
        assert (alpha > 0).sum() > 100

    def test_frames_differ(self):
        """Frames at different times should produce different pixel data."""
        md = generate_morph_data(42, size=64)
        s1, _ = render_morph_frame(md, 0)
        s2, _ = render_morph_frame(md, 3000)
        px1 = pygame.surfarray.array3d(s1)
        px2 = pygame.surfarray.array3d(s2)
        assert not np.array_equal(px1, px2)

    def test_multiple_seeds_render(self):
        """Various seeds should all produce valid morph frames."""
        for seed in [1, 42, 999, 123456, 7777777]:
            md = generate_morph_data(seed, size=32)
            surf, eyes = render_morph_frame(md, 500)
            alpha = pygame.surfarray.array_alpha(surf)
            assert (alpha > 0).sum() > 20, f"Seed {seed} produced empty frame"


class TestPreRenderedMorphFrames:
    """Tests for generate_morph_frames / get_morph_frame pre-rendered cycle."""

    @classmethod
    def setup_class(cls):
        pygame.init()

    @classmethod
    def teardown_class(cls):
        pygame.quit()

    def test_frame_count(self):
        """Should generate the expected number of frames."""
        frames, eye_info = generate_morph_frames(42, size=32)
        assert len(frames) == _MORPH_FRAMES

    def test_all_frames_have_content(self):
        """Every pre-rendered frame should have visible pixels."""
        frames, _ = generate_morph_frames(42, size=32)
        for i, surf in enumerate(frames):
            alpha = pygame.surfarray.array_alpha(surf)
            assert (alpha > 0).sum() > 20, f"Frame {i} is empty"

    def test_frames_are_surfaces(self):
        """All frames should be pygame Surfaces of the right size."""
        frames, _ = generate_morph_frames(42, size=32)
        for surf in frames:
            assert isinstance(surf, pygame.Surface)
            assert surf.get_size() == (32, 32)

    def test_get_morph_frame_cycles(self):
        """get_morph_frame should return different frames at different times."""
        frames, _ = generate_morph_frames(42, size=32)
        f0 = get_morph_frame(frames, 0)
        f_mid = get_morph_frame(frames, 4000)
        # They should be different surface objects (different frames in cycle)
        assert f0 is not f_mid

    def test_get_morph_frame_wraps(self):
        """Frame selection should wrap around the cycle."""
        frames, _ = generate_morph_frames(42, size=32)
        f0 = get_morph_frame(frames, 0)
        f_wrap = get_morph_frame(frames, 8000)  # exactly one cycle later
        assert f0 is f_wrap
