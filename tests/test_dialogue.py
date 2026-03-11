"""Tests for procedural dialogue generation."""

import pytest
from lib.dialogue import (
    generate_dialogue,
    _reputation_tier,
    _trait_temp,
    TEMPLATES,
    LORE_SNIPPETS,
    GREETINGS,
    FAREWELLS,
    BODY,
    VERBS,
    ADVERBS,
)


# -- Tier mapping tests --

class TestReputationTier:
    def test_stranger(self):
        assert _reputation_tier(0) == "stranger"

    def test_acquaintance_low(self):
        assert _reputation_tier(1) == "acquaintance"

    def test_acquaintance_high(self):
        assert _reputation_tier(2) == "acquaintance"

    def test_familiar_low(self):
        assert _reputation_tier(3) == "familiar"

    def test_familiar_high(self):
        assert _reputation_tier(5) == "familiar"

    def test_friend_low(self):
        assert _reputation_tier(6) == "friend"

    def test_friend_high(self):
        assert _reputation_tier(8) == "friend"

    def test_devoted_low(self):
        assert _reputation_tier(9) == "devoted"

    def test_devoted_high(self):
        assert _reputation_tier(10) == "devoted"


# -- Trait temperature mapping --

class TestTraitTemp:
    def test_low(self):
        assert _trait_temp(0) == "low"
        assert _trait_temp(33) == "low"

    def test_neutral(self):
        assert _trait_temp(34) == "neutral"
        assert _trait_temp(50) == "neutral"
        assert _trait_temp(66) == "neutral"

    def test_high(self):
        assert _trait_temp(67) == "high"
        assert _trait_temp(100) == "high"


# -- Template coverage --

class TestTemplates:
    def test_all_tiers_present(self):
        for tier in ("stranger", "acquaintance", "familiar", "friend", "devoted"):
            assert tier in TEMPLATES

    def test_min_templates_per_tier(self):
        for tier, pool in TEMPLATES.items():
            assert len(pool) >= 4, f"{tier} has only {len(pool)} templates"

    def test_total_templates(self):
        total = sum(len(pool) for pool in TEMPLATES.values())
        assert total >= 20, f"Only {total} templates total"

    def test_lore_snippets_count(self):
        assert len(LORE_SNIPPETS) >= 5


# -- Word bank coverage --

class TestWordBanks:
    def test_greeting_temps(self):
        for temp in ("low", "neutral", "high"):
            assert len(GREETINGS[temp]) >= 3

    def test_farewell_temps(self):
        for temp in ("low", "neutral", "high"):
            assert len(FAREWELLS[temp]) >= 3

    def test_body_temps(self):
        for temp in ("low", "neutral", "high"):
            assert len(BODY[temp]) >= 3

    def test_verb_temps(self):
        for temp in ("low", "neutral", "high"):
            assert len(VERBS[temp]) >= 3

    def test_adverb_temps(self):
        for temp in ("low", "neutral", "high"):
            assert len(ADVERBS[temp]) >= 3


# -- Core generation tests --

NEUTRAL_TRAITS = {
    "aggressive_passive": 50,
    "curious_aloof": 50,
    "friendly_hostile": 50,
    "brave_fearful": 50,
}

FRIENDLY_TRAITS = {
    "aggressive_passive": 50,
    "curious_aloof": 50,
    "friendly_hostile": 10,  # 0=friendly
    "brave_fearful": 50,
}

HOSTILE_TRAITS = {
    "aggressive_passive": 50,
    "curious_aloof": 50,
    "friendly_hostile": 90,  # 100=hostile
    "brave_fearful": 50,
}


class TestDeterminism:
    def test_same_inputs_same_output(self):
        d1 = generate_dialogue(42, NEUTRAL_TRAITS, 5)
        d2 = generate_dialogue(42, NEUTRAL_TRAITS, 5)
        assert d1 == d2

    def test_determinism_across_all_tiers(self):
        for score in [0, 1, 3, 6, 9]:
            d1 = generate_dialogue(999, NEUTRAL_TRAITS, score)
            d2 = generate_dialogue(999, NEUTRAL_TRAITS, score)
            assert d1 == d2, f"Non-deterministic at score {score}"


class TestVariation:
    def test_different_name_keys_differ(self):
        """Different creatures with same traits should usually produce different dialogue."""
        dialogues = set()
        for nk in range(100):
            dialogues.add(generate_dialogue(nk, NEUTRAL_TRAITS, 5))
        # With 100 different keys, we should get at least several distinct outputs
        assert len(dialogues) > 5, f"Only {len(dialogues)} distinct dialogues from 100 keys"

    def test_different_scores_differ(self):
        """Same creature at different reputation levels should differ."""
        dialogues = set()
        for score in [0, 1, 3, 6, 9]:
            dialogues.add(generate_dialogue(42, NEUTRAL_TRAITS, score))
        assert len(dialogues) >= 4, "Too few distinct dialogues across reputation levels"


class TestTraitInfluence:
    def test_friendly_vs_hostile_greeting(self):
        """Friendly creature should use warm greetings, hostile should use cold ones."""
        warm_greetings = set(GREETINGS["low"])
        cold_greetings = set(GREETINGS["high"])
        all_warm = warm_greetings | set(GREETINGS["neutral"])
        all_cold = cold_greetings | set(GREETINGS["neutral"])

        friendly_count = 0
        hostile_count = 0
        n = 50

        for nk in range(n):
            fd = generate_dialogue(nk, FRIENDLY_TRAITS, 3)
            hd = generate_dialogue(nk, HOSTILE_TRAITS, 3)
            for g in warm_greetings:
                if g in fd:
                    friendly_count += 1
                    break
            for g in cold_greetings:
                if g in hd:
                    hostile_count += 1
                    break

        # At least some friendly creatures should use warm greetings
        assert friendly_count > 0, "No friendly creatures used warm greetings"
        # At least some hostile creatures should use cold greetings
        assert hostile_count > 0, "No hostile creatures used cold greetings"

    def test_curious_vs_aloof_body(self):
        """Curious creatures ask questions, aloof ones make terse statements."""
        curious_traits = {**NEUTRAL_TRAITS, "curious_aloof": 10}
        aloof_traits = {**NEUTRAL_TRAITS, "curious_aloof": 90}

        curious_questions = 0
        aloof_terse = 0

        question_phrases = set(BODY["low"])  # curious body content
        aloof_phrases = set(BODY["high"])   # aloof body content

        for nk in range(50):
            cd = generate_dialogue(nk, curious_traits, 3)
            ad = generate_dialogue(nk, aloof_traits, 3)
            for q in question_phrases:
                if q in cd:
                    curious_questions += 1
                    break
            for a in aloof_phrases:
                if a in ad:
                    aloof_terse += 1
                    break

        assert curious_questions > 0, "No curious creatures asked questions"
        assert aloof_terse > 0, "No aloof creatures made terse statements"


class TestTierShift:
    def test_stranger_vs_familiar(self):
        """Same creature at rep 0 vs rep 5 should produce different dialogue."""
        d0 = generate_dialogue(42, NEUTRAL_TRAITS, 0)
        d5 = generate_dialogue(42, NEUTRAL_TRAITS, 5)
        assert d0 != d5

    def test_stranger_vs_devoted(self):
        """Stranger and devoted should be clearly different."""
        d0 = generate_dialogue(42, NEUTRAL_TRAITS, 0)
        d10 = generate_dialogue(42, NEUTRAL_TRAITS, 10)
        assert d0 != d10


class TestAllTiersCovered:
    @pytest.mark.parametrize("score", [0, 1, 3, 6, 9])
    def test_tier_produces_nonempty(self, score):
        result = generate_dialogue(42, NEUTRAL_TRAITS, score)
        assert isinstance(result, str)
        assert len(result) > 0


class TestEdgeCases:
    def test_score_zero(self):
        result = generate_dialogue(42, NEUTRAL_TRAITS, 0)
        assert isinstance(result, str) and len(result) > 0

    def test_score_ten(self):
        result = generate_dialogue(42, NEUTRAL_TRAITS, 10)
        assert isinstance(result, str) and len(result) > 0

    def test_extreme_traits_all_zero(self):
        traits = {
            "aggressive_passive": 0,
            "curious_aloof": 0,
            "friendly_hostile": 0,
            "brave_fearful": 0,
        }
        result = generate_dialogue(42, traits, 5)
        assert isinstance(result, str) and len(result) > 0

    def test_extreme_traits_all_hundred(self):
        traits = {
            "aggressive_passive": 100,
            "curious_aloof": 100,
            "friendly_hostile": 100,
            "brave_fearful": 100,
        }
        result = generate_dialogue(42, traits, 5)
        assert isinstance(result, str) and len(result) > 0

    def test_negative_score_clamped(self):
        result = generate_dialogue(42, NEUTRAL_TRAITS, -5)
        assert isinstance(result, str) and len(result) > 0

    def test_high_score_clamped(self):
        result = generate_dialogue(42, NEUTRAL_TRAITS, 99)
        assert isinstance(result, str) and len(result) > 0

    def test_large_name_key(self):
        result = generate_dialogue(11_800_000, NEUTRAL_TRAITS, 5)
        assert isinstance(result, str) and len(result) > 0

    def test_missing_trait_key_uses_default(self):
        """Missing trait keys should default to neutral (50)."""
        result = generate_dialogue(42, {}, 5)
        assert isinstance(result, str) and len(result) > 0


class TestDevotedLore:
    def test_devoted_tier_contains_lore(self):
        """At least some devoted-tier dialogues should contain lore snippets."""
        lore_found = 0
        for nk in range(50):
            d = generate_dialogue(nk, NEUTRAL_TRAITS, 10)
            for snippet in LORE_SNIPPETS:
                if snippet in d:
                    lore_found += 1
                    break
        assert lore_found > 0, "No devoted dialogues contained lore snippets"

    def test_stranger_tier_no_lore(self):
        """Stranger tier templates don't use {lore} slot."""
        for nk in range(50):
            d = generate_dialogue(nk, NEUTRAL_TRAITS, 0)
            for snippet in LORE_SNIPPETS:
                assert snippet not in d, f"Stranger dialogue contained lore: {d}"
