#!/usr/bin/env bash
# Wraps the page fragment in a full HTML document for static hosting (e.g. GitHub Pages from /docs).
set -euo pipefail
cd "$(dirname "$0")/.."
{
  printf '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n'
  cat src/planner.html
  printf '\n</body></html>\n'
} > docs/index.html
echo "wrote docs/index.html"
