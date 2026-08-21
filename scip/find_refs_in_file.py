#!/usr/bin/env python3
"""
find_refs_in_file.py — find every reference to registers/fields defined in a
given (generated) DML file, across an entire SCIP index.

Typical use case: a hand-written override (e.g. hwrs-ip-disable.dml) *reopens*
a register/field that is (partially) defined in an auto-generated file such as
srv-pm/bt/.../cor_imh2_a0_hwrs_m6_regs.dml — adding the `is <template>;`
relationship and any extra fields. DML allows a bank/register/field to be
declared piecewise across multiple files that are compiled together; the
compiled device merges them into a single logical object.

IMPORTANT: dfa's SCIP backend scopes each symbol's namespace by the *file it
is textually declared in*, so the same logical register/field ends up as two
(or more) distinct SCIP symbol strings — one per file — that only share a
common suffix after the file's backtick-quoted segment, e.g.:

    ... `cor_imh2_a0_hwrs_m6_regs.dml`.sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0.
    ... `hwrs-ip-disable.dml`.sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0.

Matching on the raw symbol string therefore misses cross-file
reopen/reference relationships. This script instead groups symbols by their
*logical path* (the suffix after the last backtick-quoted segment), so all
per-file declarations/uses of "the same" register/field are merged together
before reporting definitions and references.

Usage:
    uv run --project scip scip/find_refs_in_file.py <index.scip> <target_file_substring> \\
        [--field NAME] [--ref-in PATH_SUBSTRING] [--limit N]

Example — show only references located under srv-pm/code/hwrs-gen2:
    uv run --project scip scip/find_refs_in_file.py hwrs.scip \\
        cor_imh2_a0_hwrs_m6_regs.dml --field IP_DISABLE_RESOLVED_CR_DWORD0 \\
        --ref-in srv-pm/code/hwrs-gen2
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

sys.path.insert(0, str(Path(__file__).parent))
import scip_pb2  # noqa: E402  (generated protobuf bindings)
from scip_dml import _resolve_kind, dml_short_name  # noqa: E402
from enclosing_method import enclosing_method  # noqa: E402

ROLE_DEFINITION = scip_pb2.SymbolRole.Value("Definition")

_REG_FIELD_KINDS = {"register", "field"}


def load_index(scip_path: str) -> scip_pb2.Index:
    with open(scip_path, "rb") as f:
        idx = scip_pb2.Index()
        idx.ParseFromString(f.read())
    return idx


def logical_path(sym: str) -> str:
    """Return the DML object path shared across per-file symbol variants.

    DML SCIP symbols embed the declaring file as a backtick-quoted namespace
    segment, e.g.::

        dml simics . . srv-pm.bt...`cor_imh2_a0_hwrs_m6_regs.dml`.sb_cr.IP_DISABLE_RESOLVED_CR_DWORD0.

    Two symbols declared/reopened in different files but referring to the
    "same" DML object share everything *after* the last backtick-quoted
    segment. That suffix is what we key on here.
    """
    idx = sym.rfind("`")
    suffix = sym[idx + 1:] if idx != -1 else sym
    return suffix.lstrip(".")


def find_register_field_symbols(index: scip_pb2.Index, target_file_substr: str) -> dict[str, tuple[str, str, str, int]]:
    """Return {logical_path: (kind, symbol, def_path, def_line)} for every
    register/field SymbolInformation whose definition occurrence lives in a
    document whose relative_path contains target_file_substr.
    """
    result: dict[str, tuple[str, str, str, int]] = {}
    for doc in index.documents:
        if target_file_substr not in doc.relative_path:
            continue

        kinds: dict[str, str] = {}
        for sym_info in doc.symbols:
            kind = _resolve_kind(sym_info)
            if kind in _REG_FIELD_KINDS:
                kinds[sym_info.symbol] = kind

        for occ in doc.occurrences:
            if occ.symbol not in kinds:
                continue
            if not (occ.symbol_roles & ROLE_DEFINITION):
                continue
            lpath = logical_path(occ.symbol)
            result[lpath] = (kinds[occ.symbol], occ.symbol, doc.relative_path, occ.range[0])

    return result


def find_all_occurrences_by_logical_path(
    index: scip_pb2.Index, logical_paths: set[str]
) -> dict[str, list[tuple[str, int, bool, str]]]:
    """Return {logical_path: [(path, line, is_definition, symbol), ...]} for
    every occurrence anywhere in the index whose *logical path* matches one
    of `logical_paths` — bridging symbols reopened/declared across multiple
    files.
    """
    occs: dict[str, list[tuple[str, int, bool, str]]] = defaultdict(list)
    for doc in index.documents:
        for occ in doc.occurrences:
            lpath = logical_path(occ.symbol)
            if lpath in logical_paths:
                is_def = bool(occ.symbol_roles & ROLE_DEFINITION)
                occs[lpath].append((doc.relative_path, occ.range[0], is_def, occ.symbol))
    for lpath in occs:
        occs[lpath].sort(key=lambda t: (t[0], t[1]))
    return occs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scip_path", help="Path to .scip index file")
    parser.add_argument("target_file", help="Substring matching the target file's relative_path "
                                             "(e.g. cor_imh2_a0_hwrs_m6_regs.dml)")
    parser.add_argument("--field", help="Only show symbols whose short name matches this "
                                         "(register or field name, e.g. IP_DISABLE_RESOLVED_CR_DWORD0)")
    parser.add_argument("--ref-in", help="Only show references whose path contains this substring "
                                         "(e.g. srv-pm/code/hwrs-gen2). Symbols with no matching "
                                         "references are omitted.")
    parser.add_argument("--limit", type=int, default=None, help="Limit references shown per symbol")
    parser.add_argument("--show-method", action="store_true",
                         help="Resolve and print the enclosing `method` for each "
                              "definition/reference line, via brace-depth scanning "
                              "of the source file (not from SCIP data).")
    args = parser.parse_args()

    index = load_index(args.scip_path)
    project_root = None
    if args.show_method:
        project_root = url2pathname(urlparse(index.metadata.project_root).path)

    reg_field_defs = find_register_field_symbols(index, args.target_file)
    if not reg_field_defs:
        print(f"No register/field definitions found in documents matching '{args.target_file}'")
        return

    if args.field:
        reg_field_defs = {
            lpath: info for lpath, info in reg_field_defs.items()
            if args.field in (dml_short_name(info[1]) or "")
        }
        if not reg_field_defs:
            print(f"No register/field named like '{args.field}' found in '{args.target_file}'")
            return

    occs = find_all_occurrences_by_logical_path(index, set(reg_field_defs.keys()))

    print(f"Target file : {args.target_file}")
    if args.ref_in:
        print(f"Ref filter  : references containing '{args.ref_in}'")
    print(f"Symbols found: {len(reg_field_defs)}")
    print("=" * 70)

    # Print registers first, then fields, both sorted by def location.
    for kind_filter in ("register", "field"):
        lpaths = sorted(
            (lpath for lpath, (kind, _, _, _) in reg_field_defs.items() if kind == kind_filter),
            key=lambda lp: (reg_field_defs[lp][2], reg_field_defs[lp][3]),
        )
        if not lpaths:
            continue

        printed_header = False
        for lpath in lpaths:
            kind, sym, def_path, def_line = reg_field_defs[lpath]
            name = dml_short_name(sym) or sym
            all_occ = occs.get(lpath, [])
            # occurrences reported as "definitions" across ALL files that
            # declare/reopen this logical object (e.g. base regs file +
            # hand-written override file both have a Definition occurrence).
            defs = sorted({(p, l) for p, l, is_def, _ in all_occ if is_def})
            refs = sorted({(p, l) for p, l, is_def, _ in all_occ if not is_def})

            if args.ref_in:
                refs = [(p, l) for p, l in refs if args.ref_in in p]
                if not refs:
                    continue  # skip symbols with no reference in the requested path

            if not printed_header:
                print(f"\n### {kind_filter.upper()}S ###")
                printed_header = True

            def _fmt(p: str, l: int) -> str:
                loc = f"    {p}:{l + 1}"
                if args.show_method and project_root:
                    m = enclosing_method(str(Path(project_root) / p), l)
                    loc += f"  [in method {m}()]" if m else "  [not in a method]"
                return loc

            print(f"\n[{kind}] {name}")
            print(f"  Logical path: {lpath}")
            print(f"  Definitions ({len(defs)}):")
            for p, l in defs:
                print(_fmt(p, l))
            print(f"  References ({len(refs)}):")
            shown = refs[: args.limit] if args.limit else refs
            for p, l in shown:
                print(_fmt(p, l))
            if args.limit and len(refs) > args.limit:
                print(f"    … and {len(refs) - args.limit} more")


if __name__ == "__main__":
    main()
