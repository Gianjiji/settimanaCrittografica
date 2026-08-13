"""Layout at 360 pixels: nothing overflows sideways, and controls are thumb sized.

The gates run without a browser, so these tests work on the two things that decide the
outcome and can be checked without one: the width budget against the longest string the
generators can actually produce, and the declared size of the controls.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_puzzles.fascicle import build_issue, recent_issue_ids

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NARROW_VIEWPORT = 360
# Below 640px the stylesheet drops to a 16px base, which is what these sums use.
NARROW_BASE_PX = 16
# The usual minimum for a comfortable touch target.
MIN_TOUCH_PX = 44
SAMPLE_SIZE = 52


def stylesheet():
    """The stylesheet without comments, which would otherwise glue onto the next selector."""
    with open(os.path.join(ROOT, "static", "style.css"), encoding="utf-8") as handle:
        return re.sub(r"/\*.*?\*/", "", handle.read(), flags=re.S)


def strip_media_blocks(css):
    """Removes @media blocks so the remaining text is the unconditional rules."""
    out = []
    depth = 0
    index = 0
    while index < len(css):
        if css.startswith("@media", index):
            depth = 0
            while index < len(css):
                if css[index] == "{":
                    depth += 1
                elif css[index] == "}":
                    depth -= 1
                    if depth == 0:
                        index += 1
                        break
                index += 1
            continue
        out.append(css[index])
        index += 1
    return "".join(out)


def media_block(css, query):
    """The body of the first @media block whose header contains query."""
    start = css.find("@media")
    while start != -1:
        header_end = css.find("{", start)
        header = css[start:header_end]
        if query in header:
            depth = 0
            index = header_end
            while index < len(css):
                if css[index] == "{":
                    depth += 1
                elif css[index] == "}":
                    depth -= 1
                    if depth == 0:
                        return css[header_end + 1:index]
                index += 1
        start = css.find("@media", start + 1)
    return ""


def declarations(css, selector):
    """The declarations of every rule whose selector list mentions the selector."""
    found = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [s.strip() for s in match.group(1).strip().split(",")]
        if any(s == selector for s in selectors):
            found.append(" ".join(match.group(2).split()))
    return found


def declared_px(declarations_list, prop):
    """The largest declared value of prop, in pixels, across the declarations."""
    best = None
    for body in declarations_list:
        match = re.search(r"(?:^|;)\s*%s\s*:\s*([0-9.]+)(px|rem)" % re.escape(prop), body)
        if not match:
            continue
        value = float(match.group(1))
        if match.group(2) == "rem":
            value *= NARROW_BASE_PX
        best = value if best is None else max(best, value)
    return best


class WidthBudgetTest(unittest.TestCase):
    """The longest unbreakable run of text must fit inside a card at 360 pixels."""

    def content_width(self):
        css = stylesheet()
        body_padding = declared_px(declarations(css, "body"), "padding") or 0
        # The card sets "padding: 1.2rem 1.4rem", so the horizontal half is the second value.
        card = " ".join(declarations(css, ".scheda"))
        match = re.search(r"padding:\s*[0-9.]+rem\s+([0-9.]+)rem", card)
        card_padding = float(match.group(1)) * NARROW_BASE_PX if match else 0
        return NARROW_VIEWPORT - 2 * body_padding - 2 * card_padding - 2

    def longest_token(self):
        longest = ""
        for issue_id in recent_issue_ids(SAMPLE_SIZE):
            issue = build_issue(issue_id)
            if issue is None:
                continue
            for puzzle in issue.puzzles:
                pieces = [puzzle.statement, puzzle.title]
                pieces += [str(value) for _, value in puzzle.given]
                pieces += [f.label for f in puzzle.fields]
                for piece in pieces:
                    for token in piece.split():
                        if len(token) > len(longest):
                            longest = token
        return longest

    def test_the_longest_token_fits_a_narrow_card(self):
        """A monospace glyph is about 0.6em wide, and the data font is 1.02rem."""
        glyph = 1.02 * NARROW_BASE_PX * 0.6
        budget = int(self.content_width() // glyph)
        longest = self.longest_token()
        self.assertLessEqual(
            len(longest), budget,
            "%r is %d characters and does not fit the %d character budget at %dpx"
            % (longest, len(longest), budget, NARROW_VIEWPORT))

    def test_the_card_leaves_room_for_content(self):
        self.assertGreater(self.content_width(), 200)


class NoFixedWideBoxesTest(unittest.TestCase):
    def test_no_rule_declares_a_width_wider_than_the_viewport(self):
        css = stylesheet()
        for match in re.finditer(r"(?:^|[;{])\s*(?:min-)?width\s*:\s*([0-9.]+)(px|rem)", css):
            value = float(match.group(1)) * (1 if match.group(2) == "px" else NARROW_BASE_PX)
            with self.subTest(declaration=match.group(0).strip()):
                self.assertLessEqual(value, NARROW_VIEWPORT)

    def test_narrow_screens_release_the_fixed_label_columns(self):
        """At 9rem the label column would squeeze the field; the media query frees it."""
        narrow = media_block(stylesheet(), "max-width: 640px")
        self.assertIn("flex: none", narrow)
        for selector in (".dati dt", ".risposta label span"):
            with self.subTest(selector=selector):
                self.assertTrue(declarations(narrow, selector),
                                "%s is not relaxed on narrow screens" % selector)


class TouchTargetTest(unittest.TestCase):
    """Fields, buttons and the hint toggles are tapped with a thumb."""

    def setUp(self):
        self.narrow = media_block(stylesheet(), "max-width: 640px")

    def assertTallEnough(self, selector):
        rules = declarations(self.narrow, selector)
        self.assertTrue(rules, "%s has no narrow-screen rule" % selector)
        height = declared_px(rules, "min-height")
        self.assertIsNotNone(height, "%s declares no min-height" % selector)
        self.assertGreaterEqual(
            height, MIN_TOUCH_PX,
            "%s is %spx tall, under the %dpx touch minimum" % (selector, height, MIN_TOUCH_PX))

    def test_answer_fields_are_tall_enough(self):
        self.assertTallEnough(".risposta input")

    def test_verify_buttons_are_tall_enough(self):
        self.assertTallEnough(".risposta button")

    def test_hint_toggles_are_tall_enough(self):
        """The hint summaries are the most tapped controls on the sheet."""
        self.assertTallEnough(".aiuti summary")

    def test_buttons_span_the_width_on_narrow_screens(self):
        self.assertIn("width: 100%", " ".join(declarations(self.narrow, ".risposta button")))


if __name__ == "__main__":
    unittest.main()
