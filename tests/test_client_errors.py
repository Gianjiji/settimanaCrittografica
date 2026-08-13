"""A failed check must never look like a wrong answer.

Three outcomes have to stay distinguishable: the answer was checked and is wrong, the
request never reached the server, and the server answered with something unusable. The
gates run without a browser, so these are structural checks on the client source.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def client_source():
    with open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8") as handle:
        return handle.read()


def quoted_strings(source):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', source)


class DistinctMessagesTest(unittest.TestCase):
    def setUp(self):
        self.source = client_source()
        self.strings = quoted_strings(self.source)

    def sentences(self):
        """The strings long enough to be a message shown to the reader."""
        return [s for s in self.strings if len(s) > 20 and " " in s]

    def test_there_are_at_least_three_outcome_messages(self):
        self.assertGreaterEqual(len(self.sentences()), 3)

    def test_every_message_is_distinct(self):
        sentences = self.sentences()
        self.assertEqual(len(sentences), len(set(sentences)),
                         "two outcomes share the same wording")

    def test_the_failure_messages_say_the_answer_was_not_checked(self):
        """Otherwise the reader reads a failed request as a wrong answer."""
        failure = [s for s in self.sentences() if "verificat" in s or "controllat" in s]
        self.assertGreaterEqual(len(failure), 2,
                                "the offline and server messages must both say so")

    def test_no_message_claims_offline_without_knowing(self):
        wrong_answer = [s for s in self.sentences() if "Non torna" in s]
        self.assertTrue(wrong_answer, "the wrong-answer message went missing")
        for message in wrong_answer:
            self.assertNotIn("offline", message.lower())


class RequestHandlingTest(unittest.TestCase):
    def setUp(self):
        self.source = client_source()

    def test_the_http_status_is_checked(self):
        """Without this a 500 falls through and is rendered as a wrong answer."""
        self.assertIn("response.ok", self.source)

    def test_a_network_failure_is_told_apart_from_a_bad_response(self):
        self.assertIn("OFFLINE", self.source)
        self.assertIn("SERVER", self.source)

    def submit_handler(self):
        """The submit handler alone.

        Anchoring on the last .catch in the file would land on the service worker
        registration instead, which is a different concern entirely.
        """
        start = self.source.index('form.addEventListener("submit"')
        end = self.source.index('"serviceWorker" in navigator')
        return self.source[start:end]

    def test_the_catch_branches_on_the_reason(self):
        catch = self.submit_handler().split(".catch(")[-1]
        self.assertIn("OFFLINE", catch,
                      "the catch must distinguish why the check did not happen")

    def test_field_marks_are_cleared_when_the_check_did_not_happen(self):
        """Stale red fields after a failed request would read as a verdict."""
        handler = self.submit_handler()
        tail = handler[handler.rindex(".catch("):]
        self.assertIn("markFields", tail)

    def test_fields_are_never_marked_from_a_failed_request(self):
        self.assertNotIn("markFields(form, data.fields);\n      }).catch", self.source)


class InterfaceTextTest(unittest.TestCase):
    """Invariant 8: no emoji and no decorative characters in the interface."""

    def test_messages_stay_within_plain_text(self):
        for message in quoted_strings(client_source()):
            with self.subTest(message=message):
                for character in message:
                    self.assertLess(ord(character), 0x2000,
                                    "%r contains a decorative character" % message)


if __name__ == "__main__":
    unittest.main()
