#!/usr/bin/env python3
"""BV-250: checks of the fixed expressions (classify.py) and the key review
(scan.py), with made-up outputs. Run: python3 lab/test_lab.py"""

import hashlib
import json
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


M6_STEPS = ["install", "start", "company", "agents", "wake", "two_running", "pause", "none_running_after_wait"]
M6_FACTS = [
    "product=paperclipai",
    "product_version=2026.1117.0",
    "node_version=v24.11.1",
    "package_sha256=" + "ab" * 32,
    "runner_image=ubuntu24-20261123.1",
    "wait_seconds=60",
    "install_hosts=registry.npmjs.org",
    "outside_connections_running=0",
    "outside_connections_after=0",
    "utc=2026-11-25T18:00:00Z",
]


class MinimResult(unittest.TestCase):
    """BV-301: result.json of the minimum-of-control tests (minim/result.py)."""

    def result(self, steps, facts=M6_FACTS, criterion="M6"):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "steps.txt"), "w") as f:
            f.write("".join(s + "\n" for s in steps))
        with open(os.path.join(d, "facts.txt"), "w") as f:
            f.write("".join(x + "\n" for x in facts))
        r = run(os.path.join("minim", "result.py"), criterion,
                os.path.join(d, "steps.txt"), os.path.join(d, "facts.txt"), d)
        path = os.path.join(d, "result.json")
        doc = json.load(open(path)) if os.path.exists(path) else None
        return r, doc, d

    def test_every_step_ok_is_yes(self):
        r, doc, d = self.result([s + " ok" for s in M6_STEPS])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "M6: yes")
        self.assertEqual(doc["result"], "yes")
        self.assertEqual(doc["criterion"], "M6")
        self.assertEqual(doc["how"], "test")
        self.assertEqual(doc["product_version"], "2026.1117.0")
        self.assertEqual(doc["install_hosts"], ["registry.npmjs.org"])
        self.assertEqual(doc["wait_seconds"], 60)
        data = open(os.path.join(d, "result.json"), "rb").read()
        self.assertEqual(open(os.path.join(d, "result.json.sha256")).read().split()[0],
                         hashlib.sha256(data).hexdigest())

    def test_a_failed_step_is_no(self):
        steps = [s + " ok" for s in M6_STEPS[:-1]] + [M6_STEPS[-1] + " fail"]
        r, doc, _ = self.result(steps)
        self.assertEqual(r.stdout.strip(), "M6: no")
        self.assertEqual(doc["result"], "no")

    def test_stopped_early_is_no(self):
        # paperclip.sh stops at the first failed step: the rest are missing.
        r, doc, _ = self.result(["install ok", "start fail"])
        self.assertEqual(doc["result"], "no")
        self.assertEqual([s["id"] for s in doc["steps"]], ["install", "start"])

    def test_steps_out_of_order_or_twice_are_no(self):
        steps = [s + " ok" for s in M6_STEPS]
        swapped = steps[:]
        swapped[6], swapped[7] = swapped[7], swapped[6]
        self.assertEqual(self.result(swapped)[1]["result"], "no")
        self.assertEqual(self.result(steps + ["pause ok"])[1]["result"], "no")

    def test_unknown_step_or_text_writes_nothing(self):
        for line in ("reboot ok", "pause ok because it said so", "pause maybe"):
            r, doc, _ = self.result([line])
            self.assertEqual(r.returncode, 1, line)
            self.assertIsNone(doc, line)

    def test_a_fact_that_is_not_a_closed_value_writes_nothing(self):
        # Raw output, an address or a key must never reach result.json.
        for bad in ("install_hosts=https://registry.npmjs.org/paperclipai",
                    "product_version=2026.1117.0 (Paperclip says hi)",
                    "package_sha256=nothex",
                    "comment=anything",
                    "outside_connections_after=10.0.0.1"):
            facts = [f for f in M6_FACTS if not f.startswith(bad.split("=")[0] + "=")] + [bad]
            r, doc, _ = self.result([s + " ok" for s in M6_STEPS], facts)
            self.assertEqual(r.returncode, 1, bad)
            self.assertIsNone(doc, bad)

    def test_unknown_criterion_writes_nothing(self):
        r, doc, _ = self.result(["install ok"], criterion="M9")
        self.assertEqual(r.returncode, 1)
        self.assertIsNone(doc)


if __name__ == "__main__":
    unittest.main()
