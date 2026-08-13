"""A stopwatch per card, measured against the time the card declares.

It lives entirely in the browser: nothing is stored, so the log schema is untouched and
past fascicles keep reproducing exactly as before.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def client_source():
    with open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8") as handle:
        return handle.read()


class DeclaredTimeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)

    def test_every_card_publishes_its_declared_time(self):
        declared = [int(v) for v in re.findall(r'data-minutes="(\d+)"', self.html)]
        self.assertEqual(declared, [p.minutes for p in self.issue.puzzles])

    def test_the_declared_time_is_never_an_answer(self):
        """It is a structural number, like the card ordinal, not a result."""
        for value in re.findall(r'data-minutes="(\d+)"', self.html):
            with self.subTest(minutes=value):
                self.assertGreaterEqual(int(value), 1)
                self.assertLessEqual(int(value), 15)

    def test_each_card_has_a_place_to_show_the_time(self):
        self.assertEqual(len(re.findall(r'class="cronometro"', self.html)),
                         len(self.issue.puzzles))

    def test_the_stopwatch_ships_empty(self):
        """Nothing has been timed yet when the page arrives."""
        for content in re.findall(r'<span class="cronometro"[^>]*>(.*?)</span>', self.html, re.S):
            with self.subTest(content=content[:30]):
                self.assertEqual(content.strip(), "")

    def test_the_stopwatch_does_not_print(self):
        with open(os.path.join(ROOT, "static", "style.css"), encoding="utf-8") as handle:
            css = handle.read()
        print_block = css.split("@media print")[1]
        self.assertIn("cronometro", print_block.split("}\n}")[0])

    def test_the_export_carries_no_stopwatch(self):
        export = self.client.get("/fascicolo/%s/stampa" % self.issue_id).get_data(as_text=True)
        self.assertNotIn("cronometro", export)


class ClientTest(unittest.TestCase):
    """Structural: the gates run without a browser."""

    def setUp(self):
        self.source = client_source()

    def test_there_is_a_stopwatch(self):
        self.assertIn("startStopwatch", self.source)
        self.assertIn("stopStopwatch", self.source)

    def test_it_starts_when_the_reader_starts(self):
        self.assertIn("focus", self.source)

    def test_it_stops_when_the_card_is_solved(self):
        line = [l for l in self.source.splitlines() if 'classList.add("risolta")' in l]
        self.assertTrue(line)
        self.assertIn("stopStopwatch", line[0])

    def test_it_compares_against_the_declared_time(self):
        self.assertIn("minutes", self.source)
        self.assertIn("dataset.minutes", self.source)

    def test_it_writes_text_not_markup(self):
        for construct in ("innerHTML", "outerHTML", "insertAdjacentHTML"):
            with self.subTest(construct=construct):
                self.assertNotIn(construct, self.source)

    def test_nothing_about_timing_is_sent_to_the_server(self):
        """The log schema stays as it is, so past issues keep reproducing."""
        for suspicious in ("/api/tempo", "seconds:", "elapsed:"):
            with self.subTest(token=suspicious):
                self.assertNotIn(suspicious, self.source)


class StorageUntouchedTest(unittest.TestCase):
    def test_the_log_has_no_time_column(self):
        import storage
        self.assertNotIn("seconds", storage.SCHEMA)
        self.assertNotIn("elapsed", storage.SCHEMA)


if __name__ == "__main__":
    unittest.main()
