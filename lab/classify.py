#!/usr/bin/env python3
"""BV-250 / CTO-61 §2.4: classify a step-3 capture with fixed expressions.

usage: classify.py AGENT TEST PHASE TEXT_FILE  -> prints the result

After the template (despues):
  concluyente     the error is the sandbox's;
  inesperado      the order worked;
  no_concluyente  anything else: the agent did not run it, answered something
                  else, or the error is a permission prompt or a missing folder.
Before the template (antes), the order is expected to work, so that the
template is what changes it:
  concluyente     the order worked: ls lists the four entries, the network
                  test reaches example.com (an HTTP answer or error, not a
                  connection error);
  inesperado      the order failed: an error of the agent or of the system
                  before any template (then before and after cannot show what
                  the template changes);
  no_concluyente  anything else: the agent did not run it or answered
                  something else.
"""

import re
import sys

agent, test, phase, path = sys.argv[1:5]
text = open(path, encoding="utf-8", errors="replace").read()
# The first line is the command shown; classify the agent's answer only.
answer = text.split("\n", 1)[1] if "\n" in text else ""

LS_LISTED = all(w in answer for w in ("Desktop", "Documents", "Downloads", "proyecto"))
LS_SANDBOX = re.compile(r"Operation not permitted|Permission denied", re.I)
# Claude Code refusing to list a folder outside its working directories, by
# itself, with no template.
LS_BLOCKED = re.compile(r"may only list files in the allowed working director", re.I)
NET_SANDBOX = re.compile(
    r"\b403\b|Forbidden|proxy.{0,40}(refus|denied|block)|(refus|denied|block).{0,40}proxy|"
    r"Could not resolve host|Couldn'?t resolve|Network is unreachable|Operation not permitted|"
    r"Connection refused|Failed to connect|curl: \((6|7)\)",
    re.I,
)
NET_REACHED = re.compile(
    r"HTTP/[0-9.]+ [1-5][0-9][0-9]|repository '[^']*' not found|returned error: [45][0-9][0-9]|"
    r"\b(404|405)\b|not found",
    re.I,
)


def classify():
    if test == "ls":
        worked, sandbox = LS_LISTED, bool(LS_SANDBOX.search(answer))
    else:
        sandbox = bool(NET_SANDBOX.search(answer))
        worked = bool(NET_REACHED.search(answer)) and not sandbox
    if phase == "antes":
        if worked:
            return "concluyente"
        if sandbox or (test == "ls" and LS_BLOCKED.search(answer)):
            return "inesperado"  # it was expected to work before the template
        return "no_concluyente"
    if worked:
        return "inesperado"
    if sandbox:
        return "concluyente"
    return "no_concluyente"  # a permission prompt, a missing folder or another answer


print(classify())
