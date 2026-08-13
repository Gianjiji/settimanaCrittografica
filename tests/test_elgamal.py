"""Property tests for the El Gamal generator, over 400 seeds per difficulty.

The mathematics is checked against arithmetic written out here rather than against the
module's own helpers, so a change to a helper cannot move both sides of a comparison.

Not registered in GENERATORS: see the Bloccato section of PROGRESS.md.
"""

import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import elgamal
from crypto_puzzles.core import ALLOWED_MODULI
from crypto_puzzles.tables import DH_MODULI

SEEDS = 400
DIFFICULTIES = (1, 2, 3)


def puzzles_for(difficulty):
    for seed in range(SEEDS):
        yield seed, elgamal.generate(random.Random(seed), difficulty)


def given_of(puzzle, label):
    for name, value in puzzle.given:
        if name == label:
            return value
    raise AssertionError("missing %r in %r" % (label, [n for n, _ in puzzle.given]))


def value_after(text, name):
    match = re.search(r"%s\s*=\s*(\d+)" % re.escape(name), text)
    assert match, "no %r in %r" % (name, text)
    return int(match.group(1))


def field_of(puzzle, label):
    return int(given_of(puzzle, "Campo").lstrip("Z"))


def reference_power(base, exponent, modulus):
    """Repeated multiplication, so the test never leans on pow's three argument form."""
    result = 1
    for _ in range(exponent):
        result = (result * base) % modulus
    return result


class PrimitivesTest(unittest.TestCase):
    def test_the_moduli_are_allowed(self):
        for modulus in DH_MODULI:
            with self.subTest(modulus=modulus):
                self.assertIn(modulus, ALLOWED_MODULI)

    def test_encryption_and_decryption_are_inverse(self):
        for p in DH_MODULI:
            for g in (2, 6, 7):
                for secret in range(2, p - 1):
                    public = elgamal.public_key(g, secret, p)
                    for message in range(1, p):
                        for k in (2, 3, p - 2):
                            with self.subTest(p=p, g=g, x=secret, m=message, k=k):
                                c1, c2 = elgamal.encrypt(message, g, public, k, p)
                                self.assertEqual(elgamal.decrypt(c1, c2, secret, p), message)

    def test_the_receiver_rebuilds_the_senders_mask(self):
        """c1^x equals y^k: the two sides reach the same number by different routes."""
        for p in DH_MODULI:
            for g in (2, 7):
                for secret in range(2, p - 1):
                    public = elgamal.public_key(g, secret, p)
                    for k in range(2, p - 1):
                        with self.subTest(p=p, g=g, x=secret, k=k):
                            c1 = reference_power(g, k, p)
                            self.assertEqual(reference_power(c1, secret, p),
                                             reference_power(public, k, p))

    def test_the_public_key_agrees_with_repeated_multiplication(self):
        for p in DH_MODULI:
            for g in (2, 6, 7):
                for secret in range(2, p - 1):
                    with self.subTest(p=p, g=g, x=secret):
                        self.assertEqual(elgamal.public_key(g, secret, p),
                                         reference_power(g, secret, p))


class MentalMathTest(unittest.TestCase):
    def test_every_number_shown_stays_small(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    for _, value in puzzle.given:
                        for token in re.findall(r"\d+", str(value)):
                            self.assertLessEqual(int(token), max(ALLOWED_MODULI))

    def test_answers_are_residues_of_the_field(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                modulus = field_of(puzzle, "Campo")
                for field_obj in puzzle.fields:
                    with self.subTest(difficulty=difficulty, seed=seed):
                        self.assertLess(int(field_obj.value), modulus)
                        self.assertGreaterEqual(int(field_obj.value), 0)

    def test_the_meta_value_can_feed_the_weekly_key(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertIsInstance(puzzle.meta_value, int)
                    self.assertGreaterEqual(puzzle.meta_value, 0)
                    self.assertLess(puzzle.meta_value, 26)


class ShapeTest(unittest.TestCase):
    def test_every_puzzle_is_well_formed(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual(puzzle.kind, elgamal.KIND)
                    self.assertEqual(puzzle.difficulty, difficulty)
                    self.assertTrue(puzzle.fields)

    def test_there_are_always_three_hints(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual(len(puzzle.hints), 3)

    def test_the_first_hint_introduces_no_answer(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                public = set(re.findall(r"\d+", puzzle.statement))
                for label, value in puzzle.given:
                    public.update(re.findall(r"\d+", "%s %s" % (label, value)))
                in_hint = set(re.findall(r"\d+", puzzle.hints[0]))
                for field_obj in puzzle.fields:
                    if field_obj.value in public:
                        continue
                    with self.subTest(difficulty=difficulty, seed=seed):
                        self.assertNotIn(field_obj.value, in_hint)

    def test_every_card_declares_what_feeds_the_word(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertTrue(puzzle.meta_label.strip())

    def test_the_steps_are_reasoned(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertGreaterEqual(len(puzzle.steps), 3)

    def test_no_decorative_characters(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                text = " ".join([puzzle.statement, puzzle.title] + puzzle.hints + puzzle.steps)
                with self.subTest(difficulty=difficulty, seed=seed):
                    for character in text:
                        self.assertLess(ord(character), 0x2000)

    def test_the_same_seed_gives_the_same_puzzle(self):
        for difficulty in DIFFICULTIES:
            for seed in range(50):
                first = elgamal.generate(random.Random(seed), difficulty)
                second = elgamal.generate(random.Random(seed), difficulty)
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual([f.value for f in first.fields],
                                     [f.value for f in second.fields])


class MathematicsTest(unittest.TestCase):
    def test_the_public_key_is_the_generator_to_the_private_key(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                p = field_of(puzzle, "Campo")
                g = value_after(given_of(puzzle, "Generatore"), "g")
                x = value_after(given_of(puzzle, "Chiave privata"), "x")
                self.assertEqual(int(puzzle.fields[0].value), reference_power(g, x, p))

    def test_the_ciphertext_matches_the_definition(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                p = field_of(puzzle, "Campo")
                g = value_after(given_of(puzzle, "Generatore"), "g")
                y = value_after(given_of(puzzle, "Chiave pubblica"), "y")
                m = value_after(given_of(puzzle, "Messaggio"), "m")
                k = value_after(given_of(puzzle, "Esponente casuale"), "k")
                self.assertEqual(int(puzzle.fields[0].value), reference_power(g, k, p))
                self.assertEqual(int(puzzle.fields[1].value),
                                 (m * reference_power(y, k, p)) % p)

    def test_the_published_key_belongs_to_a_real_private_key(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                p = field_of(puzzle, "Campo")
                g = value_after(given_of(puzzle, "Generatore"), "g")
                y = value_after(given_of(puzzle, "Chiave pubblica"), "y")
                self.assertTrue(any(reference_power(g, x, p) == y for x in range(1, p)))

    def test_the_recovered_message_rebuilds_the_ciphertext(self):
        """Checked forwards: the answer must re-encrypt to what was received."""
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                p = field_of(puzzle, "Campo")
                x = value_after(given_of(puzzle, "Chiave privata"), "x")
                crypto = given_of(puzzle, "Crittogramma")
                c1 = value_after(crypto, "c1")
                c2 = value_after(crypto, "c2")
                mask = int(puzzle.fields[0].value)
                message = int(puzzle.fields[1].value)
                self.assertEqual(mask, reference_power(c1, x, p))
                self.assertEqual((message * mask) % p, c2)

    def test_the_message_is_never_zero(self):
        """Zero survives any mask: c2 would be 0 whatever the key, and the card would
        teach the wrong thing. Checked on both cards that carry a message."""
        for seed, puzzle in puzzles_for(3):
            with self.subTest(card="decrypt", seed=seed):
                self.assertNotEqual(int(puzzle.fields[1].value), 0)
        for seed, puzzle in puzzles_for(2):
            with self.subTest(card="encrypt", seed=seed):
                message = value_after(given_of(puzzle, "Messaggio"), "m")
                self.assertNotEqual(message, 0)
                self.assertNotEqual(int(puzzle.fields[1].value), 0,
                                    "c2 collapsed to zero")


class NotRegisteredTest(unittest.TestCase):
    def test_the_fascicle_still_builds_nine_cards(self):
        from crypto_puzzles.fascicle import GENERATORS, build_issue
        self.assertNotIn(elgamal, GENERATORS)
        self.assertEqual(len(build_issue("2026-W33").puzzles), 9)


if __name__ == "__main__":
    unittest.main()
