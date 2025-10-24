"""
DML Top-level Structure Analysis

Provides analysis and representation of top-level DML constructs including
file-level declarations, imports, and overall program structure. This module
corresponds to the Rust implementation in src/analysis/structure/toplevel.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from .expressions import Expression, DMLString
from .statements import Statement
from .objects import DMLObject, Device, Template, ObjectAnalyzer
from .types import DMLType, TypeRegistry, TypeAnalyzer


class DeclarationKind(Enum):
    """Types of top-level declarations."""
    DML_VERSION = "dml_version"
    IMPORT = "import"
    DEVICE = "device"
    TEMPLATE = "template"
    TYPEDEF = "typedef"
    STRUCT = "struct"
    UNION = "union"
    ENUM = "enum"
    CONSTANT = "constant"
    EXTERN = "extern"


@dataclass
class TopLevelDeclaration:
    """Base class for top-level declarations."""
    span: ZeroSpan
    kind: DeclarationKind
    name: str
    
    def get_name(self) -> str:
        """Get declaration name."""
        return self.name


@dataclass
class DMLVersionDeclaration(TopLevelDeclaration):
    """DML version declaration."""
    version: str
    
    def __post_init__(self):
        self.kind = DeclarationKind.DML_VERSION
        self.name = f"dml {self.version}"


@dataclass
class ImportDeclaration(TopLevelDeclaration):
    """Import declaration."""
    module_path: str
    is_library: bool = False
    resolved_path: Optional[Path] = None
    
    def __post_init__(self):
        self.kind = DeclarationKind.IMPORT
        self.name = self.module_path
    
    def get_module_name(self) -> str:
        """Get the module name from path."""
        if '/' in self.module_path:
            return self.module_path.split('/')[-1]
        return self.module_path


@dataclass
class DeviceDeclaration(TopLevelDeclaration):
    """Device declaration."""
    device: Device
    
    def __post_init__(self):
        self.kind = DeclarationKind.DEVICE
        self.name = self.device.name.value


@dataclass
class TemplateDeclaration(TopLevelDeclaration):
    """Template declaration."""
    template: Template
    
    def __post_init__(self):
        self.kind = DeclarationKind.TEMPLATE
        self.name = self.template.name.value


@dataclass
class TypedefDeclaration(TopLevelDeclaration):
    """Typedef declaration."""
    target_type: DMLType
    
    def __post_init__(self):
        self.kind = DeclarationKind.TYPEDEF


@dataclass
class StructDeclaration(TopLevelDeclaration):
    """Struct declaration."""
    struct_type: DMLType
    
    def __post_init__(self):
        self.kind = DeclarationKind.STRUCT


@dataclass
class UnionDeclaration(TopLevelDeclaration):
    """Union declaration."""
    union_type: DMLType
    
    def __post_init__(self):
        self.kind = DeclarationKind.UNION


@dataclass
class EnumDeclaration(TopLevelDeclaration):
    """Enum declaration."""
    enum_type: DMLType
    
    def __post_init__(self):
        self.kind = DeclarationKind.ENUM


@dataclass
class ConstantDeclaration(TopLevelDeclaration):
    """Constant declaration."""
    const_type: DMLType
    value: Expression
    
    def __post_init__(self):
        self.kind = DeclarationKind.CONSTANT


@dataclass
class ExternDeclaration(TopLevelDeclaration):
    """External declaration."""
    extern_type: DMLType
    is_function: bool = False
    
    def __post_init__(self):
        self.kind = DeclarationKind.EXTERN


@dataclass
class DMLFile:
    """Represents a complete DML file."""
    file_path: Path
    content: str
    declarations: List[TopLevelDeclaration] = field(default_factory=list)
    errors: List[DMLError] = field(default_factory=list)
    
    # Parsed information
    dml_version: Optional[str] = None
    imports: List[ImportDeclaration] = field(default_factory=list)
    devices: List[DeviceDeclaration] = field(default_factory=list)
    templates: List[TemplateDeclaration] = field(default_factory=list)
    types: List[Union[TypedefDeclaration, StructDeclaration, UnionDeclaration, EnumDeclaration]] = field(default_factory=list)
    constants: List[ConstantDeclaration] = field(default_factory=list)
    externs: List[ExternDeclaration] = field(default_factory=list)
    
    def add_declaration(self, decl: TopLevelDeclaration) -> None:
        """Add a top-level declaration."""
        self.declarations.append(decl)
        
        # Categorize declaration
        if isinstance(decl, DMLVersionDeclaration):
            self.dml_version = decl.version
        elif isinstance(decl, ImportDeclaration):
            self.imports.append(decl)
        elif isinstance(decl, DeviceDeclaration):
            self.devices.append(decl)
        elif isinstance(decl, TemplateDeclaration):
            self.templates.append(decl)
        elif isinstance(decl, (TypedefDeclaration, StructDeclaration, UnionDeclaration, EnumDeclaration)):
            self.types.append(decl)
        elif isinstance(decl, ConstantDeclaration):
            self.constants.append(decl)
        elif isinstance(decl, ExternDeclaration):
            self.externs.append(decl)
    
    def get_main_device(self) -> Optional[DeviceDeclaration]:
        """Get the main device declaration."""
        if self.devices:
            return self.devices[0]  # First device is typically main
        return None
    
    def find_template(self, name: str) -> Optional[TemplateDeclaration]:
        """Find template by name."""
        for template in self.templates:
            if template.name == name:
                return template
        return None
    
    def has_errors(self) -> bool:
        """Check if file has parsing errors."""
        return len(self.errors) > 0


@dataclass
class DMLProject:
    """Represents a DML project with multiple files."""
    root_path: Path
    files: Dict[Path, DMLFile] = field(default_factory=dict)
    dependencies: Dict[Path, Set[Path]] = field(default_factory=dict)
    main_file: Optional[Path] = None
    
    def add_file(self, file_path: Path, dml_file: DMLFile) -> None:
        """Add a file to the project."""
        self.files[file_path] = dml_file
        
        # Set as main file if it's the first device file
        if self.main_file is None and dml_file.devices:
            self.main_file = file_path
    
    def get_file(self, file_path: Path) -> Optional[DMLFile]:
        """Get file by path."""
        return self.files.get(file_path)
    
    def get_main_file(self) -> Optional[DMLFile]:
        """Get the main file."""
        if self.main_file:
            return self.files.get(self.main_file)
        return None
    
    def resolve_imports(self) -> None:
        """Resolve import dependencies."""
        for file_path, dml_file in self.files.items():
            file_deps = set()
            
            for import_decl in dml_file.imports:
                resolved_path = self._resolve_import_path(import_decl.module_path, file_path)
                if resolved_path:
                    import_decl.resolved_path = resolved_path
                    file_deps.add(resolved_path)
                else:
                    error = DMLError(
                        kind=DMLErrorKind.IMPORT_ERROR,
                        message=f"Cannot resolve import: {import_decl.module_path}",
                        span=import_decl.span
                    )
                    dml_file.errors.append(error)
            
            self.dependencies[file_path] = file_deps
    
    def _resolve_import_path(self, module_path: str, from_file: Path) -> Optional[Path]:
        """Resolve import path relative to file."""
        # Try relative to current file
        relative_path = from_file.parent / f"{module_path}.dml"
        if relative_path.exists():
            return relative_path
        
        # Try relative to project root
        root_relative = self.root_path / f"{module_path}.dml"
        if root_relative.exists():
            return root_relative
        
        # Try as absolute path
        absolute_path = Path(module_path)
        if absolute_path.suffix != '.dml':
            absolute_path = absolute_path.with_suffix('.dml')
        if absolute_path.exists():
            return absolute_path
        
        return None
    
    def get_dependency_order(self) -> List[Path]:
        """Get files in dependency order (topological sort)."""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(file_path: Path) -> None:
            if file_path in temp_visited:
                # Circular dependency detected
                return
            if file_path in visited:
                return
            
            temp_visited.add(file_path)
            
            # Visit dependencies first
            for dep in self.dependencies.get(file_path, set()):
                if dep in self.files:
                    visit(dep)
            
            temp_visited.remove(file_path)
            visited.add(file_path)
            result.append(file_path)
        
        # Visit all files
        for file_path in self.files:
            if file_path not in visited:
                visit(file_path)
        
        return result
    
    def check_circular_dependencies(self) -> List[DMLError]:
        """Check for circular dependencies."""
        errors = []
        visited = set()
        temp_visited = set()
        
        def visit(file_path: Path, path: List[Path]) -> None:
            if file_path in temp_visited:
                # Circular dependency found
                cycle_start = path.index(file_path)
                cycle = path[cycle_start:] + [file_path]
                cycle_str = " -> ".join(str(p) for p in cycle)
                
                error = DMLError(
                    kind=DMLErrorKind.CIRCULAR_DEPENDENCY,
                    message=f"Circular dependency detected: {cycle_str}",
                    span=ZeroSpan(str(file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
                )
                errors.append(error)
                return
            
            if file_path in visited:
                return
            
            temp_visited.add(file_path)
            
            for dep in self.dependencies.get(file_path, set()):
                if dep in self.files:
                    visit(dep, path + [file_path])
            
            temp_visited.remove(file_path)
            visited.add(file_path)
        
        for file_path in self.files:
            if file_path not in visited:
                visit(file_path, [])
        
        return errors
    
    def get_all_templates(self) -> List[TemplateDeclaration]:
        """Get all templates in the project."""
        templates = []
        for dml_file in self.files.values():
            templates.extend(dml_file.templates)
        return templates
    
    def get_all_devices(self) -> List[DeviceDeclaration]:
        """Get all devices in the project."""
        devices = []
        for dml_file in self.files.values():
            devices.extend(dml_file.devices)
        return devices


class TopLevelAnalyzer:
    """Analyzes top-level DML structure."""
    
    def __init__(self):
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
        self.type_registry = TypeRegistry()
        self.type_analyzer = TypeAnalyzer(self.type_registry)
        self.object_analyzer = ObjectAnalyzer()
    
    def analyze_file(self, dml_file: DMLFile) -> None:
        """Analyze a DML file."""
        # Validate DML version
        if dml_file.dml_version:
            self._validate_dml_version(dml_file.dml_version, dml_file.file_path)
        else:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Missing DML version declaration",
                span=ZeroSpan(str(dml_file.file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
        
        # Analyze type declarations
        for type_decl in dml_file.types:
            if hasattr(type_decl, 'struct_type'):
                self.type_analyzer.analyze_type_declaration(type_decl.struct_type)
            elif hasattr(type_decl, 'union_type'):
                self.type_analyzer.analyze_type_declaration(type_decl.union_type)
            elif hasattr(type_decl, 'enum_type'):
                self.type_analyzer.analyze_type_declaration(type_decl.enum_type)
            elif hasattr(type_decl, 'target_type'):
                self.type_analyzer.analyze_type_declaration(type_decl.target_type)
        
        # Analyze devices and templates
        for device_decl in dml_file.devices:
            self.object_analyzer.analyze_object(device_decl.device)
        
        for template_decl in dml_file.templates:
            self.object_analyzer.analyze_object(template_decl.template)
        
        # Collect errors from sub-analyzers
        self.errors.extend(self.type_analyzer.get_errors())
        self.errors.extend(self.object_analyzer.get_errors())
        self.references.extend(self.object_analyzer.get_references())
    
    def analyze_project(self, project: DMLProject) -> None:
        """Analyze an entire DML project."""
        # Check for circular dependencies
        circular_errors = project.check_circular_dependencies()
        self.errors.extend(circular_errors)
        
        # Resolve imports
        project.resolve_imports()
        
        # Analyze files in dependency order
        for file_path in project.get_dependency_order():
            dml_file = project.get_file(file_path)
            if dml_file:
                self.analyze_file(dml_file)
        
        # Cross-file analysis
        self._analyze_template_usage(project)
        self._validate_device_structure(project)
    
    def _validate_dml_version(self, version: str, file_path: Path) -> None:
        """Validate DML version."""
        supported_versions = ["1.4", "1.2"]
        if version not in supported_versions:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message=f"Unsupported DML version: {version}. Supported versions: {', '.join(supported_versions)}",
                span=ZeroSpan(str(file_path), ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
    
    def _analyze_template_usage(self, project: DMLProject) -> None:
        """Analyze template usage across the project."""
        all_templates = {t.name: t for t in project.get_all_templates()}
        
        # Check that all referenced templates exist
        for dml_file in project.files.values():
            for device_decl in dml_file.devices:
                device = device_decl.device
                for template_name in device.templates:
                    if template_name not in all_templates:
                        error = DMLError(
                            kind=DMLErrorKind.TEMPLATE_ERROR,
                            message=f"Template not found: {template_name}",
                            span=device.span
                        )
                        self.errors.append(error)
                    else:
                        # Add template reference
                        node_ref = NodeRef(template_name, device.span)
                        reference = SymbolReference(
                            node_ref=node_ref,
                            kind=ReferenceKind.TEMPLATE,
                            location=device.span
                        )
                        self.references.append(reference)
    
    def _validate_device_structure(self, project: DMLProject) -> None:
        """Validate device structure across project."""
        devices = project.get_all_devices()
        
        if not devices:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="No devices found in project",
                span=ZeroSpan("project", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
        elif len(devices) > 1:
            # Multiple devices - check for conflicts
            device_names = set()
            for device_decl in devices:
                device_name = device_decl.device.name.value
                if device_name in device_names:
                    error = DMLError(
                        kind=DMLErrorKind.DUPLICATE_SYMBOL,
                        message=f"Duplicate device name: {device_name}",
                        span=device_decl.device.span
                    )
                    self.errors.append(error)
                device_names.add(device_name)
    
    def get_errors(self) -> List[DMLError]:
        """Get all analysis errors."""
        return self.errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get all symbol references."""
        return self.references
    
    def get_type_registry(self) -> TypeRegistry:
        """Get the type registry."""
        return self.type_registry


def create_dml_file(file_path: Path, content: str) -> DMLFile:
    """Helper to create DML file objects."""
    return DMLFile(file_path=file_path, content=content)


def create_dml_project(root_path: Path) -> DMLProject:
    """Helper to create DML project objects."""
    return DMLProject(root_path=root_path)


__all__ = [
    'DeclarationKind', 'TopLevelDeclaration', 'DMLVersionDeclaration', 'ImportDeclaration',
    'DeviceDeclaration', 'TemplateDeclaration', 'TypedefDeclaration', 'StructDeclaration',
    'UnionDeclaration', 'EnumDeclaration', 'ConstantDeclaration', 'ExternDeclaration',
    'DMLFile', 'DMLProject', 'TopLevelAnalyzer', 'create_dml_file', 'create_dml_project'
]