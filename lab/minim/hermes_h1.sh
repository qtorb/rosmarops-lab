#!/bin/bash
# BV-310 H1: Hermes Agent with terminal.backend: docker, and where its memory
# and skill_manage tools write (lab/minim/hermes_h1.py). No model and no key:
# the tools are called directly. The job's log is public: this script prints
# only the step ids, ok/fail and the result; pip's output, Hermes's output and
# any error stay in a temporary folder that is neither printed nor uploaded.
#
# usage: hermes_h1.sh OUT_DIR
set -uo pipefail

out=$1
commit=02afb7489e1099a8f21cd307b96b9a648dfb9243 # NousResearch/hermes-agent, read in BV-305
image=python:3.12-slim
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
steps="$work/steps.txt"
facts="$work/facts.txt"
: >"$steps"
: >"$facts"
mkdir -p "$out" "$work/hermes-home" "$work/home"

fact() { echo "$1=$2" >>"$facts"; }

finish() {
  fact utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fact runner_image "${ImageOS:-unknown}-${ImageVersion:-unknown}"
  python3 -I "$here/result.py" H1 "$steps" "$facts" "$out"
  docker ps -aq --filter "label=hermes" 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
  rm -rf "$work"
  exit 0
}

fail() {
  echo "$1 fail" >>"$steps"
  echo "step $1: fail"
  finish
}

fact product hermes-agent
fact source_commit "$commit"
fact docker_image "$image"

# 1. Hermes at the commit read in BV-305, in its own virtual environment.
if ! git clone -q https://github.com/NousResearch/hermes-agent "$work/hermes" >"$work/git.log" 2>&1 ||
  ! git -C "$work/hermes" checkout -q "$commit" >>"$work/git.log" 2>&1; then
  fail install
fi
python3 -m venv "$work/venv" || fail install
if ! "$work/venv/bin/pip" install -q "$work/hermes" >"$work/pip.log" 2>&1; then
  fail install
fi
docker pull -q "$image" >"$work/docker.log" 2>&1 || fail install
fact python_version "$("$work/venv/bin/python" -c 'import platform; print(platform.python_version())')"
echo "install ok" >>"$steps"
echo "step install: ok"

# 2. The tools, with the terminal in a Docker container, an empty
#    environment and nothing but the Hermes home and PATH.
cat >"$work/hermes-home/config.yaml" <<YAML
terminal:
  backend: docker
  docker_image: "$image"
YAML
(cd "$work" && env -i \
  HOME="$work/home" \
  HERMES_HOME="$work/hermes-home" \
  PATH="$work/venv/bin:/usr/bin:/bin" \
  LANG=C.UTF-8 \
  "$work/venv/bin/python" "$here/hermes_h1.py" "$work/hermes" "$steps" "$work/errors.txt") 2>/dev/null
finish
