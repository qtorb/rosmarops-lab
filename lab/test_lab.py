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
        self.assertEqual(classify("codex", "red", "antes", reached), "concluyente")
        self.assertEqual(classify("codex", "red", "despues", cut), "concluyente")
        self.assertEqual(classify("codex", "red", "despues", "HTTP/2 200\ncontent-type: text/html"), "inesperado")


    def test_failed_before_the_template(self):
        # The two answers of the first capture (release lab-20261118), as they
        # are: each order failed before the template, which was expected to
        # work, so before and after cannot show what the template changes.
        claude_ls = (
            "No pude mostrarte la salida de `ls ~` porque el comando se bloqueó. Este es el mensaje que devolvió, tal cual:\n\n"
            "```\nls in '/Users/prueba' was blocked. For security, Claude Code may only list files in the allowed working "
            "directories for this session: '/Users/prueba/proyecto'.\n```\n\n"
            "En esta sesión solo puedo listar archivos dentro de `/Users/prueba/proyecto`. Tienes dos opciones:\n\n"
            "- Ejecutarlo tú directamente escribiendo `! ls ~` en el prompt.\n"
            "- Añadir tu carpeta de inicio a los directorios permitidos con `/add-dir ~` y luego pedírmelo otra vez.\n"
        )
        codex_red = (
            "```text\n  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
            "                                 Dload  Upload   Total   Spent    Left  Speed\n"
            "  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0curl: (6) Could not resolve host: example.com\n```\n"
        )
        self.assertEqual(classify("claude-code", "ls", "antes", claude_ls), "inesperado")
        self.assertEqual(classify("codex", "red", "antes", codex_red), "inesperado")
        # After the template the same error is the sandbox's: unchanged.
        self.assertEqual(classify("codex", "red", "despues", codex_red), "concluyente")

    def test_python_listing(self):
        listed = "['Desktop', 'Documents', 'Downloads', 'proyecto']"
        self.assertEqual(classify("claude-code", "ls", "antes", listed), "concluyente")
        self.assertEqual(classify("claude-code", "ls", "despues", "PermissionError: [Errno 1] Operation not permitted: '/Users/prueba'"), "concluyente")


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
