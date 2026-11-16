#!/bin/bash
# BV-250 / CTO-61 §2.0.3: versions of this job, in OUT_DIR/<agent>-meta.json.
# usage: meta.sh AGENT OUT_DIR WEB_COMMIT
set -euo pipefail
agent=$1 out=$2 commit=$3
# --version needs no key: also recorded in the dry run.
if [ "$agent" = claude-code ]; then
  version=$(claude --version)
else
  version=$(codex --version)
fi
python3 - "$out/$agent-meta.json" <<PY
import json, sys
json.dump({
  "agent": "$agent",
  "agent_version": """$version""".strip(),
  "macos": "$(sw_vers -productVersion) ($(sw_vers -buildVersion))",
  "runner_image": "${ImageVersion:-unknown}",
  "account": "$LAB_ACCOUNT",
  "web_commit": "$commit",
  "dry_run": "${LAB_DRY_RUN:-}" == "1",
  "utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
}, open(sys.argv[1], "w"), indent=2)
PY
cat "$out/$agent-meta.json"
