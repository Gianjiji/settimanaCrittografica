"""Coincidenzario: index of coincidence, mutual index of coincidence, Kasiski."""

from fractions import Fraction
from math import gcd

from .core import Field, Puzzle, MAX_IC_NUMERATOR, MAX_WORD_LENGTH, letter_counts
from .tables import IC_WORDS

KIND = "coincidenzario"
FAMILY = "Vigenère, crittanalisi"


def ic_fraction(word):
    counts = letter_counts(word)
    numerator = sum(f * (f - 1) for f in counts.values())
    n = len(word)
    return numerator, n * (n - 1)


def mic_fraction(word_a, word_b):
    ca, cb = letter_counts(word_a), letter_counts(word_b)
    numerator = sum(ca[ch] * cb.get(ch, 0) for ch in ca)
    return numerator, len(word_a) * len(word_b)


def _valid_ic(word):
    numerator, _ = ic_fraction(word)
    return 0 < numerator <= MAX_IC_NUMERATOR and 4 < len(word) <= MAX_WORD_LENGTH


def generate(rng, difficulty):
    pool = [w for w in IC_WORDS if _valid_ic(w)]
    if difficulty == 1:
        return _ic_puzzle(rng, pool)
    if difficulty == 2:
        return _mic_puzzle(rng, pool)
    return _kasiski_puzzle(rng)


def _ic_puzzle(rng, pool):
    word = rng.choice([w for w in pool if len(w) <= 7])
    numerator, denominator = ic_fraction(word)
    value = Fraction(numerator, denominator)
    counts = letter_counts(word)
    repeated = ", ".join("%s compare %d volte" % (ch.upper(), f)
                         for ch, f in sorted(counts.items()) if f > 1)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Indice di coincidenza",
        difficulty=1,
        minutes=1,
        statement="Calcola l'indice di coincidenza IC della parola. Rispondi con una frazione, "
                  "ridotta o no.",
        given=[("Parola", word.upper())],
        fields=[Field(label="IC", kind="fraction", value=str(value), placeholder="frazione, es. n/d")],
        hints=[
            "IC = somma di f(f-1) su tutte le lettere, diviso n(n-1), con n lunghezza della parola.",
            "Solo le lettere ripetute contribuiscono al numeratore: %s." % repeated,
            "Numeratore %d, denominatore %d." % (numerator, denominator),
        ],
        steps=[
            "Conteggio lettere: " + ", ".join("%s=%d" % (c.upper(), f)
                                              for c, f in sorted(counts.items())) + ".",
            "Numeratore: somma di f(f-1) = %d." % numerator,
            "Denominatore: n(n-1) = %d * %d = %d." % (len(word), len(word) - 1, denominator),
            "IC = %d/%d = %s, circa %.3f." % (numerator, denominator, value, float(value)),
        ],
        meta_value=numerator,
        meta_label="il numeratore di IC",
    )


def _mic_puzzle(rng, pool):
    while True:
        a, b = rng.sample(pool, 2)
        numerator, denominator = mic_fraction(a, b)
        if 0 < numerator <= MAX_IC_NUMERATOR and len(a) <= 8 and len(b) <= 8:
            break
    value = Fraction(numerator, denominator)
    ca, cb = letter_counts(a), letter_counts(b)
    shared = ", ".join("%s (%d per %d)" % (ch.upper(), ca[ch], cb[ch])
                       for ch in sorted(ca) if ch in cb)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Indice di mutua coincidenza",
        difficulty=2,
        minutes=3,
        statement="Calcola l'indice di mutua coincidenza MIC delle due parole. Rispondi con una "
                  "frazione, ridotta o no.",
        given=[("Prima parola", a.upper()), ("Seconda parola", b.upper())],
        fields=[Field(label="MIC", kind="fraction", value=str(value), placeholder="frazione, es. n/d")],
        hints=[
            "MIC = somma sui 26 caratteri di f(x) per f(y), diviso n(x) per n(y).",
            "Contano solo le lettere presenti in entrambe le parole: %s." % shared,
            "Numeratore %d, denominatore %d per %d." % (numerator, len(a), len(b)),
        ],
        steps=[
            "Lettere comuni e prodotti delle frequenze: %s." % shared,
            "Numeratore: %d." % numerator,
            "Denominatore: %d * %d = %d." % (len(a), len(b), denominator),
            "MIC = %d/%d = %s, circa %.3f." % (numerator, denominator, value, float(value)),
        ],
        meta_value=numerator,
        meta_label="il numeratore di MIC",
    )


def _kasiski_puzzle(rng):
    period = rng.choice([4, 5, 6, 7, 8, 9, 11, 12])
    while True:
        m1, m2 = rng.sample([2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 2)
        if gcd(m1, m2) == 1:
            break
    first = rng.choice([8, 11, 14, 17, 21])
    second = first + period * min(m1, m2)
    third = second + period * max(m1, m2)
    d1, d2 = second - first, third - second
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Kasiski, periodo della chiave",
        difficulty=3,
        minutes=3,
        statement="In un testo cifrato con Vigenère la stessa sequenza di dodici lettere compare tre "
                  "volte, alle posizioni indicate. Qual è la lunghezza di chiave più lunga compatibile "
                  "con queste ripetizioni?",
        given=[("Occorrenze", "posizioni %d, %d, %d" % (first, second, third))],
        fields=[Field(label="Lunghezza della chiave", kind="number", value=str(period),
                      placeholder="numero intero")],
        hints=[
            "Kasiski: la lunghezza della chiave divide la distanza fra due occorrenze della stessa "
            "sequenza.",
            "Le distanze sono %d e %d. Servono i divisori comuni." % (d1, d2),
            "La risposta è il massimo comun divisore fra %d e %d." % (d1, d2),
        ],
        steps=[
            "Distanze: %d - %d = %d e %d - %d = %d." % (second, first, d1, third, second, d2),
            "La chiave divide entrambe, quindi divide MCD(%d, %d) = %d." % (d1, d2, period),
            "Lunghezza massima compatibile: %d. All'esame aggiungi sempre che le ripetizioni possono "
            "essere casuali e che il periodo va confermato con l'indice di coincidenza sui "
            "sottotesti." % period,
        ],
        meta_value=period,
        meta_label="la lunghezza della chiave",
    )
