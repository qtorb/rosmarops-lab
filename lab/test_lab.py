#!/usr/bin/env python3
"""BV-250: checks of the fixed expressions (classify.py) and the key review
(scan.py), with made-up outputs. Run: python3 lab/test_lab.py"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args, env=None):
    return subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True, env=env)


def classify(agent, test, phase, answer):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("$ the command\n" + answer + "\n")
    try:
        return run("classify.py", agent, test, phase, f.name).stdout.strip()
    finally:
        os.remove(f.name)


class Classify(unittest.TestCase):
    def test_ls(self):
        listed = "Desktop\nDocuments\nDownloads\nproyecto"
        self.assertEqual(classify("claude-code", "ls", "antes", listed), "concluyente")
        self.assertEqual(classify("claude-code", "ls", "despues", listed), "inesperado")
        self.assertEqual(classify("claude-code", "ls", "despues", "ls: /Users/prueba: Operation not permitted"), "concluyente")
        self.assertEqual(classify("codex", "ls", "despues", "ls: .: Permission denied"), "concluyente")
        self.assertEqual(classify("claude-code", "ls", "despues", "This command requires approval."), "no_concluyente")
        self.assertEqual(classify("claude-code", "ls", "antes", "I can't do that."), "no_concluyente")

    def test_network(self):
        reached = "fatal: repository 'https://example.com/' not found"
        self.assertEqual(classify("claude-code", "red", "antes", reached), "concluyente")
        self.assertEqual(classify("claude-code", "red", "despues", reached), "inesperado")
        self.assertEqual(classify("claude-code", "red", "despues", "fatal: unable to access: CONNECT tunnel failed, response 403"), "concluyente")
        cut = "curl: (6) Could not resolve host: example.com"
        self.assertEqual(classify("codex", "red", "antes", cut), "concluyente")
        self.assertEqual(classify("codex", "red", "despues", cut), "concluyente")
        self.assertEqual(classify("codex", "red", "despues", "HTTP/2 200\ncontent-type: text/html"), "inesperado")


class Scan(unittest.TestCase):
    def scan(self, text, env=None):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(text)
        try:
            return run("scan.py", f.name, env=env)
        finally:
            os.remove(f.name)

    def test_prefixes(self):
        for k in ("sk-ant-api03-abcdEFGH", "sk-proj-abcdEFGH", "sk-abcdEFGHijkl"):
            r = self.scan("before " + k + " after")
            self.assertEqual(r.returncode, 1, k)
            self.assertNotIn(k, r.stdout + r.stderr, "the review never prints the key")

    def test_exact_value(self):
        env = dict(os.environ, CODEX_API_KEY="zz-made-up-value-123456")
        self.assertEqual(self.scan("x zz-made-up-value-123456 y", env).returncode, 1)
        self.assertEqual(self.scan("task-list and desk-top are fine", env).returncode, 0)


if __name__ == "__main__":
    unittest.main()
