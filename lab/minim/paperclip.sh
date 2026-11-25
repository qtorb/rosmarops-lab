#!/bin/bash
# BV-301 (from the reading BV-300 §1): the minimum of control's M6 on
# Paperclip, «an agent, and every run at once, can be stopped from the
# product». One action, PATCH /api/companies/{id} with status "paused", must
# stop the runs of every agent of the company.
#
# - No model and no key: the two agents use Paperclip's `process` adapter
#   and only run `sleep 600`.
# - Paperclip starts with an empty, explicit environment (env -i), so it
#   inherits nothing from the job.
# - The job's log is public: this script prints only the step ids, ok/fail
#   and the result. Paperclip's own output, npm's output and every API
#   answer stay in a temporary folder that is neither printed nor uploaded.
#
# usage: paperclip.sh OUT_DIR
set -uo pipefail

out=$1
version=2026.1117.0
wait_seconds=60
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
steps="$work/steps.txt"
facts="$work/facts.txt"
: >"$steps"
: >"$facts"
mkdir -p "$out" "$work/home" "$work/pc"
server_pid=""
port=3100

step() { # id ok|fail
  echo "$1 $2" >>"$steps"
  echo "step $1: $2"
}

fact() { echo "$1=$2" >>"$facts"; }

finish() {
  fact utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fact runner_image "${ImageOS:-unknown}-${ImageVersion:-unknown}"
  python3 -I "$here/result.py" M6 "$steps" "$facts" "$out"
  if [ -n "$server_pid" ]; then
    kill -TERM -- "-$server_pid" 2>/dev/null
    sleep 5
    kill -KILL -- "-$server_pid" 2>/dev/null
  fi
  pkill -x sleep 2>/dev/null
  rm -rf "$work"
  exit 0
}

# A failed step ends the test: the steps after it are not recorded, so the
# result is `no`.
fail() {
  step "$1" fail
  finish
}

# api METHOD PATH [JSON] : the answer's body goes to $work/body.json and only
# the HTTP code is returned; nothing of the body is printed.
api() {
  local data=()
  [ $# -ge 3 ] && data=(-H 'Content-Type: application/json' --data "$3")
  curl -sS -o "$work/body.json" -w '%{http_code}' -X "$1" "${data[@]}" \
    "http://127.0.0.1:$port/api$2" 2>/dev/null || echo 000
}

# field NAME : a top-level string field of the last answer.
field() {
  python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))' \
    "$work/body.json" "$1" 2>/dev/null
}

# running_runs COMPANY : how many of the company's runs are `running`.
running_runs() {
  [ "$(api GET "/companies/$1/heartbeat-runs?limit=100")" = 200 ] || { echo -1; return; }
  python3 -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
runs = d if isinstance(d, list) else d.get("runs", d.get("items", []))
print(sum(1 for r in runs if isinstance(r, dict) and r.get("status") == "running"))' \
    "$work/body.json" 2>/dev/null || echo -1
}

sleepers() {
  local n
  # The adapter spawns the resolved path (/usr/bin/sleep 600), with no shell.
  n=$(pgrep -fxc '(.*/)?sleep 600' 2>/dev/null)
  echo "${n:-0}"
}

# outside_connections : established TCP connections of the node and postgres
# processes to any address that is not this machine (a count, no address).
outside_connections() {
  ss -tnpH state established 2>/dev/null | python3 -I -c '
import sys
n = 0
for line in sys.stdin:
    if "\"node\"" not in line and "\"postgres\"" not in line:
        continue
    addrs = [t for t in line.split() if ":" in t and not t.startswith("users:")]
    if len(addrs) < 2:
        continue
    peer = addrs[1].rsplit(":", 1)[0].strip("[]")
    if not (peer.startswith("127.") or peer in ("::1", "::ffff:127.0.0.1")):
        n += 1
print(n)' 2>/dev/null || echo 0
}

fact product paperclipai
fact wait_seconds "$wait_seconds"
fact node_version "$(node --version)"

# 1. Install the exact version from its npm tarball, whose SHA-256 is
#    recorded. npm's http log stays here; only its host names are kept.
if (cd "$work" && npm pack "paperclipai@$version" --silent >pack.txt 2>npm-pack.log); then
  tarball="$work/$(tail -n 1 "$work/pack.txt")"
else
  fail install
fi
[ -f "$tarball" ] || fail install
fact package_sha256 "$(sha256sum "$tarball" | cut -d' ' -f1)"
if ! npm install --prefix "$work/pc" --no-audit --no-fund --loglevel http "$tarball" >"$work/npm.log" 2>&1; then
  fail install
fi
hosts=$(cat "$work/npm-pack.log" "$work/npm.log" | grep -oE 'https?://[A-Za-z0-9.-]+' | sed -E 's#^https?://##' |
  tr '[:upper:]' '[:lower:]' | sort -u | paste -sd, -)
fact install_hosts "$hosts"
installed=$(node -p 'require(process.argv[1]).version' "$work/pc/node_modules/paperclipai/package.json" 2>/dev/null)
[ "$installed" = "$version" ] || fail install
fact product_version "$installed"
step install ok

# 2. Start it with an empty, explicit environment. Telemetry and the update
#    check are switched off by name: Paperclip turns telemetry off by itself
#    when it sees CI variables such as GITHUB_ACTIONS, and env -i removes them.
setsid env -i \
  HOME="$work/home" \
  PATH="$work/pc/node_modules/.bin:$(dirname "$(command -v node)"):/usr/bin:/bin" \
  LANG=C.UTF-8 \
  PAPERCLIP_TELEMETRY_DISABLED=1 \
  DO_NOT_TRACK=1 \
  PAPERCLIP_UPDATE_CHECK=0 \
  paperclipai onboard --yes --no-install-service >"$work/server.log" 2>&1 </dev/null &
server_pid=$!
started=0
for _ in $(seq 1 150); do
  config="$work/home/.paperclip/instances/default/config.json"
  if [ -f "$config" ]; then
    p=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("server", {}).get("port", ""))' "$config" 2>/dev/null)
    [ -n "$p" ] && port=$p
  fi
  if [ "$(api GET /health)" = 200 ]; then started=1; break; fi
  sleep 2
done
[ "$started" = 1 ] || fail start
step start ok

# 3. A company made up for the test.
case "$(api POST /companies '{"name":"RosmarOps lab M6"}')" in 200 | 201) ;; *) fail company ;; esac
company=$(field id)
[ -n "$company" ] || fail company
step company ok

# 4. Two agents with the `process` adapter that only sleep. No model, no key.
#    The adapter runs `command` with `args` and no shell: «sleep 600» as one
#    command would look for a program of that name and fail.
agents=()
for n in 1 2; do
  code=$(api POST "/companies/$company/agents" \
    "{\"name\":\"Sleeper $n\",\"adapterType\":\"process\",\"adapterConfig\":{\"command\":\"sleep\",\"args\":[\"600\"],\"timeoutSec\":900}}")
  case "$code" in 200 | 201) ;; *) fail agents ;; esac
  id=$(field id)
  [ -n "$id" ] || fail agents
  agents+=("$id")
done
step agents ok

# 5. Wake both.
for id in "${agents[@]}"; do
  case "$(api POST "/agents/$id/heartbeat/invoke" '{}')" in 200 | 201 | 202) ;; *) fail wake ;; esac
done
step wake ok

# 6. Two runs `running` and two `sleep 600` processes alive.
ok=0
for _ in $(seq 1 30); do
  runs_seen=$(running_runs "$company")
  sleepers_seen=$(sleepers)
  if [ "$runs_seen" = 2 ] && [ "$sleepers_seen" = 2 ]; then ok=1; break; fi
  sleep 2
done
# Two counts only, so a failure here says which half failed.
[ "$runs_seen" -ge 0 ] 2>/dev/null && fact runs_running_seen "$runs_seen"
fact sleepers_seen "$sleepers_seen"
fact outside_connections_running "$(outside_connections)"
[ "$ok" = 1 ] || fail two_running
step two_running ok

# 7. One action: pause the company.
case "$(api PATCH "/companies/$company" '{"status":"paused"}')" in 200 | 201) ;; *) fail pause ;; esac
step pause ok

# 8. After a fixed wait: no run `running` and no `sleep 600` left.
sleep "$wait_seconds"
fact outside_connections_after "$(outside_connections)"
if [ "$(running_runs "$company")" = 0 ] && [ "$(sleepers)" = 0 ]; then
  step none_running_after_wait ok
else
  step none_running_after_wait fail
fi
finish
