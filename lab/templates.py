#!/usr/bin/env python3
"""BV-250 / CTO-61 §2.2, step 1: write an agent's macOS template from the
web's published data at a fixed commit, and one capture per file (its path
and content).

usage: templates.py AGENT WEB_COMMIT HOME OUT_DIR

The blocks come from `templates.macos.blocks` of
observatory/data/agents/<agent>.json in qtorb/rosmarops-web at WEB_COMMIT.
A file starting with ~/ goes under HOME; any other is relative to
HOME/proyecto. The files are written as the test account (sudo -u) when it
is not the runner account.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

agent, commit, home, out = sys.argv[1:5]
if not re.fullmatch(r"[0-9a-f]{40}", commit):
    sys.exit("web_commit must be a full 40-character commit")
url = f"https://raw.githubusercontent.com/qtorb/rosmarops-web/{commit}/observatory/data/agents/{agent}.json"
with urllib.request.urlopen(url, timeout=30) as r:
    data = json.load(r)
tpl = data["templates"]["macos"]
if tpl.get("kind") != "agent_sandbox" or not tpl.get("blocks"):
    sys.exit(f"{agent}: no agent_sandbox template for macOS at {commit}")

user = os.environ["LAB_USER"]
me = subprocess.run(["id", "-un"], capture_output=True, text=True, check=True).stdout.strip()


def write_as_user(path, content):
    cmd = ["/bin/sh", "-c", 'mkdir -p "$(dirname "$1")" && cat > "$1"', "sh", path]
    if user != me:
        cmd = ["sudo", "-u", user, "-H"] + cmd
    subprocess.run(cmd, input=content, text=True, check=True)


os.makedirs(out, exist_ok=True)
for n, block in enumerate(tpl["blocks"], 1):
    shown = block["file"]
    if shown.startswith("~/"):
        path = os.path.join(home, shown[2:])
    else:
        shown = "~/proyecto/" + shown
        path = os.path.join(home, "proyecto", block["file"])
    content = block["value"].rstrip("\n") + "\n"
    write_as_user(path, content)
    name = f"{agent}-macos-1-fichero{n}-despues"
    with open(os.path.join(out, name + ".txt"), "w") as f:
        f.write(f"$ cat {shown}\n{content}")
    with open(os.path.join(out, name + ".entry.json"), "w") as f:
        json.dump({
            "agent": agent, "os": "macos", "step": 1, "test": f"fichero{n}", "phase": "despues",
            "command": f"cat {shown}", "result": "concluyente", "file": shown,
        }, f)
    print(f"{name}: {shown}")
