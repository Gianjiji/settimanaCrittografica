"""Property tests for the Feistel generator, over 400 seeds per difficulty.

Not registered in GENERATORS: see the Bloccato section of PROGRESS.md.
"""

import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import feistel

SEEDS = 400
DIFFICULTIES = (1, 2, 3)


def puzzles_for(difficulty):
    for seed in range(SEEDS):
        yield seed, feistel.generate(random.Random(seed), difficulty)


def reference_f(half, key):
    """F written out again, independently of the module.

    Comparing the puzzles against feistel.feistel_round only proves the generator is
    consistent with itself: change F and both sides move together. This is the oracle.
    """
    mixed = half ^ key
    return ((mixed << 1) & 0b1111) | (mixed >> 3)


def reference_round(left, right, key):
    return right, left ^ reference_f(right, key)


def given_of(puzzle, label):
    for name, value in puzzle.given:
        if name == label:
            return value
    raise AssertionError("missing %r in %r" % (label, [n for n, _ in puzzle.given]))


class PrimitivesTest(unittest.TestCase):
    def test_rotation_stays_on_four_bits(self):
        for value in range(16):
            with self.subTest(value=value):
                self.assertLess(feistel.rotate_left(value), 16)
                self.assertGreaterEqual(feistel.rotate_left(value), 0)

    def test_rotation_is_a_permutation(self):
        self.assertEqual(len({feistel.rotate_left(v) for v in range(16)}), 16)

    def test_rotating_four_times_returns_the_value(self):
        for value in range(16):
            rotated = value
            for _ in range(4):
                rotated = feistel.rotate_left(rotated)
            with self.subTest(value=value):
                self.assertEqual(rotated, value)

    def test_the_round_undoes_itself_with_the_same_key(self):
        """The whole point of Feistel: F never has to be invertible."""
        for left in range(16):
            for right in range(16):
                for key in (1, 7, 15):
                    with self.subTest(left=left, right=right, key=key):
                        new = feistel.feistel_round(left, right, key)
                        self.assertEqual(feistel.unfeistel_round(*new, key), (left, right))

    def test_the_round_function_is_xor_then_rotate(self):
        """Pinned against an independent implementation, not against itself."""
        for half in range(16):
            for key in range(16):
                with self.subTest(half=half, key=key):
                    self.assertEqual(feistel.round_function(half, key),
                                     reference_f(half, key))

    def test_the_round_function_actually_rotates(self):
        """Dropping the rotation would leave a plain xor, and two rounds would collapse."""
        differences = [feistel.round_function(h, k) != (h ^ k)
                       for h in range(16) for k in range(16)]
        self.assertTrue(any(differences), "F is indistinguishable from a bare xor")

    def test_bits_are_always_four_characters(self):
        for value in range(16):
            with self.subTest(value=value):
                self.assertEqual(len(feistel.bits(value)), 4)
                self.assertEqual(int(feistel.bits(value), 2), value)


class MentalMathTest(unittest.TestCase):
    """Invariant 1. No modulus is involved at all: the round function is bitwise."""

    def test_the_module_uses_no_modular_arithmetic(self):
        with open(feistel.__file__, encoding="utf-8") as handle:
            source = handle.read()
        body = source.split('"""', 2)[2]
        self.assertNotIn("% 16", body)
        self.assertNotIn("modinv", body)

    def test_every_value_shown_is_four_bits(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    for _, value in puzzle.given:
                        self.assertRegex(str(value), r"^[01]{4}$")

    def test_answers_are_four_bit_strings(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                for field_obj in puzzle.fields:
                    with self.subTest(difficulty=difficulty, seed=seed):
                        self.assertRegex(field_obj.value, r"^[01]{4}$")

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
                    self.assertEqual(puzzle.kind, feistel.KIND)
                    self.assertEqual(puzzle.difficulty, difficulty)
                    self.assertTrue(puzzle.statement)
                    self.assertEqual(len(puzzle.fields), 2)

    def test_there_are_always_three_hints(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual(len(puzzle.hints), 3)

    def test_the_first_hint_introduces_no_answer(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                public = set(re.findall(r"[01]{4}", puzzle.statement))
                for _, value in puzzle.given:
                    public.update(re.findall(r"[01]{4}", str(value)))
                in_hint = set(re.findall(r"[01]{4}", puzzle.hints[0]))
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
                first = feistel.generate(random.Random(seed), difficulty)
                second = feistel.generate(random.Random(seed), difficulty)
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual([f.value for f in first.fields],
                                     [f.value for f in second.fields])


class MathematicsTest(unittest.TestCase):
    def read(self, puzzle, label):
        return int(given_of(puzzle, label), 2)

    def test_one_round_matches_the_definition(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                left = self.read(puzzle, "Meta' sinistra L0")
                right = self.read(puzzle, "Meta' destra R0")
                key = self.read(puzzle, "Chiave k")
                expected = reference_round(left, right, key)
                self.assertEqual(int(puzzle.fields[0].value, 2), expected[0])
                self.assertEqual(int(puzzle.fields[1].value, 2), expected[1])

    def test_one_round_moves_the_right_half_left(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                self.assertEqual(puzzle.fields[0].value, given_of(puzzle, "Meta' destra R0"))

    def test_two_rounds_match_applying_the_round_twice(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                left = self.read(puzzle, "Meta' sinistra L0")
                right = self.read(puzzle, "Meta' destra R0")
                k1 = self.read(puzzle, "Chiave del primo round")
                k2 = self.read(puzzle, "Chiave del secondo round")
                state = reference_round(left, right, k1)
                state = reference_round(state[0], state[1], k2)
                self.assertEqual((int(puzzle.fields[0].value, 2),
                                  int(puzzle.fields[1].value, 2)), state)

    def test_decryption_returns_the_original_block(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                l2 = self.read(puzzle, "Meta' sinistra L2")
                r2 = self.read(puzzle, "Meta' destra R2")
                k1 = self.read(puzzle, "Chiave del primo round")
                k2 = self.read(puzzle, "Chiave del secondo round")
                state = feistel.unfeistel_round(l2, r2, k2)
                state = feistel.unfeistel_round(state[0], state[1], k1)
                self.assertEqual((int(puzzle.fields[0].value, 2),
                                  int(puzzle.fields[1].value, 2)), state)

    def test_encrypting_the_decrypted_answer_gives_the_ciphertext_back(self):
        """The round trip, checked from the answer rather than from the generator."""
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                left = int(puzzle.fields[0].value, 2)
                right = int(puzzle.fields[1].value, 2)
                k1 = self.read(puzzle, "Chiave del primo round")
                k2 = self.read(puzzle, "Chiave del secondo round")
                state = reference_round(left, right, k1)
                state = reference_round(state[0], state[1], k2)
                self.assertEqual(state, (self.read(puzzle, "Meta' sinistra L2"),
                                         self.read(puzzle, "Meta' destra R2")))


class NotRegisteredTest(unittest.TestCase):
    def test_the_fascicle_still_builds_nine_cards(self):
        from crypto_puzzles.fascicle import GENERATORS, build_issue
        self.assertNotIn(feistel, GENERATORS)
        self.assertEqual(len(build_issue("2026-W33").puzzles), 9)


if __name__ == "__main__":
    unittest.main()
