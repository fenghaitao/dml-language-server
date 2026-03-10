#!/usr/bin/env bash
# bootstrap.sh — set up the Simics project and initialize the CMake build.
#
# Run once from a fresh checkout to get everything ready:
#   bash simics-project/bootstrap.sh
#
# Requires Simics Base to be installed. Set SIMICS_BASE to override the
# default install path.
#
set -euo pipefail

SIMICS_BASE="${SIMICS_BASE:-$HOME/.simics-mcp-server/simics-install/simics-7.57.0}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

[ -d "$SIMICS_BASE" ] || { echo "ERROR: Simics Base not found: $SIMICS_BASE"; echo "Set SIMICS_BASE env var to your install path."; exit 1; }

echo "Simics Base : $SIMICS_BASE"
echo "Project dir : $PROJECT_DIR"

# ── 1. Simics project-setup ───────────────────────────────────────────────────
"$SIMICS_BASE/bin/project-setup" --ignore-existing-files "$PROJECT_DIR"

# ── 2. CMake configure ────────────────────────────────────────────────────────
# CMAKE_EXPORT_COMPILE_COMMANDS=1 is required to enable the
# generate-dml-compile-commands target (see Simics.cmake).
echo "Configuring CMake..."
cmake -S "$PROJECT_DIR" -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=1 \
    -Wno-dev

# ── 3. Generate DML compile commands JSON ────────────────────────────────────
# Produces build/dml_compile_commands.json used by the DLS and gen_scip.sh.
echo "Generating DML compile commands..."
cmake --build "$BUILD_DIR" --target generate-dml-compile-commands

echo ""
echo "Done. Build the wdt module with:"
echo "  cmake --build $BUILD_DIR --target wdt"
echo ""
echo "Generate a SCIP index with:"
echo "  bash $PROJECT_DIR/gen_scip.sh wdt"
