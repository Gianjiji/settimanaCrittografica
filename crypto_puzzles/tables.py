"""Curated pools. Nothing outside these lists ever reaches a puzzle."""

# Italian words, 5 to 9 letters, at least one repeated letter.
IC_WORDS = [
    "canotto", "pallino", "caccia", "babbo", "accada", "gattino", "mattone",
    "stelle", "collina", "farfalla", "corallo", "salame", "melone", "nonno",
    "ottone", "trattore", "rossetto", "bottone", "cassetto", "ombrello",
    "cappello", "martello", "zanzara", "sonnetto", "paletta", "mattina",
    "scatola", "pinolo", "salato", "cannone", "terrazza", "pennello",
    "villaggio", "sassolino", "maratona", "caramella", "panetto", "settori",
    "nocciola", "biscotto", "pomodoro", "cucchiaio", "lucciola", "mimosa",
    "rondine", "balestra", "grattugia", "settembre", "pettine", "zucchero",
]

# Words for the closing metapuzzle, from the vocabulary of the course.
META_WORDS = [
    "cifrario", "chiave", "modulo", "enigma", "segreto", "fattore", "residuo",
    "inverso", "periodo", "alfabeto", "primo", "quaderno", "matita", "blocco",
    "firma", "hash", "share", "vigenere", "euclide", "generatore",
]

# Small semiprimes: every product stays under 221 so the arithmetic stays mental.
RSA_PRIMES = [
    (3, 5), (3, 7), (3, 11), (3, 13), (5, 7), (5, 11), (5, 13), (7, 11),
    (7, 13), (7, 17), (11, 13), (11, 17), (13, 17),
]

PUBLIC_EXPONENTS = [3, 5, 7, 11, 13, 17]

SHARING_MODULI = [11, 13]

# Modular inverses worth memorising, shown in the pocket table of the fascicle.
INVERSE_TABLES = {
    11: {1: 1, 2: 6, 3: 4, 4: 3, 5: 9, 6: 2, 7: 8, 8: 7, 9: 5, 10: 10},
    13: {1: 1, 2: 7, 3: 9, 4: 10, 5: 8, 6: 11, 7: 2, 8: 5, 9: 3, 10: 4, 11: 6, 12: 12},
    26: {1: 1, 3: 9, 5: 21, 7: 15, 9: 3, 11: 19, 15: 7, 17: 23, 19: 11, 21: 5, 23: 17, 25: 25},
}
