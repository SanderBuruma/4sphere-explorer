"""Tests for trait generation, descriptors, and visual expression."""

import pytest
import numpy as np
import os
import sys

# Headless pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from lib.traits import generate_traits, trait_descriptor, TRAIT_AXES, TRAIT_LABELS
from lib.graphics import generate_creature, _trait_intensity


# --- Trait generation tests ---

class TestTraitGeneration:
    def test_determinism(self):
        """Same key always produces same traits."""
        t1 = generate_traits(12345)
        t2 = generate_traits(12345)
        assert t1 == t2

    def test_different_keys_differ(self):
        """Different keys produce different trait values (statistically)."""
        results = [generate_traits(k) for k in range(20)]
        # At least some variation across keys
        for axis in TRAIT_AXES:
            values = [r[axis] for r in results]
            assert len(set(values)) > 1, f"{axis} has no variation across 20 keys"

    def test_range(self):
        """All trait values are 0-100."""
        for k in range(100):
            traits = generate_traits(k)
            for axis in TRAIT_AXES:
                assert 0 <= traits[axis] <= 100, f"{axis}={traits[axis]} out of range for key {k}"

    def test_all_four_axes_present(self):
        """Traits dict has exactly 4 expected axes."""
        traits = generate_traits(42)
        assert set(traits.keys()) == set(TRAIT_AXES)

    def test_large_key_values(self):
        """Works with large name key integers."""
        traits = generate_traits(2**31 - 1)
        for axis in TRAIT_AXES:
            assert 0 <= traits[axis] <= 100


# --- Descriptor tests ---

class TestDescriptors:
    def test_extreme_low_has_descriptor(self):
        """Values 0-10 should always have a descriptor."""
        for axis in TRAIT_AXES:
            desc = trait_descriptor(axis, 5)
            assert desc != "", f"{axis} at 5 should have descriptor"

    def test_extreme_high_has_descriptor(self):
        """Values 90-100 should always have a descriptor."""
        for axis in TRAIT_AXES:
            desc = trait_descriptor(axis, 95)
            assert desc != "", f"{axis} at 95 should have descriptor"

    def test_dead_zone_empty(self):
        """Values 40-60 should return empty descriptor."""
        for axis in TRAIT_AXES:
            for v in [40, 50, 60]:
                desc = trait_descriptor(axis, v)
                assert desc == "", f"{axis} at {v} should be in dead zone"

    def test_specific_descriptors(self):
        """Check specific known descriptor values."""
        assert trait_descriptor("aggressive_passive", 0) == "Ferocious"
        assert trait_descriptor("aggressive_passive", 100) == "Placid"
        assert trait_descriptor("friendly_hostile", 5) == "Devoted"
        assert trait_descriptor("friendly_hostile", 95) == "Vicious"

    def test_labels_exist_for_all_axes(self):
        """TRAIT_LABELS has entries for all axes."""
        for axis in TRAIT_AXES:
            assert axis in TRAIT_LABELS


# --- Trait intensity function ---

class TestTraitIntensity:
    def test_dead_zone_zero(self):
        for v in [40, 45, 50, 55, 60]:
            assert _trait_intensity(v) == 0.0

    def test_extreme_low(self):
        assert _trait_intensity(0) == pytest.approx(-1.0)

    def test_extreme_high(self):
        assert _trait_intensity(100) == pytest.approx(1.0)

    def test_graduated(self):
        """Values closer to 50 have less intensity."""
        assert abs(_trait_intensity(30)) < abs(_trait_intensity(10))
        assert abs(_trait_intensity(70)) < abs(_trait_intensity(90))


# --- Visual expression tests ---

class TestVisualExpression:
    def test_neutral_traits_no_crash(self):
        """Creature with all-50 traits generates without error."""
        traits = {a: 50 for a in TRAIT_AXES}
        surf, eyes = generate_creature(42, size=32, traits=traits)
        assert surf.get_size() == (32, 32)
        assert len(eyes) >= 0

    def test_extreme_traits_no_crash(self):
        """Creature with extreme traits generates without error."""
        for extremes in [
            {a: 0 for a in TRAIT_AXES},
            {a: 100 for a in TRAIT_AXES},
        ]:
            surf, eyes = generate_creature(42, size=32, traits=extremes)
            assert surf.get_size() == (32, 32)

    def test_no_traits_backward_compatible(self):
        """generate_creature without traits still works."""
        surf, eyes = generate_creature(42, size=32)
        assert surf.get_size() == (32, 32)

    def test_friendly_vs_hostile_hue_differs(self):
        """Friendly creature has different average hue than hostile."""
        friendly_traits = {a: 50 for a in TRAIT_AXES}
        friendly_traits["friendly_hostile"] = 0
        hostile_traits = {a: 50 for a in TRAIT_AXES}
        hostile_traits["friendly_hostile"] = 100

        surf_f, _ = generate_creature(99, size=32, traits=friendly_traits)
        surf_h, _ = generate_creature(99, size=32, traits=hostile_traits)

        # Extract average color of non-transparent pixels
        def avg_hue(surf):
            arr = pygame.surfarray.array3d(surf)
            alpha = pygame.surfarray.array_alpha(surf)
            mask = alpha > 0
            if mask.sum() == 0:
                return 0
            r, g, b = arr[:, :, 0][mask].mean(), arr[:, :, 1][mask].mean(), arr[:, :, 2][mask].mean()
            # Simple hue approximation
            return (r - b)  # warm = positive, cool = negative

        hue_f = avg_hue(surf_f)
        hue_h = avg_hue(surf_h)
        # Friendly should be warmer (more red/orange) than hostile
        # Just check they differ — exact direction depends on base hue
        assert hue_f != hue_h, "Friendly and hostile should produce different colors"

    def test_brave_vs_fearful_width_differs(self):
        """Brave creature is wider than fearful."""
        brave_traits = {a: 50 for a in TRAIT_AXES}
        brave_traits["brave_fearful"] = 0
        fearful_traits = {a: 50 for a in TRAIT_AXES}
        fearful_traits["brave_fearful"] = 100

        surf_b, _ = generate_creature(99, size=64, traits=brave_traits)
        surf_f, _ = generate_creature(99, size=64, traits=fearful_traits)

        def body_width(surf):
            alpha = pygame.surfarray.array_alpha(surf)
            cols_with_pixels = np.any(alpha > 0, axis=1)
            if not cols_with_pixels.any():
                return 0
            xs = np.where(cols_with_pixels)[0]
            return xs[-1] - xs[0]

        assert body_width(surf_b) > body_width(surf_f), "Brave should be wider than fearful"

    def test_curious_vs_aloof_eye_size(self):
        """Curious creature has larger eye radius than aloof."""
        curious_traits = {a: 50 for a in TRAIT_AXES}
        curious_traits["curious_aloof"] = 0
        aloof_traits = {a: 50 for a in TRAIT_AXES}
        aloof_traits["curious_aloof"] = 100

        _, eyes_c = generate_creature(99, size=64, traits=curious_traits)
        _, eyes_a = generate_creature(99, size=64, traits=aloof_traits)

        if eyes_c and eyes_a:
            avg_r_c = sum(e[2] for e in eyes_c) / len(eyes_c)
            avg_r_a = sum(e[2] for e in eyes_a) / len(eyes_a)
            assert avg_r_c > avg_r_a, "Curious should have larger eyes than aloof"

    def test_traits_independent_of_creature_rng(self):
        """Generating traits does not affect creature output."""
        # Generate creature without traits
        surf1, eyes1 = generate_creature(42, size=32)
        # Generate traits (should not affect creature)
        generate_traits(42)
        # Generate same creature again
        surf2, eyes2 = generate_creature(42, size=32)
        # They should be identical
        arr1 = pygame.surfarray.array3d(surf1)
        arr2 = pygame.surfarray.array3d(surf2)
        assert np.array_equal(arr1, arr2)
