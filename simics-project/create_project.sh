#!/usr/bin/env bash
# create_project.sh — set up the Simics project in the current directory.
#
# Run from the directory where you want the project created:
#   bash /path/to/create_project.sh
#
# Requires Simics Base to be installed. Set SIMICS_BASE to override the
# default install path.
#
set -euo pipefail

SIMICS_BASE="${SIMICS_BASE:-$HOME/.simics-mcp-server/simics-install/simics-7.57.0}"
PROJECT_DIR="$(pwd)"

[ -d "$SIMICS_BASE" ] || { echo "ERROR: Simics Base not found: $SIMICS_BASE"; echo "Set SIMICS_BASE env var to your install path."; exit 1; }

echo "Simics Base : $SIMICS_BASE"
echo "Project dir : $PROJECT_DIR"

"$SIMICS_BASE/bin/project-setup" --ignore-existing-files "$PROJECT_DIR"

echo "Done. Build the wdt module with:"
echo "  cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
echo "  cmake --build build --target wdt"
