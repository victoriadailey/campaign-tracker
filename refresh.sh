#!/usr/bin/env bash
# Hard-refresh the dashboard from live data sources (MS API + ad-platform CSVs).
#
# What it does:
#   1. Pulls fresh posts from Measure Studio via the API
#   2. Re-parses any ad-platform CSV supplements in tests/fixtures/
#   3. Re-runs all merge / rollup logic
#   4. Writes viewer/data.js
#   5. Bundles viewer/Pulse_Dashboard_Standalone.html
#   6. Copies the bundle to ~/Desktop (so you can share / open it)
#
# Usage:
#     ./refresh.sh
#     ./refresh.sh --quiet     # suppress per-campaign summary
#
# Hard-refresh the browser (Cmd+Shift+R) after this runs if you have the
# dashboard open at file:// or http://localhost.

set -uo pipefail   # NOT -e — we want to detect refresh's non-zero exit ourselves

cd "$(dirname "$0")"

QUIET=""
[[ "${1:-}" == "--quiet" ]] && QUIET="1"

echo "→ Refreshing data from MS API + supplemental CSVs…"
if [[ -n "$QUIET" ]]; then
  .venv/bin/python -m app.viewer.refresh --exclude usbank --output viewer/data.js > /dev/null
else
  .venv/bin/python -m app.viewer.refresh --exclude usbank --output viewer/data.js
fi
REFRESH_EXIT=$?

# Exit code 2 = MS fetch failed for one+ campaigns. Skip the rebundle so the
# last-good standalone stays on disk and the operator notices.
if [[ "$REFRESH_EXIT" == "2" ]]; then
  echo ""
  echo "✗ MS fetch errors above — SKIPPING rebundle. The Desktop standalone is unchanged."
  echo "  Re-run ./refresh.sh in a minute (transient 5xx usually clears),"
  echo "  or drop a fresh manual CSV in tests/fixtures/ and comment out the"
  echo "  failing campaign's \`measure_studio_group_id\` line in config/campaigns.yaml."
  exit 2
fi

if [[ "$REFRESH_EXIT" != "0" ]]; then
  echo "✗ Refresh failed with exit $REFRESH_EXIT — see output above. Skipping rebundle."
  exit "$REFRESH_EXIT"
fi

echo "→ Rebundling standalone HTML…"
.venv/bin/python -m app.viewer.bundle

echo "→ Copying to Desktop…"
cp viewer/Pulse_Dashboard_Standalone.html ~/Desktop/Pulse_Dashboard_Standalone.html

echo "✓ Done @ $(date '+%I:%M%p'). Hard-refresh the browser to see updates."
