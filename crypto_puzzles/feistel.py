"""Rete di Feistel a due round su otto bit, con funzione di round elementare.

The round function is purely bitwise, XOR followed by a rotation of the four bits. No
modular arithmetic is involved, so the mental-math rule on allowed moduli is untouched:
working mod 16 would have introduced a modulus that invariant 1 does not list.

Not registered in GENERATORS, for the reason recorded in the Bloccato section of
PROGRESS.md.
"""

from .core import Field, Puzzle

KIND = "rete_feistel"
FAMILY = "Rete di Feistel"

HALF_BITS = 4


def bits(value):
    return format(value, "04b")


def rotate_left(value):
    """One position left, on four bits."""
    return ((value << 1) & 0b1111) | (value >> (HALF_BITS - 1))


def round_function(half, key):
    """F(x, k): exclusive or with the key, then rotate the four bits by one."""
    return rotate_left(half ^ key)


def feistel_round(left, right, key):
    return right, left ^ round_function(right, key)


def unfeistel_round(left, right, key):
    """The same F undoes the round: that is the point of the construction."""
    return right ^ round_function(left, key), left


def generate(rng, difficulty):
    if difficulty == 1:
        return _one_round(rng)
    if difficulty == 2:
        return _two_rounds(rng)
    return _decrypt(rng)


def _halves(rng):
    return rng.randrange(0, 16), rng.randrange(0, 16)


def _f_steps(half, key):
    mixed = half ^ key
    return ("%s xor %s = %s, ruotato di uno a sinistra = %s"
            % (bits(half), bits(key), bits(mixed), bits(rotate_left(mixed))))


def _one_round(rng):
    left, right = _halves(rng)
    key = rng.randrange(1, 16)
    new_left, new_right = feistel_round(left, right, key)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Un round di Feistel",
        difficulty=1,
        minutes=3,
        statement="Un blocco di otto bit si divide in due meta' da quattro. Un round di "
                  "Feistel produce L1 = R0 e R1 = L0 xor F(R0, k), dove F fa lo xor con la "
                  "chiave e poi ruota i quattro bit di una posizione a sinistra. Calcola il "
                  "blocco dopo un round.",
        given=[("Meta' sinistra L0", bits(left)),
               ("Meta' destra R0", bits(right)),
               ("Chiave k", bits(key))],
        fields=[
            Field(label="L1", kind="text", value=bits(new_left), placeholder="quattro bit"),
            Field(label="R1", kind="text", value=bits(new_right), placeholder="quattro bit"),
        ],
        hints=[
            "La meta' sinistra nuova e' semplicemente la vecchia meta' destra: L1 = R0.",
            "Per R1 calcola prima F(R0, k), poi fai lo xor con L0.",
            "F(R0, k): %s." % _f_steps(right, key),
        ],
        steps=[
            "L1 = R0 = %s." % bits(new_left),
            "F(R0, k): %s." % _f_steps(right, key),
            "R1 = L0 xor F(R0, k) = %s xor %s = %s."
            % (bits(left), bits(round_function(right, key)), bits(new_right)),
            "Nota da esame: la meta' destra entra in F, la sinistra viene solo mescolata "
            "con lo xor. Nessuna delle due operazioni perde informazione.",
        ],
        meta_value=new_right,
        meta_label="il valore di R1 in decimale",
    )


def _two_rounds(rng):
    left, right = _halves(rng)
    k1 = rng.randrange(1, 16)
    k2 = rng.randrange(1, 16)
    l1, r1 = feistel_round(left, right, k1)
    l2, r2 = feistel_round(l1, r1, k2)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Due round di Feistel",
        difficulty=2,
        minutes=4,
        statement="Stessa rete di Feistel su otto bit, con F che fa lo xor con la chiave di "
                  "round e poi ruota i quattro bit di una posizione a sinistra. Applica due "
                  "round, con chiavi diverse, e dai il blocco finale.",
        given=[("Meta' sinistra L0", bits(left)),
               ("Meta' destra R0", bits(right)),
               ("Chiave del primo round", bits(k1)),
               ("Chiave del secondo round", bits(k2))],
        fields=[
            Field(label="L2", kind="text", value=bits(l2), placeholder="quattro bit"),
            Field(label="R2", kind="text", value=bits(r2), placeholder="quattro bit"),
        ],
        hints=[
            "Fai un round alla volta, e scrivi il risultato intermedio prima di continuare.",
            "Dopo il primo round hai L1 = R0 e R1 = L0 xor F(R0, k1). Quelli entrano nel "
            "secondo round al posto di L0 e R0.",
            "Primo round, F(R0, k1): %s." % _f_steps(right, k1),
        ],
        steps=[
            "Primo round. F(R0, k1): %s." % _f_steps(right, k1),
            "L1 = %s, R1 = %s xor %s = %s."
            % (bits(l1), bits(left), bits(round_function(right, k1)), bits(r1)),
            "Secondo round. F(R1, k2): %s." % _f_steps(r1, k2),
            "L2 = %s, R2 = %s xor %s = %s."
            % (bits(l2), bits(l1), bits(round_function(r1, k2)), bits(r2)),
            "Nota da esame: le chiavi di round si usano in ordine, e in decifratura si "
            "useranno nell'ordine opposto.",
        ],
        meta_value=r2,
        meta_label="il valore di R2 in decimale",
    )


def _decrypt(rng):
    left, right = _halves(rng)
    k1 = rng.randrange(1, 16)
    k2 = rng.randrange(1, 16)
    l1, r1 = feistel_round(left, right, k1)
    l2, r2 = feistel_round(l1, r1, k2)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Decifrare due round",
        difficulty=3,
        minutes=5,
        statement="Di un blocco cifrato con due round di Feistel si conoscono il risultato e "
                  "le due chiavi. Torna indietro e ritrova il blocco di partenza. F fa lo xor "
                  "con la chiave e poi ruota i quattro bit di una posizione a sinistra.",
        given=[("Meta' sinistra L2", bits(l2)),
               ("Meta' destra R2", bits(r2)),
               ("Chiave del primo round", bits(k1)),
               ("Chiave del secondo round", bits(k2))],
        fields=[
            Field(label="L0", kind="text", value=bits(left), placeholder="quattro bit"),
            Field(label="R0", kind="text", value=bits(right), placeholder="quattro bit"),
        ],
        hints=[
            "Non serve invertire F: la struttura di Feistel si decifra con la stessa F, "
            "percorrendo i round al contrario.",
            "Un round si annulla cosi': R = L2 xor F(R2, k), e L = R2. Parti dal secondo "
            "round, quindi usa prima k2.",
            "Passo indietro sul secondo round, F(L2, k2): %s." % _f_steps(l2, k2),
        ],
        steps=[
            "Indietro sul secondo round, con k2. Ricordo che L2 = R1, quindi R1 = %s."
            % bits(r1),
            "F(R1, k2): %s." % _f_steps(r1, k2),
            "L1 = R2 xor F(R1, k2) = %s xor %s = %s."
            % (bits(r2), bits(round_function(r1, k2)), bits(l1)),
            "Indietro sul primo round, con k1. R0 = L1 = %s." % bits(right),
            "F(R0, k1): %s. L0 = R1 xor F(R0, k1) = %s xor %s = %s."
            % (_f_steps(right, k1), bits(r1), bits(round_function(right, k1)), bits(left)),
            "Nota da esame: e' il motivo per cui una rete di Feistel non chiede che F sia "
            "invertibile. Qualunque F va bene, e cifratura e decifratura usano lo stesso "
            "circuito con le chiavi in ordine inverso.",
        ],
        meta_value=right,
        meta_label="il valore di R0 in decimale",
    )
