"""Cifrario affine: admissible key, key from two correspondences, composed encryption.

Not registered in GENERATORS, for the reason recorded in the Bloccato section of
PROGRESS.md: a fourth generator would build twelve cards and rewrite every past issue.
"""

from .core import ALPHABET, Field, Puzzle, modinv
from .tables import INVERSE_TABLES

KIND = "cifrario_affine"
FAMILY = "Cifrario affine"

MODULUS = 26
# The multipliers coprime with 26. Any other choice collapses letters onto each other.
VALID_MULTIPLIERS = tuple(a for a in range(3, MODULUS) if INVERSE_TABLES[MODULUS].get(a))
INVALID_MULTIPLIERS = tuple(a for a in range(2, MODULUS) if a not in VALID_MULTIPLIERS)


def generate(rng, difficulty):
    if difficulty == 1:
        return _admissible_key(rng)
    if difficulty == 2:
        return _key_from_pairs(rng)
    return _composed(rng)


def encrypt_letter(letter, a, b):
    return ALPHABET[(a * ALPHABET.index(letter) + b) % MODULUS]


def encrypt(text, a, b):
    return "".join(encrypt_letter(c, a, b) for c in text)


def _positions(letters):
    return ", ".join("%s = %d" % (c.upper(), ALPHABET.index(c)) for c in letters)


def _admissible_key(rng):
    good = rng.choice(VALID_MULTIPLIERS)
    bad = rng.choice(INVALID_MULTIPLIERS)
    b = rng.randrange(1, MODULUS)
    plain = rng.choice("bcdfghlmnprst")
    cipher = encrypt_letter(plain, good, b)
    candidates = sorted([good, bad])
    common = 2 if bad % 2 == 0 else 13
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Quale moltiplicatore si puo' usare",
        difficulty=1,
        minutes=3,
        statement="Un cifrario affine su 26 lettere usa E(x) = a x + b mod 26. Fra i due "
                  "valori proposti per a, uno solo da' un cifrario decifrabile. Scegli quello "
                  "giusto e cifra la lettera %s con b = %d." % (plain.upper(), b),
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Candidati per a", "%d e %d" % (candidates[0], candidates[1])),
               ("Termine noto", "b = %d" % b),
               ("Lettera da cifrare", "%s, cioe' %d" % (plain.upper(), ALPHABET.index(plain)))],
        fields=[
            Field(label="Valore di a", kind="number", value=str(good),
                  placeholder="uno dei due candidati"),
            Field(label="Lettera cifrata", kind="text", value=cipher.upper(),
                  placeholder="una lettera"),
        ],
        hints=[
            "Il cifrario e' invertibile solo se a e 26 sono coprimi: MCD(a, 26) = 1.",
            "26 = 2 * 13, quindi ogni a pari e ogni multiplo di 13 e' da scartare.",
            "Uno dei due candidati condivide il fattore %d con 26. L'altro e' quello buono."
            % common,
        ],
        steps=[
            "MCD(%d, 26) = %d, quindi %d non va: piu' lettere finirebbero sulla stessa "
            "immagine e la decifratura sarebbe impossibile." % (bad, common, bad),
            "MCD(%d, 26) = 1, quindi a = %d e' ammissibile." % (good, good),
            "Cifratura: E(%d) = %d * %d + %d = %d mod 26."
            % (ALPHABET.index(plain), good, ALPHABET.index(plain), b,
               (good * ALPHABET.index(plain) + b) % MODULUS),
            "La posizione %d corrisponde alla lettera %s."
            % ((good * ALPHABET.index(plain) + b) % MODULUS, cipher.upper()),
            "Nota da esame: i moltiplicatori ammessi sono %d, tanti quanti gli interi "
            "coprimi con 26." % (len(VALID_MULTIPLIERS) + 1),
        ],
        meta_value=(good * ALPHABET.index(plain) + b) % MODULUS,
        meta_label="la posizione della lettera cifrata",
    )


def _key_from_pairs(rng):
    a = rng.choice(VALID_MULTIPLIERS)
    b = rng.randrange(1, MODULUS)
    # The difference of the two plaintext positions must be invertible, or the key is
    # not determined by the pair.
    while True:
        x1, x2 = rng.sample(range(MODULUS), 2)
        delta = (x1 - x2) % MODULUS
        if INVERSE_TABLES[MODULUS].get(delta):
            break
    y1 = (a * x1 + b) % MODULUS
    y2 = (a * x2 + b) % MODULUS
    inv = modinv(delta, MODULUS)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Chiave da due corrispondenze",
        difficulty=2,
        minutes=4,
        statement="Di un cifrario affine E(x) = a x + b mod 26 si conoscono due "
                  "corrispondenze. Ricava la chiave, cioe' a e b.",
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Prima corrispondenza", "%s -> %s" % (ALPHABET[x1].upper(), ALPHABET[y1].upper())),
               ("Seconda corrispondenza", "%s -> %s" % (ALPHABET[x2].upper(), ALPHABET[y2].upper())),
               ("Posizioni", _positions([ALPHABET[x1], ALPHABET[y1], ALPHABET[x2], ALPHABET[y2]]))],
        fields=[
            Field(label="Moltiplicatore a", kind="number", value=str(a),
                  placeholder="resto in Z26"),
            Field(label="Termine noto b", kind="number", value=str(b),
                  placeholder="resto in Z26"),
        ],
        hints=[
            "Scrivi le due equazioni a x + b = y mod 26 e sottraile: b sparisce.",
            "Resta a (x1 - x2) = y1 - y2 mod 26, quindi serve l'inverso di %d." % delta,
            "L'inverso di %d modulo 26 e' %d. Poi ricava b da una delle due equazioni."
            % (delta, inv),
        ],
        steps=[
            "Sistema: %d a + b = %d e %d a + b = %d, tutto mod 26." % (x1, y1, x2, y2),
            "Sottraendo: a * %d = %d mod 26." % (delta, (y1 - y2) % MODULUS),
            "Moltiplico per l'inverso di %d, che e' %d: a = %d * %d = %d mod 26."
            % (delta, inv, (y1 - y2) % MODULUS, inv, a),
            "Sostituisco nella prima: b = %d - %d * %d = %d mod 26." % (y1, a, x1, b),
            "Verifica sulla seconda: %d * %d + %d = %d mod 26, che e' proprio %s."
            % (a, x2, b, y2, ALPHABET[y2].upper()),
        ],
        meta_value=a,
        meta_label="il moltiplicatore a",
    )


def _composed(rng):
    a1 = rng.choice(VALID_MULTIPLIERS)
    b1 = rng.randrange(1, MODULUS)
    a2 = rng.choice(VALID_MULTIPLIERS)
    b2 = rng.randrange(1, MODULUS)
    big_a = (a2 * a1) % MODULUS
    big_b = (a2 * b1 + b2) % MODULUS
    plain = rng.choice("bcdfghlmnprst")
    cipher = encrypt_letter(plain, big_a, big_b)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Due cifrari affini in cascata",
        difficulty=3,
        minutes=5,
        statement="Si applica prima E1(x) = %d x + %d, poi E2(y) = %d y + %d, tutto modulo "
                  "26. La composizione e' ancora un cifrario affine: trovane la chiave, e "
                  "cifra la lettera %s." % (a1, b1, a2, b2, plain.upper()),
        given=[("Alfabeto", "26 lettere, A = 0"),
               ("Primo cifrario", "E1(x) = %d x + %d" % (a1, b1)),
               ("Secondo cifrario", "E2(y) = %d y + %d" % (a2, b2)),
               ("Lettera da cifrare", "%s, cioe' %d" % (plain.upper(), ALPHABET.index(plain)))],
        fields=[
            Field(label="Moltiplicatore composto A", kind="number", value=str(big_a),
                  placeholder="resto in Z26"),
            Field(label="Termine noto composto B", kind="number", value=str(big_b),
                  placeholder="resto in Z26"),
            Field(label="Lettera cifrata", kind="text", value=cipher.upper(),
                  placeholder="una lettera"),
        ],
        hints=[
            "Sostituisci E1 dentro E2 e raccogli: E2(E1(x)) = a2 (a1 x + b1) + b2.",
            "Sviluppando viene (a2 a1) x + (a2 b1 + b2), tutto ridotto modulo 26.",
            "Quindi A = %d * %d e B = %d * %d + %d, da ridurre." % (a2, a1, a2, b1, b2),
        ],
        steps=[
            "E2(E1(x)) = %d (%d x + %d) + %d." % (a2, a1, b1, b2),
            "Sviluppo: %d * %d x + %d * %d + %d." % (a2, a1, a2, b1, b2),
            "Riduco: A = %d mod 26 = %d, B = %d mod 26 = %d."
            % (a2 * a1, big_a, a2 * b1 + b2, big_b),
            "Cifro la lettera: E(%d) = %d * %d + %d = %d mod 26, cioe' %s."
            % (ALPHABET.index(plain), big_a, ALPHABET.index(plain), big_b,
               (big_a * ALPHABET.index(plain) + big_b) % MODULUS, cipher.upper()),
            "Nota da esame: A resta coprimo con 26 perche' prodotto di due coprimi, quindi "
            "la composizione e' ancora decifrabile. I cifrari affini formano un gruppo.",
        ],
        meta_value=big_a,
        meta_label="il moltiplicatore composto A",
    )
