"""Property tests for the Diffie-Hellman generator, over 400 seeds per difficulty.

The module is deliberately not registered in GENERATORS. See the Bloccato section of
PROGRESS.md: a fourth generator would build twelve cards and rewrite every past issue.
"""

import os
import random
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import diffie_hellman
from crypto_puzzles.core import ALLOWED_MODULI
from crypto_puzzles.tables import DH_MODULI, PRIMITIVE_ROOTS

SEEDS = 400
DIFFICULTIES = (1, 2, 3)


def puzzles_for(difficulty):
    for seed in range(SEEDS):
        yield seed, diffie_hellman.generate(random.Random(seed), difficulty)


class TablesTest(unittest.TestCase):
    def test_the_moduli_are_allowed(self):
        for modulus in DH_MODULI:
            with self.subTest(modulus=modulus):
                self.assertIn(modulus, ALLOWED_MODULI)

    def test_every_listed_root_really_generates_the_field(self):
        for modulus, roots in PRIMITIVE_ROOTS.items():
            for root in roots:
                with self.subTest(modulus=modulus, root=root):
                    self.assertTrue(diffie_hellman.is_primitive_root(root, modulus))

    def test_no_generator_is_missing_from_the_table(self):
        for modulus in DH_MODULI:
            found = tuple(g for g in range(2, modulus)
                          if diffie_hellman.is_primitive_root(g, modulus))
            self.assertEqual(found, tuple(sorted(PRIMITIVE_ROOTS[modulus])))

    def test_power_table_has_the_right_length(self):
        for modulus in DH_MODULI:
            for base in range(2, modulus):
                with self.subTest(modulus=modulus, base=base):
                    self.assertEqual(len(diffie_hellman.power_table(base, modulus)), modulus - 1)


class MentalMathTest(unittest.TestCase):
    """Invariant 1: everything must stay solvable in the head."""

    def test_every_number_shown_stays_small(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    for _, value in puzzle.given:
                        for token in str(value).replace("=", " ").replace(",", " ").split():
                            if token.lstrip("-").isdigit():
                                self.assertLess(abs(int(token)), max(ALLOWED_MODULI) + 1)

    def test_answers_are_residues_of_the_field(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    for field_obj in puzzle.fields:
                        self.assertTrue(field_obj.value.isdigit())
                        self.assertLess(int(field_obj.value), max(DH_MODULI))

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
                    self.assertEqual(puzzle.kind, diffie_hellman.KIND)
                    self.assertEqual(puzzle.difficulty, difficulty)
                    self.assertTrue(puzzle.statement)
                    self.assertTrue(puzzle.given)
                    self.assertTrue(puzzle.fields)
                    self.assertGreaterEqual(puzzle.minutes, 1)

    def test_there_are_always_three_hints(self):
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual(len(puzzle.hints), 3)
                    for hint in puzzle.hints:
                        self.assertTrue(hint.strip())

    def test_the_first_hint_never_gives_the_answer(self):
        """Invariant 3: the hints go procedure, blocking step, near solution.

        A number already printed in the statement carries no information, so it is not a
        leak when it happens to equal the answer. Only a number appearing for the first
        time in the first hint would be one.
        """
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                public = set()
                for _, value in puzzle.given:
                    public.update(re.findall(r"\d+", str(value)))
                public.update(re.findall(r"\d+", puzzle.statement))
                in_hint = set(re.findall(r"\d+", puzzle.hints[0]))
                for field_obj in puzzle.fields:
                    with self.subTest(difficulty=difficulty, seed=seed):
                        if field_obj.value in public:
                            continue
                        self.assertNotIn(field_obj.value, in_hint,
                                         "the first hint introduces the answer %r"
                                         % field_obj.value)

    def test_every_card_declares_what_feeds_the_word(self):
        """Invariant 5."""
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertTrue(puzzle.meta_label.strip())

    def test_the_steps_are_reasoned_not_just_the_result(self):
        """Invariant 6."""
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertGreaterEqual(len(puzzle.steps), 3)

    def test_no_decorative_characters(self):
        """Invariant 8."""
        for difficulty in DIFFICULTIES:
            for seed, puzzle in puzzles_for(difficulty):
                text = " ".join([puzzle.statement, puzzle.title] + puzzle.hints + puzzle.steps)
                with self.subTest(difficulty=difficulty, seed=seed):
                    for character in text:
                        self.assertLess(ord(character), 0x2000)

    def test_the_same_seed_gives_the_same_puzzle(self):
        """Invariant 2, at the level of this generator."""
        for difficulty in DIFFICULTIES:
            for seed in range(50):
                first = diffie_hellman.generate(random.Random(seed), difficulty)
                second = diffie_hellman.generate(random.Random(seed), difficulty)
                with self.subTest(difficulty=difficulty, seed=seed):
                    self.assertEqual([f.value for f in first.fields],
                                     [f.value for f in second.fields])
                    self.assertEqual(first.statement, second.statement)


class MathematicsTest(unittest.TestCase):
    """The answers have to be right, not merely well shaped."""

    def read_given(self, puzzle, label):
        for name, value in puzzle.given:
            if name == label:
                return value
        raise AssertionError("missing %r in %r" % (label, puzzle.given))

    def test_the_shared_key_is_what_both_sides_compute(self):
        for seed, puzzle in puzzles_for(1):
            with self.subTest(seed=seed):
                modulus = int(self.read_given(puzzle, "Campo").lstrip("Z"))
                secret = int(self.read_given(puzzle, "Segreto di Alice").split("=")[1])
                public_b = int(self.read_given(puzzle, "Pubblico di Bob").split("=")[1])
                self.assertEqual(int(puzzle.fields[0].value), pow(public_b, secret, modulus))

    def test_the_discrete_log_solves_its_own_equation(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                modulus = int(self.read_given(puzzle, "Campo").lstrip("Z"))
                base = int(self.read_given(puzzle, "Generatore").split("=")[1])
                target = int(self.read_given(puzzle, "Valore").split("=")[1])
                exponent = int(puzzle.fields[0].value)
                self.assertEqual(pow(base, exponent, modulus), target)

    def test_the_discrete_log_base_is_a_generator(self):
        for seed, puzzle in puzzles_for(2):
            with self.subTest(seed=seed):
                modulus = int(self.read_given(puzzle, "Campo").lstrip("Z"))
                base = int(self.read_given(puzzle, "Generatore").split("=")[1])
                self.assertTrue(diffie_hellman.is_primitive_root(base, modulus))

    def test_exactly_one_candidate_is_a_primitive_root(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                modulus = int(self.read_given(puzzle, "Campo").lstrip("Z"))
                candidates = [int(t) for t in self.read_given(puzzle, "Candidati").split(" e ")]
                generators = [c for c in candidates
                              if diffie_hellman.is_primitive_root(c, modulus)]
                self.assertEqual(len(generators), 1)
                self.assertEqual(generators[0], int(puzzle.fields[0].value))

    def test_the_reported_order_is_the_real_order(self):
        for seed, puzzle in puzzles_for(3):
            with self.subTest(seed=seed):
                modulus = int(self.read_given(puzzle, "Campo").lstrip("Z"))
                candidates = [int(t) for t in self.read_given(puzzle, "Candidati").split(" e ")]
                other = [c for c in candidates
                         if not diffie_hellman.is_primitive_root(c, modulus)][0]
                order = int(puzzle.fields[1].value)
                self.assertEqual(order, len(set(diffie_hellman.power_table(other, modulus))))
                self.assertEqual((modulus - 1) % order, 0, "an order must divide p-1")
                self.assertEqual(pow(other, order, modulus), 1)


class NotRegisteredTest(unittest.TestCase):
    """Invariant 2 at the level of the fascicle: registering this would rewrite the past."""

    def test_the_fascicle_still_builds_nine_cards(self):
        from crypto_puzzles.fascicle import GENERATORS, build_issue
        self.assertNotIn(diffie_hellman, GENERATORS)
        self.assertEqual(len(build_issue("2026-W33").puzzles), 9)


if __name__ == "__main__":
    unittest.main()
