#!/bin/bash
# BV-250 / CTO-61 §2.6: delete the test account's folder and every agent
# state the job could have left, for the test account and the runner. The
# GitHub runner is destroyed afterwards anyway.
set -uo pipefail
for h in "${LAB_HOME:-}" "$HOME"; do
  [ -n "$h" ] || continue
  sudo rm -rf "$h/.claude.json" "$h/.claude" "$h/.codex"
done
if [ -n "${LAB_HOME:-}" ]; then sudo rm -rf "$LAB_HOME"; fi
if [ "${LAB_ACCOUNT:-}" = prueba ]; then sudo sysadminctl -deleteUser prueba >/dev/null 2>&1 || true; fi
echo "cleaned"
