"""
Enhanced Analysis module for the DML Language Server.

Provides comprehensive parsing, semantic analysis, symbol resolution, and reference tracking for DML code.
This is an enhanced version porting concepts from the Rust implementation.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor

from ..config import Config
from ..file_management import FileManager
from ..span import ZeroSpan, ZeroPosition, ZeroRange, SpanBuilder
from ..lsp_data import DMLDiagnostic, DMLDiagnosticSeverity, DMLLocation, DMLSymbol, DMLSymbolKind
from .types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from .parsing.enhanced_parser import EnhancedDMLParser, TemplateDeclaration, DeviceDeclaration, DMLVersionDeclaration
from .parsing.template_system import TemplateSystem

logger = logging.getLogger(__name__)


@dataclass
class SymbolDefinition:
    """Represents a symbol definition with references."""
    symbol: DMLSymbol
    references: List[SymbolReference] = field(default_factory=list)
    scope_chain: List[str] = field(default_factory=list)
    
    def add_reference(self, ref: SymbolReference):
        """Add a reference to this symbol."""
        self.references.append(ref)


class SymbolScope:
    """Enhanced scope management for symbol resolution."""
    
    def __init__(self, name: str, span: ZeroSpan, parent: Optional['SymbolScope'] = None):
        self.name = name
        self.span = span
        self.parent = parent
        self.children: List['SymbolScope'] = []
        self.symbols: Dict[str, SymbolDefinition] = {}
        self.references: List[SymbolReference] = []
        
        if parent:
            parent.children.append(self)
    
    def add_symbol(self, symbol: DMLSymbol) -> SymbolDefinition:
        """Add a symbol to this scope."""
        definition = SymbolDefinition(symbol=symbol, scope_chain=self.get_scope_chain())
        self.symbols[symbol.name] = definition
        return definition
    
    def add_reference(self, ref: SymbolReference):
        """Add a reference to this scope."""
        self.references.append(ref)
    
    def resolve_symbol(self, name: str) -> Optional[SymbolDefinition]:
        """Resolve a symbol by name, searching up the scope chain."""
        # First check current scope
        if name in self.symbols:
            return self.symbols[name]
        
        # Check parent scopes
        if self.parent:
            return self.parent.resolve_symbol(name)
        
        return None
    
    def get_scope_chain(self) -> List[str]:
        """Get the full scope chain from root to this scope."""
        if self.parent:
            return self.parent.get_scope_chain() + [self.name]
        return [self.name]
    
    def find_scope_at_position(self, pos: ZeroPosition) -> Optional['SymbolScope']:
        """Find the innermost scope containing the given position."""
        if not self.span.range.contains_position(pos):
            return None
        
        # Check children first (innermost scope)
        for child in self.children:
            if result := child.find_scope_at_position(pos):
                return result
        
        # If no child contains the position, this scope does
        return self
    
    def get_all_symbols(self, include_children: bool = True) -> List[SymbolDefinition]:
        """Get all symbols in this scope and optionally its children."""
        symbols = list(self.symbols.values())
        
        if include_children:
            for child in self.children:
                symbols.extend(child.get_all_symbols(include_children=True))
        
        return symbols


class AdvancedSymbolTable:
    """Enhanced symbol table with cross-file resolution and reference tracking."""
    
    def __init__(self):
        self.global_symbols: Dict[str, SymbolDefinition] = {}
        self.file_scopes: Dict[Path, SymbolScope] = {}
        self.references: Dict[str, List[SymbolReference]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def create_file_scope(self, file_path: Path, span: ZeroSpan) -> SymbolScope:
        """Create a root scope for a file."""
        with self._lock:
            scope = SymbolScope(name=f"file:{file_path.name}", span=span)
            self.file_scopes[file_path] = scope
            return scope
    
    def add_global_symbol(self, symbol: DMLSymbol) -> SymbolDefinition:
        """Add a symbol to the global scope."""
        with self._lock:
            definition = SymbolDefinition(symbol=symbol, scope_chain=["global"])
            self.global_symbols[symbol.name] = definition
            return definition
    
    def add_reference(self, ref: SymbolReference):
        """Add a reference to the symbol table."""
        with self._lock:
            self.references[ref.node_ref.name].append(ref)
    
    def resolve_symbol(self, name: str, file_path: Optional[Path] = None, 
                      position: Optional[ZeroPosition] = None) -> Optional[SymbolDefinition]:
        """Resolve a symbol with context-aware lookup."""
        with self._lock:
            # If we have file and position context, start with local scope
            if file_path and position and file_path in self.file_scopes:
                file_scope = self.file_scopes[file_path]
                if local_scope := file_scope.find_scope_at_position(position):
                    if symbol := local_scope.resolve_symbol(name):
                        return symbol
            
            # Check file-level scope
            if file_path and file_path in self.file_scopes:
                if symbol := self.file_scopes[file_path].resolve_symbol(name):
                    return symbol
            
            # Check global scope
            return self.global_symbols.get(name)
    
    def find_references(self, symbol_name: str) -> List[SymbolReference]:
        """Find all references to a symbol."""
        with self._lock:
            return self.references.get(symbol_name, []).copy()
    
    def get_symbols_in_scope(self, file_path: Path, position: ZeroPosition) -> List[SymbolDefinition]:
        """Get all symbols visible from a given position."""
        with self._lock:
            symbols = []
            
            if file_path in self.file_scopes:
                file_scope = self.file_scopes[file_path]
                if local_scope := file_scope.find_scope_at_position(position):
                    # Get symbols from current scope and parents
                    current = local_scope
                    while current:
                        symbols.extend(current.symbols.values())
                        current = current.parent
            
            # Add global symbols
            symbols.extend(self.global_symbols.values())
            
            return symbols


class IsolatedAnalysis:
    """Enhanced analysis of a single file with advanced scope and reference tracking."""
    
    def __init__(self, file_path: Path, content: str):
        self.file_path = file_path
        self.content = content
        self.span_builder = SpanBuilder(str(file_path))
        self.span_builder.set_content(content)
        
        # Create file-level scope
        file_span = ZeroSpan(
            file_path=str(file_path),
            range=ZeroRange(
                start=ZeroPosition(line=0, column=0),
                end=ZeroPosition(line=len(content.splitlines()), column=0)
            )
        )
        self.root_scope = SymbolScope(name=f"file:{file_path.name}", span=file_span)
        
        # Analysis results
        self.errors: List[DMLError] = []
        self.symbols: List[DMLSymbol] = []
        self.symbol_definitions: Dict[str, SymbolDefinition] = {}
        self.references: List[SymbolReference] = []
        self.imports: List[str] = []
        self.dml_version: Optional[str] = None
        self.dependencies: Set[Path] = set()
        
        # Enhanced parsing components
        self.enhanced_parser: Optional[EnhancedDMLParser] = None
        self.template_system = TemplateSystem()
        self.ast_declarations: List = []
        
        # Parse the file
        self._parse()
    
    def _parse(self) -> None:
        """Parse the DML file using enhanced parser and template system."""
        try:
            # Try enhanced parser first
            try:
                self.enhanced_parser = EnhancedDMLParser(self.content, str(self.file_path))
                self.ast_declarations = self.enhanced_parser.parse()
                
                # Extract basic information
                self.errors = self.enhanced_parser.get_errors()
                self.symbols = self.enhanced_parser.get_symbols()
                self.references = self.enhanced_parser.get_references()
                self.imports = self.enhanced_parser.imports
                self.dml_version = self.enhanced_parser.dml_version
                
                # Initialize template system with global scope
                self.template_system.initialize_template_scope(self.root_scope)
                
                # Validate file structure (DML language rules)
                self._validate_file_structure()
                
                # Process AST declarations
                self._process_ast_declarations()
                
                logger.debug(f"Enhanced parser processed {len(self.symbols)} symbols, {len(self.errors)} errors")
                
            except Exception as enhanced_error:
                logger.warning(f"Enhanced parser failed for {self.file_path}: {enhanced_error}, falling back to basic parser")
                
                # Fallback to basic parser
                from .parsing import DMLParser
                parser = DMLParser(self.content, str(self.file_path))
                
                # Parse and extract information
                self.dml_version = parser.extract_dml_version()
                self.imports = parser.extract_imports()
                self.symbols = parser.extract_symbols()
                self.errors = parser.get_errors()
            
            # Build symbol table
            for symbol in self.symbols:
                if symbol.name in self.symbol_definitions:
                    # Duplicate symbol
                    error = DMLError(
                        kind=DMLErrorKind.DUPLICATE_SYMBOL,
                        message=f"Duplicate symbol '{symbol.name}'",
                        span=symbol.location.span
                    )
                    self.errors.append(error)
                else:
                    self.symbol_definitions[symbol.name] = SymbolDefinition(symbol=symbol)
                    # Also add to scope
                    self.root_scope.add_symbol(symbol)
                    
        except Exception as e:
            logger.error(f"Failed to parse {self.file_path}: {e}")
            # Add a general syntax error
            error = DMLError(
                kind=DMLErrorKind.SYNTAX_ERROR,
                message=f"Parse error: {e}",
                span=ZeroSpan(str(self.file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
    
    def _validate_file_structure(self) -> None:
        """Validate DML file structure according to language rules."""
        if not self.ast_declarations:
            return
        
        # Track what we've seen
        seen_dml_version = False
        seen_device = False
        declaration_index = 0
        
        for i, declaration in enumerate(self.ast_declarations):
            # Check DML version position (must be first)
            if isinstance(declaration, DMLVersionDeclaration):
                if i != 0:
                    error = DMLError(
                        kind=DMLErrorKind.SEMANTIC_ERROR,
                        message="Version declaration must be first statement in file",
                        span=declaration.span
                    )
                    self.errors.append(error)
                seen_dml_version = True
                declaration_index = i
            
            # Check device position (must be second, right after dml version)
            elif isinstance(declaration, DeviceDeclaration):
                if seen_dml_version and i != 1:
                    error = DMLError(
                        kind=DMLErrorKind.SEMANTIC_ERROR,
                        message="Device declaration must be second statement in file",
                        span=declaration.span
                    )
                    self.errors.append(error)
                seen_device = True
                declaration_index = i
            
            # Other top-level declarations should come after device
            # (This is enforced by the parser structure)
    
    def _process_ast_declarations(self) -> None:
        """Process AST declarations for template resolution and symbol extraction."""
        templates_to_process = []
        devices_to_process = []
        
        # First pass: collect templates and devices
        for declaration in self.ast_declarations:
            if isinstance(declaration, TemplateDeclaration):
                templates_to_process.append(declaration)
                self.template_system.add_template(declaration)
            elif isinstance(declaration, DeviceDeclaration):
                devices_to_process.append(declaration)
        
        # Second pass: process devices with template application
        for device in devices_to_process:
            if device.templates:
                logger.debug(f"Applying templates {device.templates} to device {device.name}")
                
                # Apply templates to device
                enhanced_device = self.template_system.process_device(device)
                
                # Extract additional symbols from template application
                template_symbols = self.template_system.applicator.get_template_symbols(device.name)
                self.symbols.extend(template_symbols)
                
                # Add template symbols to symbol definitions
                for symbol in template_symbols:
                    if symbol.name not in self.symbol_definitions:
                        self.symbol_definitions[symbol.name] = SymbolDefinition(symbol=symbol)
                        self.root_scope.add_symbol(symbol)
        
        # Add template system errors
        template_errors = self.template_system.get_all_errors()
        if template_errors:
            logger.debug(f"Template system found {len(template_errors)} errors")
            self.errors.extend(template_errors)
    
    def get_symbol_at_position(self, position: ZeroPosition) -> Optional[DMLSymbol]:
        """Get the symbol at the given position."""
        for symbol in self.symbols:
            if symbol.location.span.contains_position(position):
                return symbol
        return None
    
    def find_symbol(self, name: str) -> Optional[SymbolDefinition]:
        """Find a symbol by name."""
        return self.symbol_definitions.get(name)
    
    def get_diagnostics(self) -> List[DMLDiagnostic]:
        """Get all diagnostics for this file."""
        return [error.to_diagnostic() for error in self.errors]


class DeviceAnalysis:
    """Enhanced analysis engine for DML device files with advanced symbol resolution."""
    
    def __init__(self, config: Config, file_manager: FileManager):
        self.config = config
        self.file_manager = file_manager
        self.file_analyses: Dict[Path, IsolatedAnalysis] = {}
        
        # Enhanced symbol management
        self.symbol_table = AdvancedSymbolTable()
        self.reference_tracker: Dict[str, List[SymbolReference]] = defaultdict(list)
        self.dependency_graph: Dict[Path, Set[Path]] = defaultdict(set)
        
        # Legacy compatibility
        self.global_symbol_table: Dict[str, List[SymbolDefinition]] = {}
        
        # Thread pool for parallel analysis
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._analysis_lock = threading.RLock()
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
            # Use the new symbol_definitions attribute
            symbol_table = getattr(analysis, 'symbol_definitions', {})
            for symbol_name, symbol_def in symbol_table.items():
                if symbol_name not in self.global_symbol_table:
                    self.global_symbol_table[symbol_name] = []
                self.global_symbol_table[symbol_name].append(symbol_def)
            
            # Also register symbols in the enhanced symbol table
            if hasattr(analysis, 'root_scope'):
                scope = self.symbol_table.create_file_scope(file_path, analysis.root_scope.span)
                for symbol in analysis.symbols:
                    scope.add_symbol(symbol)
    
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
    "SymbolDefinition",
    "NodeRef",
    "ReferenceKind",
    "SymbolScope",
    "AdvancedSymbolTable",
    "TemplateSystem",
    "EnhancedDMLParser",
    "TemplateDeclaration",
    "DeviceDeclaration"
]