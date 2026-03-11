#!/usr/bin/env bash
# gen_scip.sh — run dfa to produce a SCIP index for a module.
#
# Requires bootstrap.sh to have been run first, which sets up the CMake
# build and generates build/dml_compile_commands.json.
#
# Usage (from repo root or simics-project/):
#   bash simics-project/gen_scip.sh <module_name> [output.scip]
#
# Example:
#   bash simics-project/gen_scip.sh wdt
#
set -euo pipefail

# ── args ─────────────────────────────────────────────────────────────────────

MODULE="${1:?Usage: $0 <module_name> [output.scip]}"
SCIP_OUT_ARG="${2:-}"

# ── resolve paths ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SCIP_OUT="${SCIP_OUT_ARG:-${SCRIPT_DIR}/index.scip}"

# Read simics-root from project-paths
SIMICS_ROOT="$(grep '^simics-root:' "$SCRIPT_DIR/.project-properties/project-paths" \
    | awk '{print $2}')"

DML_BASE="$SIMICS_ROOT/linux64/bin/dml"
MODULE_DIR="$SCRIPT_DIR/modules/$MODULE"
CMAKE_BUILD_DIR="$SCRIPT_DIR/build"
COMPILE_INFO="$CMAKE_BUILD_DIR/dml_compile_commands.json"
DFA="$REPO_ROOT/target/release/dfa"
DLS="$REPO_ROOT/target/release/dls"

# ── sanity checks ─────────────────────────────────────────────────────────────

[ -d "$MODULE_DIR" ]  || { echo "ERROR: module dir not found: $MODULE_DIR"; exit 1; }
[ -d "$DML_BASE" ]    || { echo "ERROR: DML base not found: $DML_BASE"; exit 1; }
[ -f "$COMPILE_INFO" ] || { echo "ERROR: $COMPILE_INFO not found — run bootstrap.sh first"; exit 1; }

# ── build dfa/dls if needed ───────────────────────────────────────────────────

if [ ! -f "$DFA" ] || [ ! -f "$DLS" ]; then
    echo "Building dfa/dls (cargo build --release)..."
    cargo build --release --manifest-path "$REPO_ROOT/Cargo.toml"
fi

# ── collect .dml files from CMake JSON (authoritative source list) ────────────
# After CMake runs we extract the top-level DML files for this module from the
# generated JSON, rather than globbing the directory. This matches exactly what
# the build system knows about (imported files like wdt-registers.dml are
# resolved transitively by the DLS, not listed here explicitly).

echo "Module   : $MODULE"
echo "Simics   : $SIMICS_ROOT"

# ── filter compile info to this module ───────────────────────────────────────
# Extract only the entries for this module into a trimmed JSON for dfa.
MODULE_COMPILE_INFO="$CMAKE_BUILD_DIR/dml_compile_commands_${MODULE}.json"
python3 -c "
import json
data = json.load(open('$COMPILE_INFO'))
module_dir = '$MODULE_DIR'
filtered = {k: v for k, v in data.items() if module_dir in k}
print(f'Filtered {len(filtered)} of {len(data)} entries for module $MODULE', flush=True)
import sys; sys.stderr.write('')
json.dump(filtered, open('$MODULE_COMPILE_INFO', 'w'), indent=4)
"
echo "Written  : $MODULE_COMPILE_INFO"

# Extract the DML files for this module from the filtered JSON
mapfile -t DML_FILES < <(python3 -c "
import json
data = json.load(open('$MODULE_COMPILE_INFO'))
for k in sorted(data.keys()):
    print(k)
")

[ ${#DML_FILES[@]} -gt 0 ] || { echo "ERROR: no entries for module '$MODULE' found in $COMPILE_INFO"; exit 1; }
echo "DML files: ${DML_FILES[*]}"

# ── run dfa ───────────────────────────────────────────────────────────────────
# Use / as the workspace root so that system DML files (under $SIMICS_ROOT)
# also become SCIP documents with source locations, rather than external
# symbols. The DLS resolves all transitively imported files automatically;
# we only need to pass the top-level module file(s) explicitly.
# Relative paths in the index will be absolute-looking (e.g.
# nfs/site/.../simics/base/bank.dml) but are still valid SCIP paths.

echo "Running dfa..."
"$DFA" \
    --compile-info "$MODULE_COMPILE_INFO" \
    --workspace / \
    --scip-output "$SCIP_OUT" \
    "$DLS" \
    "${DML_FILES[@]}"

echo "SCIP index: $SCIP_OUT"
