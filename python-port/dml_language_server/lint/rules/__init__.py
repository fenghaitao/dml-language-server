"""
Lint rules for DML code quality checking.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional
import re

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ...analysis.types import DMLError, DMLErrorKind
from ...lsp_data import DMLDiagnosticSeverity


class LintRuleLevel(Enum):
    """Severity level for lint rules."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class LintRuleConfig:
    """Configuration for a lint rule."""
    enabled: bool = True
    level: LintRuleLevel = LintRuleLevel.WARNING


class LintRule:
    """Base class for lint rules."""
    
    def __init__(self, name: str, description: str, level: LintRuleLevel = LintRuleLevel.WARNING):
        self.name = name
        self.description = description
        self.level = level
        self.enabled = True
    
    def check(self, file_path: Path, content: str) -> List[DMLError]:
        """
        Check the file content for violations of this rule.
        
        Args:
            file_path: Path to the file being checked
            content: File content as string
            
        Returns:
            List of DMLError objects for violations found
        """
        raise NotImplementedError("Subclasses must implement check()")
    
    def _create_error(self, file_path: Path, line: int, column: int, message: str) -> DMLError:
        """Helper to create a DMLError for a lint violation."""
        span = ZeroSpan(
            str(file_path),
            ZeroRange(
                ZeroPosition(line, column),
                ZeroPosition(line, column + 1)
            )
        )
        
        severity_map = {
            LintRuleLevel.ERROR: DMLDiagnosticSeverity.ERROR,
            LintRuleLevel.WARNING: DMLDiagnosticSeverity.WARNING,
            LintRuleLevel.INFO: DMLDiagnosticSeverity.INFO,
            LintRuleLevel.HINT: DMLDiagnosticSeverity.HINT,
        }
        
        return DMLError(
            kind=DMLErrorKind.SEMANTIC_ERROR,  # Lint errors are semantic
            message=f"{self.name}: {message}",
            span=span,
            severity=severity_map[self.level],
            code=self.name
        )


class TrailingWhitespaceRule(LintRule):
    """Check for trailing whitespace on lines."""
    
    def __init__(self):
        super().__init__(
            name="nsp_trailing",
            description="Found trailing whitespace on row",
            level=LintRuleLevel.WARNING
        )
    
    def check(self, file_path: Path, content: str) -> List[DMLError]:
        errors = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            # Check if line has trailing whitespace
            if line and line != line.rstrip():
                # Find the position of trailing whitespace
                stripped = line.rstrip()
                column = len(stripped)
                
                error = self._create_error(
                    file_path,
                    line_num,
                    column,
                    "Found trailing whitespace on row"
                )
                errors.append(error)
        
        return errors


class LongLinesRule(LintRule):
    """Check for lines exceeding maximum length."""
    
    def __init__(self, max_length: int = 100):
        super().__init__(
            name="long_lines",
            description="Line length is above the threshold",
            level=LintRuleLevel.WARNING
        )
        self.max_length = max_length
    
    def check(self, file_path: Path, content: str) -> List[DMLError]:
        errors = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            # Check line length (excluding newline)
            if len(line) > self.max_length:
                error = self._create_error(
                    file_path,
                    line_num,
                    self.max_length,
                    f"Line length is above the threshold"
                )
                errors.append(error)
        
        return errors


class IndentationRule(LintRule):
    """Check for consistent indentation."""
    
    def __init__(self, indent_size: int = 4):
        super().__init__(
            name="indent_size",
            description="Inconsistent indentation",
            level=LintRuleLevel.WARNING
        )
        self.indent_size = indent_size
    
    def check(self, file_path: Path, content: str) -> List[DMLError]:
        errors = []
        lines = content.splitlines()
        
        for line_num, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check for tabs
            if '\t' in line[:len(line) - len(line.lstrip())]:
                error = self._create_error(
                    file_path,
                    line_num,
                    0,
                    "Use spaces for indentation, not tabs"
                )
                errors.append(error)
                continue
            
            # Check indentation level
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces % self.indent_size != 0:
                error = self._create_error(
                    file_path,
                    line_num,
                    0,
                    f"Indentation should be a multiple of {self.indent_size} spaces"
                )
                errors.append(error)
        
        return errors


class DevicePositionRule(LintRule):
    """Check that device declaration is in the correct position."""
    
    def __init__(self):
        super().__init__(
            name="device_position",
            description="Device declaration must be second statement in file",
            level=LintRuleLevel.WARNING
        )
    
    def check(self, file_path: Path, content: str) -> List[DMLError]:
        """
        This rule is handled by the parser's file structure validation.
        Kept here for completeness but returns empty list.
        """
        return []


# Registry of all available lint rules
ALL_LINT_RULES = [
    TrailingWhitespaceRule,
    LongLinesRule,
    IndentationRule,
    DevicePositionRule,
]


def get_default_rules() -> List[LintRule]:
    """Get the default set of enabled lint rules."""
    return [rule_class() for rule_class in ALL_LINT_RULES]


__all__ = [
    'LintRule',
    'LintRuleLevel',
    'LintRuleConfig',
    'TrailingWhitespaceRule',
    'LongLinesRule',
    'IndentationRule',
    'DevicePositionRule',
    'ALL_LINT_RULES',
    'get_default_rules',
]
