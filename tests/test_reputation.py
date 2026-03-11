"""Tests for lib/reputation.py — reputation tracking system."""

import pytest
from lib.reputation import (
    REPUTATION_TIERS,
    get_tier,
    get_reputation,
    record_visit,
    record_talk,
    reset_visit_flags,
)


class TestGetTier:
    """Tier name lookup at all boundaries."""

    def test_score_0_is_stranger(self):
        assert get_tier(0) == "Stranger"

    def test_score_1_is_acquaintance(self):
        assert get_tier(1) == "Acquaintance"

    def test_score_2_is_acquaintance(self):
        assert get_tier(2) == "Acquaintance"

    def test_score_3_is_familiar(self):
        assert get_tier(3) == "Familiar"

    def test_score_5_is_familiar(self):
        assert get_tier(5) == "Familiar"

    def test_score_6_is_friend(self):
        assert get_tier(6) == "Friend"

    def test_score_8_is_friend(self):
        assert get_tier(8) == "Friend"

    def test_score_9_is_devoted(self):
        assert get_tier(9) == "Devoted"

    def test_score_10_is_devoted(self):
        assert get_tier(10) == "Devoted"


class TestGetReputation:
    """Default entries for unknown creatures."""

    def test_unknown_idx_returns_default(self):
        store = {}
        rep = get_reputation(store, 999)
        assert rep == {"score": 0, "visits": 0, "talked_this_visit": False}

    def test_known_idx_returns_stored(self):
        store = {5: {"score": 3, "visits": 2, "talked_this_visit": True}}
        rep = get_reputation(store, 5)
        assert rep["score"] == 3
        assert rep["visits"] == 2

    def test_does_not_insert_into_store(self):
        store = {}
        get_reputation(store, 42)
        assert 42 not in store


class TestRecordVisit:
    """Visit tracking and first-visit reputation bonus."""

    def test_first_visit_creates_entry(self):
        store = {}
        entry = record_visit(store, 10)
        assert 10 in store
        assert entry["visits"] == 1
        assert entry["score"] == 1  # first visit bonus

    def test_first_visit_sets_talked_false(self):
        store = {}
        entry = record_visit(store, 10)
        assert entry["talked_this_visit"] is False

    def test_repeat_visit_increments_count_only(self):
        store = {}
        record_visit(store, 10)
        entry = record_visit(store, 10)
        assert entry["visits"] == 2
        assert entry["score"] == 1  # no additional score

    def test_repeat_visit_resets_talked_flag(self):
        store = {}
        record_visit(store, 10)
        record_talk(store, 10)  # sets talked_this_visit = True
        assert store[10]["talked_this_visit"] is True
        record_visit(store, 10)  # new visit resets it
        assert store[10]["talked_this_visit"] is False

    def test_score_clamped_at_10(self):
        store = {1: {"score": 10, "visits": 5, "talked_this_visit": False}}
        entry = record_visit(store, 1)
        assert entry["score"] == 10

    def test_sparse_storage(self):
        store = {}
        record_visit(store, 100)
        record_visit(store, 200)
        assert len(store) == 2
        assert 50 not in store


class TestRecordTalk:
    """Talk reputation grants, once-per-visit enforcement."""

    def test_talk_grants_plus_one(self):
        store = {}
        record_visit(store, 1)  # score = 1
        entry = record_talk(store, 1)
        assert entry["score"] == 2
        assert entry["talked_this_visit"] is True

    def test_second_talk_same_visit_no_change(self):
        store = {}
        record_visit(store, 1)
        record_talk(store, 1)
        entry = record_talk(store, 1)
        assert entry["score"] == 2  # still 2, not 3

    def test_talk_after_revisit_grants_again(self):
        store = {}
        record_visit(store, 1)   # score=1
        record_talk(store, 1)    # score=2
        record_visit(store, 1)   # resets talked flag
        entry = record_talk(store, 1)  # score=3
        assert entry["score"] == 3

    def test_talk_without_prior_visit(self):
        store = {}
        entry = record_talk(store, 7)
        assert entry["score"] == 1
        assert entry["visits"] == 0
        assert entry["talked_this_visit"] is True

    def test_score_clamped_at_10_on_talk(self):
        store = {1: {"score": 10, "visits": 3, "talked_this_visit": False}}
        entry = record_talk(store, 1)
        assert entry["score"] == 10

    def test_score_never_below_zero(self):
        store = {1: {"score": 0, "visits": 1, "talked_this_visit": False}}
        # Manually set negative (shouldn't happen, but verify clamp)
        store[1]["score"] = -5
        entry = record_visit(store, 1)
        assert entry["score"] >= 0


class TestResetVisitFlags:
    """Clearing talked_this_visit across all entries."""

    def test_resets_all_flags(self):
        store = {
            1: {"score": 2, "visits": 1, "talked_this_visit": True},
            2: {"score": 5, "visits": 3, "talked_this_visit": True},
            3: {"score": 0, "visits": 1, "talked_this_visit": False},
        }
        reset_visit_flags(store)
        for entry in store.values():
            assert entry["talked_this_visit"] is False

    def test_empty_store_no_error(self):
        store = {}
        reset_visit_flags(store)  # should not raise

    def test_preserves_other_fields(self):
        store = {1: {"score": 7, "visits": 10, "talked_this_visit": True}}
        reset_visit_flags(store)
        assert store[1]["score"] == 7
        assert store[1]["visits"] == 10


class TestTierCoverage:
    """Ensure all scores 0-10 have a tier."""

    def test_all_scores_have_tier(self):
        for score in range(11):
            tier = get_tier(score)
            assert tier in ("Stranger", "Acquaintance", "Familiar", "Friend", "Devoted"), \
                f"Score {score} returned unexpected tier: {tier}"

    def test_tier_list_is_complete(self):
        """Tiers cover full 0-10 range without gaps."""
        covered = set()
        for lo, hi, _ in REPUTATION_TIERS:
            for s in range(lo, hi + 1):
                covered.add(s)
        assert covered == set(range(11))
