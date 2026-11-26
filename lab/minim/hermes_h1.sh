#!/bin/bash
# BV-310 H1: Hermes Agent with terminal.backend: docker, and where its memory
# and skill_manage tools write (lab/minim/hermes_h1.py). No model and no key:
# the tools are called directly. The job's log is public: this script prints
# only the step ids, ok/fail and the result; uv's output, Hermes's output and
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

# install_fail STAGE: the install step failed at STAGE (a closed value:
# clone, venv, pip or image), recorded in the result and printed.
install_fail() {
  fact install_failed_at "$1"
  echo "install failed at: $1"
  fail install
}

fact product hermes-agent
fact source_commit "$commit"
fact docker_image "$image"

# 1. Hermes at the commit read in BV-305, in its own virtual environment.
if ! git clone -q https://github.com/NousResearch/hermes-agent "$work/hermes" >"$work/git.log" 2>&1 ||
  ! git -C "$work/hermes" checkout -q "$commit" >>"$work/git.log" 2>&1; then
  install_fail clone
fi
# Hermes pins its dependencies in uv.lock, and at this commit every one of
# them is declared for Python >= 3.14 only: pip on 3.13 installs none of them
# (the third run: import failed, no module ruamel), and pip on 3.14 cannot
# resolve them. `uv sync --frozen` installs exactly the lock, into
# hermes/.venv. uv itself comes from PyPI at a fixed version.
python3 -m pip install -q --target "$work/uv" uv==0.13.10 >"$work/venv.log" 2>&1 || install_fail venv
if ! (cd "$work/hermes" && "$work/uv/bin/uv" sync --frozen --python "$(command -v python3)") >"$work/pip.log" 2>&1; then
  install_fail pip
fi
venv="$work/hermes/.venv"
docker pull -q "$image" >"$work/docker.log" 2>&1 || install_fail image
fact python_version "$("$venv/bin/python" -c 'import platform; print(platform.python_version())')"
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
  PATH="$venv/bin:/usr/bin:/bin" \
  LANG=C.UTF-8 \
  "$venv/bin/python" "$here/hermes_h1.py" "$work/hermes" "$steps" "$work/errors.txt" "$facts") 2>/dev/null
finish
