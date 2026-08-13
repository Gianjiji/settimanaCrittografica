"""Property tests for the Hill generator, over 400 seeds per difficulty.

The mathematics is checked against arithmetic written out here, not against the module's
own helpers: comparing a generator with the function it uses proves only self consistency.

Not registered in GENERATORS: see the Bloccato section of PROGRESS.md.
"""

import math
import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import hill
from crypto_puzzles.core import ALPHABET, ALLOWED_MODULI

SEEDS = 400
DIFFICULTIES = (1, 2, 3)


def puzzles_for(difficulty):
    for seed in range(SEEDS):
        yield seed, hill.generate(random.Random(seed), difficulty)


def given_of(puzzle, label):
    for name, value in puzzle.given:
        if name == label:
            return value
    raise AssertionError("missing %r in %r" % (label, [n for n, _ in puzzle.given]))


def read_matrix(text):
    a, b, c, d = [int(t) for t in re.findall(r"-?\d+", text)]
    return ((a, b), (c, d))


def reference_determinant(matrix):
    """Written out again, independently of hill.determinant."""
    (a, b), (c, d) = matrix
    return (a * d - b * c) % 26


class MatrixTest(unittest.TestCase):
    def test_the_modulus_is_allowed(self):
        self.assertIn(hill.MODULUS, ALLOWED_MODULI)

    def test_the_determinant_agrees_with_the_definition(self):
        for a in range(12):
            for b in range(12):
                for c in range(12):
                    for d in (0, 5, 11):
                        matrix = ((a, b), (c, d))
                        with self.subTest(matrix=matrix):
                            self.assertEqual(hill.determinant(matrix),
                                             reference_determinant(matrix))

    def test_usable_means_the_determinant_is_coprime_with_26(self):
        for a in range(12):
            for b in range(12):
                matrix = ((a, b), (3, 7))
                with self.subTest(matrix=matrix):
                    self.assertEqual(hill.is_usable(matrix),
                                     math.gcd(reference_determinant(matrix), 26) == 1)

    def test_the_inverse_really_inverts_the_matrix(self):
        """Multiplying key by inverse must give the identity modulo 26."""
        checked = 0
        for a in range(12):
            for b in range(12):
                matrix = ((a, b), (3, 7))
                if not hill.is_usable(matrix):
                    continue
                checked += 1
                ia, ib, ic, idd = hill.inverse_matrix(matrix)
                (m00, m01), (m10, m11) = matrix
                with self.subTest(matrix=matrix):
                    self.assertEqual((ia * m00 + ib * m10) % 26, 1)
                    self.assertEqual((ia * m01 + ib * m11) % 26, 0)
                    self.assertEqual((ic * m00 + idd * m10) % 26, 0)
                    self.assertEqual((ic * m01 + idd * m11) % 26, 1)
        self.assertGreater(checked, 20, "too few usable matrices to mean anything")

    def test_encryption_is_a_bijection_on_pairs_for_a_usable_key(self):
        matrix = ((3, 2), (5, 7))
        self.assertTrue(hill.is_usable(matrix))
        images = {hill.encrypt_pair(matrix, x, y) for x in range(26) for y in range(26)}
        self.assertEqual(len(images), 26 * 26)


class MentalMathTest(unittest.TestCase):
    def test_every_number_shown_stays_small(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    for _, value in puzzle.given:
                        for token in re.findall(r"\d+", str(value)):
                            self.assertLessEqual(int(token), 26)

    def test_numeric_answers_are_residues(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                for field_obj in puzzle.fields:
                    if field_obj.kind != "number":
                        continue
                    with self.subTest(difficulty=difficulty, seed=seed):
                        self.assertLess(int(field_obj.value), 26)
                        self.assertGreaterEqual(int(field_obj.value), 0)

    def test_letter_answers_are_single_letters(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                for field_obj in puzzle.fields:
                    if field_obj.kind != "text":
                        continue
                    with self.subTest(difficulty=difficulty, seed=seed):
                        self.assertEqual(len(field_obj.value), 1)
                        self.assertIn(field_obj.value.lower(), ALPHABET)

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
                    self.assertEqual(puzzle.kind, hill.KIND)
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
                    if field_obj.kind != "number" or field_obj.value in public:
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
                    self.assertGreaterEqual(len(puzzle.steps), 4)

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
                first = hill.generate(random.Random(seed), difficulty)
                second = hill.generate(random.Random(seed), difficulty)
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual([f.value for f in first.fields],
                                     [f.value for f in second.fields])


class MathematicsTest(unittest.TestCase):
    def test_exactly_one_matrix_is_usable(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                matrices = [read_matrix(given_of(puzzle, "Matrice %d" % n)) for n in (1, 2)]
                usable = [n for n, m in enumerate(matrices, start=1)
                          if math.gcd(reference_determinant(m), 26) == 1]
                self.assertEqual(len(usable), 1)
                self.assertEqual(usable[0], int(puzzle.fields[0].value))

    def test_the_reported_determinant_belongs_to_the_valid_matrix(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                chosen = read_matrix(given_of(puzzle, "Matrice %s" % puzzle.fields[0].value))
                self.assertEqual(int(puzzle.fields[1].value), reference_determinant(chosen))

    def test_the_encryption_matches_the_matrix_product(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                (a, b), (c, d) = read_matrix(given_of(puzzle, "Matrice"))
                numbers = re.findall(r"\d+", given_of(puzzle, "Coppia da cifrare"))
                x1, x2 = int(numbers[0]), int(numbers[1])
                self.assertEqual(ALPHABET.index(puzzle.fields[0].value.lower()),
                                 (a * x1 + b * x2) % 26)
                self.assertEqual(ALPHABET.index(puzzle.fields[1].value.lower()),
                                 (c * x1 + d * x2) % 26)

    def test_the_encryption_key_is_usable(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                matrix = read_matrix(given_of(puzzle, "Matrice"))
                self.assertEqual(math.gcd(reference_determinant(matrix), 26), 1)

    def test_the_inverse_determinant_is_a_real_inverse(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                det = int(given_of(puzzle, "Determinante"))
                self.assertEqual((det * int(puzzle.fields[0].value)) % 26, 1)

    def test_the_reported_corners_invert_the_matrix(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                (a, b), (c, d) = read_matrix(given_of(puzzle, "Matrice"))
                inv_det = int(puzzle.fields[0].value)
                self.assertEqual(int(puzzle.fields[1].value), (inv_det * d) % 26)
                self.assertEqual(int(puzzle.fields[2].value), (inv_det * a) % 26)

    def test_the_declared_determinant_is_the_real_one(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                matrix = read_matrix(given_of(puzzle, "Matrice"))
                self.assertEqual(int(given_of(puzzle, "Determinante")),
                                 reference_determinant(matrix))


class NotRegisteredTest(unittest.TestCase):
    def test_the_fascicle_still_builds_nine_cards(self):
        from crypto_puzzles.fascicle import GENERATORS, build_issue
        self.assertNotIn(hill, GENERATORS)
        self.assertEqual(len(build_issue("2026-W33").puzzles), 9)


if __name__ == "__main__":
    unittest.main()
