"""One link, several readers: each browser sees its own progress and nobody else's.

The fascicle is handed around as a URL, so the visitors of a single address are not one
person. There is no login to tell them apart, so the server hands each browser a random
id in a cookie and files every attempt under it. These tests are the guarantee that the
id is really what the pages are built from.
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


class PlayerTestCase(unittest.TestCase):
    def setUp(self):
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.puzzle = self.issue.puzzles[0]

    def browser(self):
        """A client that keeps its cookies, which is what makes it one browser."""
        return app.test_client()

    def solve(self, client, puzzle=None):
        puzzle = puzzle or self.puzzle
        response = client.post("/api/verifica",
                               json={"issue": self.issue_id, "number": puzzle.number,
                                     "answers": [f.value for f in puzzle.fields]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["correct"])
        return response

    def issue_page(self, client):
        response = client.get("/fascicolo/" + self.issue_id)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def solved_numbers_on(self, html):
        cards = re.findall(r'<article class="scheda([^"]*)"\s+id="scheda-(\d+)"', html)
        self.assertTrue(cards, "no cards found: the page markup moved")
        return {int(number) for classes, number in cards if "risolta" in classes}

    def cookie_of(self, response):
        for header in response.headers.getlist("Set-Cookie"):
            if header.startswith(app_module.PLAYER_COOKIE + "="):
                return header
        return None


class CookieTest(PlayerTestCase):
    def test_a_first_visit_is_given_an_id(self):
        self.assertIsNotNone(self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id)))

    def test_the_id_is_kept_for_the_whole_site(self):
        cookie = self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id))
        self.assertIn("Path=/", cookie)

    def test_the_id_outlives_the_session(self):
        """A cookie with no lifetime dies with the window, and so would the progress."""
        cookie = self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id))
        self.assertIn("Max-Age=", cookie)

    def test_the_id_is_not_readable_by_scripts(self):
        cookie = self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id))
        self.assertIn("HttpOnly", cookie)

    def test_a_browser_that_kept_its_cookie_is_not_given_a_new_one(self):
        client = self.browser()
        client.get("/fascicolo/" + self.issue_id)
        self.assertIsNone(self.cookie_of(client.get("/fascicolo/" + self.issue_id)))

    def test_two_browsers_are_given_different_ids(self):
        first = self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id))
        second = self.cookie_of(self.browser().get("/fascicolo/" + self.issue_id))
        self.assertNotEqual(first, second)

    def test_an_id_that_we_did_not_mint_is_replaced(self):
        """A hand written cookie must not become a way to pick a log to read."""
        for forged in ("", "ospite", "../../etc", "A" * 32, "a" * 31, "a" * 33, "' OR 1=1"):
            with self.subTest(cookie=forged):
                client = self.browser()
                client.set_cookie(app_module.PLAYER_COOKIE, forged)
                cookie = self.cookie_of(client.get("/fascicolo/" + self.issue_id))
                self.assertIsNotNone(cookie, "%r was accepted as an id" % forged)

    def test_every_page_answers_without_an_id(self):
        for path in ("/", "/fascicolo/" + self.issue_id, "/archivio", "/ripasso",
                     "/statistiche", "/sw.js", "/manifest.webmanifest", "/non-esiste"):
            with self.subTest(path=path):
                self.assertLess(self.browser().get(path).status_code, 500)


class SeparateProgressTest(PlayerTestCase):
    def test_a_card_you_solved_is_marked_for_you(self):
        client = self.browser()
        self.solve(client)
        self.assertIn(self.puzzle.number, self.solved_numbers_on(self.issue_page(client)))

    def test_a_card_you_solved_is_not_marked_for_anyone_else(self):
        self.solve(self.browser())
        self.assertEqual(self.solved_numbers_on(self.issue_page(self.browser())), set())

    def test_the_counter_is_read_per_browser(self):
        client = self.browser()
        self.solve(client)
        self.assertIn("1 di", self.issue_page(client))
        self.assertIn("0 di", self.issue_page(self.browser()))

    def test_progress_survives_a_reload(self):
        client = self.browser()
        self.solve(client)
        self.issue_page(client)
        self.assertIn(self.puzzle.number, self.solved_numbers_on(self.issue_page(client)))

    def test_two_browsers_build_two_sets_of_solved_cards(self):
        mine, yours = self.browser(), self.browser()
        self.solve(mine, self.issue.puzzles[0])
        self.solve(yours, self.issue.puzzles[1])
        self.assertEqual(self.solved_numbers_on(self.issue_page(mine)),
                         {self.issue.puzzles[0].number})
        self.assertEqual(self.solved_numbers_on(self.issue_page(yours)),
                         {self.issue.puzzles[1].number})


class SeparateStatisticsTest(PlayerTestCase):
    def wrong_answer(self, client):
        response = client.post("/api/verifica",
                               json={"issue": self.issue_id, "number": self.puzzle.number,
                                     "answers": ["999999"] * len(self.puzzle.fields)})
        self.assertEqual(response.status_code, 200)

    def stats(self, client):
        response = client.get("/statistiche")
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_your_own_mistakes_reach_your_register(self):
        client = self.browser()
        self.wrong_answer(client)
        self.assertIn(self.puzzle.kind, self.stats(client))

    def test_someone_else_mistakes_do_not(self):
        other = self.browser()
        for _ in range(4):
            self.wrong_answer(other)
        self.assertNotIn(self.puzzle.kind, self.stats(self.browser()))

    def test_a_fresh_browser_is_told_its_register_is_empty(self):
        for _ in range(4):
            self.wrong_answer(self.browser())
        self.assertIn("Nessun tentativo", self.stats(self.browser()))


class CachingTest(PlayerTestCase):
    """The same address answers differently per browser, and caches must be told."""

    def test_pages_are_marked_as_varying_by_cookie(self):
        for path in ("/fascicolo/" + self.issue_id, "/statistiche", "/ripasso", "/archivio"):
            with self.subTest(path=path):
                response = self.browser().get(path)
                fields = [field.strip().lower()
                          for field in (response.headers.get("Vary") or "").split(",")]
                self.assertIn("cookie", fields)


if __name__ == "__main__":
    unittest.main()
