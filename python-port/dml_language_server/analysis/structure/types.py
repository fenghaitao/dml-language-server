"""
DML Type Structure Analysis

Provides analysis and representation of DML types, including primitive types,
struct types, function types, and type declarations. This module corresponds
to the Rust implementation in src/analysis/structure/types.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind
from .expressions import Expression, DMLString


class TypeKind(Enum):
    """Types of DML types."""
    PRIMITIVE = "primitive"
    STRUCT = "struct"
    UNION = "union"
    ENUM = "enum"
    ARRAY = "array"
    POINTER = "pointer"
    FUNCTION = "function"
    TEMPLATE = "template"
    VOID = "void"
    AUTO = "auto"
    TYPEDEF = "typedef"


class PrimitiveType(Enum):
    """Primitive DML types."""
    INT = "int"
    UINT = "uint"
    BOOL = "bool"
    CHAR = "char"
    FLOAT = "float"
    DOUBLE = "double"
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"


@dataclass
class DMLType:
    """Base class for all DML types."""
    span: ZeroSpan
    kind: TypeKind
    name: str
    is_const: bool = False
    is_volatile: bool = False
    
    def get_name(self) -> str:
        """Get the type name."""
        return self.name
    
    def is_primitive(self) -> bool:
        """Check if this is a primitive type."""
        return self.kind == TypeKind.PRIMITIVE
    
    def is_pointer(self) -> bool:
        """Check if this is a pointer type."""
        return self.kind == TypeKind.POINTER
    
    def is_array(self) -> bool:
        """Check if this is an array type."""
        return self.kind == TypeKind.ARRAY
    
    def is_function(self) -> bool:
        """Check if this is a function type."""
        return self.kind == TypeKind.FUNCTION
    
    def get_size(self) -> Optional[int]:
        """Get type size in bytes if known."""
        return None  # Override in subclasses


@dataclass
class PrimitiveTypeDecl(DMLType):
    """Primitive type declaration."""
    primitive: PrimitiveType
    bit_width: Optional[int] = None
    
    def __post_init__(self):
        self.kind = TypeKind.PRIMITIVE
        self.name = self.primitive.value
    
    def get_size(self) -> Optional[int]:
        """Get primitive type size."""
        if self.bit_width:
            return (self.bit_width + 7) // 8  # Round up to bytes
        
        # Standard sizes
        size_map = {
            PrimitiveType.BOOL: 1,
            PrimitiveType.CHAR: 1,
            PrimitiveType.INT8: 1,
            PrimitiveType.UINT8: 1,
            PrimitiveType.INT16: 2,
            PrimitiveType.UINT16: 2,
            PrimitiveType.INT32: 4,
            PrimitiveType.UINT32: 4,
            PrimitiveType.INT64: 8,
            PrimitiveType.UINT64: 8,
            PrimitiveType.FLOAT: 4,
            PrimitiveType.DOUBLE: 8,
            PrimitiveType.INT: 4,  # Default int size
            PrimitiveType.UINT: 4,  # Default uint size
        }
        return size_map.get(self.primitive)


@dataclass
class StructType(DMLType):
    """Struct type declaration."""
    fields: List['StructField'] = field(default_factory=list)
    is_packed: bool = False
    
    def __post_init__(self):
        self.kind = TypeKind.STRUCT
    
    def add_field(self, field: 'StructField') -> None:
        """Add a field to the struct."""
        self.fields.append(field)
    
    def find_field(self, name: str) -> Optional['StructField']:
        """Find field by name."""
        for field in self.fields:
            if field.name.value == name:
                return field
        return None
    
    def get_size(self) -> Optional[int]:
        """Calculate struct size."""
        if not self.fields:
            return 0
        
        total_size = 0
        for field in self.fields:
            field_size = field.get_size()
            if field_size is None:
                return None  # Can't determine size
            total_size += field_size
        
        return total_size


@dataclass
class StructField:
    """Field in a struct."""
    span: ZeroSpan
    name: DMLString
    field_type: DMLType
    bit_width: Optional[int] = None
    offset: Optional[int] = None
    
    def get_size(self) -> Optional[int]:
        """Get field size."""
        if self.bit_width:
            return (self.bit_width + 7) // 8
        return self.field_type.get_size()


@dataclass
class UnionType(DMLType):
    """Union type declaration."""
    fields: List[StructField] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = TypeKind.UNION
    
    def add_field(self, field: StructField) -> None:
        """Add a field to the union."""
        self.fields.append(field)
    
    def get_size(self) -> Optional[int]:
        """Get union size (size of largest field)."""
        if not self.fields:
            return 0
        
        max_size = 0
        for field in self.fields:
            field_size = field.get_size()
            if field_size is None:
                return None
            max_size = max(max_size, field_size)
        
        return max_size


@dataclass
class EnumType(DMLType):
    """Enum type declaration."""
    values: List['EnumValue'] = field(default_factory=list)
    underlying_type: Optional[DMLType] = None
    
    def __post_init__(self):
        self.kind = TypeKind.ENUM
    
    def add_value(self, value: 'EnumValue') -> None:
        """Add an enum value."""
        self.values.append(value)
    
    def find_value(self, name: str) -> Optional['EnumValue']:
        """Find enum value by name."""
        for value in self.values:
            if value.name.value == name:
                return value
        return None
    
    def get_size(self) -> Optional[int]:
        """Get enum size."""
        if self.underlying_type:
            return self.underlying_type.get_size()
        return 4  # Default enum size


@dataclass
class EnumValue:
    """Value in an enum."""
    span: ZeroSpan
    name: DMLString
    value: Optional[Expression] = None
    computed_value: Optional[int] = None


@dataclass
class ArrayType(DMLType):
    """Array type declaration."""
    element_type: DMLType
    size: Optional[Expression] = None
    computed_size: Optional[int] = None
    
    def __post_init__(self):
        self.kind = TypeKind.ARRAY
        self.name = f"{self.element_type.name}[]"
    
    def get_size(self) -> Optional[int]:
        """Get array size."""
        if self.computed_size is not None:
            element_size = self.element_type.get_size()
            if element_size is not None:
                return self.computed_size * element_size
        return None


@dataclass
class PointerType(DMLType):
    """Pointer type declaration."""
    target_type: DMLType
    
    def __post_init__(self):
        self.kind = TypeKind.POINTER
        self.name = f"{self.target_type.name}*"
    
    def get_size(self) -> Optional[int]:
        """Get pointer size."""
        return 8  # Assume 64-bit pointers


@dataclass
class FunctionType(DMLType):
    """Function type declaration."""
    return_type: DMLType
    parameter_types: List[DMLType] = field(default_factory=list)
    is_variadic: bool = False
    
    def __post_init__(self):
        self.kind = TypeKind.FUNCTION
        param_names = [p.name for p in self.parameter_types]
        params_str = ", ".join(param_names)
        self.name = f"{self.return_type.name}({params_str})"
    
    def get_size(self) -> Optional[int]:
        """Function types don't have a size."""
        return None


@dataclass
class TemplateType(DMLType):
    """Template type declaration."""
    template_parameters: List[str] = field(default_factory=list)
    specializations: Dict[str, DMLType] = field(default_factory=dict)
    
    def __post_init__(self):
        self.kind = TypeKind.TEMPLATE
    
    def add_specialization(self, params: str, specialized_type: DMLType) -> None:
        """Add a template specialization."""
        self.specializations[params] = specialized_type


@dataclass
class VoidType(DMLType):
    """Void type."""
    
    def __post_init__(self):
        self.kind = TypeKind.VOID
        self.name = "void"
    
    def get_size(self) -> Optional[int]:
        """Void has no size."""
        return None


@dataclass
class AutoType(DMLType):
    """Auto type (type to be inferred)."""
    inferred_type: Optional[DMLType] = None
    
    def __post_init__(self):
        self.kind = TypeKind.AUTO
        self.name = "auto"
    
    def get_size(self) -> Optional[int]:
        """Auto type size depends on inferred type."""
        if self.inferred_type:
            return self.inferred_type.get_size()
        return None


@dataclass
class TypedefType(DMLType):
    """Typedef declaration."""
    target_type: DMLType
    
    def __post_init__(self):
        self.kind = TypeKind.TYPEDEF
    
    def get_size(self) -> Optional[int]:
        """Typedef size is the same as target type."""
        return self.target_type.get_size()


class TypeRegistry:
    """Registry for managing DML types."""
    
    def __init__(self):
        self.types: Dict[str, DMLType] = {}
        self.errors: List[DMLError] = []
        self._register_builtin_types()
    
    def _register_builtin_types(self) -> None:
        """Register built-in primitive types."""
        # Create a dummy span for built-in types
        builtin_span = ZeroSpan("builtin", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        for primitive in PrimitiveType:
            type_decl = PrimitiveTypeDecl(
                span=builtin_span,
                primitive=primitive,
                kind=TypeKind.PRIMITIVE,
                name=primitive.value
            )
            self.types[primitive.value] = type_decl
        
        # Add void type
        void_type = VoidType(span=builtin_span, kind=TypeKind.VOID, name="void")
        self.types["void"] = void_type
    
    def register_type(self, type_decl: DMLType) -> None:
        """Register a new type."""
        if type_decl.name in self.types:
            error = DMLError(
                kind=DMLErrorKind.DUPLICATE_SYMBOL,
                message=f"Type '{type_decl.name}' already defined",
                span=type_decl.span
            )
            self.errors.append(error)
        else:
            self.types[type_decl.name] = type_decl
    
    def find_type(self, name: str) -> Optional[DMLType]:
        """Find type by name."""
        return self.types.get(name)
    
    def get_primitive_type(self, primitive: PrimitiveType) -> PrimitiveTypeDecl:
        """Get a primitive type."""
        type_decl = self.types.get(primitive.value)
        if isinstance(type_decl, PrimitiveTypeDecl):
            return type_decl
        raise ValueError(f"Primitive type {primitive.value} not found")
    
    def create_array_type(self, element_type: DMLType, size: Optional[Expression] = None) -> ArrayType:
        """Create an array type."""
        span = element_type.span
        return ArrayType(
            span=span,
            kind=TypeKind.ARRAY,
            name=f"{element_type.name}[]",
            element_type=element_type,
            size=size
        )
    
    def create_pointer_type(self, target_type: DMLType) -> PointerType:
        """Create a pointer type."""
        span = target_type.span
        return PointerType(
            span=span,
            kind=TypeKind.POINTER,
            name=f"{target_type.name}*",
            target_type=target_type
        )
    
    def create_function_type(self, return_type: DMLType, parameter_types: List[DMLType]) -> FunctionType:
        """Create a function type."""
        span = return_type.span
        return FunctionType(
            span=span,
            kind=TypeKind.FUNCTION,
            name="function",
            return_type=return_type,
            parameter_types=parameter_types
        )
    
    def get_all_types(self) -> List[DMLType]:
        """Get all registered types."""
        return list(self.types.values())
    
    def get_errors(self) -> List[DMLError]:
        """Get type registry errors."""
        return self.errors


class TypeAnalyzer:
    """Analyzes DML types for semantic information."""
    
    def __init__(self, type_registry: TypeRegistry):
        self.type_registry = type_registry
        self.errors: List[DMLError] = []
    
    def analyze_type_declaration(self, type_decl: DMLType) -> None:
        """Analyze a type declaration."""
        if isinstance(type_decl, StructType):
            self._analyze_struct_type(type_decl)
        elif isinstance(type_decl, UnionType):
            self._analyze_union_type(type_decl)
        elif isinstance(type_decl, EnumType):
            self._analyze_enum_type(type_decl)
        elif isinstance(type_decl, ArrayType):
            self._analyze_array_type(type_decl)
        elif isinstance(type_decl, FunctionType):
            self._analyze_function_type(type_decl)
        elif isinstance(type_decl, TypedefType):
            self._analyze_typedef_type(type_decl)
    
    def _analyze_struct_type(self, struct_type: StructType) -> None:
        """Analyze struct type."""
        field_names = set()
        
        for field in struct_type.fields:
            # Check for duplicate field names
            if field.name.value in field_names:
                error = DMLError(
                    kind=DMLErrorKind.DUPLICATE_SYMBOL,
                    message=f"Duplicate field name: {field.name.value}",
                    span=field.span
                )
                self.errors.append(error)
            field_names.add(field.name.value)
            
            # Validate field type
            self._validate_type_exists(field.field_type)
    
    def _analyze_union_type(self, union_type: UnionType) -> None:
        """Analyze union type."""
        field_names = set()
        
        for field in union_type.fields:
            # Check for duplicate field names
            if field.name.value in field_names:
                error = DMLError(
                    kind=DMLErrorKind.DUPLICATE_SYMBOL,
                    message=f"Duplicate field name: {field.name.value}",
                    span=field.span
                )
                self.errors.append(error)
            field_names.add(field.name.value)
            
            # Validate field type
            self._validate_type_exists(field.field_type)
    
    def _analyze_enum_type(self, enum_type: EnumType) -> None:
        """Analyze enum type."""
        value_names = set()
        
        for value in enum_type.values:
            # Check for duplicate value names
            if value.name.value in value_names:
                error = DMLError(
                    kind=DMLErrorKind.DUPLICATE_SYMBOL,
                    message=f"Duplicate enum value: {value.name.value}",
                    span=value.span
                )
                self.errors.append(error)
            value_names.add(value.name.value)
    
    def _analyze_array_type(self, array_type: ArrayType) -> None:
        """Analyze array type."""
        # Validate element type
        self._validate_type_exists(array_type.element_type)
        
        # TODO: Validate array size expression
    
    def _analyze_function_type(self, func_type: FunctionType) -> None:
        """Analyze function type."""
        # Validate return type
        self._validate_type_exists(func_type.return_type)
        
        # Validate parameter types
        for param_type in func_type.parameter_types:
            self._validate_type_exists(param_type)
    
    def _analyze_typedef_type(self, typedef: TypedefType) -> None:
        """Analyze typedef."""
        # Validate target type
        self._validate_type_exists(typedef.target_type)
    
    def _validate_type_exists(self, type_decl: DMLType) -> None:
        """Validate that a type exists."""
        if not isinstance(type_decl, (PrimitiveTypeDecl, VoidType)):
            # For user-defined types, check if they exist in registry
            if not self.type_registry.find_type(type_decl.name):
                error = DMLError(
                    kind=DMLErrorKind.UNDEFINED_SYMBOL,
                    message=f"Unknown type: {type_decl.name}",
                    span=type_decl.span
                )
                self.errors.append(error)
    
    def get_errors(self) -> List[DMLError]:
        """Get analysis errors."""
        return self.errors


def create_primitive_type(primitive: PrimitiveType, span: ZeroSpan) -> PrimitiveTypeDecl:
    """Helper to create primitive types."""
    return PrimitiveTypeDecl(
        span=span,
        kind=TypeKind.PRIMITIVE,
        name=primitive.value,
        primitive=primitive
    )


def create_struct_type(name: str, span: ZeroSpan) -> StructType:
    """Helper to create struct types."""
    return StructType(
        span=span,
        kind=TypeKind.STRUCT,
        name=name
    )


__all__ = [
    'TypeKind', 'PrimitiveType', 'DMLType', 'PrimitiveTypeDecl', 'StructType', 'StructField',
    'UnionType', 'EnumType', 'EnumValue', 'ArrayType', 'PointerType', 'FunctionType',
    'TemplateType', 'VoidType', 'AutoType', 'TypedefType', 'TypeRegistry', 'TypeAnalyzer',
    'create_primitive_type', 'create_struct_type'
]