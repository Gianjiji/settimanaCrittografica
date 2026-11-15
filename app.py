"""La Settimana Crittografica: a weekly fascicle of mental cryptography puzzles."""

import os
import re
import secrets

from flask import (Flask, abort, g, jsonify, redirect, render_template, request,
                  send_from_directory, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

import storage
from crypto_puzzles.core import check_puzzle
from crypto_puzzles.fascicle import SECTIONS, build_issue, current_issue_id, recent_issue_ids
from crypto_puzzles.tables import INVERSE_TABLES
from ratelimit import RateLimiter

app = Flask(__name__)

# How many proxies sit in front, when there are any (a tunnel is one). Without this the
# only address the app ever sees is the proxy's own: every reader would share a single
# request budget, and a page served over https would look like plain http. Left at zero
# the forwarding headers are ignored, because a client reaching the app directly could
# write whatever it wanted in them.
PROXY_HOPS_VARIABLE = "SETTIMANA_PROXY_HOPS"


def _proxy_hops(environ):
    try:
        return max(0, int(environ.get(PROXY_HOPS_VARIABLE, "0")))
    except ValueError:
        return 0


_HOPS = _proxy_hops(os.environ)
if _HOPS:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_HOPS, x_proto=_HOPS)

# A reader sends one answer every few seconds at most; forty in a row and then one a
# second is far more than a fascicle of nine cards asks for, and far less than a loop.
RATE_LIMIT_BURST = 40
RATE_LIMIT_PER_SECOND = 1.0
app.config.setdefault("RATE_LIMIT_ENABLED", True)
api_budget = RateLimiter(RATE_LIMIT_BURST, RATE_LIMIT_PER_SECOND)

PLAYER_COOKIE = "giocatore"
PLAYER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # two years, longer than any run of issues
PLAYER_ID_PATTERN = re.compile(r"\A[0-9a-f]{32}\Z")


@app.before_request
def assign_player():
    """Tell one browser from another, with no account to open and no name to give.

    The fascicle is shared as a link, so several readers arrive at the same address and
    each expects to see their own progress. The id below names nobody: it is a random
    number the browser keeps in a cookie and hands back on every request, which is all
    it takes to keep two logs apart. Clearing the cookie starts an empty history, which
    is the price of asking for nothing.

    A cookie that does not have the shape of a minted id is thrown away rather than
    filed under, so a hand written value cannot become a log of its own; and 128 random
    bits is far too much room to stumble into somebody else's by trying.
    """
    cookie = request.cookies.get(PLAYER_COOKIE, "")
    known = bool(PLAYER_ID_PATTERN.match(cookie))
    g.player_id = cookie if known else secrets.token_hex(16)
    g.player_is_new = not known


@app.after_request
def remember_player(response):
    if g.get("player_is_new"):
        # Secure only when the request itself came over https: on plain http, which is
        # how the fascicle is reached on a home network, a Secure cookie would never be
        # sent back and every page view would start a new history.
        response.set_cookie(PLAYER_COOKIE, g.player_id, max_age=PLAYER_COOKIE_MAX_AGE,
                            path="/", httponly=True, samesite="Lax",
                            secure=request.is_secure)
    if response.mimetype == "text/html":
        # One address now answers differently per browser. Without this a cache in the
        # middle, or the reader's own, could hand one player the page built for another.
        # Added to the set rather than assigned: a tunnel or proxy in front may already
        # have made the page vary by Accept-Encoding, and overwriting that would let a
        # cache answer a client with a body it cannot read.
        response.vary.add("Cookie")
    return response


@app.before_request
def spend_request_budget():
    """Refuse an address that posts faster than any reader could.

    Only the POST routes write to the log, so only they are counted: reading pages
    costs nothing that needs rationing. The refusal is a 429 with a Retry-After, which
    the page reports as "not checked" rather than as a wrong answer.
    """
    if request.method != "POST" or not app.config["RATE_LIMIT_ENABLED"]:
        return None
    address = request.remote_addr or ""
    if api_budget.allow(address):
        return None
    response = jsonify({"error": "troppe richieste, riprova fra poco"})
    response.status_code = 429
    response.headers["Retry-After"] = str(api_budget.retry_after(address))
    return response


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


def _card_number(value):
    """The card number as an int, or None when the client sent something else.

    int() alone is too willing: it reads true as card 1, cuts 1.9 down to 1, and raises
    OverflowError, not ValueError, for the Infinity and 1e999 that the JSON parser
    accepts as numbers. A whole number, or a string that spells one, is all a card
    number can be.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None  # also inf and nan, which are no integers either
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


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
                           solved=storage.solved_numbers(g.player_id, issue_id),
                           inverse_tables=INVERSE_TABLES, current=current_issue_id())


@app.route("/fascicolo/<issue_id>/soluzioni")
def solutions_page(issue_id):
    issue = _issue_or_404(issue_id)
    return render_template("solutions.html", issue=issue, sections=_sections(issue),
                           current=current_issue_id())


@app.route("/fascicolo/<issue_id>/stampa")
def export_page(issue_id):
    """The fascicle as one self-contained file, for printing or keeping.

    A PDF would need a library, and the dependency rule forbids one, so the styles are
    inlined instead: the file prints from anywhere with nothing left to fetch.
    """
    issue = _issue_or_404(issue_id)
    document = render_template("export.html", issue=issue, sections=_sections(issue))
    response = app.make_response(document)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = (
        'attachment; filename="fascicolo-%s.html"' % issue.issue_id)
    return response


@app.route("/archivio")
def archive_page():
    issues = [build_issue(i) for i in recent_issue_ids(12)]
    return render_template("archive.html", issues=[i for i in issues if i],
                           current=current_issue_id())


MIN_ATTEMPTS_TO_JUDGE = 3
REVIEW_CARDS = 6
REVIEW_HISTORY = 12


def weak_families(player_id):
    """The (kind, difficulty) pairs this reader most often gets wrong, worst first.

    The pair, not just the kind: RSA at difficulty 3 can be a weakness while the same
    family at difficulty 1 is not. A pair also needs a few attempts before its error
    rate means anything, since one unlucky answer is not a weakness.
    """
    rows = [r for r in storage.stats_by_kind(player_id)
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
    return render_template("review.html", cards=review_cards(weak_families(g.player_id)),
                           current=current_issue_id())


@app.route("/statistiche")
def stats_page():
    return render_template("stats.html", rows=storage.stats_by_kind(g.player_id),
                           current=current_issue_id())


@app.post("/api/verifica")
def verify():
    payload = _payload()
    issue = _issue_from(payload)
    if issue is None:
        return jsonify({"error": "fascicolo inesistente"}), 404
    number = _card_number(payload.get("number", 0))
    if number is None:
        return jsonify({"error": "scheda non valida"}), 400
    puzzle = next((p for p in issue.puzzles if p.number == number), None)
    if puzzle is None:
        return jsonify({"error": "scheda non valida"}), 404
    answers = payload.get("answers")
    if not isinstance(answers, list):
        answers = []
    correct, per_field = check_puzzle(puzzle, answers)
    storage.log_attempt(g.player_id, issue.issue_id, puzzle.number, puzzle.kind,
                        puzzle.difficulty, correct)
    return jsonify({"correct": correct, "fields": per_field})


@app.post("/api/parola")
def verify_word():
    payload = _payload()
    issue = _issue_from(payload)
    if issue is None:
        return jsonify({"error": "fascicolo inesistente"}), 404
    guess = re.sub(r"[^a-z]", "", str(payload.get("answer", "")).lower())
    correct = guess == issue.meta.word.lower()
    storage.log_attempt(g.player_id, issue.issue_id, 0, "parola_settimana", 3, correct)
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


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def server_settings(environ):
    """Where to listen and whether to debug, as (host, port, debug).

    The defaults are the safe ones: this machine only, debugger off. Listening on the
    whole network is a choice (SETTIMANA_HOST=0.0.0.0), and so is the debugger
    (SETTIMANA_DEBUG=1), but never both together: the debugger hands a Python console
    to whoever can load an error page, so it is refused on any address another machine
    can reach.
    """
    host = environ.get("SETTIMANA_HOST", "127.0.0.1").strip() or "127.0.0.1"
    raw_port = environ.get("SETTIMANA_PORT", "5000")
    try:
        port = int(raw_port)
    except ValueError:
        raise SystemExit("SETTIMANA_PORT deve essere un numero di porta, non %r" % raw_port)
    if not 0 <= port <= 65535:
        raise SystemExit("SETTIMANA_PORT fuori intervallo: %d" % port)
    debug = environ.get("SETTIMANA_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
    if debug and host not in LOOPBACK_HOSTS:
        raise SystemExit(
            "SETTIMANA_DEBUG=1 e SETTIMANA_HOST=%s non possono stare insieme: il debugger "
            "espone una console Python a chiunque raggiunga la pagina di errore. "
            "Usa il debug solo su 127.0.0.1." % host)
    return host, port, debug


if __name__ == "__main__":
    _host, _port, _debug = server_settings(os.environ)
    app.run(host=_host, port=_port, debug=_debug)
