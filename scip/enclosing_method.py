#!/usr/bin/env python3
"""
enclosing_method.py — find the DML `method` that lexically encloses a given
source line, using brace-depth scanning (no compiler/SCIP support needed).

Why this exists: SCIP's `Occurrence.enclosing_range` for a method *definition*
only covers the method's own signature line (e.g. `method read() -> (uint64)
default {`), not its full body. There is no SCIP field that maps an arbitrary
reference occurrence back to "which method's body contains this line" — so we
recover it directly from the source text.

Approach: scan the file character-by-character, tracking `{`/`}` nesting
depth. Whenever a `{` is opened, check whether the text since the last
`{`/`}`/`;` looks like a DML method header (`[shared] method NAME(...) [->
(...)] [default]? {`). If so, push (name, start_line, depth). When the
matching `}` closes that depth, pop it and record (start_line, end_line,
name). The result is an interval list per file that can be queried for any
line number, returning the innermost (most specific) enclosing method — this
also naturally handles nested methods (e.g. inline `each ... in (...) { }`
loops don't count, but a method nested inside another method's `#if` block
still resolves to the outer method unless a `method` header is matched again).

Usage as a library:
    from enclosing_method import build_method_ranges, enclosing_method_for_line
    ranges = build_method_ranges("/abs/path/to/file.dml")
    name = enclosing_method_for_line(ranges, line)  # 0-indexed line number

Usage as a CLI (for quick manual checks):
    uv run --project scip scip/enclosing_method.py <file.dml> <line_1_indexed>
"""
import re
import sys
from functools import lru_cache
from pathlib import Path

# Matches "method NAME(" optionally preceded by "shared"/"inline" and
# optionally including a "-> (...)" return-type clause, up to the opening
# brace. We don't need the full signature — just enough to confirm it's a
# method header and capture its name.
_METHOD_HEADER_RE = re.compile(
    r"(?:shared\s+|inline\s+)*method\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.DOTALL,
)


def _looks_like_method_header(pending: str) -> str | None:
    """Return the method name if `pending` (the buffered text right before an
    opening '{') looks like a DML method declaration header, else None.
    """
    m = _METHOD_HEADER_RE.search(pending)
    if not m:
        return None
    return m.group(1)


def build_method_ranges(abs_path: str) -> list[tuple[int, int, str]]:
    """Scan `abs_path` and return a list of (start_line, end_line, name)
    0-indexed, inclusive, for every `method` body found — including nested
    ones. Returns [] if the file can't be read.
    """
    try:
        text = Path(abs_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    ranges: list[tuple[int, int, str]] = []
    stack: list[tuple[str, int, int]] = []  # (name, start_line, depth_after_open)
    depth = 0
    line = 0
    pending_start = 0  # line where current "pending" token buffer began
    pending_chars: list[str] = []

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch == "{":
            pending = "".join(pending_chars)
            name = _looks_like_method_header(pending)
            depth += 1
            if name is not None:
                stack.append((name, pending_start, depth))
            pending_chars = []
            pending_start = line
        elif ch == "}":
            if stack and stack[-1][2] == depth:
                name, start_line, _ = stack.pop()
                ranges.append((start_line, line, name))
            depth = max(0, depth - 1)
            pending_chars = []
            pending_start = line
        elif ch == ";":
            pending_chars = []
            pending_start = line
        else:
            if not pending_chars:
                pending_start = line
            pending_chars.append(ch)
        i += 1

    return ranges


@lru_cache(maxsize=None)
def _cached_method_ranges(abs_path: str) -> tuple[tuple[int, int, str], ...]:
    return tuple(build_method_ranges(abs_path))


def enclosing_method_for_line(
    ranges: "list[tuple[int, int, str]] | tuple[tuple[int, int, str], ...]",
    line0: int,
) -> str | None:
    """Given ranges from build_method_ranges() and a 0-indexed line number,
    return the innermost enclosing method's name, or None if the line isn't
    inside any method body.
    """
    best: tuple[int, int, str] | None = None
    for start, end, name in ranges:
        if start <= line0 <= end:
            # innermost = smallest span containing the line
            if best is None or (end - start) < (best[1] - best[0]):
                best = (start, end, name)
    return best[2] if best else None


def enclosing_method(abs_path: str, line0: int) -> str | None:
    """Convenience one-shot: resolve + cache ranges for abs_path, then look up
    the enclosing method for 0-indexed line0.
    """
    ranges = _cached_method_ranges(abs_path)
    return enclosing_method_for_line(ranges, line0)


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <file.dml> <line_1_indexed>", file=sys.stderr)
        sys.exit(1)
    path, line1 = sys.argv[1], int(sys.argv[2])
    name = enclosing_method(path, line1 - 1)
    print(name if name else "(not inside any method)")


if __name__ == "__main__":
    main()
