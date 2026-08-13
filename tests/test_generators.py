"""Property tests: every generated puzzle must stay solvable without a calculator."""

import os
import random
import re
import sys
import unittest
from fractions import Fraction
from math import gcd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles import coincidence, rsa_chain, secret_sharing  # noqa: E402
from crypto_puzzles.core import (MAX_PRIVATE_EXPONENT, MAX_PUBLIC_EXPONENT, MAX_RSA_MODULUS,  # noqa: E402
                                 Field, check_field, check_puzzle)
from crypto_puzzles.fascicle import build_issue, parse_issue_id  # noqa: E402

ROUNDS = 400


def numbers_in(text):
    return [int(x) for x in re.findall(r"-?\d+", text)]


class CommonShapeTests(unittest.TestCase):
    def test_every_puzzle_is_well_formed(self):
        for module in (coincidence, rsa_chain, secret_sharing):
            for difficulty in (1, 2, 3):
                for seed in range(ROUNDS):
                    puzzle = module.generate(random.Random(seed), difficulty)
                    self.assertEqual(puzzle.difficulty, difficulty)
                    self.assertEqual(len(puzzle.hints), 3, puzzle.title)
                    self.assertGreaterEqual(len(puzzle.steps), 3, puzzle.title)
                    self.assertTrue(puzzle.fields)
                    self.assertTrue(puzzle.statement.strip())
                    self.assertIsInstance(puzzle.meta_value, int)
                    self.assertTrue(puzzle.meta_label.strip(), puzzle.title)
                    self.assertGreaterEqual(puzzle.meta_value, 0)
                    for field in puzzle.fields:
                        self.assertTrue(str(field.value).strip())
                        self.assertIn(field.kind, ("number", "fraction", "text"))
                    ok, _ = check_puzzle(puzzle, [f.value for f in puzzle.fields])
                    self.assertTrue(ok, "own answer rejected in %s" % puzzle.title)


class CoincidenceTests(unittest.TestCase):
    def test_ic_stays_small(self):
        for seed in range(ROUNDS):
            puzzle = coincidence.generate(random.Random(seed), 1)
            word = puzzle.given[0][1].lower()
            numerator, denominator = coincidence.ic_fraction(word)
            self.assertLessEqual(len(word), 7)
            self.assertGreater(numerator, 0)
            self.assertLessEqual(numerator, 30)
            self.assertEqual(Fraction(puzzle.fields[0].value), Fraction(numerator, denominator))

    def test_mic_matches_definition(self):
        for seed in range(ROUNDS):
            puzzle = coincidence.generate(random.Random(seed), 2)
            a = puzzle.given[0][1].lower()
            b = puzzle.given[1][1].lower()
            numerator, denominator = coincidence.mic_fraction(a, b)
            self.assertGreater(numerator, 0)
            self.assertLessEqual(numerator, 30)
            self.assertEqual(Fraction(puzzle.fields[0].value), Fraction(numerator, denominator))

    def test_kasiski_answer_is_the_gcd(self):
        for seed in range(ROUNDS):
            puzzle = coincidence.generate(random.Random(seed), 3)
            positions = numbers_in(puzzle.given[0][1])
            self.assertEqual(len(positions), 3)
            d1 = positions[1] - positions[0]
            d2 = positions[2] - positions[1]
            self.assertGreater(d1, 0)
            self.assertGreater(d2, 0)
            self.assertEqual(int(puzzle.fields[0].value), gcd(d1, d2))


class RsaTests(unittest.TestCase):
    def test_private_key_puzzle(self):
        for seed in range(ROUNDS):
            puzzle = rsa_chain.generate(random.Random(seed), 1)
            n = int(puzzle.given[0][1])
            e = int(puzzle.given[1][1])
            d = int(puzzle.fields[0].value)
            self.assertLessEqual(n, MAX_RSA_MODULUS)
            self.assertLessEqual(e, MAX_PUBLIC_EXPONENT)
            self.assertLessEqual(d, MAX_PRIVATE_EXPONENT)
            phi = self.phi_of(n)
            self.assertEqual(gcd(e, phi), 1)
            self.assertEqual((e * d) % phi, 1)

    def test_encryption_puzzle(self):
        for seed in range(ROUNDS):
            puzzle = rsa_chain.generate(random.Random(seed), 2)
            n = int(puzzle.given[0][1])
            e = int(puzzle.given[1][1])
            m = int(puzzle.given[2][1])
            c = int(puzzle.fields[0].value)
            d = int(puzzle.fields[1].value)
            self.assertEqual(pow(m, e, n), c)
            self.assertEqual(pow(c, d, n), m % n)
            self.assertLess(len(bin(e)) - 2, 6, "exponent too long for mental work")

    def test_factoring_puzzle(self):
        for seed in range(ROUNDS):
            puzzle = rsa_chain.generate(random.Random(seed), 3)
            n = int(puzzle.given[0][1])
            phi = int(puzzle.given[1][1])
            p = int(puzzle.fields[0].value)
            q = int(puzzle.fields[1].value)
            self.assertLess(p, q)
            self.assertEqual(p * q, n)
            self.assertEqual((p - 1) * (q - 1), phi)

    @staticmethod
    def phi_of(n):
        for p in range(2, n):
            if n % p == 0:
                q = n // p
                return (p - 1) * (q - 1)
        raise AssertionError("modulus is prime")


class SharingTests(unittest.TestCase):
    def test_additive_reconstruction(self):
        for seed in range(ROUNDS):
            puzzle = secret_sharing.generate(random.Random(seed), 1)
            p = int(puzzle.given[0][1][1:])
            shares = [int(x) for x in re.findall(r"=\s*(\d+)", puzzle.given[1][1])]
            secret = int(puzzle.fields[0].value)
            self.assertIn(p, (11, 13))
            self.assertEqual(sum(shares) % p, secret)
            self.assertTrue(0 <= secret < p)

    def test_shamir_consecutive(self):
        for seed in range(ROUNDS):
            puzzle = secret_sharing.generate(random.Random(seed), 2)
            p = int(puzzle.given[0][1][1:])
            y1, y2 = [int(x) for x in re.findall(r"=\s*(\d+)", puzzle.given[1][1])]
            secret = int(puzzle.fields[0].value)
            self.assertEqual((2 * y1 - y2) % p, secret)

    def test_shamir_gapped(self):
        for seed in range(ROUNDS):
            puzzle = secret_sharing.generate(random.Random(seed), 3)
            p = int(puzzle.given[0][1][1:])
            values = numbers_in(puzzle.given[1][1])
            x1, y1, x2, y2 = values
            secret = int(puzzle.fields[0].value)
            slope = ((y2 - y1) * pow(x2 - x1, -1, p)) % p
            self.assertEqual((y1 - slope * x1) % p, secret)
            self.assertNotEqual(x2 - x1, 1)


class FascicleTests(unittest.TestCase):
    def test_issue_structure_and_determinism(self):
        for year in (2024, 2025, 2026, 2027):
            for week in (1, 7, 18, 33, 47, 52):
                issue_id = "%d-W%02d" % (year, week)
                issue = build_issue(issue_id)
                self.assertIsNotNone(issue)
                self.assertEqual(len(issue.puzzles), 9)
                self.assertEqual([p.number for p in issue.puzzles], list(range(1, 10)))
                self.assertEqual(sorted(p.difficulty for p in issue.puzzles),
                                 [1, 1, 1, 2, 2, 2, 3, 3, 3])
                self.assertEqual(len({p.kind for p in issue.puzzles}), 3)
                total = sum(p.meta_value for p in issue.puzzles)
                self.assertNotEqual(issue.meta.shift, 0)
                self.assertEqual(issue.meta.shift, total % 26)
                self.assertEqual(len(issue.meta.ciphertext), len(issue.meta.word))
                again = build_issue(issue_id)
                self.assertEqual([f.value for p in again.puzzles for f in p.fields],
                                 [f.value for p in issue.puzzles for f in p.fields])

    def test_bad_issue_ids(self):
        for bad in ("", "2026", "2026-W00", "2026-W54", "1999-W10", "abc", "2026-Wxx"):
            self.assertIsNone(parse_issue_id(bad))
            self.assertIsNone(build_issue(bad))


class CheckerTests(unittest.TestCase):
    def test_fraction_variants(self):
        field = Field(label="IC", kind="fraction", value="2/21")
        for good in ("2/21", "4/42", " 2 / 21 ", "0.095", "0,095", "IC=2/21"):
            self.assertTrue(check_field(field, good), good)
        for bad in ("3/21", "21/2", "", "due", "0.2"):
            self.assertFalse(check_field(field, bad), bad)

    def test_number_variants(self):
        field = Field(label="d", kind="number", value="23")
        for good in ("23", " 23 ", "d=23", "d = 23"):
            self.assertTrue(check_field(field, good), good)
        for bad in ("32", "2", "", "ventitre"):
            self.assertFalse(check_field(field, bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
