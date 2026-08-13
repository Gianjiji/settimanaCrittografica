"""Smoke check of every public route, driven by app.test_client().

No server, no network, no shell dependency: run it with `python tools/smoke.py`.
Exits 0 when every check passes, 1 otherwise.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from crypto_puzzles.fascicle import current_issue_id  # noqa: E402

MISSING_ISSUE_ID = "1970-W01"


def checks(issue_id):
    return [
        ("home redirects to the current issue", "/", 302),
        ("current issue page", "/fascicolo/" + issue_id, 200),
        ("solutions page", "/fascicolo/" + issue_id + "/soluzioni", 200),
        ("archive page", "/archivio", 200),
        ("stats page", "/statistiche", 200),
        ("unknown issue is a 404", "/fascicolo/" + MISSING_ISSUE_ID, 404),
        ("unknown issue solutions is a 404", "/fascicolo/" + MISSING_ISSUE_ID + "/soluzioni", 404),
    ]


def main():
    issue_id = current_issue_id()
    failures = []
    with app.test_client() as client:
        for label, path, expected in checks(issue_id):
            response = client.get(path)
            if response.status_code != expected:
                failures.append(
                    "%s: GET %s returned %d, expected %d" % (label, path, response.status_code, expected)
                )
                continue
            print("ok   %-40s %s" % (label, path))

        # The home redirect must land on a page that actually renders.
        landing = client.get("/", follow_redirects=True)
        if landing.status_code != 200:
            failures.append("home after redirect returned %d, expected 200" % landing.status_code)
        else:
            print("ok   %-40s %s" % ("home after redirect", "/"))

    if failures:
        print()
        for failure in failures:
            print("FAIL " + failure)
        print("\n%d check(s) failed" % len(failures))
        return 1
    print("\nsmoke ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
