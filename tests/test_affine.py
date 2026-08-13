"""Property tests for the affine generator, over 400 seeds per difficulty.

Not registered in GENERATORS: see the Bloccato section of PROGRESS.md.
"""

import math
import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import affine
from crypto_puzzles.core import ALPHABET, ALLOWED_MODULI

SEEDS = 400
DIFFICULTIES = (1, 2, 3)


def puzzles_for(difficulty):
    for seed in range(SEEDS):
        yield seed, affine.generate(random.Random(seed), difficulty)


def given_of(puzzle, label):
    for name, value in puzzle.given:
        if name == label:
            return value
    raise AssertionError("missing %r" % label)


class KeySpaceTest(unittest.TestCase):
    def test_the_modulus_is_allowed(self):
        self.assertIn(affine.MODULUS, ALLOWED_MODULI)

    def test_valid_multipliers_are_exactly_the_coprime_ones(self):
        expected = tuple(a for a in range(3, 26) if math.gcd(a, 26) == 1)
        self.assertEqual(affine.VALID_MULTIPLIERS, expected)

    def test_invalid_multipliers_share_a_factor_with_26(self):
        for a in affine.INVALID_MULTIPLIERS:
            with self.subTest(a=a):
                self.assertGreater(math.gcd(a, 26), 1)

    def test_the_two_sets_do_not_overlap(self):
        self.assertEqual(set(affine.VALID_MULTIPLIERS) & set(affine.INVALID_MULTIPLIERS), set())

    def test_a_valid_multiplier_is_a_bijection_on_the_alphabet(self):
        for a in affine.VALID_MULTIPLIERS:
            with self.subTest(a=a):
                images = {(a * x + 4) % 26 for x in range(26)}
                self.assertEqual(len(images), 26)

    def test_an_invalid_multiplier_collapses_letters(self):
        for a in affine.INVALID_MULTIPLIERS:
            with self.subTest(a=a):
                images = {(a * x + 4) % 26 for x in range(26)}
                self.assertLess(len(images), 26)


class MentalMathTest(unittest.TestCase):
    """Invariant 1."""

    def test_every_number_shown_stays_within_the_alphabet(self):
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

    def test_letter_answers_are_a_single_letter(self):
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
                    self.assertEqual(puzzle.kind, affine.KIND)
                    self.assertEqual(puzzle.difficulty, difficulty)
                    self.assertTrue(puzzle.statement)
                    self.assertTrue(puzzle.given)
                    self.assertTrue(puzzle.fields)

    def test_there_are_always_three_hints(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual(len(puzzle.hints), 3)

    def test_the_first_hint_introduces_no_answer(self):
        """A number already printed carries no information; a new one would."""
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                public = set(re.findall(r"\d+", puzzle.statement))
                for _, value in puzzle.given:
                    public.update(re.findall(r"\d+", str(value)))
                in_hint = set(re.findall(r"\d+", puzzle.hints[0]))
                for field_obj in puzzle.fields:
                    if field_obj.kind != "number":
                        continue
                    with self.subTest(difficulty=difficulty, seed=seed):
                        if field_obj.value in public:
                            continue
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
                first = affine.generate(random.Random(seed), difficulty)
                second = affine.generate(random.Random(seed), difficulty)
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual([f.value for f in first.fields],
                                     [f.value for f in second.fields])


class MathematicsTest(unittest.TestCase):
    def test_the_admissible_multiplier_is_the_coprime_one(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                candidates = [int(t) for t in
                              given_of(puzzle, "Candidati per a").split(" e ")]
                good = [c for c in candidates if math.gcd(c, 26) == 1]
                self.assertEqual(len(good), 1, "exactly one candidate must be usable")
                self.assertEqual(good[0], int(puzzle.fields[0].value))

    def test_the_encrypted_letter_matches_the_chosen_key(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                a = int(puzzle.fields[0].value)
                b = int(given_of(puzzle, "Termine noto").split("=")[1])
                plain = given_of(puzzle, "Lettera da cifrare").split(",")[0].strip().lower()
                self.assertEqual(puzzle.fields[1].value.lower(),
                                 affine.encrypt_letter(plain, a, b))

    def test_the_recovered_key_reproduces_both_correspondences(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                a = int(puzzle.fields[0].value)
                b = int(puzzle.fields[1].value)
                for label in ("Prima corrispondenza", "Seconda corrispondenza"):
                    plain, cipher = [t.strip().lower()
                                     for t in given_of(puzzle, label).split("->")]
                    self.assertEqual(affine.encrypt_letter(plain, a, b), cipher)

    def test_the_recovered_multiplier_is_admissible(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                self.assertEqual(math.gcd(int(puzzle.fields[0].value), 26), 1)

    def test_the_two_correspondences_determine_the_key(self):
        """A pair whose positions differ by a non invertible amount has many keys."""
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                plains = []
                for label in ("Prima corrispondenza", "Seconda corrispondenza"):
                    plains.append(given_of(puzzle, label).split("->")[0].strip().lower())
                delta = (ALPHABET.index(plains[0]) - ALPHABET.index(plains[1])) % 26
                self.assertEqual(math.gcd(delta, 26), 1)

    def test_the_composition_agrees_with_applying_both_ciphers(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                a1, b1 = self.read_cipher(puzzle, "Primo cifrario")
                a2, b2 = self.read_cipher(puzzle, "Secondo cifrario")
                big_a = int(puzzle.fields[0].value)
                big_b = int(puzzle.fields[1].value)
                for x in range(26):
                    self.assertEqual((big_a * x + big_b) % 26,
                                     (a2 * ((a1 * x + b1) % 26) + b2) % 26)

    def test_the_composed_multiplier_stays_admissible(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                self.assertEqual(math.gcd(int(puzzle.fields[0].value), 26), 1)

    def test_the_composed_letter_matches_the_composed_key(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                big_a = int(puzzle.fields[0].value)
                big_b = int(puzzle.fields[1].value)
                plain = given_of(puzzle, "Lettera da cifrare").split(",")[0].strip().lower()
                self.assertEqual(puzzle.fields[2].value.lower(),
                                 affine.encrypt_letter(plain, big_a, big_b))

    def read_cipher(self, puzzle, label):
        text = given_of(puzzle, label)
        numbers = [int(t) for t in re.findall(r"\d+", text.split("=")[1])]
        return numbers[0], numbers[1]


class NotRegisteredTest(unittest.TestCase):
    def test_the_fascicle_still_builds_nine_cards(self):
        from crypto_puzzles.fascicle import GENERATORS, build_issue
        self.assertNotIn(affine, GENERATORS)
        self.assertEqual(len(build_issue("2026-W33").puzzles), 9)


if __name__ == "__main__":
    unittest.main()
