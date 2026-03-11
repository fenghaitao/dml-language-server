#!/usr/bin/env bash
# read_scip.sh — read a SCIP index and dump symbol info as markdown via read_scip.py
#
# Usage (from repo root or simics-project/):
#   bash simics-project/read_scip.sh [path/to/index.scip] [output.md]
#
# Defaults to simics-project/index.scip and simics-project/scip_dump.md.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SCIP_FILE="${1:-${SCRIPT_DIR}/index.scip}"
OUTPUT="${2:-${SCRIPT_DIR}/scip_dump.md}"
SCIP_PY="$REPO_ROOT/scip/read_scip.py"
PYPROJECT="$REPO_ROOT/scip"

[ -f "$SCIP_FILE" ] || { echo "ERROR: index not found: $SCIP_FILE (run gen_scip.sh first)"; exit 1; }
[ -f "$SCIP_PY" ]   || { echo "ERROR: read_scip.py not found: $SCIP_PY"; exit 1; }

echo "Generating scip_pb2.py ..."
bash "$REPO_ROOT/scip/generate_pb2.sh"

uv run --project "$PYPROJECT" "$SCIP_PY" "$SCIP_FILE" "$OUTPUT"
