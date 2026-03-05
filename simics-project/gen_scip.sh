#!/usr/bin/env bash
# gen_scip.sh — generate dml_compile_info.json for a module and run dfa to
# produce a SCIP index.
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
COMPILE_INFO="$SCRIPT_DIR/dml_compile_info.json"
DFA="$REPO_ROOT/target/release/dfa"
DLS="$REPO_ROOT/target/release/dls"

# ── sanity checks ─────────────────────────────────────────────────────────────

[ -d "$MODULE_DIR" ]  || { echo "ERROR: module dir not found: $MODULE_DIR"; exit 1; }
[ -d "$DML_BASE" ]    || { echo "ERROR: DML base not found: $DML_BASE"; exit 1; }

# ── build dfa/dls if needed ───────────────────────────────────────────────────

if [ ! -f "$DFA" ] || [ ! -f "$DLS" ]; then
    echo "Building dfa/dls (cargo build --release)..."
    cargo build --release --manifest-path "$REPO_ROOT/Cargo.toml"
fi

# ── collect .dml files ────────────────────────────────────────────────────────

mapfile -t DML_FILES < <(find "$MODULE_DIR" -maxdepth 1 -name "*.dml" | sort)

[ ${#DML_FILES[@]} -gt 0 ] || { echo "ERROR: no .dml files found in $MODULE_DIR"; exit 1; }

echo "Module   : $MODULE"
echo "DML files: ${DML_FILES[*]}"
echo "Simics   : $SIMICS_ROOT"

# ── generate dml_compile_info.json ────────────────────────────────────────────

# Read SIMICS_API from the module Makefile (default 7)
SIMICS_API="$(grep -m1 '^SIMICS_API' "$MODULE_DIR/Makefile" 2>/dev/null \
    | sed 's/.*:=\s*//' | tr -d '[:space:]')"
SIMICS_API="${SIMICS_API:-7}"

INCLUDES=(
    "$DML_BASE/1.4"
    "$DML_BASE/include"
    "$DML_BASE"
    "$DML_BASE/api/$SIMICS_API/1.4"
)

# Build JSON
{
    echo "{"
    first=1
    for f in "${DML_FILES[@]}"; do
        [ "$first" -eq 0 ] && echo ","
        first=0
        printf '  "%s": {\n' "$f"
        printf '    "dmlc_flags": [],\n'
        printf '    "includes": [\n'
        inc_first=1
        for inc in "${INCLUDES[@]}"; do
            [ "$inc_first" -eq 0 ] && echo ","
            inc_first=0
            printf '      "%s"' "$inc"
        done
        printf '\n    ]\n'
        printf '  }'
    done
    echo ""
    echo "}"
} > "$COMPILE_INFO"

echo "Written  : $COMPILE_INFO"

# ── run dfa ───────────────────────────────────────────────────────────────────

echo "Running dfa..."
"$DFA" \
    --compile-info "$COMPILE_INFO" \
    --workspace "$SCRIPT_DIR" \
    --scip-output "$SCIP_OUT" \
    "$DLS" \
    "${DML_FILES[@]}"

echo "SCIP index: $SCIP_OUT"
