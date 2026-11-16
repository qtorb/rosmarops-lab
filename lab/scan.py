#!/usr/bin/env python3
"""BV-250 / CTO-61 §2.5: before any PNG, look for the keys in every file that
will be published. The exact value of each key in this step's environment is
compared without printing it, and the prefixes sk-ant-, sk-proj- and sk- are
searched. On a hit it fails and names only the file.

usage: scan.py FILE...
"""

import os
import re
import sys

values = [v for v in (os.environ.get("ANTHROPIC_API_KEY", ""), os.environ.get("CODEX_API_KEY", "")) if len(v) >= 8]
prefix = re.compile(r"(?<![A-Za-z0-9])sk-(ant-|proj-)?[A-Za-z0-9_-]{4,}")
bad = []
for path in sys.argv[1:]:
    text = open(path, encoding="utf-8", errors="replace").read()
    if any(v in text for v in values) or prefix.search(text):
        bad.append(path)
for path in bad:
    print(f"::error::possible key in {os.path.basename(path)}; nothing is uploaded")
sys.exit(1 if bad else 0)
