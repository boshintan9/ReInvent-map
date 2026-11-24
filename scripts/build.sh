#!/usr/bin/env bash
# Wraps the page fragment in a full HTML document for static hosting (e.g. GitHub Pages from /docs)
# and copies the map data next to it.
set -euo pipefail
cd "$(dirname "$0")/.."
{
  printf '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n'
  cat src/planner.html
  printf '\n</body></html>\n'
} > docs/index.html
cp src/strip-map.json docs/strip-map.json
echo "wrote docs/index.html and docs/strip-map.json"
