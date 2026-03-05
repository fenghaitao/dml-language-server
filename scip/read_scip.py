"""
read_scip.py — explore a .scip index produced by the DML language server (dfa).

Usage:
    uv run --project scip scip/read_scip.py [path/to/index.scip]
    # or from inside the scip/ directory:
    uv run read_scip.py [path/to/index.scip]

If no path is given, defaults to index.scip in the current directory.

DML SCIP symbol format:
    dml simics <device_name> . <fully.qualified.path><suffix>

Descriptor suffixes (per DLS SCIP schema):
    .    term  — composite objects, parameters, named values
    #    type  — templates
    ().  method — methods

Prerequisites:
    pip install grpcio-tools
    bash scip/generate_pb2.sh   # generates scip_pb2.py once
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scip_pb2  # noqa: E402  (generated protobuf bindings)


# ── helpers ──────────────────────────────────────────────────────────

ROLE_DEFINITION = scip_pb2.SymbolRole.Value("Definition")


def load_index(scip_path: str) -> scip_pb2.Index:
    with open(scip_path, "rb") as f:
        idx = scip_pb2.Index()
        idx.ParseFromString(f.read())
    return idx


def build_maps(index: scip_pb2.Index):
    """Return (definitions, references) dicts keyed by symbol string."""
    definitions: dict[str, tuple[str, int]] = {}        # sym -> (path, line)
    references:  dict[str, list[tuple[str, int]]] = {}  # sym -> [(path, line)]

    for doc in index.documents:
        path = doc.relative_path
        for occ in doc.occurrences:
            sym  = occ.symbol
            line = occ.range[0]
            if occ.symbol_roles & ROLE_DEFINITION:
                definitions[sym] = (path, line)
            else:
                references.setdefault(sym, []).append((path, line))

    return definitions, references


def symbol_kind(sym: str) -> str:
    """Classify a DML SCIP symbol by its descriptor suffix.

    DML descriptor suffixes (from USAGE.md):
      method    : ends with  ")."   e.g.  device.bank.read().
      template  : ends with  "#"    e.g.  bank#
      term/obj  : ends with  "."    e.g.  device.regs.r1.offset.
      local     : starts with "local "
    """
    if sym.startswith("local "):
        return "local"
    descriptor = sym.split(" ", 4)[-1] if " " in sym else sym
    if descriptor.endswith(")."):
        return "method"
    if descriptor.endswith("#"):
        return "template"
    if descriptor.endswith("."):
        return "object"
    return "other"


def short_name(sym: str) -> str:
    """Extract a readable name from a DML SCIP symbol."""
    # DML format: "dml simics <device> . <path>"
    parts = sym.split(" ", 4)
    descriptor = parts[-1] if len(parts) >= 5 else sym
    # Take the last component of the dotted path
    name = descriptor.rstrip("#().")
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    return name or descriptor


# ── main ─────────────────────────────────────────────────────────────

def find_and_print(
    fragment: str,
    definitions: dict,
    references: dict,
    skip_kinds: tuple = (),
    limit: int = 10,
):
    """Find symbols matching fragment and print their definition + reference sites."""
    matches = [
        (s, d) for s, d in definitions.items()
        if fragment in s and symbol_kind(s) not in skip_kinds
    ]
    if not matches:
        print(f"  (no symbols found matching '{fragment}')\n")
        return
    for sym, (def_path, def_line) in matches[:limit]:
        refs = references.get(sym, [])
        kind = symbol_kind(sym)
        print(f"[{kind}] {short_name(sym)}")
        print(f"  Symbol : {sym}")
        print(f"  Defined: {def_path}:{def_line + 1}")
        print(f"  References ({len(refs)} sites):")
        for ref_path, ref_line in refs[:6]:
            print(f"    {ref_path}:{ref_line + 1}")
        print()


def main():
    scip_path = sys.argv[1] if len(sys.argv) > 1 else "index.scip"

    print(f"Loading {scip_path} ...")
    index = load_index(scip_path)
    print(f"Tool : {index.metadata.tool_info.name} {index.metadata.tool_info.version}")
    print(f"Docs : {len(index.documents)}")
    for doc in index.documents:
        print(f"  {doc.relative_path}  ({len(doc.occurrences)} occurrences)")
    print()

    definitions, references = build_maps(index)

    kinds = Counter(symbol_kind(s) for s in definitions)
    print(f"Symbols: {len(definitions)} defined  |  {len(references)} referenced")
    for kind, count in sorted(kinds.items()):
        print(f"  {kind:<12} {count}")
    print()

    # ── 1. All methods ───────────────────────────────────────────────
    print("=== Methods ===")
    find_and_print(").", definitions, references, skip_kinds=("local",))

    # ── 2. All templates ─────────────────────────────────────────────
    print("=== Templates ===")
    find_and_print("#", definitions, references,
                   skip_kinds=("local", "method", "object"))

    # ── 3. Cross-file references ──────────────────────────────────────
    print("=" * 60)
    print("Cross-file references")
    print("=" * 60)
    for sym, (def_path, def_line) in sorted(definitions.items(),
                                             key=lambda x: x[1]):
        if symbol_kind(sym) not in ("method", "object"):
            continue
        refs = references.get(sym, [])
        cross = [(p, l) for p, l in refs if p != def_path]
        if not cross:
            continue
        print(f"\n  [{symbol_kind(sym)}] {short_name(sym)}  ({def_path}:{def_line + 1})")
        for p, l in cross:
            print(f"    <- {p}:{l + 1}")


if __name__ == "__main__":
    main()
