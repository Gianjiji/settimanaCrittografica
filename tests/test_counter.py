"""The solved counter at the top of the fascicle.

It must count the nine cards, never the final word, follow the log, and reveal nothing
about the answers themselves.
"""

import os
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage
from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_PER_ISSUE = 9


class CounterText(HTMLParser):
    """The text of the element carrying the given class."""

    def __init__(self, wanted):
        super().__init__(convert_charrefs=True)
        self.wanted = wanted
        self.depth = 0
        self.text = []
        self.attrs = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if self.depth:
            self.depth += 1
        elif self.wanted in (attributes.get("class") or "").split():
            self.depth = 1
            self.attrs = attributes

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)


def counter_of(html):
    parser = CounterText("contatore")
    parser.feed(html)
    return " ".join("".join(parser.text).split()), parser.attrs


class CounterTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.real_db_path = storage.DB_PATH
        self.addCleanup(self.restore_db_path)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "attempts.db")
        self.client = app.test_client()
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)

    def restore_db_path(self):
        storage.DB_PATH = self.real_db_path

    def page(self):
        return self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)

    def counter(self):
        return counter_of(self.page())[0]

    def solve(self, puzzle):
        response = self.client.post("/api/verifica",
                                    json={"issue": self.issue_id, "number": puzzle.number,
                                          "answers": [f.value for f in puzzle.fields]})
        self.assertTrue(response.get_json()["correct"])


class CounterContentTest(CounterTestCase):
    def test_the_counter_is_on_the_page(self):
        self.assertTrue(self.counter(), "no element with class 'contatore'")

    def test_a_fresh_issue_starts_at_zero(self):
        self.assertIn("0", self.counter())
        self.assertIn(str(CARDS_PER_ISSUE), self.counter())

    def test_the_counter_follows_the_log(self):
        for index, puzzle in enumerate(self.issue.puzzles, start=1):
            self.solve(puzzle)
            with self.subTest(solved=index):
                numbers = re.findall(r"\d+", self.counter())
                self.assertEqual(numbers[0], str(index))
                self.assertEqual(numbers[1], str(CARDS_PER_ISSUE))

    def test_a_wrong_attempt_does_not_move_the_counter(self):
        puzzle = self.issue.puzzles[0]
        self.client.post("/api/verifica", json={"issue": self.issue_id, "number": puzzle.number,
                                                "answers": ["999999"]})
        self.assertEqual(re.findall(r"\d+", self.counter())[0], "0")

    def test_solving_the_same_card_twice_counts_once(self):
        puzzle = self.issue.puzzles[0]
        self.solve(puzzle)
        self.solve(puzzle)
        self.assertEqual(re.findall(r"\d+", self.counter())[0], "1")

    def test_the_weekly_word_is_not_counted_as_a_card(self):
        """The word is logged as card zero and must stay out of the total."""
        self.client.post("/api/parola", json={"issue": self.issue_id,
                                              "answer": self.issue.meta.word})
        numbers = re.findall(r"\d+", self.counter())
        self.assertEqual(numbers[0], "0")
        self.assertEqual(numbers[1], str(CARDS_PER_ISSUE))

    def test_the_count_is_scoped_to_its_own_issue(self):
        other = build_issue("2026-W30")
        self.client.post("/api/verifica",
                         json={"issue": other.issue_id, "number": other.puzzles[0].number,
                               "answers": [f.value for f in other.puzzles[0].fields]})
        self.assertEqual(re.findall(r"\d+", self.counter())[0], "0")

    def test_the_counter_is_announced(self):
        self.assertEqual(counter_of(self.page())[1].get("role"), "status")


class CounterLeaksNothingTest(CounterTestCase):
    def test_the_counter_carries_no_answer(self):
        for puzzle in self.issue.puzzles:
            self.solve(puzzle)
        text = self.counter()
        for puzzle in self.issue.puzzles:
            for field_obj in puzzle.fields:
                with self.subTest(value=field_obj.value):
                    self.assertIsNone(
                        re.search(r"(?<![0-9A-Za-z/])%s(?![0-9A-Za-z/])" % re.escape(field_obj.value),
                                  text),
                        "the counter shows the answer %r" % field_obj.value)


class CounterStaysCurrentTest(unittest.TestCase):
    """The page never reloads, so the client has to keep the counter honest."""

    def setUp(self):
        with open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8") as handle:
            self.source = handle.read()

    def test_the_client_refreshes_the_counter(self):
        self.assertIn("contatore", self.source)

    def test_the_counter_is_recomputed_from_the_cards(self):
        """Counting .scheda.risolta needs no extra state, so it cannot drift."""
        self.assertIn("risolta", self.source)

    def test_the_refresh_happens_where_a_card_is_marked_solved(self):
        """Marking a card solved and recounting must not drift apart."""
        line = [l for l in self.source.splitlines() if 'classList.add("risolta")' in l]
        self.assertTrue(line, "nothing marks a card solved any more")
        self.assertIn("refreshCounter()", line[0])


if __name__ == "__main__":
    unittest.main()
