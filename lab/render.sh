#!/bin/bash
# BV-250 / CTO-61 §2.5: draw each reviewed text as a PNG with freeze, from the
# same text (never a live screen). Theme, font size, width and padding fixed,
# so every capture looks the same. Runs only after scan.py passed, in a step
# without keys.
#
# usage: render.sh OUT_DIR
set -euo pipefail
out=$1
for txt in "$out"/*.txt; do
  # The text goes in through stdin: off a terminal (CI), freeze reads stdin
  # and ignores a file argument.
  freeze --language txt --theme github-dark --font.size 14 --line-height 1.3 \
    --wrap 100 --padding 24 --window --border.radius 8 --output "${txt%.txt}.png" < "$txt"
done
ls "$out"/*.png
