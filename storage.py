"""SQLite log of every answer attempt, used to build the error report."""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "attempts.db")

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


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def log_attempt(issue_id, puzzle_number, kind, difficulty, correct):
    conn = connect()
    with conn:
        conn.execute(
            "INSERT INTO attempts (issue_id, puzzle_number, kind, difficulty, correct)"
            " VALUES (?, ?, ?, ?, ?)",
            (issue_id, puzzle_number, kind, difficulty, int(correct)),
        )
    conn.close()


def solved_numbers(issue_id):
    conn = connect()
    rows = conn.execute(
        "SELECT DISTINCT puzzle_number FROM attempts WHERE issue_id = ? AND correct = 1",
        (issue_id,),
    ).fetchall()
    conn.close()
    return {row["puzzle_number"] for row in rows}


def stats_by_kind():
    conn = connect()
    rows = conn.execute(
        "SELECT kind, difficulty, COUNT(*) AS total, SUM(correct) AS ok"
        " FROM attempts GROUP BY kind, difficulty ORDER BY kind, difficulty"
    ).fetchall()
    conn.close()
    out = []
    for row in rows:
        total, ok = row["total"], row["ok"] or 0
        out.append({
            "kind": row["kind"],
            "difficulty": row["difficulty"],
            "total": total,
            "ok": ok,
            "error_rate": round(100.0 * (total - ok) / total) if total else 0,
        })
    return out
