#!/usr/bin/env python3
"""
scip_closure.py — build a bounded, source-grounded "code closure" for a
register/field anchor, using an already-generated SCIP index (`.scip`) instead
of Graphify.

Motivation
----------
srv-pm/conductor-autodml's measure-features pipeline builds one Graphify graph
of the DML device, resolves each feature-contract leaf's `depends_on` anchors
onto graph nodes, then (assemble_evidence.py) walks a depth-bounded closure of
`contains`/`calls` edges from each anchor to assemble the adjudicator's
evidence packet. Graphify's graph is built by its own tree-sitter-based
extraction and does not reason about DML's compiled semantics; for hwrs it
does not work at all (whatever the underlying cause).

`dfa` (the DML language server's analysis engine, the same thing that backs
hover/go-to-definition) already builds this same kind of structural knowledge,
and exports it faithfully as SCIP:

  * `SymbolInformation.relationships[].is_implementation`  -- emitted for every
    `is <template>;` a register/field/bank instantiates, and for every method
    override. This is Graphify's "calls"/"is-a" edge, but derived from the
    compiler's real template-expansion, not lexical guessing.
  * `SymbolInformation.relationships[].is_type_definition`  -- emitted for
    object/port typing relationships.
  * Symbol *namespace nesting* (`ip_disable_resolved_cr_reg#read_register()`)
    -- this is Graphify's "contains" edge: template -> its own methods/params;
    register -> nested fields (`sb_cr.REG.FIELD`).

The one thing SCIP does NOT give for free is cross-file "reopened register"
identity (see find_refs_in_file.py's docstring): the same logical register
may have multiple SCIP symbol strings, one per declaring file. This script
reuses the same *logical path* bridging (the suffix after the last
backtick-quoted file segment) to first collect every DEF site of the anchor
across files, then walks relationships from all of them.

Closure algorithm (mirrors assemble_evidence.py's depth<=2 contract):
  depth 0: every DEF of the anchor itself (register, and its fields if the
           anchor names a register with no field, via logical-path prefix).
  depth 1: templates/relationships attached to any depth-0 symbol
           (`is_implementation`, `is_type_definition`), plus, for any
           depth-0/1 symbol that is a template, its direct members
           (`template#member`) -- params AND methods.
  depth 2 (optional, --depth 2): the same relationship/member walk one more
           hop out from whatever depth 1 added -- e.g. a method a template
           overrides, or a nested type's own template.

For every symbol reached, every one of its DEF occurrences (there can be
several across files for a reopened register) is turned into a source-line
slice by locating the declaration's brace-delimited block (register/field/
bank/method/template bodies are all `NAME ... { ... }` or `NAME(...) { ... }`
constructs) via a generic brace-depth scan starting at the DEF line -- the
same technique as enclosing_method.py, run in reverse (span-from-declaration
instead of enclosing-lookup). Slices are capped at --max-lines and merged when
overlapping in the same file, exactly like assemble_evidence.py's
merge_overlapping_slices, so the output is schema-compatible with its
`code_evidence` list and can be dropped into the same evidence packet.

Usage:
    uv run --project scip scip/scip_closure.py hwrs.scip \\
        --anchor sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0 \\
        --root /path/to/vp --depth 2 --max-lines 40 \\
        --output ip_disable_dword0.evidence.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

sys.path.insert(0, str(Path(__file__).parent))
import scip_pb2  # noqa: E402
from scip_dml import _resolve_kind, dml_short_name  # noqa: E402

ROLE_DEFINITION = scip_pb2.SymbolRole.Value("Definition")

_REG_FIELD_KINDS = {"register", "field"}
_MEMBER_KINDS = {"method", "param", "unknown"}  # params report as "unknown" per _resolve_kind


def load_index(scip_path: str) -> scip_pb2.Index:
    with open(scip_path, "rb") as f:
        idx = scip_pb2.Index()
        idx.ParseFromString(f.read())
    return idx


def logical_path(sym: str) -> str:
    """Suffix after the last backtick-quoted (file) segment -- see
    find_refs_in_file.py for the full rationale. Bridges the same logical
    DML object across files that reopen/extend it.
    """
    idx = sym.rfind("`")
    suffix = sym[idx + 1:] if idx != -1 else sym
    return suffix.lstrip(".")


class SymbolIndex:
    """One-time pass building every lookup the closure walk needs:
    symbol -> SymbolInformation, symbol -> (doc_path, def_line), and
    logical_path -> [symbols] for cross-file bridging.
    """

    def __init__(self, index: scip_pb2.Index):
        self.info: dict[str, scip_pb2.SymbolInformation] = {}
        self.def_loc: dict[str, tuple[str, int]] = {}
        self.by_logical_path: dict[str, list[str]] = defaultdict(list)

        for doc in index.documents:
            for sym_info in doc.symbols:
                self.info[sym_info.symbol] = sym_info
                self.by_logical_path[logical_path(sym_info.symbol)].append(sym_info.symbol)
            for occ in doc.occurrences:
                if occ.symbol_roles & ROLE_DEFINITION:
                    # first DEF wins; later ones (rare) are still discoverable
                    # via by_logical_path if the caller wants every site.
                    self.def_loc.setdefault(occ.symbol, (doc.relative_path, occ.range[0]))

    def kind(self, sym: str) -> str:
        return _resolve_kind(self.info.get(sym))

    def relationships(self, sym: str) -> list[str]:
        info = self.info.get(sym)
        if not info:
            return []
        return [
            rel.symbol for rel in info.relationships
            if rel.is_implementation or rel.is_type_definition
        ]

    def members(self, template_sym: str) -> list[str]:
        """Direct METHOD members of a template symbol (`tmpl#method().`), i.e.
        Graphify's 'contains' edge from a template to its own behavior.

        Restricted to methods (not param members like `cr_reg`/`fuses_reg`):
        params add little standalone value as separate slices -- they are
        short, and register/field bodies that reference them are sliced as a
        whole anyway. Methods are where behavior lives (per
        assemble_evidence.py's own docstring: "DML registers have no
        outgoing calls; their behavior lives in write_register()/
        read_register() children") and budget is better spent there.
        """
        if not template_sym.endswith("#"):
            return []
        return [
            s for s in self.info
            if s != template_sym and s.startswith(template_sym) and self.kind(s) == "method"
        ]

    def children(self, sym: str) -> list[str]:
        """Register/field nodes nested directly under a register/bank symbol,
        matched by logical-path prefix (e.g. 'sb_cr.REG.' -> 'sb_cr.REG.FIELD.').

        Restricted to register/field kinds: leaf param descendants (`.lsb`,
        `.msb`, `.offset`, `.init_val`, `.anonymized_name`, ...) are not
        walked separately -- their source lines already fall inside the
        parent register/field's own sliced block, so adding them as distinct
        closure members would both double the slice count for no new
        information and starve the symbol budget before it reaches the
        higher-value template/method hops.
        """
        lp = logical_path(sym)
        if not lp.endswith("."):
            return []
        out = []
        for other_lp, syms in self.by_logical_path.items():
            if other_lp != lp and other_lp.startswith(lp):
                # only direct children: exactly one more dotted segment
                remainder = other_lp[len(lp):]
                if remainder.count(".") == 1:
                    out.extend(s for s in syms if self.kind(s) in _REG_FIELD_KINDS)
        return out


def find_anchor_symbols(sidx: SymbolIndex, anchor: str) -> list[str]:
    """Resolve an anchor path (e.g. 'sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0' or
    'sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0.Mc_Stack_Disable') to every SCIP
    symbol (across all declaring files) whose logical path is an exact match.
    """
    target_lp = anchor.rstrip(".") + "."
    return list(sidx.by_logical_path.get(target_lp, []))


def build_closure(sidx: SymbolIndex, anchor_symbols: list[str], depth: int,
                   max_symbols: int = 120) -> dict[str, str]:
    """Breadth-first walk from the anchor's DEF symbols out to `depth` hops of
    relationships/members/children. Returns {symbol: reason} for reporting;
    reason is one of 'anchor', 'child', 'relationship', 'member'.
    """
    collected: dict[str, str] = {s: "anchor" for s in anchor_symbols}
    frontier = list(anchor_symbols)

    for _hop in range(depth + 1):  # +1: depth 0 = anchor's own children/rels
        if len(collected) >= max_symbols:
            break
        next_frontier: list[str] = []
        for sym in frontier:
            if len(collected) >= max_symbols:
                break  # stop mid-hop too, so members/relationships from the
                        # *next* hop aren't starved by one oversized hop
                        # (e.g. a register with 60 leaf-param descendants).
            for child in sidx.children(sym):
                if child not in collected:
                    collected[child] = "child"
                    next_frontier.append(child)
            for rel in sidx.relationships(sym):
                if rel not in collected:
                    collected[rel] = "relationship"
                    next_frontier.append(rel)
            for member in sidx.members(sym):
                if member not in collected:
                    collected[member] = "member"
                    next_frontier.append(member)
        frontier = next_frontier
        if not frontier:
            break

    if len(collected) > max_symbols:
        # keep anchors + first max_symbols others, stable order
        keep = {s: r for s, r in list(collected.items())[:max_symbols]}
        collected = keep
    return collected


def block_span(path: Path, start_line0: int) -> tuple[int, int] | None:
    """Given the 0-indexed line of a declaration (`register NAME {`,
    `method NAME() {`, `template NAME is (...) {`, a bare `param X = ...;`,
    etc.), return the (start, end) 0-indexed inclusive line span of its
    brace-delimited body, or (start_line0, start_line0) for a body-less
    single-line statement (e.g. `param X = Y;`).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    if start_line0 >= len(lines):
        return None

    # Find the char offset of the start of start_line0.
    offset = sum(len(l) + 1 for l in lines[:start_line0])
    n = len(text)
    depth = 0
    i = offset
    opened = False
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
            opened = True
        elif ch == "}":
            depth -= 1
            if opened and depth == 0:
                end_line0 = text.count("\n", 0, i)
                return start_line0, end_line0
        elif ch == ";" and not opened:
            # single-line statement with no body (e.g. `param X = Y;`)
            end_line0 = text.count("\n", 0, i)
            return start_line0, end_line0
        i += 1
    return start_line0, start_line0


def slice_for(root: Path, doc_path: str, start0: int, end0: int, max_lines: int) -> dict | None:
    abs_path = root / doc_path
    try:
        lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    end0 = min(end0, start0 + max_lines - 1, len(lines) - 1)
    text = "\n".join(f"{i + 1}: {lines[i]}" for i in range(start0, end0 + 1))
    return {
        "file": doc_path,
        "lines": f"L{start0 + 1}-L{end0 + 1}",
        "truncated": end0 < min(start0 + max_lines - 1, len(lines) - 1) and end0 - start0 + 1 >= max_lines,
        "text": text,
    }


def merge_overlapping_slices(slices: list[dict]) -> list[dict]:
    by_file: dict[str, list[tuple[int, int, dict]]] = defaultdict(list)
    for s in slices:
        m = re.match(r"^L(\d+)-L(\d+)$", s["lines"])
        if m:
            by_file[s["file"]].append((int(m.group(1)), int(m.group(2)), s))

    merged: list[dict] = []
    for file_path in sorted(by_file):
        groups: list[tuple[int, int, list[dict]]] = []
        for start, end, item in sorted(by_file[file_path], key=lambda r: (r[0], r[1])):
            if groups and start <= groups[-1][1] + 1:
                old_start, old_end, members = groups[-1]
                groups[-1] = (old_start, max(old_end, end), [*members, item])
            else:
                groups.append((start, end, [item]))
        for start, end, members in groups:
            labels = list(dict.fromkeys(m.get("label") for m in members if m.get("label")))
            texts = sorted({m["text"] for m in members}, key=len, reverse=True)
            merged.append({
                "file": file_path,
                "lines": f"L{start}-L{end}",
                "labels": labels,
                "truncated": any(m["truncated"] for m in members),
                "text": texts[0] if texts else "",
            })
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scip_path", help="Path to .scip index file")
    parser.add_argument("--anchor", required=True,
                         help="Logical DML path of the register/field, e.g. "
                              "'sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0' or "
                              "'sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0.Mc_Stack_Disable'")
    parser.add_argument("--root", type=Path, default=None,
                         help="Repo root for resolving doc.relative_path; "
                              "defaults to the SCIP index's own project_root")
    parser.add_argument("--depth", type=int, default=2, help="Relationship/member hops (default 2)")
    parser.add_argument("--max-lines", type=int, default=40, help="Cap per source slice")
    parser.add_argument("--max-symbols", type=int, default=120, help="Safety cap on closure size")
    parser.add_argument("--output", type=Path, default=None, help="Write evidence JSON here")
    args = parser.parse_args()

    index = load_index(args.scip_path)
    root = args.root or Path(url2pathname(urlparse(index.metadata.project_root).path))

    sidx = SymbolIndex(index)
    anchor_symbols = find_anchor_symbols(sidx, args.anchor)
    if not anchor_symbols:
        print(f"No register/field symbols found for anchor '{args.anchor}'", file=sys.stderr)
        sys.exit(1)

    closure = build_closure(sidx, anchor_symbols, args.depth, args.max_symbols)

    print(f"Anchor: {args.anchor}")
    print(f"Anchor DEF sites: {len(anchor_symbols)}")
    print(f"Closure size (depth<={args.depth}): {len(closure)}")
    by_reason: dict[str, int] = defaultdict(int)
    for r in closure.values():
        by_reason[r] += 1
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(by_reason.items())))
    print("=" * 70)

    slices: list[dict] = []
    for sym, reason in closure.items():
        # Report every DEF site of this symbol's *logical path* -- a reopened
        # register/field will have one DEF per declaring file.
        lp = logical_path(sym)
        for candidate in sidx.by_logical_path.get(lp, []):
            loc = sidx.def_loc.get(candidate)
            if not loc:
                continue
            doc_path, def_line0 = loc
            span = block_span(root / doc_path, def_line0)
            if span is None:
                continue
            s = slice_for(root, doc_path, span[0], span[1], args.max_lines)
            if s is None:
                continue
            s["label"] = f"{sidx.kind(candidate)} {dml_short_name(candidate) or candidate} ({reason})"
            slices.append(s)

    merged = merge_overlapping_slices(slices)
    total_lines = sum(len(s["text"].splitlines()) for s in merged)
    print(f"Source slices: {len(slices)} raw -> {len(merged)} merged ({total_lines} lines)")

    for s in sorted(merged, key=lambda x: (x["file"], x["lines"])):
        labels = "; ".join(s["labels"])
        print(f"\n[{s['file']}:{s['lines']}] {labels}{'  (truncated)' if s['truncated'] else ''}")

    if args.output:
        payload = {
            "anchor": args.anchor,
            "closure_symbols": [{"symbol": s, "reason": r, "kind": sidx.kind(s)}
                                 for s, r in closure.items()],
            "code_evidence": merged,
        }
        args.output.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"\nWrote evidence -> {args.output}")


if __name__ == "__main__":
    main()
