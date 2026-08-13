"""Exporting a fascicle as a self-contained printable file.

A PDF would need a library, and the dependency rule forbids one, so the export is a single
HTML file with its styles inlined: it opens and prints from anywhere, with nothing to fetch.
"""

import os
import re
import sys
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

MISSING_ISSUE_ID = "1970-W01"
INTERACTIVE_TAGS = ("form", "input", "button", "select", "textarea", "details", "summary")


class Collector(HTMLParser):
    VOID = {"input", "br", "img", "meta", "link", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.external = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append(tag)
        for name in ("src", "href"):
            value = attributes.get(name)
            if value and not value.startswith("#"):
                self.external.append((tag, name, value))

    def handle_data(self, data):
        self.text.append(data)


def parse(html):
    collector = Collector()
    collector.feed(html)
    return collector


class ExportTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)

    def export(self, issue_id=None):
        response = self.client.get("/fascicolo/%s/stampa" % (issue_id or self.issue_id))
        self.assertEqual(response.status_code, 200)
        return response


class DeliveryTest(ExportTestCase):
    def test_a_missing_issue_is_404(self):
        self.assertEqual(
            self.client.get("/fascicolo/%s/stampa" % MISSING_ISSUE_ID).status_code, 404)

    def test_it_is_served_as_a_download(self):
        disposition = self.export().headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition)

    def test_the_filename_names_the_issue(self):
        disposition = self.export().headers["Content-Disposition"]
        self.assertIn(self.issue_id, disposition)
        self.assertIn(".html", disposition)

    def test_it_is_html(self):
        self.assertIn("text/html", self.export().headers["Content-Type"])

    def test_the_fascicle_links_to_its_export(self):
        page = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.assertIn("/fascicolo/%s/stampa" % self.issue_id, page)


class SelfContainedTest(ExportTestCase):
    def test_nothing_is_fetched_from_outside(self):
        """The file must print from a folder with no server behind it."""
        collector = parse(self.export().get_data(as_text=True))
        self.assertEqual(collector.external, [],
                         "the export still points at %r" % collector.external)

    def test_the_styles_travel_with_the_file(self):
        html = self.export().get_data(as_text=True)
        self.assertIn("<style", html)
        self.assertNotIn("<link", html)

    def test_no_script_is_shipped(self):
        self.assertNotIn("script", parse(self.export().get_data(as_text=True)).tags)

    def test_it_is_a_whole_document(self):
        html = self.export().get_data(as_text=True)
        self.assertIn("<!doctype html", html.lower())
        for tag in ("html", "head", "body", "title"):
            with self.subTest(tag=tag):
                self.assertIn(tag, parse(html).tags)


class PaperOnlyTest(ExportTestCase):
    def test_no_interactive_element_survives(self):
        tags = parse(self.export().get_data(as_text=True)).tags
        for tag in INTERACTIVE_TAGS:
            with self.subTest(tag=tag):
                self.assertNotIn(tag, tags)

    def test_every_card_is_there(self):
        text = " ".join(parse(self.export().get_data(as_text=True)).text)
        for puzzle in self.issue.puzzles:
            with self.subTest(number=puzzle.number):
                self.assertIn(puzzle.title, text)
                self.assertIn(puzzle.statement, text)

    def test_the_given_data_is_there(self):
        text = " ".join(parse(self.export().get_data(as_text=True)).text)
        for puzzle in self.issue.puzzles:
            for label, value in puzzle.given:
                with self.subTest(number=puzzle.number, label=label):
                    self.assertIn(str(value), text)

    def test_the_card_numbers_are_there(self):
        text = " ".join(parse(self.export().get_data(as_text=True)).text)
        for puzzle in self.issue.puzzles:
            with self.subTest(number=puzzle.number):
                self.assertIn("%02d" % puzzle.number, text)


class NoAnswersTest(ExportTestCase):
    """Invariant 4 holds on paper too: the sheet is for solving, not for reading."""

    def card_blocks(self, html):
        """The markup of each card on its own, so a leak cannot hide behind another card."""
        blocks = re.split(r'<div class="scheda">', html)[1:]
        self.assertEqual(len(blocks), len(self.issue.puzzles))
        return [b.split("</div>")[0] for b in blocks]

    def test_no_answer_is_in_the_file(self):
        """Checked against visible text, not just attributes: the export has no form to
        hide behind, so a printed answer would simply be readable.

        A number already printed in the statement carries no information; only a value
        that turns up for the first time next to its own card would be a leak.
        """
        html = self.export().get_data(as_text=True)
        for puzzle, block in zip(self.issue.puzzles, self.card_blocks(html)):
            # Everything the card legitimately prints: the exercise, plus the header
            # numbers. The estimated minutes and the card number collide with a small
            # answer often enough that scanning for the bare digit finds only noise.
            public = set(re.findall(r"[0-9]+(?:/[0-9]+)?", puzzle.statement + " " + puzzle.title))
            for label, value in puzzle.given:
                public.update(re.findall(r"[0-9]+(?:/[0-9]+)?", "%s %s" % (label, value)))
            public.update({str(puzzle.minutes), str(puzzle.number), "%02d" % puzzle.number})
            for field_obj in puzzle.fields:
                public.update(re.findall(r"[0-9]+(?:/[0-9]+)?", field_obj.label))
            public.update(re.findall(r"[0-9]+(?:/[0-9]+)?", puzzle.meta_label))
            visible = " ".join(parse(block).text)
            for field_obj in puzzle.fields:
                if field_obj.value in public:
                    continue
                with self.subTest(number=puzzle.number, value=field_obj.value):
                    self.assertIsNone(
                        re.search(r"(?<![0-9A-Za-z/])%s(?![0-9A-Za-z/])"
                                  % re.escape(field_obj.value), visible),
                        "answer %r is printed on card %d" % (field_obj.value, puzzle.number))

    def test_the_answer_lines_are_blank(self):
        """The sheet is for writing on, so every line must arrive empty."""
        html = self.export().get_data(as_text=True)
        for line in re.findall(r'<span class="riga-vuota">(.*?)</span>', html, re.S):
            with self.subTest(line=line[:30]):
                self.assertEqual(line.strip(), "")

    def test_no_solution_step_is_in_the_file(self):
        html = self.export().get_data(as_text=True)
        for puzzle in self.issue.puzzles:
            for step in puzzle.steps:
                if len(step) < 12:
                    continue
                with self.subTest(number=puzzle.number):
                    self.assertNotIn(step, html)

    def test_the_boxes_for_the_word_arrive_empty(self):
        html = self.export().get_data(as_text=True)
        boxes = re.findall(r'<span class="casella">(.*?)</span>', html, re.S)
        self.assertEqual(len(boxes), len(self.issue.meta.word))
        for box in boxes:
            with self.subTest(box=box[:30]):
                self.assertEqual(box.strip(), "")

    def test_the_final_block_shows_the_ciphertext_and_not_the_word(self):
        html = self.export().get_data(as_text=True)
        final = html.split('<div class="finale">')[1].split("<p class=\"piede\"")[0]
        visible = " ".join(parse(final).text)
        self.assertIn(self.issue.meta.ciphertext, visible)
        self.assertNotIn(self.issue.meta.word.lower(), visible.lower())

    def test_the_caesar_shift_is_not_given_away(self):
        """The shift is the whole point of adding up the nine answers."""
        html = self.export().get_data(as_text=True)
        final = html.split('<div class="finale">')[1]
        self.assertIsNone(re.search(r"(?<!\d)%d(?!\d)" % self.issue.meta.shift, final))

    def test_the_hints_are_not_spelled_out(self):
        """On paper nothing can stay folded, so the near-solution hint must not travel."""
        html = self.export().get_data(as_text=True)
        for puzzle in self.issue.puzzles:
            with self.subTest(number=puzzle.number):
                self.assertNotIn(puzzle.hints[2], html)


class ReproducibleTest(ExportTestCase):
    def test_the_same_issue_exports_the_same_bytes(self):
        """Invariant 2, at the level of the export."""
        first = self.export().get_data()
        second = self.export().get_data()
        self.assertEqual(first, second)

    def test_a_past_issue_can_still_be_exported(self):
        response = self.client.get("/fascicolo/2026-W30/stampa")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2026-W30", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
