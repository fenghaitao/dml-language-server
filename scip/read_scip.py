"""
read_scip.py — explore a .scip index produced by the DML language server (dfa).

Usage:
    uv run --project scip scip/read_scip.py [path/to/index.scip] [output.md]

If no path is given, defaults to index.scip in the current directory.
If output.md is given, writes markdown there; otherwise prints to stdout.

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
    """Return (definitions, references, relationships, enclosing_ranges) dicts keyed by symbol string.

    relationships: sym -> list of (related_symbol, rel_type)
      where rel_type is one of: "implementation", "reference", "type_definition", "definition"
    enclosing_ranges: sym -> (path, [startLine, startChar, endLine, endChar])
      Only populated when the DLS emits enclosing_range on definition occurrences.
    """
    definitions:     dict[str, tuple[str, int]] = {}
    references:      dict[str, list[tuple[str, int]]] = {}
    relationships:   dict[str, list[tuple[str, str]]] = {}  # sym -> [(rel_sym, rel_type)]
    enclosing_ranges: dict[str, tuple[str, list[int]]] = {}  # sym -> (path, range)

    for doc in index.documents:
        path = doc.relative_path
        # Collect relationships from SymbolInformation entries in this document
        for sym_info in doc.symbols:
            for rel in sym_info.relationships:
                rel_type = (
                    "implementation" if rel.is_implementation else
                    "reference"      if rel.is_reference      else
                    "type_definition" if rel.is_type_definition else
                    "definition"
                )
                relationships.setdefault(sym_info.symbol, []).append(
                    (rel.symbol, rel_type)
                )
        for occ in doc.occurrences:
            sym  = occ.symbol
            line = occ.range[0]
            if occ.symbol_roles & ROLE_DEFINITION:
                definitions[sym] = (path, line)
                # enclosing_range: 3-element [sl, sc, ec] or 4-element [sl, sc, el, ec]
                if occ.enclosing_range:
                    enclosing_ranges[sym] = (path, list(occ.enclosing_range))
            else:
                references.setdefault(sym, []).append((path, line))

    # Also collect relationships from external_symbols
    for sym_info in index.external_symbols:
        for rel in sym_info.relationships:
            rel_type = (
                "implementation" if rel.is_implementation else
                "reference"      if rel.is_reference      else
                "type_definition" if rel.is_type_definition else
                "definition"
            )
            relationships.setdefault(sym_info.symbol, []).append(
                (rel.symbol, rel_type)
            )

    return definitions, references, relationships, enclosing_ranges


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

def fmt_range(r: list[int]) -> str:
    """Format a SCIP range [sl, sc, ec] or [sl, sc, el, ec] as a human-readable span."""
    if len(r) == 3:
        return f"{r[0]+1}:{r[1]+1}-{r[2]+1}"
    if len(r) == 4:
        return f"{r[0]+1}:{r[1]+1}-{r[2]+1}:{r[3]+1}"
    return str(r)


def find_and_print(
    fragment: str,
    definitions: dict,
    references: dict,
    relationships: dict,
    enclosing_ranges: dict,
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
        # enclosing_range — full AST span of the definition node
        if sym in enclosing_ranges:
            enc_path, enc_r = enclosing_ranges[sym]
            print(f"  Enclosing range: {enc_path}  {fmt_range(enc_r)}")
        else:
            print(f"  Enclosing range: (not emitted by DLS)")
        # relationships — templates this object implements
        rels = relationships.get(sym, [])
        if rels:
            print(f"  Relationships ({len(rels)}):")
            for rel_sym, rel_type in rels:
                print(f"    [{rel_type}] {short_name(rel_sym)}  ({rel_sym})")
        print(f"  References ({len(refs)} sites):")
        for ref_path, ref_line in refs[:6]:
            print(f"    {ref_path}:{ref_line + 1}")
        print()


def main():
    scip_path = sys.argv[1] if len(sys.argv) > 1 else "index.scip"
    out_path  = sys.argv[2] if len(sys.argv) > 2 else None

    index = load_index(scip_path)

    # Split documents into workspace vs system DML
    def is_workspace_doc(doc) -> bool:
        p = doc.relative_path
        return "simics-project/modules" in p or p.startswith("modules/")

    workspace_docs = sorted([d for d in index.documents if is_workspace_doc(d)],
                             key=lambda d: d.relative_path)
    system_docs    = sorted([d for d in index.documents if not is_workspace_doc(d)],
                             key=lambda d: d.relative_path)

    definitions, references, relationships, enclosing_ranges = build_maps(index)
    kinds = Counter(symbol_kind(s) for s in definitions)

    lines: list[str] = []
    def h(level: int, text: str):
        lines.append(f"{'#' * level} {text}\n")
    def p(*args):
        lines.append(" ".join(str(a) for a in args) + "\n")
    def blank():
        lines.append("\n")
    def row(*cells):
        lines.append("| " + " | ".join(str(c) for c in cells) + " |\n")
    def sep(*widths):
        lines.append("| " + " | ".join("-" * w for w in widths) + " |\n")
    def code(text: str):
        lines.append(f"`{text}`")
        return lines[-1]

    tool = index.metadata.tool_info
    h(1, f"SCIP Index — {scip_path}")
    p(f"**Tool:** {tool.name} {tool.version}")
    blank()

    # ── Documents ────────────────────────────────────────────────────
    h(2, f"Documents ({len(index.documents)} total)")
    h(3, f"Workspace ({len(workspace_docs)} files)")
    row("File", "Occurrences")
    sep(60, 11)
    for doc in workspace_docs:
        row(f"`{doc.relative_path}`", doc.occurrences.__len__())
    blank()

    h(3, f"System DML ({len(system_docs)} files)")
    row("File", "Occurrences")
    sep(60, 11)
    for doc in system_docs:
        path = doc.relative_path
        marker = "/dml/"
        short = path[path.index(marker) + 1:] if marker in path else path
        row(f"`{short}`", doc.occurrences.__len__())
    blank()

    # ── Symbol summary ───────────────────────────────────────────────
    h(2, f"Symbols ({len(definitions)} defined, {len(references)} referenced)")
    row("Kind", "Count")
    sep(12, 6)
    for kind, count in sorted(kinds.items()):
        row(kind, count)
    blank()

    # ── Methods ──────────────────────────────────────────────────────
    h(2, "Methods")
    method_syms = [(s, d) for s, d in definitions.items()
                   if symbol_kind(s) == "method" and not s.startswith("local ")]
    for sym, (def_path, def_line) in sorted(method_syms, key=lambda x: short_name(x[0])):
        refs = references.get(sym, [])
        rels = [rs for rs, rt in relationships.get(sym, [])
                if not short_name(rs).startswith("_")]
        h(4, f"`{short_name(sym)}`")
        p(f"- **Symbol:** `{sym}`")
        p(f"- **Defined:** `{def_path}:{def_line + 1}`")
        if sym in enclosing_ranges:
            enc_path, enc_r = enclosing_ranges[sym]
            p(f"- **Enclosing range:** `{enc_path}` {fmt_range(enc_r)}")
        if rels:
            p(f"- **Implements:** " + ", ".join(f"`{short_name(r)}`" for r in rels))
        if refs:
            p(f"- **References ({len(refs)}):** " +
              ", ".join(f"`{rp}:{rl+1}`" for rp, rl in refs[:6]) +
              (f" … +{len(refs)-6}" if len(refs) > 6 else ""))
        blank()

    # ── Templates ────────────────────────────────────────────────────
    h(2, "Templates")
    templ_syms = [(s, d) for s, d in definitions.items()
                  if symbol_kind(s) == "template"]
    for sym, (def_path, def_line) in sorted(templ_syms, key=lambda x: short_name(x[0])):
        refs = references.get(sym, [])
        h(4, f"`{short_name(sym)}`")
        p(f"- **Symbol:** `{sym}`")
        p(f"- **Defined:** `{def_path}:{def_line + 1}`")
        if refs:
            p(f"- **References ({len(refs)}):** " +
              ", ".join(f"`{rp}:{rl+1}`" for rp, rl in refs[:6]) +
              (f" … +{len(refs)-6}" if len(refs) > 6 else ""))
        blank()

    # ── Cross-file references ─────────────────────────────────────────
    h(2, "Cross-file References")
    cross_found = False
    for sym, (def_path, def_line) in sorted(definitions.items(), key=lambda x: x[1]):
        if symbol_kind(sym) not in ("method", "object"):
            continue
        refs = references.get(sym, [])
        cross = [(p, l) for p, l in refs if p != def_path]
        if not cross:
            continue
        cross_found = True
        p(f"- **[{symbol_kind(sym)}]** `{short_name(sym)}` — "
          f"defined `{def_path}:{def_line + 1}`")
        for cp, cl in cross:
            p(f"  - ← `{cp}:{cl + 1}`")
    if not cross_found:
        p("_(none)_")
    blank()

    # ── Relationships ─────────────────────────────────────────────────
    h(2, "Relationships")
    all_rels = [(sym, rel_sym, rel_type)
                for sym, rels in relationships.items()
                for rel_sym, rel_type in rels]
    rel_counts = Counter(rt for _, _, rt in all_rels)
    row("Type", "Count")
    sep(20, 6)
    for rt, count in sorted(rel_counts.items()):
        row(rt, count)
    blank()

    impl_rels = [(sym, rel_sym)
                 for sym, rel_sym, rel_type in all_rels
                 if rel_type == "implementation"
                 and not short_name(rel_sym).startswith("_")]
    by_obj: dict[str, list[str]] = {}
    for sym, rel_sym in impl_rels:
        by_obj.setdefault(sym, []).append(rel_sym)

    if by_obj:
        row("Object", "Location", "Implements")
        sep(30, 40, 60)
        for sym in sorted(by_obj):
            def_path, def_line = definitions.get(sym, ("?", -1))
            templates = ", ".join(f"`{short_name(r)}`" for r in by_obj[sym])
            row(f"`{short_name(sym)}`", f"`{def_path}:{def_line + 1}`", templates)
    blank()

    # ── Enclosing ranges ──────────────────────────────────────────────
    h(2, "Enclosing Ranges")
    if not enclosing_ranges:
        p("_(none — DLS does not currently emit `enclosing_range`)_")
    else:
        row("Symbol", "Location", "Span")
        sep(30, 50, 20)
        for sym in sorted(enclosing_ranges):
            enc_path, enc_r = enclosing_ranges[sym]
            row(f"`{short_name(sym)}`", f"`{enc_path}`", fmt_range(enc_r))
    blank()

    # ── External symbols ──────────────────────────────────────────────
    h(2, f"External Symbols ({len(index.external_symbols)})")
    if not index.external_symbols:
        p("_(none — all imported files are included as documents)_")
        p("_`gen_scip.sh` uses `--workspace /` so system DML files appear as documents above._")
    else:
        ext_kinds = Counter(symbol_kind(s.symbol) for s in index.external_symbols)
        row("Kind", "Count")
        sep(12, 6)
        for kind, count in sorted(ext_kinds.items()):
            row(kind, count)
        blank()
        used_externals = [s for s in index.external_symbols if s.symbol in references]
        p(f"**{len(used_externals)} referenced in docs** | "
          f"{len(index.external_symbols) - len(used_externals)} unreferenced")
        blank()
        for sym_info in sorted(used_externals, key=lambda s: s.symbol):
            kind = symbol_kind(sym_info.symbol)
            name = short_name(sym_info.symbol)
            refs = references[sym_info.symbol]
            h(4, f"`{name}` ({kind}, {len(refs)} refs)")
            p(f"- **Symbol:** `{sym_info.symbol}`")
            for ref_path, ref_line in refs[:5]:
                p(f"  - ← `{ref_path}:{ref_line + 1}`")
            if len(refs) > 5:
                p(f"  - … and {len(refs) - 5} more")
            blank()

    # ── Write output ──────────────────────────────────────────────────
    content = "".join(lines)
    if out_path:
        Path(out_path).write_text(content)
        print(f"Written: {out_path}")
    else:
        sys.stdout.write(content)


if __name__ == "__main__":
    main()
