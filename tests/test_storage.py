"""The attempt log: database creation, counting, and the error percentages."""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage


class StorageTestCase(unittest.TestCase):
    """Every test gets its own database, so nothing touches the player's own log."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.real_db_path = storage.DB_PATH
        self.addCleanup(self.restore_db_path)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "attempts.db")

    def restore_db_path(self):
        storage.DB_PATH = self.real_db_path

    def log(self, issue_id="2026-W33", number=1, kind="catena_rsa", difficulty=2, correct=True):
        storage.log_attempt(issue_id, number, kind, difficulty, correct)

    def row_count(self):
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        finally:
            conn.close()


class DatabaseCreationTest(StorageTestCase):
    def test_database_is_created_on_first_write(self):
        self.assertFalse(os.path.exists(storage.DB_PATH))
        self.log()
        self.assertTrue(os.path.exists(storage.DB_PATH))

    def test_database_is_created_on_first_read(self):
        self.assertFalse(os.path.exists(storage.DB_PATH))
        self.assertEqual(storage.stats_by_kind(), [])
        self.assertTrue(os.path.exists(storage.DB_PATH))

    def test_missing_parent_directories_are_created(self):
        storage.DB_PATH = os.path.join(self.temp_dir.name, "uno", "due", "attempts.db")
        self.log()
        self.assertTrue(os.path.exists(storage.DB_PATH))

    def test_bare_filename_without_a_directory_works(self):
        """os.path.dirname of a bare filename is empty, and makedirs('') raises."""
        previous_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        self.addCleanup(os.chdir, previous_cwd)
        storage.DB_PATH = "attempts.db"
        self.log()
        self.assertEqual(self.row_count(), 1)

    def test_schema_has_the_expected_columns(self):
        self.log()
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(attempts)")}
        finally:
            conn.close()
        self.assertEqual(columns, {"id", "created_at", "issue_id", "puzzle_number",
                                   "kind", "difficulty", "correct"})

    def test_reconnecting_keeps_existing_rows(self):
        self.log()
        self.log()
        self.assertEqual(self.row_count(), 2)
        self.assertEqual(len(storage.stats_by_kind()), 1)
        self.assertEqual(self.row_count(), 2)


class LogAttemptTest(StorageTestCase):
    def test_every_attempt_is_recorded(self):
        for _ in range(5):
            self.log()
        self.assertEqual(self.row_count(), 5)

    def test_stored_values_round_trip(self):
        self.log(issue_id="2026-W10", number=7, kind="coincidenzario", difficulty=3, correct=False)
        conn = sqlite3.connect(storage.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM attempts").fetchone()
        finally:
            conn.close()
        self.assertEqual(row["issue_id"], "2026-W10")
        self.assertEqual(row["puzzle_number"], 7)
        self.assertEqual(row["kind"], "coincidenzario")
        self.assertEqual(row["difficulty"], 3)
        self.assertEqual(row["correct"], 0)
        self.assertIsNotNone(row["created_at"])

    def test_correct_flag_is_stored_as_zero_or_one(self):
        self.log(correct=True)
        self.log(correct=False)
        conn = sqlite3.connect(storage.DB_PATH)
        try:
            values = sorted(row[0] for row in conn.execute("SELECT correct FROM attempts"))
        finally:
            conn.close()
        self.assertEqual(values, [0, 1])


class SolvedNumbersTest(StorageTestCase):
    def test_empty_database_has_nothing_solved(self):
        self.assertEqual(storage.solved_numbers("2026-W33"), set())

    def test_only_correct_attempts_count_as_solved(self):
        self.log(number=1, correct=True)
        self.log(number=2, correct=False)
        self.assertEqual(storage.solved_numbers("2026-W33"), {1})

    def test_a_wrong_attempt_does_not_unsolve_a_card(self):
        self.log(number=1, correct=True)
        self.log(number=1, correct=False)
        self.assertEqual(storage.solved_numbers("2026-W33"), {1})

    def test_repeated_solutions_are_reported_once(self):
        for _ in range(4):
            self.log(number=3, correct=True)
        self.assertEqual(storage.solved_numbers("2026-W33"), {3})

    def test_solutions_are_scoped_to_their_issue(self):
        self.log(issue_id="2026-W33", number=1, correct=True)
        self.log(issue_id="2026-W32", number=5, correct=True)
        self.assertEqual(storage.solved_numbers("2026-W33"), {1})
        self.assertEqual(storage.solved_numbers("2026-W32"), {5})
        self.assertEqual(storage.solved_numbers("2026-W31"), set())

    def test_the_weekly_word_is_recorded_as_card_zero(self):
        self.log(number=0, kind="parola_settimana", difficulty=3, correct=True)
        self.assertEqual(storage.solved_numbers("2026-W33"), {0})


class StatsByKindTest(StorageTestCase):
    def test_empty_database_returns_no_rows(self):
        self.assertEqual(storage.stats_by_kind(), [])

    def test_attempts_are_grouped_by_kind_and_difficulty(self):
        self.log(kind="catena_rsa", difficulty=1)
        self.log(kind="catena_rsa", difficulty=1)
        self.log(kind="catena_rsa", difficulty=2)
        self.log(kind="coincidenzario", difficulty=1)
        rows = storage.stats_by_kind()
        self.assertEqual([(r["kind"], r["difficulty"], r["total"]) for r in rows],
                         [("catena_rsa", 1, 2), ("catena_rsa", 2, 1), ("coincidenzario", 1, 1)])

    def test_totals_and_successes_are_counted(self):
        for _ in range(3):
            self.log(correct=True)
        for _ in range(2):
            self.log(correct=False)
        row = storage.stats_by_kind()[0]
        self.assertEqual(row["total"], 5)
        self.assertEqual(row["ok"], 3)

    def test_error_rate_of_a_perfect_record_is_zero(self):
        self.log(correct=True)
        self.assertEqual(storage.stats_by_kind()[0]["error_rate"], 0)

    def test_error_rate_of_a_hopeless_record_is_one_hundred(self):
        self.log(correct=False)
        self.assertEqual(storage.stats_by_kind()[0]["error_rate"], 100)

    def test_error_rate_is_a_percentage_of_the_total(self):
        for _ in range(3):
            self.log(correct=True)
        self.log(correct=False)
        self.assertEqual(storage.stats_by_kind()[0]["error_rate"], 25)

    def test_halves_always_round_up(self):
        """round() halves to even, so 12.5 became 12 while 37.5 became 38."""
        for errors, total, expected in ((1, 8, 13), (3, 8, 38), (1, 40, 3), (5, 8, 63)):
            with self.subTest(errors=errors, total=total):
                self.setUp()
                for _ in range(total - errors):
                    self.log(correct=True)
                for _ in range(errors):
                    self.log(correct=False)
                self.assertEqual(storage.stats_by_kind()[0]["error_rate"], expected,
                                 "%d errors out of %d" % (errors, total))

    def test_error_rate_stays_within_bounds(self):
        for errors in range(8):
            with self.subTest(errors=errors):
                self.setUp()
                for _ in range(7 - errors):
                    self.log(correct=True)
                for _ in range(errors):
                    self.log(correct=False)
                rate = storage.stats_by_kind()[0]["error_rate"]
                self.assertGreaterEqual(rate, 0)
                self.assertLessEqual(rate, 100)

    def test_kinds_are_kept_separate(self):
        self.log(kind="catena_rsa", correct=False)
        self.log(kind="coincidenzario", correct=True)
        rates = {r["kind"]: r["error_rate"] for r in storage.stats_by_kind()}
        self.assertEqual(rates, {"catena_rsa": 100, "coincidenzario": 0})


if __name__ == "__main__":
    unittest.main()
