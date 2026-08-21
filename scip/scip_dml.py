#!/usr/bin/env python3
# /// script
# dependencies = [
#   "protobuf>=3.20.0",
#   "grpcio-tools>=1.50.0",
# ]
# ///
"""
scip_dml.py — Generate SCIP index and build nodes/relationships for DML modules.

Combines functionality from gen_scip.sh and read_scip.sh.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# scip_pb2 is a generated protobuf module that lives alongside this file.
# Insert the scip/ directory into sys.path (idempotent) so that the bare
# `import scip_pb2` works regardless of how this module is invoked —
# matching the same pattern used by scip_python.py.
_SCIP_DIR = Path(__file__).resolve().parent
if str(_SCIP_DIR) not in sys.path:
    sys.path.insert(0, str(_SCIP_DIR))

_scip_pb2_path = _SCIP_DIR / "scip_pb2.py"
if not _scip_pb2_path.exists():
    raise FileNotFoundError(
        f"scip_pb2.py not found in {_SCIP_DIR}. "
        "Run 'bash scip/generate_pb2.sh' to generate it."
    )
import scip_pb2  # type: ignore  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass


@contextmanager
def changing_folder(path):
    """Context manager to temporarily change working directory."""
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)

# Path to the dml-language-server submodule/repo root.
# scip_dml.py lives at <dls_root>/scip/scip_dml.py, so the parent of this
# file's directory *is* the dml-language-server root.
_DLS_ROOT: Path = Path(__file__).resolve().parents[1]


def prepare_dls_tools() -> Path:
    """Ensure the dml-language-server Rust release binaries (``dfa``, ``dls``)
    are built.  The submodule must already be checked out via::

        git submodule update --init dml-language-server

    If ``_DLS_ROOT/target/release/dfa`` or ``…/dls`` are missing, runs::

        cargo build --release --manifest-path ./Cargo.toml

    inside ``_DLS_ROOT``, then sets ``os.environ["DLS_ROOT"]`` and returns
    ``_DLS_ROOT``.
    """
    if not (_DLS_ROOT / ".git").exists() and not (_DLS_ROOT / "Cargo.toml").exists():
        raise RuntimeError(
            f"dml-language-server submodule not found at {_DLS_ROOT}.\n"
            "Please initialise it with:\n"
            "    git submodule update --init dml-language-server"
        )

    # ── Build release binaries if missing ────────────────────────────────────
    dfa_bin = _DLS_ROOT / "target" / "release" / "dfa"
    dls_bin = _DLS_ROOT / "target" / "release" / "dls"
    if not dfa_bin.exists() or not dls_bin.exists():
        print(f"[prepare_dls_tools] Building dfa/dls with cargo (this may take a while) ...")
        with changing_folder(_DLS_ROOT):
            subprocess.run(
                ["cargo", "build", "--release", "--manifest-path", "./Cargo.toml"],
                check=True,
                timeout=int(os.getenv("DML_CARGO_BUILD_TIMEOUT", "1800")),  # 30 min
            )
        if not dfa_bin.exists() or not dls_bin.exists():
            raise RuntimeError(
                f"cargo build succeeded but binaries not found under "
                f"{_DLS_ROOT / 'target' / 'release'}; check Cargo output."
            )
        print(f"[prepare_dls_tools] Binaries built: {dfa_bin}, {dls_bin}")
    else:
        print(f"[prepare_dls_tools] Binaries already exist: {dfa_bin}, {dls_bin}")

    # Export DLS_ROOT so gen_scip / callers can rely on it
    os.environ["DLS_ROOT"] = str(_DLS_ROOT)
    return _DLS_ROOT


@dataclass
class SymbolLocation:
    """A temporary symbol definition with source location, kind, extend list."""
    symbol: str
    locations: tuple[str, int, int]  # (relative_path, start_line, end_line)
    # Human-readable kind: method | template | interface | implement | namespace | object | ...
    kind: str = "unknown"
    parent: str | None = None  # for nested symbols (e.g. register fields), the parent symbol
    extends: set[str] = field(default_factory=set)  # the list of extended templates
    code: list[str] = field(default_factory=list)  # optional source code snippets for the definition

@dataclass
class Relationship:
    """A directed relationship between two symbols.

    Kinds:
      - "function_call" caller (method) calls callee (method)
    """
    kind: str
    caller: str
    callee: str
    caller_file: str
    callee_file: str
    line: int = -1
    end_line: int = -1

@dataclass
class DocumentRecord:
    """Document record with symbol definitions, references, and relationships."""
    relative_path: str
    definitions: list[SymbolLocation] = field(default_factory=list)
    references: list[Relationship] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

def prepare_compile_info(compile_info_path: Path, platform_path: Path) -> None:
    """Ensure ``dml_compile_commands.json`` exists under ``platform_path/bt/``.

    If the file is missing, runs CMake to configure and build the
    ``generate-dml-compile-commands`` target.

    Args:
        compile_info_path: Expected path of ``dml_compile_commands.json``.
        platform_path:     Platform project root (cmake -S target).
    """
    if compile_info_path.exists():
        print(f"dml_compile_commands.json already exists, skipping generation.")
    else:
        print("Generating dml_compile_commands.json...")
        cmake_bin = "/usr/intel/pkgs/cmake/3.31.5/bin/cmake"
        import shutil as _shutil
        cmake_bin = _shutil.which("cmake") or cmake_bin
        _CMAKE_CONFIGURE_TIMEOUT = int(os.getenv("DML_CMAKE_TIMEOUT", "300"))  # 5 min
        _CMAKE_BUILD_TIMEOUT = int(os.getenv("DML_CMAKE_BUILD_TIMEOUT", "600"))  # 10 min
        with changing_folder(platform_path):
            result = subprocess.run(
                [
                    cmake_bin, "-S", ".", "-B", "bt", "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_EXPORT_COMPILE_COMMANDS=1",
                    "-Wno-dev",
                ],
                timeout=_CMAKE_CONFIGURE_TIMEOUT,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"CMake configure step failed with exit code {result.returncode} "
                    f"in {platform_path}"
                )
            result = subprocess.run(
                [cmake_bin, "--build", "bt", "--target", "generate-dml-compile-commands"],
                timeout=_CMAKE_BUILD_TIMEOUT,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"CMake build target 'generate-dml-compile-commands' failed with "
                    f"exit code {result.returncode} in {platform_path}"
                )


def gen_scip(
    device: str,
    platform: str,
    root_path: str,
    scip_output: str | None = None,
):
    """Ensure the DML compile-commands file exists, then run dfa to produce a SCIP index.

    Args:
        device:   Path to the top-level DML device file (relative to
                       ``platform``). The device name is extracted from
                       the 'device <name>;' declaration and used as the default
                       SCIP output filename.
        platform: Project root passed to dfa via ``--workspace``.
                       The compile-commands file is always resolved as
                       ``platform / 'bt' / 'dml_compile_commands.json'``.
                       Defaults to '.' (cwd).
        root_path: Root directory to vp repo (e.g. repo root). Used to resolve
                   relative paths for the device and platform.
        scip_output:   Explicit output path. Defaults to '<device_name>.scip'
                       in the current working directory.
    """
    # ── Step 0: ensure dml-language-server submodule is built ───────────────
    dls_root = prepare_dls_tools()
    dfa = dls_root / "target" / "release" / "dfa"
    dls = dls_root / "target" / "release" / "dls"

    root_path_obj = Path(root_path)
    platform_path = root_path_obj / platform
    device_file = platform_path / device

    if not device_file.exists():
        raise RuntimeError(f"Device file not found: {device_file}")


    # ── STEP 1: resolve/ensure compile_info file exists ────────────────────
    # Derive from platform_path and regenerate via cmake if missing.
    compile_info_path = platform_path / "bt" / "dml_compile_commands.json"
    prepare_compile_info(compile_info_path, platform_path)
    if not compile_info_path.exists():
        raise RuntimeError(f"{compile_info_path} was not produced — check CMake output")

    # ── STEP 2: extract device name from 'device <name>;' ────────────────────
    device_name = get_device_node(device_file)
    if not device_name:
        raise RuntimeError(f"Could not extract device name from {device_file} (missing 'device <name>;' declaration)")

    scip_out = Path(scip_output) if scip_output else Path(f"{device_name}.scip")
    if scip_out.exists():
        scip_out.unlink()
    scip_out.parent.mkdir(parents=True, exist_ok=True)

    # ── STEP 3: run dfa ───────────────────────────────────────────────────────
    # dfa's --scip-output is a *directory*: it writes one
    # "<workspace-root-basename>.scip" file into it per workspace root (see
    # src/actions/requests.rs). Since we only ever pass a single --workspace,
    # point dfa at scip_out's parent directory (current dir by default) and
    # then rename the single resulting file to the caller-requested scip_out
    # path.
    _DFA_TIMEOUT = int(os.getenv("DML_DFA_TIMEOUT", "1200"))  # 20 min default
    scip_out_dir = scip_out.parent
    pre_existing = set(scip_out_dir.glob("*.scip"))

    print(f"Running {dfa} (timeout={_DFA_TIMEOUT}s) ......")
    result = subprocess.run(
        [
            str(dfa),
            "--compile-info", str(compile_info_path),
            "--workspace", str(root_path_obj),
            "--scip-output", str(scip_out_dir),
            str(dls),
            str(device_file),
        ],
        capture_output=True,
        text=True,
        timeout=_DFA_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"dfa failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    generated_files = sorted(set(scip_out_dir.glob("*.scip")) - pre_existing)
    if not generated_files:
        raise RuntimeError(
            f"dfa reported success but no new .scip file was produced in "
            f"{scip_out_dir}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    if len(generated_files) > 1:
        raise RuntimeError(
            f"Expected exactly one .scip file for workspace root "
            f"{root_path_obj}, found {len(generated_files)}: {generated_files}"
        )

    generated_files[0].rename(scip_out)

    print(f"Device name : {device_name}")
    print(f"SCIP index: {scip_out}")
    return device_name, str(scip_out)


def symbol_to_kind(sym: str) -> str:
    """Classify a SCIP symbol by its descriptor suffix."""
    # Check for local symbols first
    if sym.startswith("local "):
        return "local"

    descriptor = sym.split(" ", 4)[-1] if " " in sym else sym

    if descriptor.endswith(")."):
        return "method"
    if descriptor.endswith("#"):
        return "template"
    if descriptor.endswith("."):
        # Could be comp object, variable, or constant
        # Without more context, classify as object
        return "object"
    return "unknown"


def _line_range(r) -> tuple[int, int]:
    """Extract the end line from a SCIP repeated-int32 range.

    Per scip.proto Occurrence.range definition:
      4 elements: [startLine, startCharacter, endLine, endCharacter]
                  → end line is r[2]
      3 elements: [startLine, startCharacter, endCharacter]
                  → end line is inferred to equal start line (r[0])
    """
    if len(r) >= 4:
        return r[0], r[2]   # explicit endLine
    if len(r) == 3:
        return r[0], r[0]   # endLine == startLine (single-line range)
    return -1, -1


# Map SCIP SymbolInformation.Kind enum int values to readable labels.
# Values come from scip.proto SymbolInformation.Kind enum.
_PROTO_KIND_LABELS: dict[int, str] = {
    7:  "template", # "class"
    21: "interface",
    26: "method",
    33: "object",
    55: "typealias",
}

_COMPOSITE_OBJECT_TYPE = {'port', 'bank', 'register',
                          'field', 'group', 'connect',
                          'event', "implement", 'attribute', 'device'}

def _resolve_kind(sym_info) -> str:
    """Return a human-readable kind label.

    Prefers SymbolInformation.kind (proto enum) when non-zero;
    falls back to the descriptor-suffix heuristic in symbol_to_kind().
    """
    if sym_info and sym_info.kind:
        label = _PROTO_KIND_LABELS.get(sym_info.kind)
        if label:
            doc_str = sym_info.documentation[0].lower() if sym_info.documentation else None
            if doc_str:
                if label == "object":
                    label = doc_str if doc_str in _COMPOSITE_OBJECT_TYPE else "unknown"
                elif label == "method" and "method default" in doc_str:
                    label = "unknown"
                elif label == "typealias" and sym_info.symbol.endswith("#"):
                    if doc_str == "extern typedef":
                        label = "struct"
                    else:
                        label = "unknown"
            return label
    return "unknown"

def dml_short_name(sym: str) -> str | None:
    """Extract a short readable name from a DML SCIP symbol descriptor.

    DML SCIP symbols follow the format::

        <scheme> <version> <project> <descriptor-path>

    where the descriptor path uses ``/`` as a separator and ends with
    a kind suffix (``#``, ``().``, ``.``).  We strip the suffix and
    return the last slash-separated component.
    """
    descriptor = sym.split(" ", 4)[-1] if " " in sym else sym
    descriptor = descriptor.replace('`', '')
    assert descriptor.count('.dml.') >= 1, f"Unexpected symbol format (expected at least one '.dml.'): {sym}"
    n = descriptor.rsplit('.dml.', 1)[-1]
    if not n:
        return None
    if "#" in n:
        n = n.replace("#", ".")
    # Strip trailing descriptor kind suffixes
    name = n.rstrip("#/(). ")
    return name

def convert_path(sym: str) -> str:
    # Split into backtick-wrapped and non-backtick parts
    sym = sym.rstrip('/(). ')
    parts = re.split(r'(`[^`]*`)', sym)
    result = []
    for part in parts:
        if part.startswith('`') and part.endswith('`'):
            result.append(part[1:-1])          # strip backticks, keep dots
        else:
            result.append(part.replace('.', '/'))  # replace dots with slashes
    return ''.join(result).strip()


def get_device_node(device_file) -> Optional[str]:
    """Return the device identifier declared in *device_file*.

    Searches for the first line matching ``device <objident> ;`` (DML syntax)
    and returns the captured identifier, or ``None`` if no match is found.
    """
    with open(device_file, "r", encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"device\s+(\w+)\s*;\s*$", line.rstrip("\n"))
            if m:
                return m.group(1)
    return None


def get_record_for_path(records: list[DocumentRecord], relative_path: Optional[str]) -> DocumentRecord:
    """Return the DocumentRecord for a path, creating one if missing."""
    normalized_path = (relative_path or "").replace('\\', '/').strip()
    for record in records:
        if record.relative_path.replace('\\', '/').strip() == normalized_path:
            return record

    new_record = DocumentRecord(relative_path=normalized_path)
    records.append(new_record)
    return new_record

def build_nodes_and_relationship(device_name: str, device_file: str, scip_path: str, root: str, debug: bool = False) -> list:
    """Read a SCIP index and build typed symbol nodes with relationships."""
    if not Path(scip_path).exists():
        raise RuntimeError(f"Index not found: {scip_path} (run gen_scip first)")

    print(f"Loading {scip_path} ...")
    with open(scip_path, "rb") as f:
        index = getattr(scip_pb2, "Index")()
        index.ParseFromString(f.read())

    print(f"Tool : {index.metadata.tool_info.name} {index.metadata.tool_info.version}")
    print(f"Project : {index.metadata.project_root}")
    print(f"Docs : {len(index.documents)}")

    ROLE_DEFINITION = 0x1
    IMPORT_DEFINITION = 0x2

    repo_root = Path(root)

    # ── Pass 1: build SymbolLocation nodes from occurrences ───────────────────
    seen_definitions: dict[str, SymbolLocation] = {}
    seen_interfaces: dict[str, SymbolLocation] = {}
    interfaces: dict[str, set[str]] = {}
    records: list[DocumentRecord] = []
    device_node = None
    symbol_infors_per_doc: dict[str, dict[str, tuple[str, list[str]]]] = {}
    method_symbol_infors = set()
    pending_function_calls = set()  # (caller_method_sym, callee_method_sym, line, end_line)

    for doc in index.documents:
        #  ── Pass 1: setup symbol kind lookup table ─────────────────
        # classify symbols by their SymbolInformation.kind and build a lookup dict.
        symbol_infors = {} # symbol → (kind, [extended templates])
        for sym_info in doc.symbols:
            if sym_info.symbol.startswith('local'):
                continue  # skip local symbols which are not definitions and don't have relationships
            kind = _resolve_kind(sym_info)
            if kind == "unknown":
                continue
            if kind == "method":
                method_symbol_infors.add(sym_info.symbol)
            _extends = []
            for r in sym_info.relationships:
                if r.is_implementation and symbol_to_kind(r.symbol) == "template":
                    r_desc = dml_short_name(r.symbol)
                    if not r_desc:
                        continue
                    _extends.append(r_desc)
            symbol_infors[sym_info.symbol] = (kind, _extends)
        symbol_infors_per_doc[doc.relative_path] = symbol_infors

    for doc in index.documents:
        doc_path = repo_root / doc.relative_path
        if not doc_path.exists():
            print(f"Warning: source file missing for SCIP document: {doc.relative_path}")
            continue
        with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
            code_text = f.read().splitlines()

        rec = DocumentRecord(relative_path=doc.relative_path)
        records.append(rec)

        # ── Pass 2: definitions, imports and relationships ───────
        symbol_infors = symbol_infors_per_doc[doc.relative_path]
        sorted_occs = sorted(doc.occurrences,
                             key=lambda o: (o.range[0], \
                                            -o.enclosing_range[2] if o.enclosing_range and len(o.enclosing_range)==4 \
                                                else -o.range[2] if len(o.range)==4 else -o.range[0]))

        imports = set()
        implement_range = None
        template_range = None

        for occ in sorted_occs:
            if not occ.symbol or occ.symbol.startswith('local'):
                continue  # highlight-only occurrence, no symbol

            try:
                descriptor = dml_short_name(occ.symbol)
            except AssertionError:
                continue  # skip non-DML or malformed symbols safely
            if not descriptor:
                continue
            start_line, end_line = _line_range(occ.enclosing_range or occ.range)
            if start_line < 0 or end_line < 0:
                continue
            if implement_range and start_line >= implement_range[-1]:
                implement_range = None
            if template_range and start_line >= template_range[-1]:
                template_range = None

            if occ.symbol_roles & ROLE_DEFINITION:
                if occ.symbol not in symbol_infors:
                    continue
                kind, _extends = symbol_infors[occ.symbol]

                if kind == "template":
                    template_range = (descriptor, start_line, end_line)
                elif template_range and start_line >= template_range[1] and end_line <= template_range[2]:
                    # skip definitions within template bodies, which are not real definitions but just part of the template implementation
                    if "." in descriptor:
                        parent_sym = descriptor.rsplit(".", 1)[0]
                        if parent_sym != template_range[0]:
                            continue
                    if kind in ("register", "field"):
                        continue

                # # skip dml 1.4 statement
                # No such template definitions in dml-language-server with commit 6126faf2
                # if kind == "template" and occ.symbol.endswith(".dml#"):
                #     continue

                # # skip default method inherited from template
                # last_defn = rec.definitions[-1] if rec.definitions else None
                # if kind == "method" and descriptor.count('.') >=2 and last_defn:
                #     _, s, e = last_defn.locations[0]
                #     if (s <= start_line and e >= end_line and
                #         last_defn.symbol != descriptor.rsplit('.', 1)[0]
                #         and last_defn.kind == "template"):
                #         continue

                if kind == "method" and descriptor.count('.') >= 2 \
                    and implement_range and end_line <= implement_range[-1] \
                        and start_line >= implement_range[-2]:
                    # port.signal.signal_raise -> port.signal_raise
                    psym, isym, msym = descriptor.rsplit('.', 2)
                    if psym == implement_range[0] and isym == implement_range[1]:
                        descriptor = ".".join((psym, msym))

                # relationships: implementing interface
                if kind == "interface":
                    if "." in descriptor:
                        parent_sym, iface_sym = descriptor.rsplit(".", 1)
                        if iface_sym in interfaces:
                            interfaces[iface_sym].add(parent_sym)
                        else:
                            interfaces[iface_sym] = {parent_sym}
                    continue

                if kind == "struct":
                    if descriptor.endswith("_interface_t"):
                        kind = "interface_struct"
                        descriptor = descriptor.rsplit('.', 1)[-1][:-len("_interface_t")]

                if kind == "implement":
                    if '.' in descriptor:
                        parent_sym, iface_sym = descriptor.rsplit('.', 1)
                        if parent_sym and iface_sym and parent_sym in seen_definitions:
                            pdef = seen_definitions[parent_sym]
                            if pdef.kind == "port":
                                if iface_sym not in interfaces:
                                    interfaces[iface_sym] = {parent_sym}
                                else:
                                    interfaces[iface_sym].add(parent_sym)
                            implement_range = (parent_sym, iface_sym, start_line, end_line)
                            continue
                    else:
                        kind = "port"
                        if descriptor not in interfaces:
                            interfaces[descriptor] = {descriptor}
                        else:
                            interfaces[descriptor].add(descriptor)

                code_str = "\n".join(code_text[start_line:end_line + 1])

                if descriptor in seen_definitions:
                    defn = seen_definitions[descriptor]
                    defn.code.append(code_str)
                    continue

                parent = None
                if kind in _COMPOSITE_OBJECT_TYPE | {"method"} and "." in descriptor:
                    parent = descriptor.rsplit(".", 1)[0]
                defn = SymbolLocation(
                    symbol=descriptor,
                    kind="interface" if kind=="interface_struct" else kind,
                    parent=parent,
                    locations=(
                        doc.relative_path,
                        start_line,
                        end_line
                    ),
                    extends=set(_extends),
                    code=[code_str]
                )
                seen_definitions[descriptor] = defn
                rec.definitions.append(defn)
                if kind == "device":
                    device_node = defn
                if kind == "interface_struct":
                    seen_interfaces[descriptor] = defn

            elif occ.symbol_roles & IMPORT_DEFINITION:
                p = occ.symbol.split(" ", 4)[-1] if " " in occ.symbol else occ.symbol
                ipath = convert_path(p)
                imports.add((ipath, start_line, end_line))

            else:
                if not rec.definitions:
                    continue
                last_defn = rec.definitions[-1]
                if occ.symbol not in method_symbol_infors or last_defn.kind != "method":
                    continue
                _, m_start, m_end = last_defn.locations
                if m_start <= start_line and end_line <= m_end:
                    # Find the innermost definition whose enclosing_range contains ref_line.
                    if last_defn.symbol != descriptor:
                        pending_function_calls.add((doc.relative_path, last_defn.symbol, descriptor, start_line, end_line))

        for ipath, start_line, end_line in imports:
            rec.references.append(
                Relationship(
                    kind="imports",
                    caller=doc.relative_path,
                    callee=ipath,
                    caller_file=doc.relative_path,
                    callee_file=ipath,
                    line=start_line,
                    end_line=end_line
                )
            )

        if not device_node and Path(doc.relative_path) == Path(device_file):
            device_node = SymbolLocation(
                    symbol=device_name,
                    kind="device",
                    parent=None,
                    locations=(doc.relative_path, 0, 0),
                    extends=set(),
                    code=[],
                )
            rec.definitions.append(device_node)
            seen_definitions[device_name] = device_node

    # Merge codes from multiple files
    for defn in seen_definitions.values():
        if defn.code:
            code = "\n".join(defn.code)
            defn.code = [code]

    # Function call relationships (caller method → callee method)
    for doc_path, caller_sym, callee_sym, line, end_line in pending_function_calls:
        if callee_sym not in seen_definitions:
            continue
        rec = get_record_for_path(records, doc_path)
        rec.references.append(
            Relationship(
                kind="function_call",
                caller=caller_sym,
                callee=callee_sym,
                caller_file=doc_path,
                callee_file=seen_definitions[callee_sym].locations[0],
                line=line,
                end_line=end_line
            )
        )

    # Device -- contains --> bank / direct port / connect / event children
    # Walk seen_definitions for symbols that:
    #   1. are a direct child of the device (exactly one "." and prefix == device_name)
    #   2. have a kind that represents a top-level device component
    if device_node:
        device_rec = get_record_for_path(records, device_node.locations[0])
        device_name = device_node.symbol
        _direct_child_kinds = {"bank", "port", "connect", "event", "method", "group", "attribute"}
        for defn in seen_definitions.values():
            if defn.kind not in _direct_child_kinds:
                continue
            sym = defn.symbol
            # Must start with "<device_name>." and have exactly one dot
            if not defn.parent:
                device_rec.references.append(
                    Relationship(
                        kind="contains",
                        caller=device_name,
                        callee=sym,
                        caller_file="",
                        callee_file=defn.locations[0],
                        line=0,
                        end_line=0,
                    )
                )

    for defn in seen_definitions.values():
        # bank -- contains --> register, register -- contains --> field
        if defn.parent and defn.parent in seen_definitions:
            rec = get_record_for_path(records, defn.locations[0])
            parent_defn =seen_definitions[defn.parent]
            rec.references.append(
                Relationship(
                    kind="contains",
                    caller=defn.parent,
                    callee=defn.symbol,
                    caller_file=parent_defn.locations[0] if parent_defn.kind!="device" else "",
                    callee_file=defn.locations[0],
                    line=0,
                    end_line=0
                )
            )
        # --> is_template relationship
        if defn.extends:
            rec = get_record_for_path(records, defn.locations[0])
            for ext in defn.extends:
                if ext in seen_definitions:
                    rec.references.append(
                        Relationship(
                            kind="extends" if defn.kind=="template" else "implements",
                            caller=defn.symbol,
                            callee=ext,
                            caller_file=seen_definitions[defn.symbol].locations[0] if defn.kind!="device" else "",
                            callee_file=seen_definitions[ext].locations[0],
                            line=0,
                            end_line=0
                        )
                    )

    used_iface = set()
    for iface, conns in interfaces.items():
        for con in conns:
            if con in seen_definitions:
                defn = seen_definitions[con]
                if defn.kind in ("connect", "port"):
                    rec = get_record_for_path(records, defn.locations[0])
                    iface_defn = seen_interfaces[iface] if iface in seen_interfaces else None
                    rec.references.append(
                        Relationship(
                            kind="references" if defn.kind=="connect" else "implements",
                            caller=con,
                            callee=iface,
                            caller_file=defn.locations[0],
                            callee_file=iface_defn.locations[0] if iface_defn else "",
                            line=0,
                            end_line=0
                        )
                    )
                    used_iface.add(iface)

    for iface in used_iface:
        if iface in seen_interfaces:
            continue
        records[0].definitions.append(
            SymbolLocation(
                symbol=iface,
                kind="interface",
                parent=None,
                locations=("", 0, 0),
                extends=set(),
                code=[],
            )
        )

    # ── Report (per record) ───────────────────────────────────────────────────
    if debug:
        report_lines = []
        def _p(line=""):
            report_lines.append(line)

        for rec in records:
            defs = {}
            refs = defaultdict(list)
            for d in rec.definitions:
                defs.setdefault(d.kind, []).append(d)
            for d in rec.references:
                refs.setdefault(d.kind, []).append(d)

            _p(f"FILE: {rec.relative_path}")

            for kind, def_list in defs.items():
                _p(f"  Definitions ({kind}, {len(def_list)}):")
                for d in def_list:
                    d_path, d_start, d_end = d.locations if d.locations else ("", -1, -1)
                    symbol = d.symbol if d.kind == "device" else f"{d_path}:{d.symbol}" if d_path else d.symbol
                    _p(f"    [{d.kind:<13}] {symbol}"
                       f"  ({d_path}:{d_start + 1}-{d_end + 1})"
                       f"  parent={d.parent}, has_code={bool(d.code)}")

            for kind, ref_list in refs.items():
                _p(f"  References ({kind}, {len(ref_list)}):")
                for ref in ref_list:
                    caller = f"{ref.caller_file}:{ref.caller}" if ref.caller_file else ref.caller
                    callee = f"{ref.callee_file}:{ref.callee}" if ref.callee_file else ref.callee
                    _p(f"    [{ref.kind:<13}] {caller} -> {callee}"
                       f"  (line {ref.line + 1})")

        out_path = "./scip_dml.out"
        with open(out_path, "w") as _f:
            _f.write("\n".join(report_lines) + "\n")
        print(f"Report written to {out_path}")

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Generate SCIP index and build nodes/relationships for DML modules"
    )
    parser.add_argument("--device", required=True,
                        help="Path to the top-level DML device file, relative to platform")
    parser.add_argument("--platform", required=True,
                        help="Project root containing bt/ build dir (default: .)")
    parser.add_argument("--root", required=True,
                        help="Root directory to vp repo (e.g. repo root)")
    parser.add_argument("--output", help="SCIP output file path (default: <device_name>.scip)")
    parser.add_argument("--debug", action="store_true",
                        help="Print detailed definitions and relationships report")

    args = parser.parse_args()

    # Generate SCIP index
    device_name, scip_output = gen_scip(args.device, args.platform, args.root, args.output)

    print("\n" + "=" * 60)
    print("Building nodes and relationships...")
    print("=" * 60 + "\n")

    # Build nodes and relationships
    device_file = Path(args.root) / args.platform / args.device
    tags = build_nodes_and_relationship(device_name,
                                        device_file.relative_to(args.root),
                                        scip_output,
                                        args.root,
                                        debug=args.debug)

    print(f"\nTotal document records: {len(tags)}")
    total_defs = sum(len(doc.definitions) for doc in tags)
    total_refs = sum(len(doc.references) for doc in tags)
    print(f"Total definitions: {total_defs}")
    print(f"Total references: {total_refs}")
    return tags


if __name__ == "__main__":
    main()
