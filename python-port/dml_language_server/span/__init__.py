"""
Span utilities for tracking positions and ranges in DML source code.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import Generic, TypeVar, NamedTuple, Optional
from dataclasses import dataclass
from enum import Enum

# Type parameter for indexing system
IndexType = TypeVar('IndexType')


class IndexingSystem(Enum):
    """Different indexing systems for positions."""
    ZERO_INDEXED = "zero"  # 0-based indexing (used internally)
    ONE_INDEXED = "one"    # 1-based indexing (used by LSP)


class ZeroIndexed:
    """Marker class for zero-based indexing."""
    pass


class OneIndexed:
    """Marker class for one-based indexing."""
    pass


@dataclass(frozen=True)
class Position(Generic[IndexType]):
    """A position in a text document."""
    line: int
    column: int
    
    def __post_init__(self):
        if self.line < 0 or self.column < 0:
            raise ValueError(f"Invalid position: line={self.line}, column={self.column}")
    
    def to_zero_indexed(self) -> 'Position[ZeroIndexed]':
        """Convert to zero-indexed position."""
        if isinstance(self, Position[OneIndexed]):
            return Position[ZeroIndexed](
                line=max(0, self.line - 1),
                column=max(0, self.column - 1)
            )
        return self
    
    def to_one_indexed(self) -> 'Position[OneIndexed]':
        """Convert to one-indexed position."""
        if isinstance(self, Position[ZeroIndexed]):
            return Position[OneIndexed](
                line=self.line + 1,
                column=self.column + 1
            )
        return self
    
    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass(frozen=True)
class Range(Generic[IndexType]):
    """A range in a text document."""
    start: Position[IndexType]
    end: Position[IndexType]
    
    def __post_init__(self):
        if (self.start.line > self.end.line or 
            (self.start.line == self.end.line and self.start.column > self.end.column)):
            raise ValueError(f"Invalid range: start={self.start} > end={self.end}")
    
    def contains_position(self, position: Position[IndexType]) -> bool:
        """Check if this range contains the given position."""
        if position.line < self.start.line or position.line > self.end.line:
            return False
        
        if position.line == self.start.line and position.column < self.start.column:
            return False
        
        if position.line == self.end.line and position.column > self.end.column:
            return False
        
        return True
    
    def overlaps_with(self, other: 'Range[IndexType]') -> bool:
        """Check if this range overlaps with another range."""
        return not (self.end < other.start or other.end < self.start)
    
    def to_zero_indexed(self) -> 'Range[ZeroIndexed]':
        """Convert to zero-indexed range."""
        return Range[ZeroIndexed](
            start=self.start.to_zero_indexed(),
            end=self.end.to_zero_indexed()
        )
    
    def to_one_indexed(self) -> 'Range[OneIndexed]':
        """Convert to one-indexed range."""
        return Range[OneIndexed](
            start=self.start.to_one_indexed(),
            end=self.end.to_one_indexed()
        )
    
    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


@dataclass(frozen=True)
class Span(Generic[IndexType]):
    """A span represents a location in source code with file information."""
    file_path: Optional[str]
    range: Range[IndexType]
    
    @property
    def start(self) -> Position[IndexType]:
        """Get the start position of this span."""
        return self.range.start
    
    @property
    def end(self) -> Position[IndexType]:
        """Get the end position of this span."""
        return self.range.end
    
    def contains_position(self, position: Position[IndexType]) -> bool:
        """Check if this span contains the given position."""
        return self.range.contains_position(position)
    
    def to_zero_indexed(self) -> 'Span[ZeroIndexed]':
        """Convert to zero-indexed span."""
        return Span[ZeroIndexed](
            file_path=self.file_path,
            range=self.range.to_zero_indexed()
        )
    
    def to_one_indexed(self) -> 'Span[OneIndexed]':
        """Convert to one-indexed span."""
        return Span[OneIndexed](
            file_path=self.file_path,
            range=self.range.to_one_indexed()
        )
    
    def __str__(self) -> str:
        file_part = f"{self.file_path}:" if self.file_path else ""
        return f"{file_part}{self.range}"


class SpanBuilder:
    """Helper class for building spans from text content."""
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path
        self._lines: Optional[list] = None
    
    def set_content(self, content: str) -> None:
        """Set the content to build spans from."""
        self._lines = content.splitlines(keepends=True)
    
    def position_from_offset(self, offset: int) -> Position[ZeroIndexed]:
        """Convert a byte offset to a zero-indexed position."""
        if self._lines is None:
            raise ValueError("Content not set")
        
        if offset < 0:
            return Position[ZeroIndexed](0, 0)
        
        current_offset = 0
        for line_num, line in enumerate(self._lines):
            line_length = len(line)
            if current_offset + line_length > offset:
                column = offset - current_offset
                return Position[ZeroIndexed](line_num, column)
            current_offset += line_length
        
        # Past end of file
        if self._lines:
            last_line = len(self._lines) - 1
            last_column = len(self._lines[-1])
            return Position[ZeroIndexed](last_line, last_column)
        else:
            return Position[ZeroIndexed](0, 0)
    
    def offset_from_position(self, position: Position[ZeroIndexed]) -> int:
        """Convert a zero-indexed position to a byte offset."""
        if self._lines is None:
            raise ValueError("Content not set")
        
        if position.line < 0 or position.line >= len(self._lines):
            return 0
        
        offset = sum(len(line) for line in self._lines[:position.line])
        offset += min(position.column, len(self._lines[position.line]))
        return offset
    
    def span_from_offsets(self, start_offset: int, end_offset: int) -> Span[ZeroIndexed]:
        """Create a span from byte offsets."""
        start_pos = self.position_from_offset(start_offset)
        end_pos = self.position_from_offset(end_offset)
        range_obj = Range[ZeroIndexed](start_pos, end_pos)
        return Span[ZeroIndexed](self.file_path, range_obj)
    
    def span_from_positions(
        self, 
        start: Position[ZeroIndexed], 
        end: Position[ZeroIndexed]
    ) -> Span[ZeroIndexed]:
        """Create a span from positions."""
        range_obj = Range[ZeroIndexed](start, end)
        return Span[ZeroIndexed](self.file_path, range_obj)
    
    def single_position_span(self, position: Position[ZeroIndexed]) -> Span[ZeroIndexed]:
        """Create a span for a single position."""
        return self.span_from_positions(position, position)


def merge_spans(spans: list[Span[IndexType]]) -> Optional[Span[IndexType]]:
    """
    Merge multiple spans into a single span covering all of them.
    
    Args:
        spans: List of spans to merge
        
    Returns:
        Merged span or None if input is empty
    """
    if not spans:
        return None
    
    if len(spans) == 1:
        return spans[0]
    
    # All spans should be from the same file
    file_path = spans[0].file_path
    if not all(span.file_path == file_path for span in spans):
        raise ValueError("Cannot merge spans from different files")
    
    # Find the earliest start and latest end
    min_start = min(span.start for span in spans)
    max_end = max(span.end for span in spans)
    
    range_obj = Range[IndexType](min_start, max_end)
    return Span[IndexType](file_path, range_obj)


# Convenience type aliases
ZeroSpan = Span[ZeroIndexed]
OneSpan = Span[OneIndexed]
ZeroPosition = Position[ZeroIndexed]
OnePosition = Position[OneIndexed]
ZeroRange = Range[ZeroIndexed]
OneRange = Range[OneIndexed]

# Export all public types
__all__ = [
    "Position",
    "Range",
    "Span",
    "SpanBuilder",
    "ZeroIndexed",
    "OneIndexed",
    "IndexingSystem",
    "ZeroSpan",
    "OneSpan",
    "ZeroPosition",
    "OnePosition",
    "ZeroRange",
    "OneRange",
    "merge_spans"
]