"""How `python app.py` listens: this machine only, and never with the debugger exposed.

The debugger is a Python console for whoever can load an error page. It used to be
switched on unconditionally, on every interface, by the one command the README gives.
These tests pin the three things that keep that from coming back: the defaults, the
refusal of debug on a reachable address, and what the real command prints when run.
"""

import os
import re
import subprocess
import sys
import threading
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app as app_module  # noqa: E402
from app import server_settings  # noqa: E402

STARTUP_TIMEOUT = 20.0


class SettingsTest(unittest.TestCase):
    def test_the_defaults_are_local_and_quiet(self):
        self.assertEqual(server_settings({}), ("127.0.0.1", 5000, False))

    def test_the_network_is_a_choice(self):
        self.assertEqual(server_settings({"SETTIMANA_HOST": "0.0.0.0", "SETTIMANA_PORT": "8080"}),
                         ("0.0.0.0", 8080, False))

    def test_debug_is_allowed_on_this_machine(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            with self.subTest(host=host):
                self.assertEqual(server_settings({"SETTIMANA_HOST": host, "SETTIMANA_DEBUG": "1"}),
                                 (host, 5000, True))

    def test_debug_is_refused_on_any_reachable_address(self):
        for host in ("0.0.0.0", "192.168.1.20", "::", "example.org"):
            with self.subTest(host=host):
                with self.assertRaises(SystemExit) as caught:
                    server_settings({"SETTIMANA_HOST": host, "SETTIMANA_DEBUG": "1"})
                self.assertIn("SETTIMANA_DEBUG", str(caught.exception))

    def test_only_an_explicit_yes_turns_debug_on(self):
        for value in ("", "0", "false", "no", "off", "debug", " "):
            with self.subTest(value=value):
                self.assertFalse(server_settings({"SETTIMANA_DEBUG": value})[2])
        for value in ("1", "true", "TRUE", "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(server_settings({"SETTIMANA_DEBUG": value})[2])

    def test_an_empty_host_falls_back_to_this_machine(self):
        self.assertEqual(server_settings({"SETTIMANA_HOST": "  "})[0], "127.0.0.1")

    def test_a_port_that_is_not_a_port_is_refused(self):
        for value in ("abc", "", "70000", "-1", "80.5"):
            with self.subTest(port=value):
                with self.assertRaises(SystemExit):
                    server_settings({"SETTIMANA_PORT": value})


class SourceTest(unittest.TestCase):
    """Structural, like the checks on the client: the old line must not come back."""

    def setUp(self):
        with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as handle:
            self.source = handle.read()

    def test_debug_is_never_a_literal_true(self):
        self.assertIsNone(re.search(r"debug\s*=\s*True", self.source))

    def test_no_address_is_hard_wired_into_the_run_call(self):
        run_call = self.source[self.source.rindex("app.run("):]
        self.assertNotIn("0.0.0.0", run_call)


class ErrorPageTest(unittest.TestCase):
    def test_a_server_error_shows_no_source_and_no_console(self):
        real = app_module.recent_issue_ids

        def broken(_count):
            raise RuntimeError("segreto-nel-traceback")

        app_module.recent_issue_ids = broken
        self.addCleanup(setattr, app_module, "recent_issue_ids", real)
        with self.assertLogs(app_module.app.logger, level="ERROR"):  # logged, not shown
            response = app_module.app.test_client().get("/archivio")
        self.assertEqual(response.status_code, 500)
        body = response.get_data(as_text=True)
        for leak in ("segreto-nel-traceback", "Traceback", "debugger", "console"):
            with self.subTest(leak=leak):
                self.assertNotIn(leak, body)


def clean_environment(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SETTIMANA_", "FLASK_"))}
    env.update(extra)
    return env


class RealCommandTest(unittest.TestCase):
    """`python app.py`, the command in the README, run for real."""

    def start(self, **extra):
        process = subprocess.Popen(
            [sys.executable, "app.py"], cwd=ROOT, env=clean_environment(**extra),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.stop, process)
        return process

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()

    def read_until_listening(self, process):
        """Everything printed up to the line that names the address, and the address."""
        lines, found = [], []

        def pump():
            for line in process.stdout:
                lines.append(line)
                match = re.search(r"Running on (http://[^\s]+)", line)
                if match:
                    found.append(match.group(1))
                    return

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        reader.join(STARTUP_TIMEOUT)
        if not found:
            raise AssertionError("the server never said where it listens:\n" + "".join(lines))
        return "".join(lines), found[0]

    def test_it_listens_on_this_machine_with_the_debugger_off(self):
        process = self.start(SETTIMANA_PORT="0")
        banner, address = self.read_until_listening(process)
        self.assertIn("Debug mode: off", banner)
        self.assertTrue(address.startswith("http://127.0.0.1:"), address)
        with urllib.request.urlopen(address + "/archivio", timeout=15) as response:
            self.assertEqual(response.status, 200)

    def test_it_refuses_to_start_with_debug_on_the_network(self):
        process = self.start(SETTIMANA_HOST="0.0.0.0", SETTIMANA_DEBUG="1", SETTIMANA_PORT="0")
        output, _ = process.communicate(timeout=STARTUP_TIMEOUT)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("SETTIMANA_DEBUG", output)
        self.assertNotIn("Running on", output)

    def test_the_request_budget_is_on_unless_switched_off(self):
        """Asked of a fresh process: here the other test modules have switched it off."""
        output = subprocess.run(
            [sys.executable, "-c",
             "from app import app, api_budget;"
             "print(app.config['RATE_LIMIT_ENABLED'], api_budget.burst, api_budget.per_second)"],
            cwd=ROOT, env=clean_environment(), capture_output=True, text=True, timeout=60)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.split()[0], "True")


class ProxyTest(unittest.TestCase):
    """Behind a tunnel the forwarding headers are believed only when told how many hops."""

    SCRIPT = (
        "from app import app\n"
        "c = app.test_client()\n"
        "r = c.get('/archivio', headers={'X-Forwarded-Proto': 'https',"
        " 'X-Forwarded-For': '203.0.113.9'})\n"
        "print(r.headers.get('Set-Cookie', ''))\n"
    )

    def cookie(self, **extra):
        output = subprocess.run([sys.executable, "-c", self.SCRIPT], cwd=ROOT,
                                env=clean_environment(**extra), capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(output.returncode, 0, output.stderr)
        return output.stdout

    def test_forwarded_headers_are_ignored_by_default(self):
        self.assertNotIn("Secure", self.cookie())

    def test_one_declared_hop_makes_the_cookie_secure(self):
        self.assertIn("Secure", self.cookie(SETTIMANA_PROXY_HOPS="1"))

    def test_a_hop_count_that_is_not_a_number_counts_as_none(self):
        self.assertNotIn("Secure", self.cookie(SETTIMANA_PROXY_HOPS="molti"))


class CookieTest(unittest.TestCase):
    def test_the_cookie_is_secure_exactly_when_the_request_is(self):
        client = app_module.app.test_client()
        plain = client.get("/archivio").headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", plain)
        self.assertNotIn("Secure", plain)
        secure = app_module.app.test_client().get(
            "/archivio", base_url="https://localhost").headers.get("Set-Cookie", "")
        self.assertIn("Secure", secure)
        self.assertIn("HttpOnly", secure)


if __name__ == "__main__":
    unittest.main()
