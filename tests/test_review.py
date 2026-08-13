"""The review page: the families you get wrong most often, drawn from real issues.

It reuses cards from past fascicles, so /api/verifica keeps working unchanged: an issue id
and a card number already identify an exercise.
"""

import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
import storage
from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id, recent_issue_ids

MIN_ATTEMPTS = 3


class ReviewTestCase(unittest.TestCase):
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
        response = self.client.get("/ripasso")
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def log(self, kind, difficulty=2, correct=False, times=1):
        for _ in range(times):
            storage.log_attempt(self.issue_id, 1, kind, difficulty, correct)

    def kinds_in(self, html):
        return set(re.findall(r'data-kind="([^"]*)"', html))


class EmptyLogTest(ReviewTestCase):
    def test_the_page_answers_even_with_no_history(self):
        self.assertEqual(self.client.get("/ripasso").status_code, 200)

    def test_it_says_there_is_nothing_to_review_yet(self):
        html = self.page()
        self.assertNotIn('data-kind="', html)
        self.assertIn("Nessun", html)

    def test_it_is_reachable_from_the_menu(self):
        html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.assertIn("/ripasso", html)


class SelectionTest(ReviewTestCase):
    def test_the_worst_family_is_offered(self):
        self.log("catena_rsa", correct=False, times=4)
        self.log("coincidenzario", correct=True, times=4)
        self.assertIn("catena_rsa", self.kinds_in(self.page()))

    def test_a_family_you_never_miss_is_not_offered(self):
        self.log("catena_rsa", correct=False, times=4)
        self.log("coincidenzario", correct=True, times=4)
        self.assertNotIn("coincidenzario", self.kinds_in(self.page()))

    def test_a_family_with_too_few_attempts_is_ignored(self):
        """One unlucky attempt is not evidence of a weakness."""
        self.log("catena_rsa", correct=False, times=1)
        self.assertEqual(self.kinds_in(self.page()), set())

    def test_families_are_ordered_by_error_rate(self):
        """Ordered worst first, not alphabetically.

        segreto_spezzato is the worse family here and sorts last by name, so a fallback
        to alphabetical order cannot pass this by luck.
        """
        self.log("segreto_spezzato", correct=False, times=4)
        self.log("catena_rsa", correct=False, times=1)
        self.log("catena_rsa", correct=True, times=3)
        kinds = re.findall(r'data-kind="([^"]*)"', self.page())
        self.assertEqual(kinds[:2], ["segreto_spezzato", "catena_rsa"])

    def test_only_known_families_are_offered(self):
        """A retired generator leaves rows in the log that can no longer be built."""
        self.log("famiglia_che_non_esiste", correct=False, times=5)
        self.assertEqual(app_module.weak_families(), [("famiglia_che_non_esiste", 2)])
        self.assertEqual(self.kinds_in(self.page()), set())

    def test_the_offered_card_matches_the_difficulty_that_is_weak(self):
        """The log is per kind and difficulty, and so is the weakness."""
        self.log("catena_rsa", difficulty=3, correct=False, times=5)
        self.log("catena_rsa", difficulty=1, correct=True, times=5)
        html = self.page()
        cards = re.findall(r'data-issue="([^"]*)"[^>]*data-number="(\d+)"', html)
        self.assertTrue(cards)
        for issue_id, number in cards:
            issue = build_issue(issue_id)
            puzzle = next(p for p in issue.puzzles if p.number == int(number))
            with self.subTest(issue=issue_id, number=number):
                self.assertEqual(puzzle.difficulty, 3)

    def test_the_page_stays_short(self):
        """More weak families than the page shows: the cut has to bite."""
        from crypto_puzzles.fascicle import GENERATORS
        self.assertGreater(len(GENERATORS) * 3, app_module.REVIEW_CARDS)
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            for difficulty in (1, 2, 3):
                self.log(kind, difficulty=difficulty, correct=False, times=5)
        html = self.page()
        self.assertEqual(len(re.findall(r'class="scheda"', html)), app_module.REVIEW_CARDS)


class AnswersStayHiddenTest(ReviewTestCase):
    """Invariant 4 applies here exactly as it does to the fascicle."""

    def offered_cards(self, html):
        return re.findall(r'data-issue="([^"]*)"[^>]*data-number="(\d+)"', html)

    def test_only_structural_data_attributes_are_present(self):
        """As on the fascicle: a card ordinal can equal an answer by chance, so the
        guarantee comes from which attributes exist, not from scanning their values."""
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            self.log(kind, correct=False, times=5)
        names = set(re.findall(r'\b(data-[a-z-]+)=', self.page()))
        self.assertLessEqual(names, {"data-issue", "data-number", "data-index", "data-kind"})

    def test_no_answer_appears_in_a_value_attribute(self):
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            self.log(kind, correct=False, times=5)
        html = self.page()
        cards = self.offered_cards(html)
        self.assertTrue(cards, "the review page offered nothing to check")
        attributes = re.findall(r'\b(value|title|alt)="([^"]*)"', html)
        for issue_id, number in cards:
            issue = build_issue(issue_id)
            puzzle = next(p for p in issue.puzzles if p.number == int(number))
            for field_obj in puzzle.fields:
                with self.subTest(issue=issue_id, number=number, value=field_obj.value):
                    for name, content in attributes:
                        self.assertIsNone(
                            re.search(r"(?<![0-9A-Za-z/])%s(?![0-9A-Za-z/])"
                                      % re.escape(field_obj.value), content),
                            "answer %r leaked in %s" % (field_obj.value, name))

    def test_no_solution_step_appears(self):
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            self.log(kind, correct=False, times=5)
        html = self.page()
        for issue_id, number in self.offered_cards(html):
            issue = build_issue(issue_id)
            puzzle = next(p for p in issue.puzzles if p.number == int(number))
            for step in puzzle.steps:
                if len(step) < 12:
                    continue
                with self.subTest(issue=issue_id, number=number):
                    self.assertNotIn(step, html)


class VerificationStillWorksTest(ReviewTestCase):
    def test_a_reviewed_card_can_be_checked_through_the_normal_api(self):
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            self.log(kind, correct=False, times=5)
        html = self.page()
        cards = re.findall(r'data-issue="([^"]*)"[^>]*data-number="(\d+)"', html)
        self.assertTrue(cards)
        for issue_id, number in cards[:3]:
            issue = build_issue(issue_id)
            puzzle = next(p for p in issue.puzzles if p.number == int(number))
            with self.subTest(issue=issue_id, number=number):
                response = self.client.post("/api/verifica",
                                            json={"issue": issue_id, "number": int(number),
                                                  "answers": [f.value for f in puzzle.fields]})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()["correct"])

    def test_the_offered_cards_come_from_real_issues(self):
        for kind in ("catena_rsa", "coincidenzario", "segreto_spezzato"):
            self.log(kind, correct=False, times=5)
        known = set(recent_issue_ids(52))
        for issue_id, _ in re.findall(r'data-issue="([^"]*)"[^>]*data-number="(\d+)"', self.page()):
            with self.subTest(issue=issue_id):
                self.assertIn(issue_id, known)


if __name__ == "__main__":
    unittest.main()
