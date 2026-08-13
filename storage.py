"""SQLite log of every answer attempt, used to build the error report."""

import os
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "attempts.db")

BUSY_TIMEOUT_SECONDS = 5.0

_WAL_LOCK = threading.Lock()
_WAL_READY = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    issue_id TEXT NOT NULL,
    puzzle_number INTEGER NOT NULL,
    kind TEXT NOT NULL,
    difficulty INTEGER NOT NULL,
    correct INTEGER NOT NULL
);
"""


def percentage(part, whole):
    """Percentage rounded half up.

    round() rounds halves to even, so an error rate of 12.5 came out as 12 while 37.5
    came out as 38. Two identical margins must not round in opposite directions.
    """
    if not whole:
        return 0
    return (200 * part + whole) // (2 * whole)


def connect():
    directory = os.path.dirname(DB_PATH)
    if directory:  # a bare filename has no directory part, and makedirs("") raises
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=BUSY_TIMEOUT_SECONDS)
    try:
        conn.row_factory = sqlite3.Row
        _enable_wal(conn)
        conn.execute(SCHEMA)  # idempotent, and it rebuilds the table if the file is replaced
    except BaseException:
        conn.close()  # never hand back a half prepared connection, it would keep its locks
        raise
    return conn


def _enable_wal(conn):
    """Switch the file to write ahead logging, once per path.

    With the default rollback journal a page view holding a read transaction blocks the
    answer being written, and the write dies on "database is locked". Changing the journal
    mode needs an exclusive lock and reports a busy database immediately instead of waiting
    for the busy timeout, so running it on every connection is itself a source of lock
    errors when several requests arrive together.
    """
    with _WAL_LOCK:
        if DB_PATH in _WAL_READY:
            return
        conn.execute("PRAGMA journal_mode=WAL")
        _WAL_READY.add(DB_PATH)


def log_attempt(issue_id, puzzle_number, kind, difficulty, correct):
    conn = connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO attempts (issue_id, puzzle_number, kind, difficulty, correct)"
                " VALUES (?, ?, ?, ?, ?)",
                (issue_id, puzzle_number, kind, difficulty, int(correct)),
            )
    finally:
        conn.close()


def solved_numbers(issue_id):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT puzzle_number FROM attempts WHERE issue_id = ? AND correct = 1",
            (issue_id,),
        ).fetchall()
    finally:
        conn.close()
    return {row["puzzle_number"] for row in rows}


def stats_by_kind():
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT kind, difficulty, COUNT(*) AS total, SUM(correct) AS ok"
            " FROM attempts GROUP BY kind, difficulty ORDER BY kind, difficulty"
        ).fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        total, ok = row["total"], row["ok"] or 0
        out.append({
            "kind": row["kind"],
            "difficulty": row["difficulty"],
            "total": total,
            "ok": ok,
            "error_rate": percentage(total - ok, total),
        })
    return out
