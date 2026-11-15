"""The request budget: a reader never meets it, a loop runs dry at once.

Two layers. The bucket itself is tested against a clock the test moves by hand, so no
test sleeps and none depends on how fast the machine is. Then the API is tested with a
small bucket swapped in, to see that a refusal is a 429, costs no row in the log, and
is charged to the address that asked and to no other.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
import storage
from app import app
from crypto_puzzles.fascicle import current_issue_id
from ratelimit import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class BucketTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.limiter = RateLimiter(burst=3, per_second=0.5, clock=self.clock)

    def test_the_burst_is_allowed_and_then_no_more(self):
        self.assertEqual([self.limiter.allow("a") for _ in range(5)],
                         [True, True, True, False, False])

    def test_tokens_come_back_at_the_stated_rate(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.clock.advance(1.9)  # 0.95 of a token: not yet one
        self.assertFalse(self.limiter.allow("a"))
        self.clock.advance(0.2)
        self.assertTrue(self.limiter.allow("a"))
        self.assertFalse(self.limiter.allow("a"))

    def test_waiting_never_buys_more_than_the_burst(self):
        self.limiter.allow("a")
        self.clock.advance(3600)
        self.assertEqual([self.limiter.allow("a") for _ in range(4)],
                         [True, True, True, False])

    def test_each_address_has_its_own_bucket(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.assertFalse(self.limiter.allow("a"))
        self.assertTrue(self.limiter.allow("b"))

    def test_retry_after_says_when_the_next_token_arrives(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.assertEqual(self.limiter.retry_after("a"), 2)  # one token at 0.5/s
        self.clock.advance(1.5)
        self.assertEqual(self.limiter.retry_after("a"), 1)
        self.assertEqual(self.limiter.retry_after("never seen"), 1)

    def test_a_clock_that_steps_back_does_not_mint_tokens(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.clock.advance(-50)
        self.assertFalse(self.limiter.allow("a"))

    def test_nonsense_settings_are_refused(self):
        for burst, rate in ((0, 1), (3, 0), (3, -1)):
            with self.subTest(burst=burst, rate=rate):
                with self.assertRaises(ValueError):
                    RateLimiter(burst=burst, per_second=rate)


class BoundedTableTest(unittest.TestCase):
    """A flood of addresses must not be able to grow the table without end."""

    def test_idle_buckets_are_forgotten_first(self):
        clock = FakeClock()
        limiter = RateLimiter(burst=2, per_second=1.0, clock=clock, max_clients=4)
        for key in "abcd":
            limiter.allow(key)
        clock.advance(10)  # all four have refilled: nothing is lost by dropping them
        limiter.allow("e")
        self.assertEqual(set(limiter._buckets), {"e"})

    def test_a_full_table_of_busy_buckets_still_makes_room(self):
        clock = FakeClock()
        limiter = RateLimiter(burst=2, per_second=0.001, clock=clock, max_clients=4)
        for key in "abcd":
            limiter.allow(key)
            clock.advance(1)
        self.assertTrue(limiter.allow("e"))
        self.assertLessEqual(len(limiter._buckets), 4)
        self.assertIn("e", limiter._buckets)
        self.assertNotIn("a", limiter._buckets, "the oldest bucket should have gone first")


class ApiBudgetTest(unittest.TestCase):
    BURST = 3

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.real_db, storage.DB_PATH = storage.DB_PATH, os.path.join(self.temp.name, "a.db")
        self.addCleanup(setattr, storage, "DB_PATH", self.real_db)

        self.clock = FakeClock()
        self.real_budget = app_module.api_budget
        app_module.api_budget = RateLimiter(self.BURST, 1.0, clock=self.clock)
        self.addCleanup(setattr, app_module, "api_budget", self.real_budget)

        self.was_enabled = app.config["RATE_LIMIT_ENABLED"]
        app.config["RATE_LIMIT_ENABLED"] = True
        self.addCleanup(app.config.__setitem__, "RATE_LIMIT_ENABLED", self.was_enabled)

        self.client = app.test_client()
        self.issue_id = current_issue_id()

    def post(self, route="/api/parola", address="203.0.113.7"):
        return self.client.post(route, json={"issue": self.issue_id, "answer": "x",
                                             "number": 1, "answers": ["1"]},
                                environ_overrides={"REMOTE_ADDR": address})

    def rows(self):
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        finally:
            conn.close()

    def test_requests_beyond_the_burst_are_429(self):
        statuses = [self.post().status_code for _ in range(self.BURST + 2)]
        self.assertEqual(statuses, [200] * self.BURST + [429, 429])

    def test_the_refusal_says_when_to_come_back(self):
        for _ in range(self.BURST):
            self.post()
        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "1")
        self.assertIn("error", response.get_json())

    def test_a_refused_request_writes_nothing(self):
        """The whole point: past the budget the log stops growing."""
        for _ in range(self.BURST + 10):
            self.post()
        self.assertEqual(self.rows(), self.BURST)

    def test_both_post_routes_draw_on_the_same_budget(self):
        for _ in range(self.BURST):
            self.assertEqual(self.post("/api/verifica").status_code, 200)
        self.assertEqual(self.post("/api/parola").status_code, 429)

    def test_another_address_is_not_charged(self):
        for _ in range(self.BURST + 1):
            self.post(address="203.0.113.7")
        self.assertEqual(self.post(address="203.0.113.8").status_code, 200)

    def test_the_budget_comes_back_with_time(self):
        for _ in range(self.BURST + 1):
            self.post()
        self.clock.advance(1.0)
        self.assertEqual(self.post().status_code, 200)

    def test_reading_pages_is_never_rationed(self):
        for _ in range(self.BURST + 1):
            self.post()
        for route in ("/fascicolo/%s" % self.issue_id, "/archivio", "/statistiche"):
            with self.subTest(route=route):
                response = self.client.get(route, environ_overrides={"REMOTE_ADDR": "203.0.113.7"})
                self.assertEqual(response.status_code, 200)

    def test_it_can_be_switched_off(self):
        app.config["RATE_LIMIT_ENABLED"] = False
        statuses = {self.post().status_code for _ in range(self.BURST + 5)}
        self.assertEqual(statuses, {200})

    def test_the_shipped_budget_is_on_and_within_reason(self):
        """A default that is off, or generous without limit, protects nothing."""
        self.assertIsInstance(self.real_budget, RateLimiter)
        self.assertLessEqual(self.real_budget.burst, 100)
        self.assertLessEqual(self.real_budget.per_second, 5)
        self.assertGreaterEqual(self.real_budget.burst, 20, "nine cards and their retries")


if __name__ == "__main__":
    unittest.main()
