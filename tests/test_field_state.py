"""A wrong field must say so, not just look so.

Today the only signal is the class "errato", which is colour. Anyone using a screen
reader, or unable to tell the colours apart, gets nothing.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def client_source():
    with open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8") as handle:
        return handle.read()


def mark_fields_body(source):
    """The body of markFields, which owns the per-field state."""
    start = source.index("function markFields")
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError("markFields is not closed")


class FieldStateTest(unittest.TestCase):
    def setUp(self):
        self.source = client_source()
        self.body = mark_fields_body(self.source)

    def test_a_wrong_field_is_marked_invalid(self):
        self.assertIn("aria-invalid", self.body)

    def test_the_state_is_set_where_the_colour_is_set(self):
        """Two places deciding the same thing would drift apart."""
        self.assertIn("errato", self.body)
        self.assertEqual(self.source.count("aria-invalid"), self.body.count("aria-invalid"),
                         "aria-invalid is also set outside markFields")

    def test_a_correct_field_does_not_stay_invalid(self):
        self.assertTrue(
            re.search(r"removeAttribute\(\s*[\"']aria-invalid", self.body)
            or re.search(r"aria-invalid[\"']\s*,\s*ok\s*\?", self.body),
            "nothing clears aria-invalid when the field becomes correct")

    def test_colour_is_not_the_only_signal(self):
        colour_only = self.body.count("classList.toggle") and "aria-invalid" not in self.body
        self.assertFalse(colour_only)


class ServedMarkupTest(unittest.TestCase):
    """The state belongs to a verdict, so a fresh page must not carry it."""

    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()

    def test_a_fresh_page_marks_no_field_invalid(self):
        html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.assertNotIn("aria-invalid", html)

    def test_inputs_are_still_plain_text_fields(self):
        html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.assertIn("<input", html)
        for match in re.finditer(r"<input[^>]*>", html):
            with self.subTest(tag=match.group(0)[:60]):
                self.assertNotIn("required", match.group(0))


if __name__ == "__main__":
    unittest.main()
