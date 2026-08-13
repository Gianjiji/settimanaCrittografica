"""Catena RSA: extended Euclid, square and multiply, factoring n from phi(n)."""

from math import gcd, isqrt

from .core import (Field, Puzzle, MAX_PRIVATE_EXPONENT, MAX_PUBLIC_EXPONENT,
                   MAX_RSA_MODULUS, euclid_steps, modexp_steps, modinv)
from .tables import PUBLIC_EXPONENTS, RSA_PRIMES

KIND = "catena_rsa"
FAMILY = "RSA"


def _keypairs():
    """All parameter sets that stay inside the mental-math bounds."""
    out = []
    for p, q in RSA_PRIMES:
        n = p * q
        if n > MAX_RSA_MODULUS:
            continue
        phi = (p - 1) * (q - 1)
        for e in PUBLIC_EXPONENTS:
            if e >= phi or gcd(e, phi) != 1:
                continue
            d = modinv(e, phi)
            if d == e or d <= 2 or d > MAX_PRIVATE_EXPONENT:
                continue
            out.append((p, q, n, phi, e, d))
    return out


def generate(rng, difficulty):
    if difficulty == 1:
        return _private_key_puzzle(rng)
    if difficulty == 2:
        return _encrypt_puzzle(rng)
    return _factoring_puzzle(rng)


def _private_key_puzzle(rng):
    p, q, n, phi, e, d = rng.choice(_keypairs())
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="La chiave privata",
        difficulty=1,
        minutes=3,
        statement="Dati il modulo e la chiave pubblica, calcola la chiave privata d con l'algoritmo "
                  "di Euclide esteso.",
        given=[("Modulo n", str(n)), ("Chiave pubblica e", str(e))],
        fields=[Field(label="d", kind="number", value=str(d), placeholder="numero intero")],
        hints=[
            "Prima fattorizza n: è il prodotto di due primi piccoli. Poi calcola phi(n) = (p-1)(q-1).",
            "n = %d * %d, quindi phi(n) = %d * %d = %d." % (p, q, p - 1, q - 1, phi),
            "Cerca d tale che %d * d = 1 mod %d. Prova i multipli di %d aumentati di 1 e dividi per %d."
            % (e, phi, phi, e),
        ],
        steps=[
            "Fattorizzo n = %d = %d * %d." % (n, p, q),
            "phi(n) = (%d-1)(%d-1) = %d." % (p, q, phi),
            "Euclide esteso su (%d, %d):" % (phi, e),
        ] + euclid_steps(e, phi)[1],
        meta_value=d,
        meta_label="la chiave privata d",
    )


def _encrypt_puzzle(rng):
    candidates = [k for k in _keypairs() if k[4] <= MAX_PUBLIC_EXPONENT]
    p, q, n, phi, e, d = rng.choice(candidates)
    m = rng.randrange(2, min(n, 40))
    while gcd(m, n) != 1:
        m = rng.randrange(2, min(n, 40))
    c, trace = modexp_steps(m, e, n)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Cifratura con esponenziazione veloce",
        difficulty=2,
        minutes=4,
        statement="Cifra il messaggio con RSA usando l'algoritmo di esponenziazione veloce "
                  "(quadrati e moltiplicazioni). Indica anche la chiave privata d.",
        given=[("Modulo n", str(n)), ("Chiave pubblica e", str(e)), ("Messaggio m", str(m))],
        fields=[
            Field(label="Ciphertext c", kind="number", value=str(c), placeholder="numero intero"),
            Field(label="Chiave privata d", kind="number", value=str(d), placeholder="numero intero"),
        ],
        hints=[
            "c = m^e mod n. Scrivi e in binario e procedi da sinistra a destra: a ogni bit elevi al "
            "quadrato, se il bit è 1 moltiplichi anche per la base.",
            "e = %d in binario è %s, quindi %d elevamenti al quadrato." % (e, bin(e)[2:], len(bin(e)) - 3),
            "Riduci modulo %d dopo ogni operazione, non alla fine." % n,
        ],
        steps=[
            "Esponenziazione veloce di %d^%d mod %d:" % (m, e, n),
        ] + trace + [
            "Per d: n = %d * %d, phi(n) = %d, e con Euclide esteso d = %d." % (p, q, phi, d),
            "Verifica rapida: %d * %d = %d, che è 1 modulo %d." % (e, d, e * d, phi),
        ],
        meta_value=c,
        meta_label="il ciphertext c",
    )


def _factoring_puzzle(rng):
    pairs = [(p, q) for p, q in RSA_PRIMES if p * q <= MAX_RSA_MODULUS and p != q]
    p, q = rng.choice(pairs)
    n = p * q
    phi = (p - 1) * (q - 1)
    total = n - phi + 1  # p + q
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Fattorizzare con l'indizio",
        difficulty=3,
        minutes=4,
        statement="Di un modulo RSA si conosce phi(n). Usa questa informazione per fattorizzare n. "
                  "Indica i due primi con p minore di q.",
        given=[("Modulo n", str(n)), ("phi(n)", str(phi))],
        fields=[
            Field(label="p", kind="number", value=str(p), placeholder="il primo più piccolo"),
            Field(label="q", kind="number", value=str(q), placeholder="il primo più grande"),
        ],
        hints=[
            "phi(n) = (p-1)(q-1) = n - (p+q) + 1. Da qui ricavi la somma dei due primi.",
            "p + q = n - phi(n) + 1 = %d. E sai già che p * q = %d." % (total, n),
            "Cerca due numeri con somma %d e prodotto %d: risolvi a mente x^2 - %dx + %d = 0."
            % (total, n, total, n),
        ],
        steps=[
            "phi(n) = (p-1)(q-1) = pq - p - q + 1 = n - (p+q) + 1.",
            "Quindi p + q = n - phi(n) + 1 = %d - %d + 1 = %d." % (n, phi, total),
            "Con somma %d e prodotto %d, i due primi sono le radici di x^2 - %dx + %d = 0."
            % (total, n, total, n),
            "Discriminante: %d^2 - 4*%d = %d, radice %d." % (total, n, total * total - 4 * n,
                                                             isqrt(total * total - 4 * n)),
            "p = %d, q = %d." % (p, q),
        ],
        meta_value=p + q,
        meta_label="la somma p + q",
    )
