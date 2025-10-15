"""
Analysis module for the DML Language Server.

Provides parsing, semantic analysis, and symbol resolution for DML code.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..config import Config
from ..file_management import FileManager
from ..span import ZeroSpan, ZeroPosition, ZeroRange, SpanBuilder
from ..lsp_data import DMLDiagnostic, DMLDiagnosticSeverity, DMLLocation, DMLSymbol, DMLSymbolKind

logger = logging.getLogger(__name__)


class DMLErrorKind(Enum):
    """Types of DML errors."""
    SYNTAX_ERROR = "syntax_error"
    SEMANTIC_ERROR = "semantic_error"
    TYPE_ERROR = "type_error"
    UNDEFINED_SYMBOL = "undefined_symbol"
    DUPLICATE_SYMBOL = "duplicate_symbol"
    IMPORT_ERROR = "import_error"


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
class SymbolReference:
    """A reference to a symbol."""
    symbol_name: str
    location: DMLLocation
    definition_location: Optional[DMLLocation] = None


@dataclass
class SymbolDefinition:
    """A symbol definition."""
    symbol: DMLSymbol
    references: List[SymbolReference] = field(default_factory=list)


class IsolatedAnalysis:
    """Analysis of a single file without dependencies."""
    
    def __init__(self, file_path: Path, content: str):
        self.file_path = file_path
        self.content = content
        self.span_builder = SpanBuilder(str(file_path))
        self.span_builder.set_content(content)
        
        # Analysis results
        self.errors: List[DMLError] = []
        self.symbols: List[DMLSymbol] = []
        self.symbol_table: Dict[str, SymbolDefinition] = {}
        self.imports: List[str] = []
        self.dml_version: Optional[str] = None
        
        # Parse the file
        self._parse()
    
    def _parse(self) -> None:
        """Parse the file content."""
        try:
            # Basic parsing - this would be much more sophisticated in a real implementation
            from .parsing import DMLParser
            parser = DMLParser(self.content, str(self.file_path))
            
            # Parse and extract information
            self.dml_version = parser.extract_dml_version()
            self.imports = parser.extract_imports()
            self.symbols = parser.extract_symbols()
            self.errors = parser.get_errors()
            
            # Build symbol table
            for symbol in self.symbols:
                if symbol.name in self.symbol_table:
                    # Duplicate symbol
                    error = DMLError(
                        kind=DMLErrorKind.DUPLICATE_SYMBOL,
                        message=f"Duplicate symbol '{symbol.name}'",
                        span=symbol.location.span
                    )
                    self.errors.append(error)
                else:
                    self.symbol_table[symbol.name] = SymbolDefinition(symbol=symbol)
                    
        except Exception as e:
            logger.error(f"Failed to parse {self.file_path}: {e}")
            # Add a general syntax error
            error = DMLError(
                kind=DMLErrorKind.SYNTAX_ERROR,
                message=f"Parse error: {e}",
                span=ZeroSpan(str(self.file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
    
    def get_symbol_at_position(self, position: ZeroPosition) -> Optional[DMLSymbol]:
        """Get the symbol at the given position."""
        for symbol in self.symbols:
            if symbol.location.span.contains_position(position):
                return symbol
        return None
    
    def find_symbol(self, name: str) -> Optional[SymbolDefinition]:
        """Find a symbol by name."""
        return self.symbol_table.get(name)
    
    def get_diagnostics(self) -> List[DMLDiagnostic]:
        """Get all diagnostics for this file."""
        return [error.to_diagnostic() for error in self.errors]


class DeviceAnalysis:
    """Analysis of a device and its dependencies."""
    
    def __init__(self, config: Config, file_manager: FileManager):
        self.config = config
        self.file_manager = file_manager
        self.file_analyses: Dict[Path, IsolatedAnalysis] = {}
        self.global_symbol_table: Dict[str, List[SymbolDefinition]] = {}
        self.dependency_order: List[Path] = []
    
    def analyze_file(self, file_path: Path, content: str) -> List[DMLError]:
        """
        Analyze a single file and its dependencies.
        
        Args:
            file_path: Path to the file to analyze
            content: Content of the file
            
        Returns:
            List of errors found
        """
        file_path = file_path.resolve()
        
        try:
            # Create isolated analysis
            analysis = IsolatedAnalysis(file_path, content)
            self.file_analyses[file_path] = analysis
            
            # Analyze dependencies
            self._analyze_dependencies(file_path)
            
            # Perform cross-file analysis
            self._analyze_cross_file_references(file_path)
            
            return analysis.errors
            
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            error = DMLError(
                kind=DMLErrorKind.SYNTAX_ERROR,
                message=f"Analysis error: {e}",
                span=ZeroSpan(str(file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            return [error]
    
    def _analyze_dependencies(self, file_path: Path) -> None:
        """Analyze dependencies of a file."""
        dependencies = self.file_manager.get_dependencies(file_path)
        
        for dep_path in dependencies:
            if dep_path not in self.file_analyses:
                try:
                    # Read dependency content
                    with open(dep_path, 'r', encoding='utf-8') as f:
                        dep_content = f.read()
                    
                    # Analyze dependency
                    dep_analysis = IsolatedAnalysis(dep_path, dep_content)
                    self.file_analyses[dep_path] = dep_analysis
                    
                    # Recursively analyze its dependencies
                    self._analyze_dependencies(dep_path)
                    
                except Exception as e:
                    logger.error(f"Failed to analyze dependency {dep_path}: {e}")
    
    def _analyze_cross_file_references(self, file_path: Path) -> None:
        """Analyze cross-file symbol references."""
        analysis = self.file_analyses.get(file_path)
        if not analysis:
            return
        
        # Build global symbol table
        self._build_global_symbol_table()
        
        # Resolve imports and references
        for import_name in analysis.imports:
            if not self._resolve_import(file_path, import_name):
                error = DMLError(
                    kind=DMLErrorKind.IMPORT_ERROR,
                    message=f"Cannot resolve import '{import_name}'",
                    span=ZeroSpan(str(file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
                )
                analysis.errors.append(error)
    
    def _build_global_symbol_table(self) -> None:
        """Build a global symbol table from all analyzed files."""
        self.global_symbol_table.clear()
        
        for file_path, analysis in self.file_analyses.items():
            for symbol_name, symbol_def in analysis.symbol_table.items():
                if symbol_name not in self.global_symbol_table:
                    self.global_symbol_table[symbol_name] = []
                self.global_symbol_table[symbol_name].append(symbol_def)
    
    def _resolve_import(self, file_path: Path, import_name: str) -> bool:
        """Try to resolve an import."""
        # This would involve looking up the import in include paths
        # and checking if the imported file exists and has been analyzed
        include_paths = self.config.get_include_paths_for_file(file_path)
        
        for include_path in include_paths:
            import_file = include_path / import_name
            if import_file.exists():
                return True
        
        # Also check relative to current file
        current_dir = file_path.parent
        import_file = current_dir / import_name
        return import_file.exists()
    
    def get_symbol_at_position(self, file_path: Path, position: ZeroPosition) -> Optional[DMLSymbol]:
        """Get symbol at position in a file."""
        analysis = self.file_analyses.get(file_path.resolve())
        if analysis:
            return analysis.get_symbol_at_position(position)
        return None
    
    def find_symbol_definitions(self, symbol_name: str) -> List[SymbolDefinition]:
        """Find all definitions of a symbol across all files."""
        return self.global_symbol_table.get(symbol_name, [])
    
    def get_all_symbols_in_file(self, file_path: Path) -> List[DMLSymbol]:
        """Get all symbols in a file."""
        analysis = self.file_analyses.get(file_path.resolve())
        if analysis:
            return analysis.symbols
        return []
    
    def get_diagnostics_for_file(self, file_path: Path) -> List[DMLDiagnostic]:
        """Get diagnostics for a specific file."""
        analysis = self.file_analyses.get(file_path.resolve())
        if analysis:
            return analysis.get_diagnostics()
        return []
    
    def get_all_diagnostics(self) -> Dict[Path, List[DMLDiagnostic]]:
        """Get diagnostics for all analyzed files."""
        diagnostics = {}
        for file_path, analysis in self.file_analyses.items():
            diagnostics[file_path] = analysis.get_diagnostics()
        return diagnostics
    
    def invalidate_file(self, file_path: Path) -> Set[Path]:
        """Invalidate analysis for a file and return affected files."""
        file_path = file_path.resolve()
        
        # Get all files that depend on this file
        affected_files = self.file_manager.get_all_dependents(file_path)
        affected_files.add(file_path)
        
        # Remove analyses for affected files
        for affected_file in affected_files:
            self.file_analyses.pop(affected_file, None)
        
        return affected_files


# Export main classes
__all__ = [
    "IsolatedAnalysis",
    "DeviceAnalysis", 
    "DMLError",
    "DMLErrorKind",
    "SymbolReference",
    "SymbolDefinition"
]