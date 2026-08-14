"""The whole thing running for real: a server on a socket, browsers with cookie jars.

Everywhere else the app is driven through Flask's test client, which calls the views in
this same process and hands the cookies back by hand. That proves the views are right,
not that the parts fit: it never opens a socket, never lets a real HTTP client decide
whether a Set-Cookie is worth keeping, and never sees the database outlive the process.

So these tests start `app` on a port, talk to it with urllib over a cookie jar, and stop
and restart it underneath the same jar. What they check is the promise the project makes
to the people the link is sent to: each of them sees their own fascicle, and still sees
it tomorrow.

Only the standard library is used, as everywhere else in the project.
"""

import http.cookiejar
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crypto_puzzles.fascicle import build_issue, current_issue_id  # noqa: E402

BOOT_TIMEOUT = 30.0
REQUEST_TIMEOUT = 15.0

# Started in a subprocess so the database is a file two processes agree on, and so a
# restart is a real restart: nothing of the first run stays behind in memory.
SERVER_SOURCE = """
import sys
sys.path.insert(0, %(root)r)
import storage
storage.DB_PATH = %(db)r
from app import app
from werkzeug.serving import make_server
server = make_server("127.0.0.1", 0, app, threaded=True)
print(server.port, flush=True)
server.serve_forever()
"""


class Server:
    """The app on a port of its own, against the database it is told to use."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.process = None
        self.port = None

    def start(self):
        source = SERVER_SOURCE % {"root": ROOT, "db": self.db_path}
        self.process = subprocess.Popen(
            [sys.executable, "-c", source], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.port = self._await_port()
        return self

    def _await_port(self):
        """The port comes back on stdout, because asking for 0 means asking the kernel.

        Picking a free port here and passing it down would leave a gap between the check
        and the bind, which is exactly long enough for something else to take it.
        """
        line = self._readline_within(BOOT_TIMEOUT)
        if line is None:
            self.stop()
            raise AssertionError("the server printed no port within %gs:\n%s"
                                 % (BOOT_TIMEOUT, self._drain_errors()))
        return int(line.strip())

    def _readline_within(self, timeout):
        result = []

        def read():
            result.append(self.process.stdout.readline())

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        reader.join(timeout)
        return result[0] if result and result[0] else None

    def _drain_errors(self):
        if self.process.poll() is None:
            self.process.kill()
        return (self.process.stderr.read() or "")[-2000:]

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def restart(self):
        """Same handle, new process, new port.

        The handle has to survive so the browsers pointed at it survive too, and the
        port has to be asked for again because the old one may not be free yet. A cookie
        jar does not care: cookies are matched by host, so the reader is still the same
        reader on the other side of the restart.
        """
        self.stop()
        return self.start()

    def stop(self):
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()
        self.process = None


class Browser:
    """A cookie jar and an opener: one reader, keeping whatever the server gives it.

    Nothing here knows the cookie exists. That is the point: if the server stopped
    sending it, or sent one no browser would store, these tests would notice.
    """

    def __init__(self, server):
        self.server = server
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, path):
        with self.opener.open(self.server.url(path), timeout=REQUEST_TIMEOUT) as response:
            return response.status, response.read().decode("utf-8")

    def post_json(self, path, payload):
        request = urllib.request.Request(
            self.server.url(path), data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with self.opener.open(request, timeout=REQUEST_TIMEOUT) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def cookies(self):
        return {cookie.name: cookie for cookie in self.jar}


class IntegrationTestCase(unittest.TestCase):
    """One server per test, on a database that dies with it."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, "attempts.db")
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.server = self.boot()

    def boot(self):
        server = Server(self.db_path).start()
        self.addCleanup(server.stop)
        return server

    def browser(self):
        return Browser(self.server)

    def solve(self, browser, puzzle):
        status, body = browser.post_json(
            "/api/verifica",
            {"issue": self.issue_id, "number": puzzle.number,
             "answers": [field.value for field in puzzle.fields]})
        self.assertEqual(status, 200)
        self.assertTrue(body["correct"], "card %d rejected its own answer" % puzzle.number)

    def miss(self, browser, puzzle):
        status, body = browser.post_json(
            "/api/verifica",
            {"issue": self.issue_id, "number": puzzle.number,
             "answers": ["999999"] * len(puzzle.fields)})
        self.assertEqual(status, 200)
        self.assertFalse(body["correct"])

    def fascicle(self, browser):
        status, html = browser.get("/fascicolo/" + self.issue_id)
        self.assertEqual(status, 200)
        return html

    def solved_on(self, html):
        cards = re.findall(r'<article class="scheda([^"]*)"\s+id="scheda-(\d+)"', html)
        self.assertTrue(cards, "no cards in the page: the markup moved")
        return {int(number) for classes, number in cards if "risolta" in classes}

    def rows(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        finally:
            conn.close()


class ServerComesUpTest(IntegrationTestCase):
    def test_the_front_page_leads_to_this_week(self):
        status, html = self.browser().get("/")
        self.assertEqual(status, 200)
        self.assertIn(self.issue_id, html)

    def test_every_page_is_served(self):
        browser = self.browser()
        for path in ("/", "/fascicolo/" + self.issue_id,
                     "/fascicolo/%s/soluzioni" % self.issue_id, "/archivio",
                     "/ripasso", "/statistiche", "/static/style.css", "/static/app.js",
                     "/sw.js", "/manifest.webmanifest"):
            with self.subTest(path=path):
                self.assertEqual(browser.get(path)[0], 200)

    def test_an_unknown_fascicle_is_a_404_page_and_not_a_crash(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.browser().get("/fascicolo/1970-W01")
        self.assertEqual(caught.exception.code, 404)

    def test_the_database_is_created_where_the_server_was_told(self):
        self.solve(self.browser(), self.issue.puzzles[0])
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(self.rows(), 1)


class RealBrowserIdentityTest(IntegrationTestCase):
    def test_a_real_client_keeps_the_cookie_it_is_given(self):
        browser = self.browser()
        self.assertEqual(browser.cookies(), {})
        self.fascicle(browser)
        self.assertIn("giocatore", browser.cookies())

    def test_the_cookie_is_one_a_browser_would_store_past_today(self):
        browser = self.browser()
        self.fascicle(browser)
        cookie = browser.cookies()["giocatore"]
        self.assertIsNotNone(cookie.expires, "a session cookie would lose the history")
        self.assertGreater(cookie.expires, time.time() + 60 * 60 * 24 * 30)
        self.assertEqual(cookie.path, "/")

    def test_the_id_does_not_change_while_the_reader_reads(self):
        browser = self.browser()
        self.fascicle(browser)
        first = browser.cookies()["giocatore"].value
        for path in ("/statistiche", "/ripasso", "/archivio", "/fascicolo/" + self.issue_id):
            browser.get(path)
        self.assertEqual(browser.cookies()["giocatore"].value, first)

    def test_two_clients_are_never_given_the_same_id(self):
        ids = set()
        for _ in range(6):
            browser = self.browser()
            self.fascicle(browser)
            ids.add(browser.cookies()["giocatore"].value)
        self.assertEqual(len(ids), 6)


class SharedLinkTest(IntegrationTestCase):
    """The scene the whole change is for: one address, several readers."""

    def test_a_reader_sees_the_cards_they_solved(self):
        browser = self.browser()
        self.solve(browser, self.issue.puzzles[0])
        self.assertEqual(self.solved_on(self.fascicle(browser)),
                         {self.issue.puzzles[0].number})

    def test_a_reader_does_not_see_the_cards_someone_else_solved(self):
        mine = self.browser()
        self.solve(mine, self.issue.puzzles[0])
        self.assertEqual(self.solved_on(self.fascicle(self.browser())), set())

    def test_three_readers_keep_three_fascicles(self):
        wanted = []
        browsers = []
        for index in range(3):
            browser = self.browser()
            puzzles = self.issue.puzzles[index * 2:index * 2 + 2]
            for puzzle in puzzles:
                self.solve(browser, puzzle)
            browsers.append(browser)
            wanted.append({puzzle.number for puzzle in puzzles})
        for browser, expected in zip(browsers, wanted):
            with self.subTest(expected=sorted(expected)):
                self.assertEqual(self.solved_on(self.fascicle(browser)), expected)

    def test_the_counter_belongs_to_the_reader(self):
        mine = self.browser()
        for puzzle in self.issue.puzzles[:3]:
            self.solve(mine, puzzle)
        self.assertIn("3 di", self.fascicle(mine))
        self.assertIn("0 di", self.fascicle(self.browser()))

    def test_the_error_register_belongs_to_the_reader(self):
        mine = self.browser()
        for _ in range(4):
            self.miss(mine, self.issue.puzzles[0])
        self.assertIn(self.issue.puzzles[0].kind, mine.get("/statistiche")[1])
        theirs = self.browser().get("/statistiche")[1]
        self.assertNotIn(self.issue.puzzles[0].kind, theirs)
        self.assertIn("Nessun tentativo", theirs)

    def test_the_review_page_belongs_to_the_reader(self):
        mine = self.browser()
        for _ in range(5):
            self.miss(mine, self.issue.puzzles[0])
        self.assertIn('data-kind="', mine.get("/ripasso")[1])
        self.assertNotIn('data-kind="', self.browser().get("/ripasso")[1])

    def test_every_attempt_of_every_reader_is_kept(self):
        for _ in range(3):
            browser = self.browser()
            for puzzle in self.issue.puzzles[:2]:
                self.solve(browser, puzzle)
        self.assertEqual(self.rows(), 6)

    def test_the_weekly_word_lands_in_the_register_of_whoever_missed_it(self):
        """The word never marks the page from the server, but it does reach the log."""
        mine = self.browser()
        for _ in range(4):
            status, body = mine.post_json("/api/parola",
                                          {"issue": self.issue_id, "answer": "sbagliata"})
            self.assertEqual(status, 200)
            self.assertFalse(body["correct"])
        self.assertIn("parola_settimana", mine.get("/statistiche")[1])
        self.assertNotIn("parola_settimana", self.browser().get("/statistiche")[1])

    def test_the_right_word_is_accepted_from_any_reader(self):
        for _ in range(2):
            status, body = self.browser().post_json(
                "/api/parola", {"issue": self.issue_id, "answer": self.issue.meta.word})
            self.assertEqual(status, 200)
            self.assertTrue(body["correct"])


class AcrossRestartTest(IntegrationTestCase):
    """The reader closes the laptop, the server is redeployed, the week goes on."""

    def restart(self):
        self.server.restart()

    def test_progress_survives_the_server_going_away(self):
        browser = self.browser()
        self.solve(browser, self.issue.puzzles[0])
        self.solve(browser, self.issue.puzzles[1])
        self.restart()
        self.assertEqual(self.solved_on(self.fascicle(browser)),
                         {self.issue.puzzles[0].number, self.issue.puzzles[1].number})

    def test_the_reader_is_not_handed_a_new_identity_on_the_way_back(self):
        browser = self.browser()
        self.fascicle(browser)
        before = browser.cookies()["giocatore"].value
        self.restart()
        self.fascicle(browser)
        self.assertEqual(browser.cookies()["giocatore"].value, before)

    def test_a_restart_does_not_make_one_history_out_of_the_others(self):
        mine, yours = self.browser(), self.browser()
        self.solve(mine, self.issue.puzzles[0])
        self.solve(yours, self.issue.puzzles[1])
        self.restart()
        self.assertEqual(self.solved_on(self.fascicle(mine)), {self.issue.puzzles[0].number})
        self.assertEqual(self.solved_on(self.fascicle(yours)), {self.issue.puzzles[1].number})

    def test_a_reader_who_cleared_the_cookies_starts_over(self):
        """Stated plainly because it is the deal: nothing is asked, nothing is recovered."""
        browser = self.browser()
        self.solve(browser, self.issue.puzzles[0])
        browser.jar.clear()
        self.assertEqual(self.solved_on(self.fascicle(browser)), set())
        self.assertEqual(self.rows(), 1, "the old attempt was thrown away, not just hidden")


class OlderDatabaseTest(IntegrationTestCase):
    """A file written before the ids existed must be picked up by a running server."""

    OLD_SCHEMA = """
    CREATE TABLE attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        issue_id TEXT NOT NULL,
        puzzle_number INTEGER NOT NULL,
        kind TEXT NOT NULL,
        difficulty INTEGER NOT NULL,
        correct INTEGER NOT NULL
    );
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, "attempts.db")
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.write_old_log()
        self.server = self.boot()

    def write_old_log(self):
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(self.OLD_SCHEMA)
                for number in (1, 2, 3):
                    conn.execute(
                        "INSERT INTO attempts (issue_id, puzzle_number, kind, difficulty,"
                        " correct) VALUES (?, ?, 'catena_rsa', 2, 1)", (self.issue_id, number))
        finally:
            conn.close()

    def test_the_server_serves_the_old_file_without_being_migrated_by_hand(self):
        self.assertEqual(self.browser().get("/statistiche")[0], 200)

    def test_the_old_rows_are_still_there(self):
        self.fascicle(self.browser())
        self.assertEqual(self.rows(), 3)

    def test_the_old_rows_are_shown_to_nobody(self):
        self.assertEqual(self.solved_on(self.fascicle(self.browser())), set())
        self.assertIn("Nessun tentativo", self.browser().get("/statistiche")[1])

    def test_the_column_is_added_once_and_stays(self):
        self.fascicle(self.browser())
        conn = sqlite3.connect(self.db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(attempts)")]
        finally:
            conn.close()
        self.assertEqual(columns.count("player_id"), 1)

    def test_new_attempts_are_filed_under_their_reader(self):
        browser = self.browser()
        self.solve(browser, self.issue.puzzles[0])
        self.assertEqual(self.solved_on(self.fascicle(browser)),
                         {self.issue.puzzles[0].number})
        self.assertEqual(self.rows(), 4)


class ManyReadersAtOnceTest(IntegrationTestCase):
    """Answers and page views crossing on real connections, not in one process."""

    READERS = 8
    ROUNDS = 4

    def test_nothing_breaks_when_readers_overlap(self):
        failures = []
        lock = threading.Lock()
        solved = {}

        def reader(index):
            try:
                browser = self.browser()
                mine = set()
                for step in range(self.ROUNDS):
                    puzzle = self.issue.puzzles[(index + step) % len(self.issue.puzzles)]
                    self.solve(browser, puzzle)
                    mine.add(puzzle.number)
                    self.assertEqual(browser.get("/statistiche")[0], 200)
                with lock:
                    solved[index] = (self.solved_on(self.fascicle(browser)), mine)
            except Exception as error:  # noqa: BLE001 - the test reports whatever escapes
                with lock:
                    failures.append("reader %d: %s: %s" % (index, type(error).__name__, error))

        threads = [threading.Thread(target=reader, args=(i,)) for i in range(self.READERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(failures, [])
        self.assertEqual(len(solved), self.READERS)
        for index, (seen, mine) in solved.items():
            with self.subTest(reader=index):
                self.assertEqual(seen, mine, "reader %d saw a fascicle that is not theirs" % index)


if __name__ == "__main__":
    unittest.main()
