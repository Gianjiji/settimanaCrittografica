"""On paper the fascicle must stay readable and carry nothing to click.

Browsers do not print background colours by default, so any text that relies on a coloured
box behind it comes out white on white. That, and leftover controls, are what these tests
check, by reading the print block of the stylesheet against the real markup.
"""

import os
import re
import sys
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INTERACTIVE_TAGS = ("button", "input", "select", "textarea", "details", "summary", "form")
WHITE = re.compile(r"color:\s*(#fff\b|#ffffff\b|white\b)")


def stylesheet():
    with open(os.path.join(ROOT, "static", "style.css"), encoding="utf-8") as handle:
        return re.sub(r"/\*.*?\*/", "", handle.read(), flags=re.S)


def block_of(css, header_fragment):
    start = css.find("@media")
    while start != -1:
        brace = css.find("{", start)
        if header_fragment in css[start:brace]:
            depth, index = 0, brace
            while index < len(css):
                if css[index] == "{":
                    depth += 1
                elif css[index] == "}":
                    depth -= 1
                    if depth == 0:
                        return css[brace + 1:index]
                index += 1
        start = css.find("@media", start + 1)
    return ""


def rules(css):
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [s.strip() for s in match.group(1).strip().split(",")]
        yield selectors, " ".join(match.group(2).split())


def hidden_selectors(print_block):
    hidden = set()
    for selectors, body in rules(print_block):
        if "display: none" in body or "display:none" in body:
            hidden.update(selectors)
    return hidden


class Collector(HTMLParser):
    """Records interactive elements together with the classes of their ancestors."""

    VOID = {"input", "br", "img", "meta", "link", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.interactive = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        self.stack.append((tag, classes))
        if tag in INTERACTIVE_TAGS:
            ancestry = set()
            for _, ancestor_classes in self.stack:
                ancestry |= ancestor_classes
            self.interactive.append((tag, attributes.get("class", ""), ancestry))
        if tag in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


class PrintTestCase(unittest.TestCase):
    def setUp(self):
        self.css = stylesheet()
        self.print_block = block_of(self.css, "print")
        self.hidden = hidden_selectors(self.print_block)
        self.client = app.test_client()
        self.issue_id = current_issue_id()

    def pages(self):
        return ("/fascicolo/" + self.issue_id, "/fascicolo/" + self.issue_id + "/soluzioni")

    def collect(self, path):
        collector = Collector()
        collector.feed(self.client.get(path).get_data(as_text=True))
        return collector


class NoControlsOnPaperTest(PrintTestCase):
    def test_the_print_block_exists(self):
        self.assertTrue(self.print_block.strip())
        self.assertTrue(self.hidden)

    def test_the_issue_page_really_has_controls_to_hide(self):
        """Guards the test below from passing because it found nothing."""
        self.assertTrue(self.collect("/fascicolo/" + self.issue_id).interactive)

    def test_every_interactive_element_is_hidden_when_printing(self):
        for path in self.pages():
            collector = self.collect(path)
            for tag, css_class, ancestry in collector.interactive:
                with self.subTest(page=path, tag=tag, css_class=css_class):
                    covered = any("." + name in self.hidden for name in ancestry)
                    self.assertTrue(
                        covered,
                        "<%s class=%r> still prints; no ancestor is hidden by @media print"
                        % (tag, css_class))


class ReadableOnPaperTest(PrintTestCase):
    def selector_is_hidden(self, selector):
        """True when the selector, or one of its ancestor parts, is hidden in print."""
        parts = selector.replace(">", " ").split()
        return any(part in self.hidden for part in parts) or selector in self.hidden

    def test_no_visible_text_depends_on_a_printed_background(self):
        """Backgrounds are dropped by default, so white text becomes invisible."""
        outside_print = self.css.replace(self.print_block, "")
        for selectors, body in rules(outside_print):
            if not WHITE.search(body):
                continue
            for selector in selectors:
                with self.subTest(selector=selector):
                    if self.selector_is_hidden(selector):
                        continue
                    override = [b for s, b in rules(self.print_block)
                                if selector in s and "color:" in b and not WHITE.search(b)]
                    self.assertTrue(
                        override,
                        "%r prints white text on white paper; give it a print colour"
                        % selector)

    def test_the_page_background_is_reset(self):
        body_rules = [b for s, b in rules(self.print_block) if "body" in s]
        self.assertTrue(body_rules)
        self.assertTrue(any("background" in b for b in body_rules),
                        "the squared paper pattern would be printed on every page")

    def test_cards_are_not_split_across_pages(self):
        card = " ".join(b for s, b in rules(self.print_block) if ".scheda" in s)
        self.assertIn("page-break-inside: avoid", card)

    def test_the_masthead_is_not_styled_as_a_link(self):
        """It is an anchor that stays on paper, so it must read as a title."""
        marchio = " ".join(b for s, b in rules(self.css) if ".marchio" in s)
        self.assertIn("text-decoration: none", marchio)


if __name__ == "__main__":
    unittest.main()
