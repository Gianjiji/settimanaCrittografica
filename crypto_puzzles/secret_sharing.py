"""Segreto spezzato: (n,n) additive scheme and (k,n) Shamir reconstruction."""

from .core import Field, Puzzle, modinv
from .tables import INVERSE_TABLES, SHARING_MODULI

KIND = "segreto_spezzato"
FAMILY = "Secret sharing"


def generate(rng, difficulty):
    if difficulty == 1:
        return _additive_puzzle(rng)
    if difficulty == 2:
        return _shamir_consecutive(rng)
    return _shamir_gapped(rng)


def _additive_puzzle(rng):
    p = rng.choice(SHARING_MODULI)
    n = rng.choice([3, 4, 5])
    shares = [rng.randrange(0, p) for _ in range(n)]
    secret = sum(shares) % p
    listed = ", ".join("P%d = %d" % (i + 1, s) for i, s in enumerate(shares))
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Schema (%d,%d), ricostruzione" % (n, n),
        difficulty=1,
        minutes=2,
        statement="In uno schema (%d,%d) su Z%d, tutti i partecipanti mettono insieme le loro share. "
                  "Qual è il segreto?" % (n, n, p),
        given=[("Campo", "Z%d" % p), ("Share", listed)],
        fields=[Field(label="Segreto s", kind="number", value=str(secret),
                      placeholder="resto in Z%d" % p)],
        hints=[
            "Nello schema (n,n) il segreto è la somma delle share nel campo.",
            "Somma i valori: %s." % " + ".join(str(s) for s in shares),
            "Ricordati di ridurre modulo %d alla fine." % p,
        ],
        steps=[
            "Somma delle share: %s = %d." % (" + ".join(str(s) for s in shares), sum(shares)),
            "Riduzione: %d mod %d = %d." % (sum(shares), p, secret),
            "Nota da esame: le prime %d share sono casuali, l'ultima è costruita come s meno la somma "
            "delle altre. Nessun sottoinsieme proprio ottiene informazione sul segreto." % (n - 1),
        ],
        meta_value=secret,
        meta_label="il segreto s",
    )


def _shamir_consecutive(rng):
    p = rng.choice(SHARING_MODULI)
    secret = rng.randrange(1, p)
    a1 = rng.randrange(1, p)
    y1 = (secret + a1) % p
    y2 = (secret + 2 * a1) % p
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Schema (2,3), due share",
        difficulty=2,
        minutes=3,
        statement="Uno schema di Shamir (2,3) su Z%d distribuisce le share con il polinomio "
                  "f(x) = s + a1 x. Ricostruisci il segreto dalle due share disponibili." % p,
        given=[("Campo", "Z%d" % p), ("Share", "P1 = %d, P2 = %d" % (y1, y2))],
        fields=[Field(label="Segreto s", kind="number", value=str(secret),
                      placeholder="resto in Z%d" % p)],
        hints=[
            "Le share sono i valori del polinomio in x = 1 e x = 2. Il segreto è f(0).",
            "Con x = 1 e x = 2 la formula di Lagrange si riduce a s = 2*y1 - y2 mod %d." % p,
            "Calcola 2 * %d - %d e riduci modulo %d." % (y1, y2, p),
        ],
        steps=[
            "f(1) = s + a1 = %d e f(2) = s + 2a1 = %d." % (y1, y2),
            "Sottraendo: a1 = %d - %d = %d mod %d." % (y2, y1, (y2 - y1) % p, p),
            "s = f(1) - a1 = %d - %d = %d mod %d." % (y1, (y2 - y1) % p, secret, p),
            "Scorciatoia con Lagrange: s = 2*y1 - y2 = 2*%d - %d = %d mod %d."
            % (y1, y2, secret, p),
        ],
        meta_value=secret,
        meta_label="il segreto s",
    )


def _shamir_gapped(rng):
    p = rng.choice(SHARING_MODULI)
    secret = rng.randrange(1, p)
    a1 = rng.randrange(1, p)
    x1, x2 = rng.choice([(1, 3), (1, 4), (1, 5), (2, 4), (2, 5), (3, 5)])
    y1 = (secret + a1 * x1) % p
    y2 = (secret + a1 * x2) % p
    delta = (x2 - x1) % p
    inv = modinv(delta, p)
    table = ", ".join("%d con %d" % (k, v) for k, v in sorted(INVERSE_TABLES[p].items()) if k <= 6)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Schema (2,n), share non consecutive",
        difficulty=3,
        minutes=5,
        statement="Uno schema di Shamir (2,n) su Z%d usa il polinomio f(x) = s + a1 x. Ricostruisci "
                  "il segreto dalle due share, che stavolta non sono consecutive." % p,
        given=[("Campo", "Z%d" % p),
               ("Share", "f(%d) = %d, f(%d) = %d" % (x1, y1, x2, y2))],
        fields=[Field(label="Segreto s", kind="number", value=str(secret),
                      placeholder="resto in Z%d" % p)],
        hints=[
            "Il segreto è f(0). Con due punti passi per la retta e la valuti in zero.",
            "Coefficiente angolare: a1 = (y2 - y1) * inverso di (x2 - x1) modulo %d." % p,
            "Ti serve l'inverso di %d in Z%d: dalla tabella è %d." % (delta, p, inv),
        ],
        steps=[
            "Differenza fra le ascisse: %d - %d = %d, il suo inverso in Z%d è %d."
            % (x2, x1, delta, p, inv),
            "a1 = (%d - %d) * %d = %d mod %d." % (y2, y1, inv, a1, p),
            "s = y1 - a1 * x1 = %d - %d * %d = %d mod %d." % (y1, a1, x1, secret, p),
            "Tabella degli inversi in Z%d, da sapere a memoria: %s." % (p, table),
        ],
        meta_value=secret,
        meta_label="il segreto s",
    )
