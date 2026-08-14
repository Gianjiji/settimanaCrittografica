"""Hostile input must never be interpreted, neither by the browser nor by Jinja."""

import os
import sys
import tempfile
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
import storage
from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The stats page only prints what this browser logged, so the two must agree.
PLAYER = "a" * 32

HOSTILE = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '"><script>alert(1)</script>',
    "</td><td onclick=alert(1)>",
    "<b>grassetto</b>",
    "javascript:alert(1)",
    "';alert(1);//",
]

# Rendered by Jinja, it would print 49 if the value ever reached render_template_string.
TEMPLATE_INJECTION = "{{7*7}}"


class TagCollector(HTMLParser):
    """Records the markup a browser would actually build, plus the visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, tuple(sorted(name for name, _ in attrs))))

    def handle_endtag(self, tag):
        self.tags.append(("/" + tag, ()))

    def handle_data(self, data):
        self.text.append(data)


def parse(html):
    collector = TagCollector()
    collector.feed(html)
    return collector


def tag_signature(html):
    """The document structure. Escaped input contributes no tags, so this must not move."""
    return parse(html).tags


def visible_text(html):
    return "".join(parse(html).text)


class EscapingTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.real_db_path = storage.DB_PATH
        self.addCleanup(self.restore_db_path)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "attempts.db")
        self.client = app.test_client()
        self.client.set_cookie(app_module.PLAYER_COOKIE, PLAYER)
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)

    def restore_db_path(self):
        storage.DB_PATH = self.real_db_path

    def assertNoExtraMarkup(self, hostile_html, benign_html, payload, where):
        """Escaped input builds no tags, so the structure must match the benign page.

        Comparing whole pages beats scanning for fragments: every page legitimately
        contains </script> and </td>, so searching for those finds only false alarms.
        """
        self.assertEqual(tag_signature(hostile_html), tag_signature(benign_html),
                         "%r changed the markup of %s" % (payload, where))


class StoredValueEscapingTest(EscapingTestCase):
    """The statistics page prints values straight from the database."""

    def stats_page_for_kind(self, kind, tag):
        """The stats page with a single logged attempt of that kind, on a fresh database."""
        storage.DB_PATH = os.path.join(self.temp_dir.name, "kind-%s.db" % tag)
        storage.log_attempt(PLAYER, self.issue_id, 1, kind, 1, False)
        return self.client.get("/statistiche").get_data(as_text=True)

    def test_hostile_kind_builds_no_markup_on_the_stats_page(self):
        benign = self.stats_page_for_kind("famiglia", "benign")
        for index, payload in enumerate(HOSTILE):
            with self.subTest(payload=payload):
                hostile = self.stats_page_for_kind(payload, str(index))
                self.assertNoExtraMarkup(hostile, benign, payload, "the stats page")

    def test_hostile_kind_survives_as_readable_text(self):
        """Escaping must neutralise the payload, not silently drop it."""
        for index, payload in enumerate(HOSTILE):
            with self.subTest(payload=payload):
                html = self.stats_page_for_kind(payload, "text%d" % index)
                self.assertIn(payload, visible_text(html))

    def test_hostile_kind_is_still_shown_as_text(self):
        storage.log_attempt(PLAYER, self.issue_id, 1, "<b>ciao</b>", 1, False)
        html = self.client.get("/statistiche").get_data(as_text=True)
        self.assertIn("&lt;b&gt;ciao&lt;/b&gt;", html)

    def test_stored_braces_are_not_evaluated_as_a_template(self):
        storage.log_attempt(PLAYER, self.issue_id, 1, TEMPLATE_INJECTION, 1, False)
        html = self.client.get("/statistiche").get_data(as_text=True)
        self.assertNotIn("49", html)
        self.assertIn("7*7", html)


class ApiEscapingTest(EscapingTestCase):
    def test_hostile_answers_are_never_echoed(self):
        number = self.issue.puzzles[0].number
        for payload in HOSTILE + [TEMPLATE_INJECTION]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/verifica",
                                            json={"issue": self.issue_id, "number": number,
                                                  "answers": [payload]})
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertNotIn(payload, body)
                self.assertFalse(response.get_json()["correct"])

    def test_hostile_word_guess_is_never_echoed(self):
        for payload in HOSTILE + [TEMPLATE_INJECTION]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/parola",
                                            json={"issue": self.issue_id, "answer": payload})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(payload, response.get_data(as_text=True))

    def test_hostile_issue_id_is_never_echoed(self):
        for route in ("/api/verifica", "/api/parola"):
            for payload in HOSTILE:
                with self.subTest(route=route, payload=payload):
                    response = self.client.post(route, json={"issue": payload, "number": 1,
                                                             "answers": ["1"]})
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn(payload, response.get_data(as_text=True))

    def test_api_answers_are_json_not_html(self):
        response = self.client.post("/api/verifica",
                                    json={"issue": self.issue_id,
                                          "number": self.issue.puzzles[0].number,
                                          "answers": ["<b>x</b>"]})
        self.assertIn("application/json", response.headers["Content-Type"])


class UrlEscapingTest(EscapingTestCase):
    def test_hostile_issue_id_in_the_url_is_not_reflected(self):
        benign = self.client.get("/fascicolo/1970-W01").get_data(as_text=True)
        for payload in HOSTILE:
            with self.subTest(payload=payload):
                response = self.client.get("/fascicolo/" + payload)
                self.assertEqual(response.status_code, 404)
                html = response.get_data(as_text=True)
                self.assertNoExtraMarkup(html, benign, payload, "the 404 page")
                self.assertNotIn(payload, visible_text(html))

    def test_hostile_path_is_not_reflected(self):
        benign = self.client.get("/rotta-inesistente").get_data(as_text=True)
        for payload in HOSTILE:
            with self.subTest(payload=payload):
                response = self.client.get("/" + payload)
                self.assertEqual(response.status_code, 404)
                html = response.get_data(as_text=True)
                self.assertNoExtraMarkup(html, benign, payload, "the 404 page")
                self.assertNotIn(payload, visible_text(html))

    def test_hostile_query_string_is_not_reflected(self):
        response = self.client.get("/statistiche?x=%3Cscript%3Ealert(1)%3C/script%3E")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>alert(1)</script>", response.get_data(as_text=True))


class SourceLevelGuardTest(unittest.TestCase):
    """Behavioural tests cannot see a leak that no current input reaches.

    These pin the two habits that keep the app safe: templates never mark a value
    safe, and the client writes text, never markup.
    """

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
            return handle.read()

    def test_no_template_marks_a_value_safe(self):
        directory = os.path.join(ROOT, "templates")
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".html"):
                continue
            with self.subTest(template=name):
                source = self.read("templates", name)
                self.assertNotRegex(source, r"\|\s*safe")
                self.assertNotIn("{% autoescape false %}", source)

    def test_the_client_never_writes_markup(self):
        source = self.read("static", "app.js")
        for construct in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            with self.subTest(construct=construct):
                self.assertNotIn(construct, source)

    def test_jinja_autoescaping_is_on_for_html(self):
        self.assertTrue(app.jinja_env.autoescape)
        self.assertTrue(app.select_jinja_autoescape("issue.html"))


if __name__ == "__main__":
    unittest.main()
