#!/usr/bin/env bash
# Generate scip_pb2.py from scip.proto.
# Run from the scip/ directory:
#
#   bash generate_pb2.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Generating scip_pb2.py ..."
uv run --project "$SCRIPT_DIR" python -m grpc_tools.protoc \
    -I"$SCRIPT_DIR" \
    --python_out="$SCRIPT_DIR" \
    "$SCRIPT_DIR/scip.proto"

echo "Done → scip/scip_pb2.py"
