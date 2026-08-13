"""La Settimana Crittografica: a weekly fascicle of mental cryptography puzzles."""

import re

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for

import storage
from crypto_puzzles.core import check_puzzle
from crypto_puzzles.fascicle import (GENERATORS, SECTIONS, build_issue, current_issue_id,
                                     recent_issue_ids)
from crypto_puzzles.tables import INVERSE_TABLES

app = Flask(__name__)


def _issue_or_404(issue_id):
    issue = build_issue(issue_id)
    if issue is None:
        abort(404)
    return issue


def _payload():
    """The request body as a dict. A body that is not a JSON object counts as empty."""
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _issue_from(payload):
    """The requested issue, or None when the client sent something that is not an id."""
    issue_id = payload.get("issue", "")
    if not isinstance(issue_id, str):
        return None
    return build_issue(issue_id)


def _sections(issue):
    grouped = []
    for difficulty, name, blurb in SECTIONS:
        items = [p for p in issue.puzzles if p.difficulty == difficulty]
        grouped.append({"name": name, "blurb": blurb, "difficulty": difficulty, "puzzles": items})
    return grouped


@app.route("/")
def home():
    return redirect(url_for("issue_page", issue_id=current_issue_id()))


@app.route("/fascicolo/<issue_id>")
def issue_page(issue_id):
    issue = _issue_or_404(issue_id)
    return render_template("issue.html", issue=issue, sections=_sections(issue),
                           solved=storage.solved_numbers(issue_id),
                           inverse_tables=INVERSE_TABLES, current=current_issue_id())


@app.route("/fascicolo/<issue_id>/soluzioni")
def solutions_page(issue_id):
    issue = _issue_or_404(issue_id)
    return render_template("solutions.html", issue=issue, sections=_sections(issue),
                           current=current_issue_id())


@app.route("/archivio")
def archive_page():
    issues = [build_issue(i) for i in recent_issue_ids(12)]
    return render_template("archive.html", issues=[i for i in issues if i],
                           current=current_issue_id())


MIN_ATTEMPTS_TO_JUDGE = 3
REVIEW_CARDS = 6
REVIEW_HISTORY = 12


def weak_families():
    """The (kind, difficulty) pairs most often got wrong, worst first.

    The pair, not just the kind: RSA at difficulty 3 can be a weakness while the same
    family at difficulty 1 is not. A pair also needs a few attempts before its error
    rate means anything, since one unlucky answer is not a weakness.
    """
    rows = [r for r in storage.stats_by_kind()
            if r["total"] >= MIN_ATTEMPTS_TO_JUDGE and r["error_rate"] > 0]
    rows.sort(key=lambda r: (-r["error_rate"], -r["total"], r["kind"], r["difficulty"]))
    return [(r["kind"], r["difficulty"]) for r in rows]


def review_cards(families):
    """Real cards from recent issues, in the order the families were ranked."""
    issues = [i for i in (build_issue(x) for x in recent_issue_ids(REVIEW_HISTORY)) if i]
    picked = []
    for kind, difficulty in families:
        for issue in issues:
            match = next((p for p in issue.puzzles
                          if p.kind == kind and p.difficulty == difficulty), None)
            if match is not None:
                picked.append({"issue": issue, "puzzle": match})
                break
        # A family from a retired generator matches nothing above, and drops out here.
        if len(picked) == REVIEW_CARDS:
            return picked
    return picked


@app.route("/ripasso")
def review_page():
    return render_template("review.html", cards=review_cards(weak_families()),
                           current=current_issue_id())


@app.route("/statistiche")
def stats_page():
    return render_template("stats.html", rows=storage.stats_by_kind(), current=current_issue_id())


@app.post("/api/verifica")
def verify():
    payload = _payload()
    issue = _issue_from(payload)
    if issue is None:
        return jsonify({"error": "fascicolo inesistente"}), 404
    try:
        number = int(payload.get("number", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "scheda non valida"}), 400
    puzzle = next((p for p in issue.puzzles if p.number == number), None)
    if puzzle is None:
        return jsonify({"error": "scheda non valida"}), 404
    answers = payload.get("answers")
    if not isinstance(answers, list):
        answers = []
    correct, per_field = check_puzzle(puzzle, answers)
    storage.log_attempt(issue.issue_id, puzzle.number, puzzle.kind, puzzle.difficulty, correct)
    return jsonify({"correct": correct, "fields": per_field})


@app.post("/api/parola")
def verify_word():
    payload = _payload()
    issue = _issue_from(payload)
    if issue is None:
        return jsonify({"error": "fascicolo inesistente"}), 404
    guess = re.sub(r"[^a-z]", "", str(payload.get("answer", "")).lower())
    correct = guess == issue.meta.word.lower()
    storage.log_attempt(issue.issue_id, 0, "parola_settimana", 3, correct)
    return jsonify({"correct": correct})


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(app.static_folder, "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest")


@app.errorhandler(404)
def not_found(_error):
    return render_template("missing.html", current=current_issue_id()), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
