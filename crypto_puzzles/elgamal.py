"""El Gamal in Z11 o Z13: public key, encryption with a small k, decryption.

Reuses the moduli and primitive roots of the Diffie-Hellman module: the table of powers
stays ten or twelve rows, which is what can be built by hand.

Not registered in GENERATORS, for the reason recorded in the Bloccato section of
PROGRESS.md.
"""

from .core import Field, Puzzle, modinv
from .tables import DH_MODULI, INVERSE_TABLES, PRIMITIVE_ROOTS

KIND = "el_gamal"
FAMILY = "El Gamal"


def public_key(g, secret, p):
    return pow(g, secret, p)


def encrypt(message, g, public, k, p):
    """The pair the sender transmits: the hint g^k, and the message masked by y^k."""
    return pow(g, k, p), (message * pow(public, k, p)) % p


def decrypt(c1, c2, secret, p):
    return (c2 * modinv(pow(c1, secret, p), p)) % p


def _powers_text(base, p, upto):
    values = []
    current = 1
    for exponent in range(1, upto + 1):
        current = (current * base) % p
        values.append("%d^%d = %d" % (base, exponent, current))
    return ", ".join(values)


def generate(rng, difficulty):
    if difficulty == 1:
        return _public_key(rng)
    if difficulty == 2:
        return _encrypt(rng)
    return _decrypt(rng)


def _setup(rng):
    p = rng.choice(DH_MODULI)
    g = rng.choice(PRIMITIVE_ROOTS[p])
    secret = rng.randrange(2, p - 1)
    return p, g, secret


def _public_key(rng):
    p, g, secret = _setup(rng)
    public = public_key(g, secret, p)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="La chiave pubblica",
        difficulty=1,
        minutes=3,
        statement="In El Gamal su Z%d si sceglie un generatore g e una chiave privata x. "
                  "La chiave pubblica e' y = g^x mod %d. Calcolala." % (p, p),
        given=[("Campo", "Z%d" % p),
               ("Generatore", "g = %d" % g),
               ("Chiave privata", "x = %d" % secret)],
        fields=[Field(label="Chiave pubblica y", kind="number", value=str(public),
                      placeholder="resto in Z%d" % p)],
        hints=[
            "La chiave pubblica e' semplicemente il generatore elevato alla chiave privata.",
            "Calcola %d^%d modulo %d, elevando al quadrato per passi." % (g, secret, p),
            "Le prime potenze di %d sono %s." % (g, _powers_text(g, p, 4)),
        ],
        steps=[
            "Potenze di %d in Z%d: %s." % (g, p, _powers_text(g, p, min(secret, p - 1))),
            "Quindi y = %d^%d = %d mod %d." % (g, secret, public, p),
            "Nota da esame: y e g viaggiano in chiaro. Risalire da y a x e' il logaritmo "
            "discreto, ed e' li' che sta la sicurezza dello schema.",
        ],
        meta_value=public,
        meta_label="la chiave pubblica y",
    )


def _encrypt(rng):
    p, g, secret = _setup(rng)
    public = public_key(g, secret, p)
    message = rng.randrange(1, p)
    k = rng.randrange(2, p - 1)
    c1, c2 = encrypt(message, g, public, k, p)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Cifrare un messaggio",
        difficulty=2,
        minutes=4,
        statement="Con la chiave pubblica di El Gamal su Z%d, cifra il messaggio m usando "
                  "l'esponente casuale k. Il crittogramma e' la coppia "
                  "(g^k, m * y^k), tutto modulo %d." % (p, p),
        given=[("Campo", "Z%d" % p),
               ("Generatore", "g = %d" % g),
               ("Chiave pubblica", "y = %d" % public),
               ("Messaggio", "m = %d" % message),
               ("Esponente casuale", "k = %d" % k)],
        fields=[
            Field(label="Prima componente c1", kind="number", value=str(c1),
                  placeholder="resto in Z%d" % p),
            Field(label="Seconda componente c2", kind="number", value=str(c2),
                  placeholder="resto in Z%d" % p),
        ],
        hints=[
            "Servono due potenze: g elevato a k, e y elevato a k. Poi un solo prodotto.",
            "c1 = %d^%d mod %d. Per c2 moltiplica il messaggio per %d^%d mod %d."
            % (g, k, p, public, k, p),
            "Le prime potenze di %d sono %s." % (public, _powers_text(public, p, 4)),
        ],
        steps=[
            "c1 = %d^%d = %d mod %d." % (g, k, c1, p),
            "Maschera: %d^%d = %d mod %d." % (public, k, pow(public, k, p), p),
            "c2 = m * maschera = %d * %d = %d mod %d."
            % (message, pow(public, k, p), c2, p),
            "Nota da esame: k va cambiato a ogni messaggio. Riusandolo, due crittogrammi "
            "diversi avrebbero la stessa maschera e il rapporto rivelerebbe i messaggi.",
        ],
        meta_value=c1,
        meta_label="la prima componente c1",
    )


def _decrypt(rng):
    p, g, secret = _setup(rng)
    public = public_key(g, secret, p)
    message = rng.randrange(1, p)
    k = rng.randrange(2, p - 1)
    c1, c2 = encrypt(message, g, public, k, p)
    shared = pow(c1, secret, p)
    inverse = modinv(shared, p)
    table = ", ".join("%d con %d" % (key, value)
                      for key, value in sorted(INVERSE_TABLES[p].items()) if key <= 6)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Decifrare un crittogramma",
        difficulty=3,
        minutes=5,
        statement="Ricevi un crittogramma di El Gamal su Z%d e conosci la chiave privata x. "
                  "Recupera il messaggio: si calcola c1^x, se ne prende l'inverso e lo si "
                  "moltiplica per c2, tutto modulo %d." % (p, p),
        given=[("Campo", "Z%d" % p),
               ("Chiave privata", "x = %d" % secret),
               ("Crittogramma", "c1 = %d, c2 = %d" % (c1, c2))],
        fields=[
            Field(label="Maschera c1^x", kind="number", value=str(shared),
                  placeholder="resto in Z%d" % p),
            Field(label="Messaggio m", kind="number", value=str(message),
                  placeholder="resto in Z%d" % p),
        ],
        hints=[
            "Il destinatario ricostruisce la stessa maschera che il mittente ha usato, "
            "perche' c1^x vale y^k.",
            "Calcola prima c1^x modulo %d, poi cercane l'inverso sulla tabella." % p,
            "Le prime potenze di %d sono %s." % (c1, _powers_text(c1, p, 4)),
        ],
        steps=[
            "Maschera: c1^x = %d^%d = %d mod %d." % (c1, secret, shared, p),
            "Inverso della maschera in Z%d: %d, perche' %d * %d = %d = 1 mod %d."
            % (p, inverse, shared, inverse, shared * inverse, p),
            "m = c2 * %d = %d * %d = %d mod %d." % (inverse, c2, inverse, message, p),
            "Verifica che la maschera sia quella giusta: il mittente aveva usato y^k, e "
            "c1^x = (g^k)^x = (g^x)^k = y^k. Le due strade portano allo stesso numero.",
            "Tabella degli inversi in Z%d, da sapere a memoria: %s." % (p, table),
        ],
        meta_value=message,
        meta_label="il messaggio m",
    )
