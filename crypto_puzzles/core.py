"""Data model, modular arithmetic helpers and answer checking."""

from dataclasses import dataclass, field
from fractions import Fraction
import re

ALPHABET = "abcdefghijklmnopqrstuvwxyz"

# Mental-math guard rails. Every generator must stay inside these bounds.
ALLOWED_MODULI = (11, 13, 17, 19, 23, 26)
MAX_WORD_LENGTH = 9
MAX_IC_NUMERATOR = 30
MAX_RSA_MODULUS = 221
MAX_PUBLIC_EXPONENT = 17
MAX_PRIVATE_EXPONENT = 33


@dataclass
class Field:
    label: str
    kind: str  # number, fraction or text
    value: str
    placeholder: str = ""


@dataclass
class Puzzle:
    kind: str
    family: str
    title: str
    difficulty: int  # 1 easy, 2 medium, 3 hard
    minutes: int
    statement: str
    given: list
    fields: list
    hints: list
    steps: list
    meta_value: int
    meta_label: str = ""
    number: int = 0


def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def modinv(a, m):
    g, x, _ = egcd(a % m, m)
    if g != 1:
        raise ValueError("no modular inverse")
    return x % m


def euclid_steps(e, phi):
    """Extended Euclid written as the division table asked for at the exam."""
    rows = []
    a, b = phi, e
    while b:
        rows.append("%d = %d * %d + %d" % (a, a // b, b, a % b))
        a, b = b, a % b
    d = modinv(e, phi)
    rows.append("MCD = 1, quindi l'inverso esiste. Risalendo le sostituzioni si ottiene d = %d." % d)
    rows.append("Verifica: %d * %d = %d = 1 mod %d." % (e, d, e * d, phi))
    return d, rows


def modexp_steps(base, exp, mod):
    """Left to right square and multiply, with the trace to copy on the exam sheet."""
    bits = bin(exp)[2:]
    rows = ["Esponente %d in binario = %s." % (exp, bits)]
    result = 1
    for index, bit in enumerate(bits):
        squared = (result * result) % mod
        if index == 0:
            rows.append("Parto da 1, primo bit 1: risultato = %d." % (base % mod))
            result = base % mod
            continue
        if bit == "1":
            new = (squared * base) % mod
            rows.append("bit %s: elevo al quadrato %d^2 = %d mod %d, poi moltiplico per %d = %d mod %d."
                        % (bit, result, squared, mod, base, new, mod))
            result = new
        else:
            rows.append("bit %s: elevo al quadrato %d^2 = %d mod %d." % (bit, result, squared, mod))
            result = squared
    rows.append("Risultato: %d^%d mod %d = %d." % (base, exp, mod, result))
    return result, rows


def caesar_encrypt(text, shift):
    out = []
    for ch in text:
        if ch in ALPHABET:
            out.append(ALPHABET[(ALPHABET.index(ch) + shift) % 26])
        else:
            out.append(ch)
    return "".join(out)


def letter_counts(word):
    counts = {}
    for ch in word:
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def _clean_number(raw):
    cleaned = re.sub(r"[^0-9-]", "", raw)
    return cleaned


def _parse_fraction(raw):
    text = raw.strip().lower().replace(" ", "").replace(",", ".")
    text = re.sub(r"^[a-z]+=", "", text)
    if "/" in text:
        num, den = text.split("/", 1)
        return Fraction(int(num), int(den))
    return Fraction(text)


def check_field(field_obj, raw):
    """True when the typed answer matches, accepting the usual human variants."""
    if raw is None:
        return False
    raw = str(raw).strip()
    if not raw:
        return False
    try:
        if field_obj.kind == "number":
            cleaned = _clean_number(raw)
            return cleaned != "" and int(cleaned) == int(field_obj.value)
        if field_obj.kind == "fraction":
            given = _parse_fraction(raw)
            expected = _parse_fraction(field_obj.value)
            if given == expected:
                return True
            return abs(float(given) - float(expected)) < 0.005
        normalized = re.sub(r"[^a-z]", "", raw.lower())
        return normalized == re.sub(r"[^a-z]", "", field_obj.value.lower())
    except (ValueError, ZeroDivisionError, ArithmeticError):
        return False


def check_puzzle(puzzle, answers):
    results = [check_field(f, answers[i] if i < len(answers) else "")
               for i, f in enumerate(puzzle.fields)]
    return all(results), results
