"""
LSP data structures and utilities for the DML Language Server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import urllib.parse

from lsprotocol.types import (
    Position as LspPosition,
    Range as LspRange,
    Location as LspLocation,
    Diagnostic as LspDiagnostic,
    DiagnosticSeverity,
    TextEdit as LspTextEdit,
    WorkspaceEdit as LspWorkspaceEdit,
    CompletionItem as LspCompletionItem,
    CompletionItemKind,
    SymbolKind,
    DocumentSymbol as LspDocumentSymbol,
    Hover as LspHover,
    MarkupContent,
    MarkupKind,
)

from .span import ZeroPosition, ZeroRange, ZeroSpan, OnePosition, OneRange


class DMLDiagnosticSeverity(Enum):
    """Severity levels for DML diagnostics."""
    ERROR = "error"
    WARNING = "warning" 
    INFO = "info"
    HINT = "hint"


@dataclass
class DMLDiagnostic:
    """A diagnostic message for DML code."""
    span: ZeroSpan
    message: str
    severity: DMLDiagnosticSeverity
    code: Optional[str] = None
    source: str = "dml-language-server"
    related_information: List['DMLDiagnostic'] = None
    
    def __post_init__(self):
        if self.related_information is None:
            self.related_information = []
    
    def to_lsp_diagnostic(self) -> LspDiagnostic:
        """Convert to LSP diagnostic."""
        # Convert severity
        severity_map = {
            DMLDiagnosticSeverity.ERROR: DiagnosticSeverity.Error,
            DMLDiagnosticSeverity.WARNING: DiagnosticSeverity.Warning,
            DMLDiagnosticSeverity.INFO: DiagnosticSeverity.Information,
            DMLDiagnosticSeverity.HINT: DiagnosticSeverity.Hint,
        }
        
        # Convert span to LSP range (one-indexed)
        one_range = self.span.range.to_one_indexed()
        lsp_range = LspRange(
            start=LspPosition(line=one_range.start.line, character=one_range.start.column),
            end=LspPosition(line=one_range.end.line, character=one_range.end.column)
        )
        
        return LspDiagnostic(
            range=lsp_range,
            message=self.message,
            severity=severity_map[self.severity],
            code=self.code,
            source=self.source
        )


@dataclass 
class DMLLocation:
    """A location in DML source code."""
    span: ZeroSpan
    
    def to_lsp_location(self) -> LspLocation:
        """Convert to LSP location."""
        if not self.span.file_path:
            raise ValueError("Cannot convert span without file path to LSP location")
        
        # Convert to file URI
        file_uri = path_to_uri(Path(self.span.file_path))
        
        # Convert to one-indexed range
        one_range = self.span.range.to_one_indexed() 
        lsp_range = LspRange(
            start=LspPosition(line=one_range.start.line, character=one_range.start.column),
            end=LspPosition(line=one_range.end.line, character=one_range.end.column)
        )
        
        return LspLocation(uri=file_uri, range=lsp_range)


@dataclass
class DMLTextEdit:
    """A text edit for DML code."""
    range: ZeroRange
    new_text: str
    
    def to_lsp_text_edit(self) -> LspTextEdit:
        """Convert to LSP text edit."""
        # Convert to one-indexed range
        one_range = self.range.to_one_indexed()
        lsp_range = LspRange(
            start=LspPosition(line=one_range.start.line, character=one_range.start.column),
            end=LspPosition(line=one_range.end.line, character=one_range.end.column)
        )
        
        return LspTextEdit(range=lsp_range, new_text=self.new_text)


@dataclass
class DMLWorkspaceEdit:
    """A workspace edit for multiple files."""
    changes: Dict[Path, List[DMLTextEdit]]
    
    def to_lsp_workspace_edit(self) -> LspWorkspaceEdit:
        """Convert to LSP workspace edit."""
        lsp_changes = {}
        
        for file_path, edits in self.changes.items():
            file_uri = path_to_uri(file_path)
            lsp_edits = [edit.to_lsp_text_edit() for edit in edits]
            lsp_changes[file_uri] = lsp_edits
        
        return LspWorkspaceEdit(changes=lsp_changes)


class DMLSymbolKind(Enum):
    """Kinds of DML symbols."""
    DEVICE = "device"
    BANK = "bank"
    REGISTER = "register" 
    FIELD = "field"
    METHOD = "method"
    PARAMETER = "parameter"
    ATTRIBUTE = "attribute"
    TEMPLATE = "template"
    CONNECT = "connect"
    INTERFACE = "interface"
    PORT = "port"
    IMPLEMENT = "implement"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPEDEF = "typedef"
    STRUCT = "struct"
    BITORDER = "bitorder"
    LAYOUT = "layout"


@dataclass
class DMLSymbol:
    """A symbol in DML code."""
    name: str
    kind: DMLSymbolKind
    location: DMLLocation
    detail: Optional[str] = None
    documentation: Optional[str] = None
    children: List['DMLSymbol'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_lsp_document_symbol(self) -> LspDocumentSymbol:
        """Convert to LSP document symbol."""
        # Map DML symbol kinds to LSP symbol kinds
        kind_map = {
            DMLSymbolKind.DEVICE: SymbolKind.Class,
            DMLSymbolKind.BANK: SymbolKind.Namespace,
            DMLSymbolKind.REGISTER: SymbolKind.Property,
            DMLSymbolKind.FIELD: SymbolKind.Field,
            DMLSymbolKind.METHOD: SymbolKind.Method,
            DMLSymbolKind.PARAMETER: SymbolKind.Variable,
            DMLSymbolKind.ATTRIBUTE: SymbolKind.Property,
            DMLSymbolKind.TEMPLATE: SymbolKind.Interface,
            DMLSymbolKind.CONNECT: SymbolKind.Event,
            DMLSymbolKind.INTERFACE: SymbolKind.Interface,
            DMLSymbolKind.PORT: SymbolKind.Event,
            DMLSymbolKind.IMPLEMENT: SymbolKind.Constructor,
            DMLSymbolKind.VARIABLE: SymbolKind.Variable,
            DMLSymbolKind.CONSTANT: SymbolKind.Constant,
            DMLSymbolKind.TYPEDEF: SymbolKind.TypeParameter,
            DMLSymbolKind.STRUCT: SymbolKind.Struct,
            DMLSymbolKind.BITORDER: SymbolKind.Enum,
            DMLSymbolKind.LAYOUT: SymbolKind.Namespace,
        }
        
        # Convert location
        one_range = self.location.span.range.to_one_indexed()
        lsp_range = LspRange(
            start=LspPosition(line=one_range.start.line, character=one_range.start.column),
            end=LspPosition(line=one_range.end.line, character=one_range.end.column)
        )
        
        # Convert children
        lsp_children = [child.to_lsp_document_symbol() for child in self.children]
        
        return LspDocumentSymbol(
            name=self.name,
            kind=kind_map.get(self.kind, SymbolKind.Variable),
            range=lsp_range,
            selection_range=lsp_range,  # For now, use same range
            detail=self.detail,
            children=lsp_children if lsp_children else None
        )


@dataclass
class DMLCompletionItem:
    """A completion item for DML code."""
    label: str
    kind: DMLSymbolKind
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    filter_text: Optional[str] = None
    sort_text: Optional[str] = None
    
    def to_lsp_completion_item(self) -> LspCompletionItem:
        """Convert to LSP completion item."""
        # Map DML symbol kinds to LSP completion item kinds
        kind_map = {
            DMLSymbolKind.DEVICE: CompletionItemKind.Class,
            DMLSymbolKind.BANK: CompletionItemKind.Module,
            DMLSymbolKind.REGISTER: CompletionItemKind.Property,
            DMLSymbolKind.FIELD: CompletionItemKind.Field,
            DMLSymbolKind.METHOD: CompletionItemKind.Method,
            DMLSymbolKind.PARAMETER: CompletionItemKind.Variable,
            DMLSymbolKind.ATTRIBUTE: CompletionItemKind.Property,
            DMLSymbolKind.TEMPLATE: CompletionItemKind.Interface,
            DMLSymbolKind.CONNECT: CompletionItemKind.Event,
            DMLSymbolKind.INTERFACE: CompletionItemKind.Interface,
            DMLSymbolKind.PORT: CompletionItemKind.Event,
            DMLSymbolKind.IMPLEMENT: CompletionItemKind.Constructor,
            DMLSymbolKind.VARIABLE: CompletionItemKind.Variable,
            DMLSymbolKind.CONSTANT: CompletionItemKind.Constant,
            DMLSymbolKind.TYPEDEF: CompletionItemKind.TypeParameter,
            DMLSymbolKind.STRUCT: CompletionItemKind.Struct,
            DMLSymbolKind.BITORDER: CompletionItemKind.Enum,
            DMLSymbolKind.LAYOUT: CompletionItemKind.Module,
        }
        
        documentation_markup = None
        if self.documentation:
            documentation_markup = MarkupContent(
                kind=MarkupKind.Markdown,
                value=self.documentation
            )
        
        return LspCompletionItem(
            label=self.label,
            kind=kind_map.get(self.kind, CompletionItemKind.Text),
            detail=self.detail,
            documentation=documentation_markup,
            insert_text=self.insert_text or self.label,
            filter_text=self.filter_text,
            sort_text=self.sort_text
        )


@dataclass
class DMLHover:
    """Hover information for DML code."""
    content: str
    range: Optional[ZeroRange] = None
    
    def to_lsp_hover(self) -> LspHover:
        """Convert to LSP hover."""
        markup_content = MarkupContent(
            kind=MarkupKind.Markdown,
            value=self.content
        )
        
        lsp_range = None
        if self.range:
            one_range = self.range.to_one_indexed()
            lsp_range = LspRange(
                start=LspPosition(line=one_range.start.line, character=one_range.start.column),
                end=LspPosition(line=one_range.end.line, character=one_range.end.column)
            )
        
        return LspHover(contents=markup_content, range=lsp_range)


def path_to_uri(path: Path) -> str:
    """Convert a file path to a URI."""
    return path.as_uri()


def uri_to_path(uri: str) -> Path:
    """Convert a URI to a file path."""
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != 'file':
        raise ValueError(f"Only file URIs are supported, got: {uri}")
    return Path(urllib.parse.unquote(parsed.path))


def lsp_position_to_zero_indexed(lsp_pos: LspPosition) -> ZeroPosition:
    """Convert LSP position (one-indexed) to zero-indexed position."""
    return ZeroPosition(
        line=max(0, lsp_pos.line),
        column=max(0, lsp_pos.character)
    )


def lsp_range_to_zero_indexed(lsp_range: LspRange) -> ZeroRange:
    """Convert LSP range (one-indexed) to zero-indexed range."""
    return ZeroRange(
        start=lsp_position_to_zero_indexed(lsp_range.start),
        end=lsp_position_to_zero_indexed(lsp_range.end)
    )


def create_edit_for_location(location: DMLLocation, new_text: str) -> DMLTextEdit:
    """Create a text edit for the given location and text."""
    return DMLTextEdit(range=location.span.range, new_text=new_text)


# Supported initialization options
@dataclass
class LSPInitializationOptions:
    """Initialization options for the LSP server."""
    compile_commands_dir: Optional[str] = None
    compile_commands_file: Optional[str] = None
    linting_enabled: bool = True
    lint_config_file: Optional[str] = None
    max_diagnostics_per_file: int = 100
    log_level: str = "info"
    
    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'LSPInitializationOptions':
        """Create from initialization options dictionary."""
        if data is None:
            return cls()
        
        return cls(
            compile_commands_dir=data.get('compile_commands_dir'),
            compile_commands_file=data.get('compile_commands_file'),
            linting_enabled=data.get('linting_enabled', True),
            lint_config_file=data.get('lint_config_file'),
            max_diagnostics_per_file=data.get('max_diagnostics_per_file', 100),
            log_level=data.get('log_level', 'info')
        )