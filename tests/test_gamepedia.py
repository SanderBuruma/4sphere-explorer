"""Tests for gamepedia click-to-select geometry and word_wrap_text."""
import unittest
from unittest.mock import MagicMock

from lib.gamepedia import (
    GP_LEFT_X, GP_LEFT_W, GP_TOP_Y, GP_LINE_H,
    GAMEPEDIA_CONTENT, _gamepedia_flat, word_wrap_text,
)


# ── Helper functions ───────────────────────────────────────────────────────

def resolve_click(mx, my, content):
    """Pure reimplementation of the gamepedia click-to-select logic from main.py.

    Returns the flat_idx of the selected topic, or None if nothing was hit.
    """
    if not (GP_LEFT_X <= mx <= GP_LEFT_X + GP_LEFT_W and my >= GP_TOP_Y):
        return None
    y_cursor = GP_TOP_Y
    flat_idx = 0
    selected = None
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        for title, _text in topics:
            if y_cursor <= my < y_cursor + GP_LINE_H:
                selected = flat_idx
            y_cursor += GP_LINE_H
            flat_idx += 1
    return selected


def compute_topic_positions(content):
    """Compute (flat_idx, y_start, y_end) for every topic using the render layout."""
    positions = []
    y_cursor = GP_TOP_Y
    flat_idx = 0
    for gname, topics in content:
        y_cursor += GP_LINE_H  # group header
        for title, _text in topics:
            positions.append((flat_idx, y_cursor, y_cursor + GP_LINE_H))
            y_cursor += GP_LINE_H
            flat_idx += 1
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
        self.assertEqual(last_idx, 22)

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
        """Sanity check: _gamepedia_flat has exactly 22 entries."""
        self.assertEqual(len(_gamepedia_flat), 23)

    def test_flat_list_matches_content_order(self):
        """_gamepedia_flat order matches iteration over GAMEPEDIA_CONTENT."""
        expected = []
        for gname, topics in GAMEPEDIA_CONTENT:
            for title, text in topics:
                expected.append((gname, title, text))
        self.assertEqual(_gamepedia_flat, expected)


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


if __name__ == "__main__":
    unittest.main()
