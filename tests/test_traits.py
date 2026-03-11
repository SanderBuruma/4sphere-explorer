"""Tests for trait generation, descriptors, and visual expression."""

import pytest

from lib.traits import generate_traits, trait_descriptor, TRAIT_AXES, TRAIT_LABELS


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

