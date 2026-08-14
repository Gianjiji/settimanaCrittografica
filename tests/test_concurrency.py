"""Concurrent verification must never hit a SQLite lock."""

import os
import sqlite3
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
import storage
from app import app
from crypto_puzzles.fascicle import build_issue, current_issue_id

THREADS = 12
ROUNDS = 12

# One browser, so a parallel read sees the rows the parallel writes are adding.
PLAYER = "a" * 32


class ConcurrencyTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.real_db_path = storage.DB_PATH
        self.addCleanup(self.restore_db_path)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "attempts.db")
        self.issue_id = current_issue_id()
        self.issue = build_issue(self.issue_id)
        self.numbers = [p.number for p in self.issue.puzzles]

    def restore_db_path(self):
        storage.DB_PATH = self.real_db_path

    def run_in_parallel(self, target):
        """Runs target(index) on THREADS threads and returns everything that went wrong."""
        failures = []
        lock = threading.Lock()

        def wrapped(index):
            try:
                target(index)
            except Exception as error:  # noqa: BLE001 - the test reports whatever escapes
                with lock:
                    failures.append("%s: %s" % (type(error).__name__, error))

        threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return failures

    def row_count(self):
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        finally:
            conn.close()


class ConcurrentApiTest(ConcurrencyTestCase):
    def test_parallel_verifications_never_fail(self):
        statuses = []
        lock = threading.Lock()

        def hammer(index):
            client = app.test_client()
            client.set_cookie(app_module.PLAYER_COOKIE, PLAYER)
            for step in range(ROUNDS):
                number = self.numbers[(index + step) % len(self.numbers)]
                response = client.post("/api/verifica",
                                       json={"issue": self.issue_id, "number": number,
                                             "answers": ["1"]})
                with lock:
                    statuses.append(response.status_code)

        failures = self.run_in_parallel(hammer)
        self.assertEqual(failures, [])
        self.assertEqual(set(statuses), {200})
        self.assertEqual(self.row_count(), THREADS * ROUNDS)

    def test_parallel_word_checks_never_fail(self):
        statuses = []
        lock = threading.Lock()

        def hammer(index):
            client = app.test_client()
            client.set_cookie(app_module.PLAYER_COOKIE, PLAYER)
            for _ in range(ROUNDS):
                response = client.post("/api/parola",
                                       json={"issue": self.issue_id, "answer": "qualcosa"})
                with lock:
                    statuses.append(response.status_code)

        self.assertEqual(self.run_in_parallel(hammer), [])
        self.assertEqual(set(statuses), {200})

    def test_reads_and_writes_in_parallel_never_fail(self):
        """Page views read the log while answers are being written to it."""
        statuses = []
        lock = threading.Lock()

        def mixed(index):
            client = app.test_client()
            client.set_cookie(app_module.PLAYER_COOKIE, PLAYER)
            for step in range(ROUNDS):
                number = self.numbers[(index + step) % len(self.numbers)]
                responses = [
                    client.post("/api/verifica", json={"issue": self.issue_id, "number": number,
                                                       "answers": ["1"]}),
                    client.get("/statistiche"),
                    client.get("/fascicolo/" + self.issue_id),
                ]
                with lock:
                    statuses.extend(r.status_code for r in responses)

        self.assertEqual(self.run_in_parallel(mixed), [])
        self.assertEqual(set(statuses), {200})

    def test_no_attempt_is_lost(self):
        def writer(index):
            for step in range(ROUNDS):
                storage.log_attempt(PLAYER, self.issue_id, self.numbers[step % len(self.numbers)],
                                    "catena_rsa", 2, step % 2 == 0)

        self.assertEqual(self.run_in_parallel(writer), [])
        self.assertEqual(self.row_count(), THREADS * ROUNDS)


class ConnectionHandlingTest(ConcurrencyTestCase):
    def test_an_open_reader_does_not_block_a_writer(self):
        """The rollback journal makes a reader block writers; WAL does not."""
        storage.log_attempt(PLAYER, self.issue_id, 1, "catena_rsa", 2, True)
        reader = sqlite3.connect(storage.DB_PATH, timeout=1.0)
        reader.isolation_level = None
        try:
            reader.execute("BEGIN")
            reader.execute("SELECT * FROM attempts").fetchall()
            storage.log_attempt(PLAYER, self.issue_id, 2, "catena_rsa", 2, False)
        finally:
            reader.rollback()
            reader.close()
        self.assertEqual(self.row_count(), 2)

    def test_the_database_uses_a_journal_that_allows_concurrent_readers(self):
        storage.log_attempt(PLAYER, self.issue_id, 1, "catena_rsa", 2, True)
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_connections_are_closed_when_a_query_fails(self):
        """A failed read must not leave a connection, and its locks, behind."""
        original = storage.SCHEMA
        # A schema that builds some other table, so every query below hits a missing one.
        storage.SCHEMA = "CREATE TABLE IF NOT EXISTS altra (id INTEGER PRIMARY KEY)"
        try:
            for _ in range(20):
                self.assertRaises(sqlite3.OperationalError, storage.stats_by_kind, PLAYER)
                self.assertRaises(sqlite3.OperationalError, storage.solved_numbers, PLAYER, self.issue_id)
        finally:
            storage.SCHEMA = original

        # No lock was left behind: the database still works.
        storage.log_attempt(PLAYER, self.issue_id, 1, "catena_rsa", 2, True)
        self.assertEqual(self.row_count(), 1)
        self.assertEqual(storage.solved_numbers(PLAYER, self.issue_id), {1})

    def test_connect_closes_the_connection_if_setup_fails(self):
        """A half prepared connection must not escape, or it keeps its locks.

        Checking that the database still works is not enough: CPython drops the connection
        by refcount anyway, so the test has to hold the object and prove it was closed.
        """
        created = []
        real_connect = sqlite3.connect

        def recording_connect(*args, **kwargs):
            conn = real_connect(*args, **kwargs)
            created.append(conn)
            return conn

        original = storage.SCHEMA
        sqlite3.connect = recording_connect
        storage.SCHEMA = "CREATE TABLE nonsintassi ((("
        try:
            self.assertRaises(sqlite3.OperationalError, storage.connect)
        finally:
            sqlite3.connect = real_connect
            storage.SCHEMA = original

        self.assertEqual(len(created), 1)
        self.assertRaises(sqlite3.ProgrammingError, created[0].execute, "SELECT 1")

    def test_connect_sets_a_busy_timeout(self):
        conn = storage.connect()
        try:
            timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        finally:
            conn.close()
        self.assertGreaterEqual(timeout_ms, 1000)


if __name__ == "__main__":
    unittest.main()
