"""
Shared types and classes for DML analysis.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..span import ZeroSpan
from ..lsp_data import DMLDiagnostic, DMLDiagnosticSeverity


class DMLErrorKind(Enum):
    """Enhanced types of DML errors."""
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    TYPE_ERROR = "type_error"
    UNDEFINED_SYMBOL = "undefined_symbol"
    DUPLICATE_SYMBOL = "duplicate_symbol"
    IMPORT_ERROR = "import_error"
    TEMPLATE_ERROR = "template_error"
    SCOPE_ERROR = "scope_error"
    REFERENCE_ERROR = "reference_error"
    CIRCULAR_DEPENDENCY = "circular_dependency"


class ReferenceKind(Enum):
    """Types of symbol references."""
    TEMPLATE = "template"
    TYPE = "type"
    VARIABLE = "variable"
    METHOD = "method"
    PARAMETER = "parameter"
    CONSTANT = "constant"


@dataclass
class DMLError:
    """Represents an error in DML code."""
    kind: DMLErrorKind
    message: str
    span: ZeroSpan
    severity: DMLDiagnosticSeverity = DMLDiagnosticSeverity.ERROR
    code: Optional[str] = None
    
    def to_diagnostic(self) -> DMLDiagnostic:
        """Convert to diagnostic."""
        return DMLDiagnostic(
            span=self.span,
            message=self.message,
            severity=self.severity,
            code=self.code
        )


@dataclass
class NodeRef:
    """Represents a reference to a DML node (symbol)."""
    name: str
    span: ZeroSpan
    parts: List[str] = field(default_factory=list)  # For nested references like obj.field
    
    def __str__(self) -> str:
        if self.parts:
            return ".".join([self.name] + self.parts)
        return self.name
    
    @property
    def full_name(self) -> str:
        return str(self)


@dataclass
class SymbolReference:
    """Enhanced symbol reference with kind and location."""
    node_ref: NodeRef
    kind: ReferenceKind
    location: ZeroSpan
    
    def __str__(self) -> str:
        return str(self.node_ref)