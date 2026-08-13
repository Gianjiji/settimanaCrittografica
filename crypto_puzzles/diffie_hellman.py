"""Diffie-Hellman: primitive root check, discrete logarithm, shared key.

Not registered in GENERATORS: a fourth generator would produce twelve cards instead of
nine and would change every past fascicle. See the Bloccato section of PROGRESS.md.
"""

from .core import Field, Puzzle
from .tables import DH_MODULI, PRIMITIVE_ROOTS

KIND = "scambio_chiave"
FAMILY = "Diffie-Hellman"


def generate(rng, difficulty):
    if difficulty == 1:
        return _shared_key(rng)
    if difficulty == 2:
        return _discrete_log(rng)
    return _primitive_root(rng)


def power_table(g, p):
    """The successive powers of g, the table the exam expects you to build by hand."""
    powers = []
    value = 1
    for _ in range(1, p):
        value = (value * g) % p
        powers.append(value)
    return powers


def is_primitive_root(g, p):
    return len(set(power_table(g, p))) == p - 1


def _table_text(g, p, upto):
    return ", ".join("%d^%d = %d" % (g, k + 1, v)
                     for k, v in enumerate(power_table(g, p)[:upto]))


def _shared_key(rng):
    p = rng.choice(DH_MODULI)
    g = rng.choice(PRIMITIVE_ROOTS[p])
    a = rng.randrange(2, p - 1)
    b = rng.randrange(2, p - 1)
    public_a = pow(g, a, p)
    public_b = pow(g, b, p)
    shared = pow(public_b, a, p)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Chiave condivisa",
        difficulty=1,
        minutes=3,
        statement="Alice e Bob usano Diffie-Hellman su Z%d con generatore %d. Alice tiene "
                  "l'esponente segreto %d e riceve da Bob il valore pubblico %d. Quale chiave "
                  "condivisa ottiene?" % (p, g, a, public_b),
        given=[("Campo", "Z%d" % p),
               ("Generatore", "g = %d" % g),
               ("Segreto di Alice", "a = %d" % a),
               ("Pubblico di Bob", "B = %d" % public_b)],
        fields=[Field(label="Chiave condivisa K", kind="number", value=str(shared),
                      placeholder="resto in Z%d" % p)],
        hints=[
            "La chiave condivisa e' B elevato al segreto di Alice, tutto modulo %d." % p,
            "Devi calcolare %d^%d mod %d. Conviene elevare al quadrato per passi." % (public_b, a, p),
            "Le prime potenze di %d in Z%d sono %s." % (public_b, p, _table_text(public_b, p, 4)),
        ],
        steps=[
            "Alice calcola K = B^a mod %d = %d^%d mod %d." % (p, public_b, a, p),
            "Potenze di %d in Z%d: %s." % (public_b, p, _table_text(public_b, p, min(6, p - 1))),
            "Quindi K = %d." % shared,
            "Verifica dalla parte di Bob: A = g^a = %d^%d = %d, e A^b = %d^%d = %d mod %d. "
            "Le due parti coincidono, ed e' tutto il senso del protocollo."
            % (g, a, public_a, public_a, b, shared, p),
            "Nota da esame: passano sul canale g, %d, A e B. Il segreto a non passa mai, e "
            "ricavarlo da A richiede il logaritmo discreto." % p,
        ],
        meta_value=shared,
        meta_label="la chiave condivisa K",
    )


def _discrete_log(rng):
    p = rng.choice(DH_MODULI)
    g = rng.choice(PRIMITIVE_ROOTS[p])
    exponent = rng.randrange(2, p - 1)
    target = pow(g, exponent, p)
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Logaritmo discreto",
        difficulty=2,
        minutes=4,
        statement="In Z%d il numero %d e' un generatore. Trova l'esponente x tale che "
                  "%d^x = %d mod %d." % (p, g, g, target, p),
        given=[("Campo", "Z%d" % p),
               ("Generatore", "g = %d" % g),
               ("Valore", "%d^x = %d" % (g, target))],
        fields=[Field(label="Esponente x", kind="number", value=str(exponent),
                      placeholder="esponente fra 1 e %d" % (p - 1))],
        hints=[
            "Non esiste una scorciatoia: si costruisce la tabella delle potenze di %d "
            "e si cerca %d." % (g, target),
            "Parti da %d^1 e moltiplica per %d a ogni passo, riducendo modulo %d." % (g, g, p),
            "Dopo quattro passi sei a %s. Continua finche' non incontri %d."
            % (_table_text(g, p, 4), target),
        ],
        steps=[
            "Tabella delle potenze di %d in Z%d: %s."
            % (g, p, _table_text(g, p, min(exponent + 1, p - 1))),
            "Il valore %d compare all'esponente %d, quindi x = %d."
            % (target, exponent, exponent),
            "Controllo: %d^%d = %d mod %d." % (g, exponent, target, p),
            "Nota da esame: la tabella ha %d righe distinte perche' %d e' un generatore, "
            "quindi la soluzione esiste ed e' unica fra 1 e %d." % (p - 1, g, p - 1),
        ],
        meta_value=exponent,
        meta_label="l'esponente x",
    )


def _primitive_root(rng):
    p = rng.choice(DH_MODULI)
    good = rng.choice(PRIMITIVE_ROOTS[p])
    bad = rng.choice([c for c in range(2, p) if not is_primitive_root(c, p)])
    candidates = sorted([good, bad])
    order_of_bad = len(set(power_table(bad, p)))
    return Puzzle(
        kind=KIND,
        family=FAMILY,
        title="Quale base genera Z%d" % p,
        difficulty=3,
        minutes=5,
        statement="Per uno scambio Diffie-Hellman su Z%d si valutano due basi, %d e %d. Una "
                  "sola e' una radice primitiva. Indica quale, e l'ordine dell'altra."
                  % (p, candidates[0], candidates[1]),
        given=[("Campo", "Z%d" % p),
               ("Candidati", "%d e %d" % (candidates[0], candidates[1]))],
        fields=[
            Field(label="Radice primitiva", kind="number", value=str(good),
                  placeholder="uno dei due candidati"),
            Field(label="Ordine dell'altra base", kind="number", value=str(order_of_bad),
                  placeholder="quante potenze distinte"),
        ],
        hints=[
            "Una base e' radice primitiva se le sue potenze producono tutti i %d elementi "
            "non nulli di Z%d." % (p - 1, p),
            "Costruisci le due tabelle. Quella che si richiude prima non e' un generatore, "
            "e il punto in cui torna a 1 e' il suo ordine.",
            "Le potenze di %d sono %s: si richiudono presto." % (bad, _table_text(bad, p, 4)),
        ],
        steps=[
            "Potenze di %d in Z%d: %s. Sono %d valori distinti su %d, quindi %d e' una "
            "radice primitiva."
            % (good, p, _table_text(good, p, min(6, p - 1)), p - 1, p - 1, good),
            "Potenze di %d in Z%d: %s. Tornano a 1 dopo %d passi, quindi l'ordine di %d "
            "e' %d." % (bad, p, _table_text(bad, p, min(order_of_bad, 6)), order_of_bad,
                        bad, order_of_bad),
            "Nota da esame: l'ordine di ogni elemento divide %d, il numero di elementi non "
            "nulli. Infatti %d divide %d." % (p - 1, order_of_bad, p - 1),
        ],
        meta_value=good,
        meta_label="la radice primitiva",
    )
