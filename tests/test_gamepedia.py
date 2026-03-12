"""Tests for gamepedia click-to-select geometry and word_wrap_text."""
import unittest
from unittest.mock import MagicMock

from lib.gamepedia import (
    GP_LEFT_X, GP_LEFT_W, GP_TOP_Y, GP_LINE_H,
    GAMEPEDIA_CONTENT, _gamepedia_flat, word_wrap_text,
)


# ── Helper functions ───────────────────────────────────────────────────────

def resolve_click(mx, my, content, collapsed_groups=None):
    """Pure reimplementation of the gamepedia click-to-select logic from main.py.

    Returns the abs flat_idx of the selected topic, or None if nothing was hit.
    Group header rows are not returned (they toggle collapse, not select a topic).
    collapsed_groups: set of group names that are collapsed (default: empty = all expanded).
    """
    if collapsed_groups is None:
        collapsed_groups = set()
    if not (GP_LEFT_X <= mx <= GP_LEFT_X + GP_LEFT_W and my >= GP_TOP_Y):
        return None
    y_cursor = GP_TOP_Y
    abs_flat_idx = 0
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        if gname in collapsed_groups:
            abs_flat_idx += len(topics)
            continue
        for title, _text in topics:
            if y_cursor <= my < y_cursor + GP_LINE_H:
                return abs_flat_idx
            y_cursor += GP_LINE_H
            abs_flat_idx += 1
    return None


def compute_topic_positions(content, collapsed_groups=None):
    """Compute (abs_flat_idx, y_start, y_end) for every visible topic using the render layout.

    collapsed_groups: set of group names that are collapsed (default: empty = all expanded).
    """
    if collapsed_groups is None:
        collapsed_groups = set()
    positions = []
    y_cursor = GP_TOP_Y
    abs_flat_idx = 0
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        if gname in collapsed_groups:
            abs_flat_idx += len(topics)
            continue
        for title, _text in topics:
            positions.append((abs_flat_idx, y_cursor, y_cursor + GP_LINE_H))
            y_cursor += GP_LINE_H
            abs_flat_idx += 1
    return positions


# ── Click-to-select tests ─────────────────────────────────────────────────

class TestGamepediaClickSelect(unittest.TestCase):
    """Tests that click coordinates correctly resolve to flat topic indices."""

    def test_click_selects_first_topic(self):
        """Click center of first topic row -> flat_idx 0 (Keyboard)."""
        positions = compute_topic_positions(GAMEPEDIA_CONTENT)
        _, y_start, y_end = positions[0]
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = (y_start + y_end) // 2
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT)
        self.assertEqual(result, 0)

    def test_click_selects_second_group_first_topic(self):
        """Click center of 'Travel & Slerp' row -> flat_idx 3."""
        positions = compute_topic_positions(GAMEPEDIA_CONTENT)
        _, y_start, y_end = positions[3]
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = (y_start + y_end) // 2
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT)
        self.assertEqual(result, 3)

    def test_click_selects_last_topic(self):
        """Click center of last topic row -> last flat_idx."""
        positions = compute_topic_positions(GAMEPEDIA_CONTENT)
        last_idx = len(positions) - 1
        _, y_start, y_end = positions[last_idx]
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = (y_start + y_end) // 2
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT)
        self.assertEqual(result, last_idx)
        self.assertEqual(last_idx, 23)

    def test_click_on_group_header_selects_nothing(self):
        """Click on first group header row (Controls) -> no selection."""
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = GP_TOP_Y + GP_LINE_H // 2  # center of header row
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT)
        self.assertIsNone(result)

    def test_click_outside_left_panel_selects_nothing(self):
        """Click at x=400 (outside panel bounds) -> no selection."""
        positions = compute_topic_positions(GAMEPEDIA_CONTENT)
        _, y_start, y_end = positions[0]
        my = (y_start + y_end) // 2
        result = resolve_click(400, my, GAMEPEDIA_CONTENT)
        self.assertIsNone(result)

    def test_click_position_matches_render_position(self):
        """Every topic's render y-center resolves to the correct flat_idx."""
        positions = compute_topic_positions(GAMEPEDIA_CONTENT)
        mx = GP_LEFT_X + GP_LEFT_W // 2
        for flat_idx, y_start, y_end in positions:
            my = (y_start + y_end) // 2
            result = resolve_click(mx, my, GAMEPEDIA_CONTENT)
            self.assertEqual(
                result,
                flat_idx,
                f"Click at y={my} (topic {flat_idx}) resolved to {result}",
            )

    def test_flat_list_length(self):
        """Sanity check: _gamepedia_flat has exactly 24 entries."""
        self.assertEqual(len(_gamepedia_flat), 24)

    def test_flat_list_matches_content_order(self):
        """_gamepedia_flat order matches iteration over GAMEPEDIA_CONTENT."""
        expected = []
        for gname, topics in GAMEPEDIA_CONTENT:
            for title, text in topics:
                expected.append((gname, title, text))
        self.assertEqual(_gamepedia_flat, expected)

    def test_compass_topic_has_visibility_note(self):
        """Compass topic must document that it is only visible in Assigned mode."""
        compass_text = None
        for group_name, topics in GAMEPEDIA_CONTENT:
            for title, text in topics:
                if title == "Compass":
                    compass_text = text
        self.assertIsNotNone(compass_text, "Compass topic not found")
        self.assertIn("Assigned color mode", compass_text)


# ── Collapse-behaviour tests ───────────────────────────────────────────────

class TestGamepediaCollapse(unittest.TestCase):
    """Tests for collapsed-group behaviour in click resolution and layout."""

    def test_collapsed_group_topics_not_clickable(self):
        """Topics in a collapsed group return None on click."""
        # Collapse 'Controls' group — its topics should not be hit
        collapsed = {"Controls"}
        # Without collapsing, first topic (Keyboard) is at GP_TOP_Y + GP_LINE_H
        # With Controls collapsed, clicking there should return None
        mx = GP_LEFT_X + GP_LEFT_W // 2
        my = GP_TOP_Y + GP_LINE_H + GP_LINE_H // 2  # where Keyboard row would be
        result = resolve_click(mx, my, GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        self.assertIsNone(result)

    def test_collapsed_group_shifts_later_groups_up(self):
        """Collapsing Controls shifts Navigation topics up by (num Controls topics) rows."""
        # With Controls collapsed: Navigation header is at GP_TOP_Y + 1*line_h (Controls header)
        # First Navigation topic (Travel & Slerp, abs_idx=3) is at GP_TOP_Y + 2*line_h
        collapsed = {"Controls"}
        positions = compute_topic_positions(GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        # First position should be for abs_flat_idx=3 (Travel & Slerp)
        abs_idx, y_start, y_end = positions[0]
        self.assertEqual(abs_idx, 3)
        # y_start = GP_TOP_Y + 2*GP_LINE_H (Controls header + Navigation header)
        expected_y = GP_TOP_Y + 2 * GP_LINE_H
        self.assertEqual(y_start, expected_y)

    def test_all_collapsed_no_clickable_topics(self):
        """With all groups collapsed, no topic click resolves."""
        all_groups = {g for g, _ in GAMEPEDIA_CONTENT}
        mx = GP_LEFT_X + GP_LEFT_W // 2
        for my in range(GP_TOP_Y, GP_TOP_Y + 20 * GP_LINE_H, GP_LINE_H):
            result = resolve_click(mx, my, GAMEPEDIA_CONTENT, collapsed_groups=all_groups)
            self.assertIsNone(result, f"Expected None at y={my}, got {result}")

    def test_partially_collapsed_positions(self):
        """compute_topic_positions with all groups collapsed returns empty list."""
        collapsed = {g for g, _ in GAMEPEDIA_CONTENT}
        positions = compute_topic_positions(GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        self.assertEqual(len(positions), 0)


# ── Word wrap tests ────────────────────────────────────────────────────────

class TestWordWrap(unittest.TestCase):
    """Tests for the word_wrap_text function using a mock font."""

    def _make_font(self, char_width=7):
        """Return a mock font where size() returns char_width * len(text)."""
        font = MagicMock()
        font.size = lambda text: (char_width * len(text), 16)
        return font

    def test_word_wrap_basic(self):
        """Short text within width returns a single line."""
        font = self._make_font(char_width=7)
        # "hello world" = 11 chars -> 77px, fits in 200px
        result = word_wrap_text("hello world", 200, font)
        self.assertEqual(result, ["hello world"])

    def test_word_wrap_splits_long_line(self):
        """Text exceeding width gets split across lines."""
        font = self._make_font(char_width=10)
        # max_width=50 -> fits 5 chars
        # "aa bb" = 5 chars -> 50 <= 50 -> fits
        # "aa bb cc" = 8 chars -> 80 > 50 -> split
        result = word_wrap_text("aa bb cc dd", 50, font)
        self.assertEqual(result, ["aa bb", "cc dd"])

    def test_word_wrap_newlines(self):
        """Explicit newlines produce separate lines, blank lines preserved."""
        font = self._make_font(char_width=7)
        result = word_wrap_text("line one\n\nline three", 500, font)
        self.assertEqual(result, ["line one", "", "line three"])

    def test_word_wrap_multiple_paragraphs(self):
        """Multiple non-empty paragraphs each wrap independently."""
        font = self._make_font(char_width=10)
        # max_width=60 -> fits 6 chars
        text = "aaa bbb ccc\ndd ee"
        result = word_wrap_text(text, 60, font)
        # "aaa bbb" = 7 chars -> 70 > 60 -> split after "aaa"
        # "bbb ccc" = 7 chars -> 70 > 60 -> split after "bbb"
        # "dd ee" = 5 chars -> 50 <= 60 -> fits
        self.assertEqual(result, ["aaa", "bbb", "ccc", "dd ee"])


# ── Keyboard nav helper ────────────────────────────────────────────────────

def build_nav_order(content, collapsed_groups=None):
    """Build unified nav order list: [("group", gname) | ("topic", abs_idx), ...]"""
    if collapsed_groups is None:
        collapsed_groups = set()
    nav = []
    abs_idx = 0
    for gname, topics in content:
        nav.append(("group", gname))
        if gname not in collapsed_groups:
            for _title, _text in topics:
                nav.append(("topic", abs_idx))
                abs_idx += 1
        else:
            abs_idx += len(topics)
    return nav


# ── Keyboard nav tests ─────────────────────────────────────────────────────

class TestGamepediaKeyboardNav(unittest.TestCase):
    """Tests for keyboard navigation order building logic."""

    def test_all_expanded_starts_with_group(self):
        """All expanded: first item is ("group", "Controls")."""
        nav = build_nav_order(GAMEPEDIA_CONTENT)
        self.assertEqual(nav[0], ("group", "Controls"))

    def test_all_expanded_second_item_is_first_topic(self):
        """All expanded: second item is ("topic", 0) (first topic in Controls)."""
        nav = build_nav_order(GAMEPEDIA_CONTENT)
        self.assertEqual(nav[1], ("topic", 0))

    def test_all_collapsed_only_groups(self):
        """All groups collapsed: nav contains only group rows."""
        all_groups = {g for g, _ in GAMEPEDIA_CONTENT}
        nav = build_nav_order(GAMEPEDIA_CONTENT, collapsed_groups=all_groups)
        self.assertTrue(all(kind == "group" for kind, _ in nav))
        self.assertEqual(len(nav), len(GAMEPEDIA_CONTENT))

    def test_collapsing_one_group_removes_its_topics(self):
        """Collapsing Controls removes its 3 topics but keeps the group row."""
        collapsed = {"Controls"}
        nav = build_nav_order(GAMEPEDIA_CONTENT, collapsed_groups=collapsed)
        total_topics = len(_gamepedia_flat)
        controls_topics = len(dict(GAMEPEDIA_CONTENT)["Controls"])
        expected_len = len(GAMEPEDIA_CONTENT) + (total_topics - controls_topics)
        self.assertEqual(len(nav), expected_len)
        self.assertIn(("group", "Controls"), nav)
        # No topics with abs_idx 0, 1, or 2 (Controls topics) should appear
        for i in range(controls_topics):
            self.assertNotIn(("topic", i), nav)

    def test_nav_order_full_length_all_expanded(self):
        """All expanded: nav length equals num_groups + num_topics."""
        nav = build_nav_order(GAMEPEDIA_CONTENT)
        expected = len(GAMEPEDIA_CONTENT) + len(_gamepedia_flat)
        self.assertEqual(len(nav), expected)


if __name__ == "__main__":
    unittest.main()
