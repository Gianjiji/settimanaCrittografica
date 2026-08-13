"""The verification API must survive any malformed payload without a 500."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage
from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

_TEMP_DIR = None
_REAL_DB_PATH = None


def setUpModule():
    """Log attempts to a throwaway database, never to the player's own log."""
    global _TEMP_DIR, _REAL_DB_PATH
    _TEMP_DIR = tempfile.TemporaryDirectory()
    _REAL_DB_PATH = storage.DB_PATH
    storage.DB_PATH = os.path.join(_TEMP_DIR.name, "attempts.db")


def tearDownModule():
    storage.DB_PATH = _REAL_DB_PATH
    _TEMP_DIR.cleanup()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.puzzle = self.issue.puzzles[0]

    def post_json(self, route, payload):
        return self.client.post(route, json=payload)

    def post_raw(self, route, body):
        return self.client.post(route, data=body, content_type="application/json")

    def assertNotServerError(self, response, label):
        self.assertNotEqual(response.status_code, 500, "%s produced a 500" % label)
        self.assertLess(response.status_code, 500, "%s produced %d" % (label, response.status_code))


NON_OBJECT_BODIES = [
    ("json array", "[1, 2]"),
    ("json string", '"ciao"'),
    ("json number", "42"),
    ("json null", "null"),
    ("json true", "true"),
    ("broken json", "{non json"),
    ("empty body", ""),
]

NON_STRING_ISSUES = [
    ("number", 123),
    ("list", []),
    ("dict", {}),
    ("bool", True),
    ("null", None),
    ("nested list", [["2026-W33"]]),
]


class MalformedBodyTest(ApiTestCase):
    def test_non_object_bodies_never_500(self):
        for route in ("/api/verifica", "/api/parola"):
            for label, body in NON_OBJECT_BODIES:
                with self.subTest(route=route, body=label):
                    response = self.post_raw(route, body)
                    self.assertNotServerError(response, "%s with %s" % (route, label))
                    self.assertEqual(response.status_code, 404)

    def test_missing_content_type_never_500(self):
        for route in ("/api/verifica", "/api/parola"):
            with self.subTest(route=route):
                self.assertNotServerError(self.client.post(route), route + " with no body")

    def test_form_encoded_body_never_500(self):
        for route in ("/api/verifica", "/api/parola"):
            with self.subTest(route=route):
                response = self.client.post(route, data={"issue": "x", "number": "1"})
                self.assertNotServerError(response, route + " with form body")


class MalformedIssueTest(ApiTestCase):
    def test_non_string_issue_never_500(self):
        for route in ("/api/verifica", "/api/parola"):
            for label, value in NON_STRING_ISSUES:
                with self.subTest(route=route, issue=label):
                    response = self.post_json(route, {"issue": value, "number": 1, "answers": ["1"]})
                    self.assertNotServerError(response, "%s with issue %s" % (route, label))
                    self.assertEqual(response.status_code, 404)

    def test_unknown_issue_string_is_404(self):
        for route in ("/api/verifica", "/api/parola"):
            with self.subTest(route=route):
                response = self.post_json(route, {"issue": "1970-W01", "number": 1, "answers": ["1"]})
                self.assertEqual(response.status_code, 404)
                self.assertIn("error", response.get_json())

    def test_missing_issue_key_is_404(self):
        for route in ("/api/verifica", "/api/parola"):
            with self.subTest(route=route):
                self.assertEqual(self.post_json(route, {"number": 1}).status_code, 404)


class MalformedNumberTest(ApiTestCase):
    def test_unusable_number_is_400(self):
        for label, value in (("string", "abc"), ("null", None), ("list", [1]),
                             ("dict", {}), ("float string", "1.5")):
            with self.subTest(number=label):
                response = self.post_json("/api/verifica",
                                          {"issue": self.issue_id, "number": value, "answers": ["1"]})
                self.assertNotServerError(response, "number %s" % label)
                self.assertEqual(response.status_code, 400)

    def test_unknown_card_number_is_404(self):
        for value in (0, 999, -1):
            with self.subTest(number=value):
                response = self.post_json("/api/verifica",
                                          {"issue": self.issue_id, "number": value, "answers": ["1"]})
                self.assertEqual(response.status_code, 404)

    def test_numeric_string_number_is_accepted(self):
        response = self.post_json("/api/verifica",
                                  {"issue": self.issue_id, "number": str(self.puzzle.number),
                                   "answers": ["1"]})
        self.assertEqual(response.status_code, 200)


class MalformedAnswersTest(ApiTestCase):
    def test_non_list_answers_never_500(self):
        for label, value in (("number", 5), ("dict", {"0": "1"}), ("string", "abc"),
                             ("bool", True), ("null", None), ("nested", [[1]])):
            with self.subTest(answers=label):
                response = self.post_json("/api/verifica",
                                          {"issue": self.issue_id, "number": self.puzzle.number,
                                           "answers": value})
                self.assertNotServerError(response, "answers %s" % label)
                self.assertEqual(response.status_code, 200)

    def test_answers_shorter_than_fields_is_200_and_not_correct(self):
        response = self.post_json("/api/verifica",
                                  {"issue": self.issue_id, "number": self.puzzle.number,
                                   "answers": []})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["correct"])
        self.assertEqual(len(body["fields"]), len(self.puzzle.fields))

    def test_answers_longer_than_fields_is_ignored(self):
        response = self.post_json("/api/verifica",
                                  {"issue": self.issue_id, "number": self.puzzle.number,
                                   "answers": ["1"] * 500})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["fields"]), len(self.puzzle.fields))

    def test_answers_with_odd_element_types_never_500(self):
        for label, value in (("null", [None]), ("list", [[1]]), ("dict", [{"a": 1}]),
                             ("number", [7]), ("bool", [True])):
            with self.subTest(element=label):
                response = self.post_json("/api/verifica",
                                          {"issue": self.issue_id, "number": self.puzzle.number,
                                           "answers": value})
                self.assertNotServerError(response, "answer element %s" % label)


class WordApiTest(ApiTestCase):
    def test_odd_answer_types_never_500(self):
        for label, value in (("missing", "__absent__"), ("null", None), ("number", 5),
                             ("list", [1]), ("dict", {"a": 1}), ("bool", True)):
            with self.subTest(answer=label):
                payload = {"issue": self.issue_id}
                if value != "__absent__":
                    payload["answer"] = value
                response = self.post_json("/api/parola", payload)
                self.assertNotServerError(response, "answer %s" % label)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.get_json()["correct"])

    def test_correct_word_is_accepted_in_any_case_and_spacing(self):
        for variant in (self.issue.meta.word.lower(), self.issue.meta.word.upper(),
                        " " + self.issue.meta.word.title() + " "):
            with self.subTest(variant=variant):
                response = self.post_json("/api/parola", {"issue": self.issue_id, "answer": variant})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()["correct"])


class HappyPathTest(ApiTestCase):
    """Hardening must not break the normal flow."""

    def test_right_answers_are_accepted_for_every_card(self):
        for puzzle in self.issue.puzzles:
            with self.subTest(number=puzzle.number):
                response = self.post_json("/api/verifica",
                                          {"issue": self.issue_id, "number": puzzle.number,
                                           "answers": [f.value for f in puzzle.fields]})
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                self.assertTrue(body["correct"], "card %d rejected its own answer" % puzzle.number)
                self.assertTrue(all(body["fields"]))

    def test_wrong_answers_are_rejected_per_field(self):
        puzzle = self.puzzle
        response = self.post_json("/api/verifica",
                                  {"issue": self.issue_id, "number": puzzle.number,
                                   "answers": ["999999"] * len(puzzle.fields)})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["correct"])
        self.assertFalse(any(body["fields"]))


if __name__ == "__main__":
    unittest.main()
