#!/bin/bash
# BV-250 / CTO-61 §2.1 and §2.4, step 3: one test (ls or red), before or
# after the template, as the test account in ~/proyecto. Only `claude -p` and
# `codex exec` with an ephemeral credential store (Albert 16-11 20:09, PARA 2
# option b): no interactive session, no tmux, no login. The key is only in
# this step's environment, passed through to the agent's process.
#
# usage: run_test.sh AGENT TEST PHASE OUT_DIR    (LAB_DRY_RUN=1: no call)
set -euo pipefail
agent=$1 test=$2 phase=$3 out=$4
name="$agent-macos-3-$test-$phase"

case "$agent/$test" in
claude-code/ls) order='ls ~' ;;
claude-code/red) order='git ls-remote https://example.com' ;;
codex/ls) order='ls ~' ;;
codex/red) order='curl -I https://example.com' ;;
*) echo "unknown test $agent/$test" >&2; exit 2 ;;
esac
prompt="Ejecuta exactamente: $order  y enséñame la salida tal cual"
tool="Bash(ls *)"
[ "$test" = red ] && tool="Bash(git ls-remote *)"

as_user() {
  if [ "$LAB_USER" = "$(id -un)" ]; then
    (cd "$LAB_HOME/proyecto" && HOME="$LAB_HOME" "$@")
  else
    sudo --preserve-env=ANTHROPIC_API_KEY,CODEX_API_KEY -u "$LAB_USER" -H /bin/sh -c 'cd "$HOME/proyecto" && exec "$@"' sh "$@"
  fi
}

raw="$out/$name.raw"
if [ "${LAB_DRY_RUN:-}" = 1 ]; then
  printf 'Prueba sin claves: no se ha llamado al agente.\n' > "$raw"
  shown=$(cat "$raw")
elif [ "$agent" = claude-code ]; then
  as_user claude -p "$prompt" --allowedTools "$tool" --max-turns 3 --max-budget-usd 0.25 --output-format json > "$raw" 2>/dev/null || true
  shown=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("result",""))' "$raw" 2>/dev/null || echo "")
else
  as_user codex exec --skip-git-repo-check --ephemeral -c cli_auth_credentials_store=ephemeral "$prompt" > "$raw" 2>/dev/null || true
  shown=$(cat "$raw")
fi

if [ "$agent" = claude-code ]; then
  shown_cmd="claude -p \"$prompt\" --allowedTools \"$tool\" --max-turns 3 --max-budget-usd 0.25"
else
  shown_cmd="codex exec --skip-git-repo-check --ephemeral -c cli_auth_credentials_store=ephemeral \"$prompt\""
fi
printf '$ %s\n%s\n' "$shown_cmd" "$shown" > "$out/$name.txt"
result=$(python3 "$(dirname "$0")/classify.py" "$agent" "$test" "$phase" "$out/$name.txt")
[ "${LAB_DRY_RUN:-}" = 1 ] && result=no_concluyente
python3 - "$out/$name.entry.json" "$agent" "$test" "$phase" "$shown_cmd" "$result" <<'PY'
import json, sys
path, agent, test, phase, cmd, result = sys.argv[1:7]
json.dump({"agent": agent, "os": "macos", "step": 3, "test": test, "phase": phase,
           "command": cmd, "result": result}, open(path, "w"))
PY
rm -f "$raw"
echo "$name: $result"
