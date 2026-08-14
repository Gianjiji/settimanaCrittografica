"""The service worker: what it keeps, and what it must throw away.

The worker caches whole pages, and the pages now say who solved what. That makes its
housekeeping part of the promise the app makes: a copy kept from before, or a copy kept
too eagerly, is a fascicle showing ticks that are not the reader's.

Read as source, like the other client side tests: there is no JavaScript runtime in the
dependencies, and the structure is what these guarantees live in.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The cache the worker used while a single log served every reader. Pages stored under
# it show whoever answered first, so it must never be the cache in use again.
SHARED_LOG_CACHE = "settimana-crittografica-v1"


class ServiceWorkerTestCase(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "static", "sw.js"), encoding="utf-8") as handle:
            self.source = handle.read()

    def cache_name(self):
        match = re.search(r'var CACHE\s*=\s*"([^"]+)"', self.source)
        self.assertIsNotNone(match, "the worker no longer names its cache")
        return match.group(1)

    def handler(self, event):
        """The body of one addEventListener call, up to the next one."""
        start = self.source.index('addEventListener("%s"' % event)
        rest = self.source[start + 1:]
        next_handler = rest.find("addEventListener(")
        return rest if next_handler == -1 else rest[:next_handler]


class StaleCopiesAreDroppedTest(ServiceWorkerTestCase):
    def test_the_cache_is_named_with_a_version(self):
        self.assertRegex(self.cache_name(), r"-v\d+$",
                         "without a version there is no way to retire a bad cache")

    def test_the_cache_that_held_a_shared_log_is_not_in_use(self):
        """Whoever read the fascicle before still has those pages on disk.

        They were built when one history answered for everybody, so they carry ticks
        belonging to whoever got there first. Naming the cache something else is what
        makes the activate handler below delete them.
        """
        self.assertNotEqual(self.cache_name(), SHARED_LOG_CACHE)

    def test_activation_deletes_every_cache_but_the_current_one(self):
        """The only way the old copies actually go away."""
        activate = self.handler("activate")
        self.assertIn("caches.keys()", activate)
        self.assertIn("caches.delete", activate)
        self.assertIn("!==", activate, "a filter that keeps everything deletes nothing")
        self.assertIn("CACHE", activate)

    def test_the_new_worker_does_not_wait_for_the_old_one_to_be_dismissed(self):
        """A reader who leaves the tab open would keep being served the old cache."""
        self.assertIn("skipWaiting", self.source)
        self.assertIn("clients.claim", self.source)


class FreshPagesWinTest(ServiceWorkerTestCase):
    def test_the_network_is_tried_before_the_cache(self):
        """Cache first would serve last week's fascicle, and last week's progress."""
        fetch = self.handler("fetch")
        self.assertLess(fetch.index("fetch(event.request)"), fetch.index("caches.match"),
                        "the cached copy must be the fallback, not the first answer")

    def test_the_cache_is_only_read_when_the_network_failed(self):
        fetch = self.handler("fetch")
        after_catch = fetch.split(".catch(")[-1]
        self.assertIn("caches.match", after_catch)

    def test_only_reads_are_cached(self):
        """A verdict replayed from cache would be an answer the server never gave."""
        fetch = self.handler("fetch")
        guard = fetch[:fetch.index("event.respondWith")]
        self.assertIn('method !== "GET"', guard)
        self.assertIn("return", guard)


class ServerAgreesTest(unittest.TestCase):
    """The worker's job only works if the server marks the pages as personal."""

    def test_the_pages_are_declared_to_vary_by_cookie(self):
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn('response.vary.add("Cookie")', source)

    def test_the_declaration_does_not_overwrite_one_already_there(self):
        """A proxy in front may have set Vary: Accept-Encoding on the way through.

        Assigning the header instead of adding to it drops that, and a cache is then
        free to hand a gzipped body to a client that never asked for one.
        """
        from flask import Flask

        probe = Flask(__name__)
        with probe.test_request_context("/"):
            response = probe.make_response("x")
            response.headers["Vary"] = "Accept-Encoding"
            response.vary.add("Cookie")
            self.assertIn("Accept-Encoding", response.headers["Vary"])
            self.assertIn("Cookie", response.headers["Vary"])


if __name__ == "__main__":
    unittest.main()
