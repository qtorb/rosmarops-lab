#!/usr/bin/env python3
"""BV-250 / CTO-61 §3: manifest.json of a lab release, from the captures of
both jobs. Each entry: agent, system, step, test, before/after, the exact
command, the result, the agent and macOS versions, the runner image, the UTC
date, the web commit of the template and the SHA-256 of each file.

usage: manifest.py DIR TAG
"""

import glob
import hashlib
import json
import os
import sys

d, tag = sys.argv[1:3]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


metas = {}
for path in glob.glob(os.path.join(d, "*-meta.json")):
    m = json.load(open(path))
    metas[m["agent"]] = m
entries = []
for path in sorted(glob.glob(os.path.join(d, "*.entry.json"))):
    e = json.load(open(path))
    base = path[: -len(".entry.json")]
    m = metas[e["agent"]]
    e.update({
        "agent_version": m["agent_version"], "macos": m["macos"], "runner_image": m["runner_image"],
        "utc": m["utc"], "web_commit": m["web_commit"], "account": m["account"],
        "files": {os.path.basename(base) + ext: sha(base + ext) for ext in (".png", ".txt")},
    })
    entries.append(e)
    os.remove(path)
meta_files = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(d, "*-meta.json")))}
json.dump({"schema": 1, "release": tag, "meta": meta_files, "entries": entries},
          open(os.path.join(d, "manifest.json"), "w"), indent=2, ensure_ascii=False)
print(f"{len(entries)} entries")
