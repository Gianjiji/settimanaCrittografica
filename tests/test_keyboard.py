"""Keyboard flow: Enter submits from every field, and focus lands where it is needed.

The gates run without a browser, so the browser behaviour itself cannot be driven here.
What these tests pin is the markup contract that makes Enter work, and the client code
that moves focus. The behaviour in a real browser still needs a human look.
"""

import os
import sys
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from crypto_puzzles.fascicle import current_issue_id

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FormCollector(HTMLParser):
    """Collects each form with the controls that sit inside it."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self.stack = []
        self.loose_inputs = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            form = {"attrs": attributes, "inputs": [], "buttons": []}
            self.forms.append(form)
            self.stack.append(form)
        elif tag == "input":
            if self.stack:
                self.stack[-1]["inputs"].append(attributes)
            else:
                self.loose_inputs.append(attributes)
        elif tag == "button":
            if self.stack:
                self.stack[-1]["buttons"].append(attributes)

    def handle_endtag(self, tag):
        if tag == "form" and self.stack:
            self.stack.pop()


def forms_of(html):
    collector = FormCollector()
    collector.feed(html)
    return collector


class EnterSubmitsTest(unittest.TestCase):
    """A form submits on Enter only when it carries a submit button."""

    def setUp(self):
        self.client = app.test_client()
        self.issue_id = current_issue_id()
        html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.collector = forms_of(html)
        self.answer_forms = [f for f in self.collector.forms
                             if "risposta" in f["attrs"].get("class", "")]

    def test_the_page_has_one_form_per_card_plus_the_word(self):
        self.assertEqual(len(self.answer_forms), 10)

    def test_every_answer_form_has_a_submit_button(self):
        for index, form in enumerate(self.answer_forms):
            with self.subTest(form=index):
                submits = [b for b in form["buttons"] if b.get("type") == "submit"]
                self.assertEqual(len(submits), 1,
                                 "implicit submission needs exactly one submit button")

    def test_every_answer_form_has_at_least_one_input(self):
        for index, form in enumerate(self.answer_forms):
            with self.subTest(form=index):
                self.assertGreaterEqual(len(form["inputs"]), 1)

    def test_every_input_sits_inside_a_form(self):
        """An input outside its form is never submitted by Enter."""
        self.assertEqual(self.collector.loose_inputs, [])

    def test_every_answer_input_is_a_text_field(self):
        for index, form in enumerate(self.answer_forms):
            for position, field in enumerate(form["inputs"]):
                with self.subTest(form=index, field=position):
                    self.assertEqual(field.get("type", "text"), "text")

    def test_no_input_swallows_the_enter_key(self):
        """A textarea keeps Enter for a newline; answers must never use one."""
        html = self.client.get("/fascicolo/" + self.issue_id).get_data(as_text=True)
        self.assertNotIn("<textarea", html)

    def test_multi_field_cards_still_have_a_single_submit(self):
        multi = [f for f in self.answer_forms if len(f["inputs"]) > 1]
        self.assertTrue(multi, "the sample issue should have a card with two fields")
        for form in multi:
            self.assertEqual(len([b for b in form["buttons"] if b.get("type") == "submit"]), 1)


class FocusHandlingTest(unittest.TestCase):
    """Structural checks on the client: the gates cannot run a browser."""

    def setUp(self):
        with open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8") as handle:
            self.source = handle.read()

    def test_the_client_moves_focus_after_a_failed_check(self):
        self.assertIn(".focus()", self.source)

    def test_the_client_selects_the_text_so_it_can_be_typed_over(self):
        self.assertIn(".select()", self.source)

    def test_a_helper_picks_the_first_wrong_field(self):
        self.assertIn("firstWrongInput", self.source)
        self.assertIn("focusForRetry", self.source)

    def test_focus_is_moved_only_on_failure(self):
        """A correct answer must not yank the focus away from the reader."""
        wrong_branch = self.source.split("data.correct")[1]
        self.assertIn("focusForRetry", wrong_branch)

    def test_the_client_still_writes_only_text(self):
        for construct in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            with self.subTest(construct=construct):
                self.assertNotIn(construct, self.source)


if __name__ == "__main__":
    unittest.main()
