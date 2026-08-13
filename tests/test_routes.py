"""Route contract: status codes, and the issue page never ships the answers."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id, recent_issue_ids

MISSING_ISSUE_ID = "1970-W01"
SAMPLE_SIZE = 52
STRUCTURAL_DATA_ATTRIBUTES = {"data-issue", "data-number", "data-index"}


def answer_pattern(value):
    """Match the answer as a standalone token, so 3 does not match 13 or 3/49."""
    return re.compile(r"(?<![0-9A-Za-z/])%s(?![0-9A-Za-z/])" % re.escape(value))


def sample_issues():
    for issue_id in recent_issue_ids(SAMPLE_SIZE):
        issue = build_issue(issue_id)
        if issue is not None:
            yield issue


class RouteStatusTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()

    def test_home_redirects_to_current_issue(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.issue_id, response.headers["Location"])

    def test_home_after_redirect_renders(self):
        self.assertEqual(self.client.get("/", follow_redirects=True).status_code, 200)

    def test_public_pages_return_200(self):
        for path in ("/fascicolo/" + self.issue_id,
                     "/fascicolo/" + self.issue_id + "/soluzioni",
                     "/archivio",
                     "/statistiche",
                     "/sw.js",
                     "/manifest.webmanifest"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_unknown_issue_pages_return_404(self):
        for path in ("/fascicolo/" + MISSING_ISSUE_ID,
                     "/fascicolo/" + MISSING_ISSUE_ID + "/soluzioni",
                     "/fascicolo/non-una-settimana",
                     "/rotta-inesistente"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_service_worker_content_type(self):
        response = self.client.get("/sw.js")
        self.assertIn("javascript", response.headers["Content-Type"])


class AnswerLeakTest(unittest.TestCase):
    """Invariant 4: the issue page carries no answer, anywhere in the markup."""

    def setUp(self):
        self.client = app.test_client()

    def issue_html(self, issue):
        response = self.client.get("/fascicolo/" + issue.issue_id)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_no_answer_in_html_comments(self):
        for issue in sample_issues():
            html = self.issue_html(issue)
            comments = re.findall(r"<!--.*?-->", html, re.S)
            for puzzle in issue.puzzles:
                for field_obj in puzzle.fields:
                    pattern = answer_pattern(field_obj.value)
                    for comment in comments:
                        self.assertIsNone(
                            pattern.search(comment),
                            "answer %r leaked in an HTML comment of %s" % (field_obj.value, issue.issue_id))

    def test_issue_page_carries_only_structural_data_attributes(self):
        """data-issue, data-number and data-index are ordinals; anything else is suspect.

        Whitelisting is stronger than scanning values: a card ordinal can collide with an
        answer by chance, so the guarantee has to come from which attributes exist at all.
        """
        for issue in sample_issues():
            html = self.issue_html(issue)
            names = set(re.findall(r'\b(data-[a-z-]+)=', html))
            self.assertLessEqual(
                names, STRUCTURAL_DATA_ATTRIBUTES,
                "unexpected data attribute on the issue page of %s: %s"
                % (issue.issue_id, sorted(names - STRUCTURAL_DATA_ATTRIBUTES)))

    def test_structural_data_attributes_hold_only_ordinals(self):
        for issue in sample_issues():
            html = self.issue_html(issue)
            numbers = {p.number for p in issue.puzzles}
            for value in re.findall(r'\bdata-number="([^"]*)"', html):
                self.assertIn(int(value), numbers)
            for value in re.findall(r'\bdata-index="([^"]*)"', html):
                self.assertLess(int(value), 4)
            for value in re.findall(r'\bdata-issue="([^"]*)"', html):
                self.assertEqual(value, issue.issue_id)

    def test_no_answer_in_value_attributes(self):
        """Inputs must ship empty: no value, title or alt may carry an answer."""
        for issue in sample_issues():
            html = self.issue_html(issue)
            attributes = re.findall(r'\b(value|title|alt)="([^"]*)"', html)
            for puzzle in issue.puzzles:
                for field_obj in puzzle.fields:
                    pattern = answer_pattern(field_obj.value)
                    for name, content in attributes:
                        self.assertIsNone(
                            pattern.search(content),
                            "answer %r leaked in attribute %s of %s" % (field_obj.value, name, issue.issue_id))

    def test_no_answer_in_inline_scripts(self):
        for issue in sample_issues():
            html = self.issue_html(issue)
            scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S)
            for puzzle in issue.puzzles:
                for field_obj in puzzle.fields:
                    pattern = answer_pattern(field_obj.value)
                    for script in scripts:
                        self.assertIsNone(
                            pattern.search(script),
                            "answer %r leaked in an inline script of %s" % (field_obj.value, issue.issue_id))

    def test_placeholder_never_shows_the_answer(self):
        """A placeholder is a format hint; it must never coincide with the answer."""
        for issue in sample_issues():
            for puzzle in issue.puzzles:
                for field_obj in puzzle.fields:
                    if not field_obj.placeholder:
                        continue
                    self.assertIsNone(
                        answer_pattern(field_obj.value).search(field_obj.placeholder),
                        "placeholder %r reveals the answer %r (%s, %s)"
                        % (field_obj.placeholder, field_obj.value, puzzle.kind, issue.issue_id))

    def test_solution_steps_are_absent_from_the_issue_page(self):
        for issue in sample_issues():
            html = self.issue_html(issue)
            for puzzle in issue.puzzles:
                for step in puzzle.steps:
                    if len(step) < 12:
                        continue
                    self.assertNotIn(
                        step, html,
                        "solution step leaked on the issue page of %s" % issue.issue_id)

    def test_meta_word_is_absent_from_the_markup_channels(self):
        """The weekly word may not hide in comments, attributes or scripts.

        Visible prose is deliberately not checked. META_WORDS is crypto vocabulary, so
        words such as SEGRETO or MODULO also occur as a field label or inside a hint. That
        is a dictionary collision, not a leak: the word is protected by the Caesar key, not
        by its absence from the page. The word list cannot be changed either, because that
        would rewrite every past fascicle.
        """
        for issue in sample_issues():
            html = self.issue_html(issue)
            channels = re.findall(r"<!--.*?-->", html, re.S)
            channels += re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S)
            channels += [c for n, c in re.findall(r'\b((?:data-)[a-z-]+|value|title|alt)="([^"]*)"', html)]
            pattern = re.compile(r"(?<![a-z])%s(?![a-z])" % re.escape(issue.meta.word.lower()))
            for channel in channels:
                self.assertIsNone(
                    pattern.search(channel.lower()),
                    "the weekly word %r leaked in the markup of %s"
                    % (issue.meta.word, issue.issue_id))

    def test_solutions_page_does_show_the_answers(self):
        """Guards the leak tests above from passing vacuously."""
        issue = build_issue(current_issue_id())
        html = self.client.get("/fascicolo/" + issue.issue_id + "/soluzioni").get_data(as_text=True)
        for puzzle in issue.puzzles:
            for field_obj in puzzle.fields:
                self.assertIsNotNone(
                    answer_pattern(field_obj.value).search(html),
                    "answer %r missing from the solutions page" % field_obj.value)


if __name__ == "__main__":
    unittest.main()
