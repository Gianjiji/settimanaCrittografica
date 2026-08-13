"""Cifrario di Hill due per due: matrix validity, encryption, and the inverse key.

Not registered in GENERATORS, for the reason recorded in the Bloccato section of
PROGRESS.md.
"""

from .core import ALPHABET, Field, Puzzle, modinv
from .tables import INVERSE_TABLES

KIND = "cifrario_hill"
FAMILY = "Cifrario di Hill"

MODULUS = 26
# Small entries only: the whole point is that the arithmetic stays doable in the head.
ENTRY_RANGE = range(0, 12)


def determinant(matrix):
    (a, b), (c, d) = matrix
    return (a * d - b * c) % MODULUS


def is_usable(matrix):
    """A Hill key works only when its determinant is invertible modulo 26."""
    return bool(INVERSE_TABLES[MODULUS].get(determinant(matrix)))


def encrypt_pair(matrix, first, second):
    (a, b), (c, d) = matrix
    return ((a * first + b * second) % MODULUS, (c * first + d * second) % MODULUS)


def inverse_matrix(matrix):
    (a, b), (c, d) = matrix
    inv = modinv(determinant(matrix), MODULUS)
    return ((inv * d) % MODULUS, (-inv * b) % MODULUS,
            (-inv * c) % MODULUS, (inv * a) % MODULUS)


def _draw_matrix(rng, usable=True):
    while True:
        matrix = ((rng.choice(ENTRY_RANGE), rng.choice(ENTRY_RANGE)),
                  (rng.choice(ENTRY_RANGE), rng.choice(ENTRY_RANGE)))
        if is_usable(matrix) == usable:
            return matrix


def _shown(matrix):
    (a, b), (c, d) = matrix
    return "[%d %d ; %d %d]" % (a, b, c, d)


def _pair(rng):
    letters = rng.sample("bcdefghilmnoprstu", 2)
    return letters[0], letters[1]


def generate(rng, difficulty):
    if difficulty == 1:
        return _validity(rng)
    if difficulty == 2:
        return _encrypt(rng)
    return _inverse(rng)


def _validity(rng):
    good = _draw_matrix(rng, usable=True)
    bad = _draw_matrix(rng, usable=False)
    order = rng.choice([True, False])
    first, second = (good, bad) if order else (bad, good)
    answer = 1 if order else 2
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Quale matrice puo' fare da chiave",
        difficulty=1,
        minutes=3,
        statement="Nel cifrario di Hill due per due la matrice e' una chiave valida solo se "
                  "il suo determinante e' invertibile modulo 26. Delle due proposte, una sola "
                  "va bene. Indica il numero della matrice buona e il suo determinante.",
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Matrice 1", _shown(first)),
               ("Matrice 2", _shown(second))],
        fields=[
            Field(label="Numero della matrice valida", kind="number", value=str(answer),
                  placeholder="1 oppure 2"),
            Field(label="Il suo determinante", kind="number", value=str(determinant(good)),
                  placeholder="resto in Z26"),
        ],
        hints=[
            "Il determinante di [a b ; c d] e' ad meno bc, ridotto modulo 26.",
            "Serve che il determinante sia coprimo con 26, cioe' ne' pari ne' multiplo di 13.",
            "Determinante della prima: %d. Determinante della seconda: %d."
            % (determinant(first), determinant(second)),
        ],
        steps=[
            "Matrice 1, %s: determinante %d." % (_shown(first), determinant(first)),
            "Matrice 2, %s: determinante %d." % (_shown(second), determinant(second)),
            "Il determinante buono e' %d, che compare nella tabella degli inversi modulo 26. "
            "L'altro condivide un fattore con 26, quindi quella matrice non e' invertibile."
            % determinant(good),
            "Nota da esame: senza inverso del determinante non esiste la matrice di "
            "decifratura, e piu' blocchi diversi finirebbero sullo stesso crittogramma.",
        ],
        meta_value=determinant(good),
        meta_label="il determinante della matrice valida",
    )


def _encrypt(rng):
    matrix = _draw_matrix(rng, usable=True)
    first, second = _pair(rng)
    x1, x2 = ALPHABET.index(first), ALPHABET.index(second)
    y1, y2 = encrypt_pair(matrix, x1, x2)
    (a, b), (c, d) = matrix
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Cifrare una coppia di lettere",
        difficulty=2,
        minutes=4,
        statement="Con il cifrario di Hill due per due, cifra la coppia di lettere %s%s. "
                  "Il vettore colonna delle posizioni si moltiplica per la matrice, tutto "
                  "modulo 26." % (first.upper(), second.upper()),
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Matrice", _shown(matrix)),
               ("Coppia da cifrare", "%s%s, cioe' %d e %d"
                % (first.upper(), second.upper(), x1, x2))],
        fields=[
            Field(label="Prima lettera cifrata", kind="text", value=ALPHABET[y1].upper(),
                  placeholder="una lettera"),
            Field(label="Seconda lettera cifrata", kind="text", value=ALPHABET[y2].upper(),
                  placeholder="una lettera"),
        ],
        hints=[
            "La prima componente e' a per x1 piu' b per x2; la seconda e' c per x1 piu' "
            "d per x2. Ogni volta si riduce modulo 26.",
            "Con questa matrice: %d * %d + %d * %d, e poi %d * %d + %d * %d."
            % (a, x1, b, x2, c, x1, d, x2),
            "I due prodotti valgono %d e %d prima della riduzione."
            % (a * x1 + b * x2, c * x1 + d * x2),
        ],
        steps=[
            "Posizioni di partenza: %s = %d, %s = %d."
            % (first.upper(), x1, second.upper(), x2),
            "Prima componente: %d * %d + %d * %d = %d, che modulo 26 fa %d, cioe' %s."
            % (a, x1, b, x2, a * x1 + b * x2, y1, ALPHABET[y1].upper()),
            "Seconda componente: %d * %d + %d * %d = %d, che modulo 26 fa %d, cioe' %s."
            % (c, x1, d, x2, c * x1 + d * x2, y2, ALPHABET[y2].upper()),
            "Nota da esame: Hill cifra a blocchi, quindi la stessa lettera puo' dare "
            "risultati diversi a seconda della lettera che le sta accanto.",
        ],
        meta_value=y1,
        meta_label="la posizione della prima lettera cifrata",
    )


def _inverse(rng):
    matrix = _draw_matrix(rng, usable=True)
    det = determinant(matrix)
    inv_det = modinv(det, MODULUS)
    ia, ib, ic, idd = inverse_matrix(matrix)
    (a, b), (c, d) = matrix
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="La matrice di decifratura",
        difficulty=3,
        minutes=5,
        statement="Per decifrare con Hill serve l'inversa della matrice modulo 26. "
                  "Calcolala: si scambiano gli elementi della diagonale, si cambia segno "
                  "agli altri due, e si moltiplica tutto per l'inverso del determinante.",
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Matrice", _shown(matrix)),
               ("Determinante", str(det))],
        fields=[
            Field(label="Inverso del determinante", kind="number", value=str(inv_det),
                  placeholder="resto in Z26"),
            Field(label="Primo elemento dell'inversa", kind="number", value=str(ia),
                  placeholder="resto in Z26"),
            Field(label="Ultimo elemento dell'inversa", kind="number", value=str(idd),
                  placeholder="resto in Z26"),
        ],
        hints=[
            "L'inversa e' l'inverso del determinante moltiplicato per [d -b ; -c a].",
            "Prima trova l'inverso di %d modulo 26 sulla tabella, poi moltiplica." % det,
            "L'inverso di %d modulo 26 e' %d. Il primo elemento e' quel numero per %d."
            % (det, inv_det, d),
        ],
        steps=[
            "Determinante: %d * %d - %d * %d = %d, cioe' %d mod 26."
            % (a, d, b, c, a * d - b * c, det),
            "Inverso del determinante: %d, perche' %d * %d = %d = 1 mod 26."
            % (inv_det, det, inv_det, det * inv_det),
            "Matrice aggiunta: [%d %d ; %d %d]." % (d, (-b) % MODULUS, (-c) % MODULUS, a),
            "Moltiplico per %d: l'inversa e' [%d %d ; %d %d]." % (inv_det, ia, ib, ic, idd),
            "Nota da esame: moltiplicando la matrice per la sua inversa si ottiene "
            "l'identita' modulo 26, ed e' la verifica che conviene fare prima di consegnare.",
        ],
        meta_value=inv_det,
        meta_label="l'inverso del determinante",
    )
