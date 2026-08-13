"""Builds the weekly issue: nine puzzles plus the closing word."""

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
import random
import re

from . import coincidence, rsa_chain, secret_sharing
from .core import caesar_encrypt
from .tables import META_WORDS

GENERATORS = [coincidence, rsa_chain, secret_sharing]

SECTIONS = [
    (1, "Riscaldamento", "Tre schede da chiudere in meno di due minuti l'una."),
    (2, "Il corpo del fascicolo", "Qui si guadagnano i punti all'esame."),
    (3, "Pagina dei tosti", "Le versioni che fanno perdere tempo agli impreparati."),
]

MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre"]

ISSUE_PATTERN = re.compile(r"^(\d{4})-W(\d{1,2})$")


@dataclass
class MetaPuzzle:
    ciphertext: str
    word: str
    shift: int
    steps: list


@dataclass
class Issue:
    issue_id: str
    year: int
    week: int
    date_range: str
    puzzles: list
    meta: MetaPuzzle


def issue_id_for(day):
    year, week, _ = day.isocalendar()
    return "%d-W%02d" % (year, week)


def current_issue_id():
    return issue_id_for(date.today())


def parse_issue_id(issue_id):
    match = ISSUE_PATTERN.match(issue_id or "")
    if not match:
        return None
    year, week = int(match.group(1)), int(match.group(2))
    if year < 2020 or year > 2100 or week < 1 or week > 53:
        return None
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError:
        return None
    return year, week


def _date_range(year, week):
    start = date.fromisocalendar(year, week, 1)
    end = start + timedelta(days=6)
    if start.month == end.month:
        return "dal %d al %d %s %d" % (start.day, end.day, MONTHS[end.month - 1], end.year)
    if start.year == end.year:
        return "dal %d %s al %d %s %d" % (start.day, MONTHS[start.month - 1], end.day,
                                          MONTHS[end.month - 1], end.year)
    return "dal %d %s %d al %d %s %d" % (start.day, MONTHS[start.month - 1], start.year,
                                         end.day, MONTHS[end.month - 1], end.year)


def _build_puzzles(seed):
    rng = random.Random(seed)
    puzzles = []
    number = 1
    for difficulty, _, _ in SECTIONS:
        order = list(GENERATORS)
        rng.shuffle(order)
        for module in order:
            puzzle = module.generate(rng, difficulty)
            puzzle.number = number
            puzzles.append(puzzle)
            number += 1
    return puzzles


@lru_cache(maxsize=64)
def build_issue(issue_id):
    parsed = parse_issue_id(issue_id)
    if parsed is None:
        return None
    year, week = parsed
    base_seed = year * 100 + week

    # The closing shift must not be zero, otherwise the final word is in clear.
    for salt in range(50):
        puzzles = _build_puzzles(base_seed * 1000 + salt)
        shift = sum(p.meta_value for p in puzzles) % 26
        if shift:
            break

    rng = random.Random(base_seed)
    word = rng.choice(META_WORDS)
    meta = MetaPuzzle(
        ciphertext=caesar_encrypt(word, shift).upper(),
        word=word.upper(),
        shift=shift,
        steps=[
            "Somma delle nove risposte numeriche (per IC e MIC vale il numeratore): %s = %d."
            % (" + ".join(str(p.meta_value) for p in puzzles),
               sum(p.meta_value for p in puzzles)),
            "Chiave di Cesare: %d mod 26 = %d." % (sum(p.meta_value for p in puzzles), shift),
            "Decifrando si ottiene %s." % word.upper(),
        ],
    )
    return Issue(issue_id=issue_id, year=year, week=week, date_range=_date_range(year, week),
                 puzzles=puzzles, meta=meta)


def recent_issue_ids(count=8, today=None):
    day = today or date.today()
    ids = []
    for step in range(count):
        ids.append(issue_id_for(day - timedelta(days=7 * step)))
    return ids
