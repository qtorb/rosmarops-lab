#!/bin/bash
# BV-250: the two tests of one phase (antes or despues) for one agent, then
# the key review of every text written so far (CTO-61 §2.5). The only script
# that runs with the agent's key in its environment.
# usage: tests.sh AGENT PHASE OUT_DIR
set -euo pipefail
here=$(dirname "$0")
agent=$1 phase=$2 out=$3
for test in ls red; do
  "$here/run_test.sh" "$agent" "$test" "$phase" "$out"
done
python3 "$here/scan.py" "$out"/*.txt "$out"/*.json
