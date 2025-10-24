"""
DML Template Type System

Provides type resolution and analysis for DML templates, including template
instantiation, type checking, and resolution. This module corresponds to the
Rust implementation in src/analysis/templating/types.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind
from ..structure.types import DMLType, TypeKind, PrimitiveType, TypeRegistry


class TemplateTypeKind(Enum):
    """Kinds of template types."""
    CONCRETE = "concrete"
    ABSTRACT = "abstract"
    PARAMETRIC = "parametric"
    SPECIALIZED = "specialized"
    RESOLVED = "resolved"
    DUMMY = "dummy"


@dataclass
class DMLBaseType:
    """Base type in the DML type system."""
    span: ZeroSpan
    name: str
    kind: TemplateTypeKind = TemplateTypeKind.CONCRETE
    
    def is_dummy(self) -> bool:
        """Check if this is a dummy type (for error recovery)."""
        return self.kind == TemplateTypeKind.DUMMY
    
    def is_concrete(self) -> bool:
        """Check if this is a concrete type."""
        return self.kind == TemplateTypeKind.CONCRETE
    
    def is_abstract(self) -> bool:
        """Check if this is an abstract type."""
        return self.kind == TemplateTypeKind.ABSTRACT


@dataclass
class DMLStructType:
    """Struct type in templates."""
    span: ZeroSpan
    name: str
    fields: Dict[str, 'DMLResolvedType'] = field(default_factory=dict)
    is_packed: bool = False
    
    def add_field(self, name: str, field_type: 'DMLResolvedType') -> None:
        """Add a field to the struct."""
        self.fields[name] = field_type
    
    def get_field(self, name: str) -> Optional['DMLResolvedType']:
        """Get field type by name."""
        return self.fields.get(name)


@dataclass
class DMLConcreteType:
    """Concrete type that can be instantiated."""
    base_type: Optional[DMLBaseType] = None
    struct_type: Optional[DMLStructType] = None
    
    def get_span(self) -> ZeroSpan:
        """Get source span."""
        if self.base_type:
            return self.base_type.span
        elif self.struct_type:
            return self.struct_type.span
        else:
            # Dummy span
            return ZeroSpan("unknown", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
    
    def get_name(self) -> str:
        """Get type name."""
        if self.base_type:
            return self.base_type.name
        elif self.struct_type:
            return self.struct_type.name
        else:
            return "unknown"
    
    def is_struct(self) -> bool:
        """Check if this is a struct type."""
        return self.struct_type is not None


@dataclass
class DMLResolvedType:
    """Resolved type that may be concrete or dummy."""
    concrete_type: Optional[DMLConcreteType] = None
    dummy_span: Optional[ZeroSpan] = None
    
    def is_dummy(self) -> bool:
        """Check if this is a dummy type."""
        return self.dummy_span is not None
    
    def is_concrete(self) -> bool:
        """Check if this is a concrete type."""
        return self.concrete_type is not None
    
    def get_span(self) -> ZeroSpan:
        """Get source span."""
        if self.concrete_type:
            return self.concrete_type.get_span()
        elif self.dummy_span:
            return self.dummy_span
        else:
            return ZeroSpan("unknown", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
    
    def get_name(self) -> str:
        """Get type name."""
        if self.concrete_type:
            return self.concrete_type.get_name()
        else:
            return "dummy"
    
    def equivalent(self, other: 'DMLResolvedType') -> bool:
        """Check if two types are equivalent."""
        # Simple implementation - both dummy or same concrete type
        if self.is_dummy() and other.is_dummy():
            return True
        
        if self.is_concrete() and other.is_concrete():
            return self.get_name() == other.get_name()
        
        return False
    
    @classmethod
    def from_concrete(cls, concrete_type: DMLConcreteType) -> 'DMLResolvedType':
        """Create resolved type from concrete type."""
        return cls(concrete_type=concrete_type)
    
    @classmethod
    def dummy(cls, span: ZeroSpan) -> 'DMLResolvedType':
        """Create dummy type for error recovery."""
        return cls(dummy_span=span)


class TemplateTypeResolver:
    """Resolves types in template contexts."""
    
    def __init__(self, type_registry: TypeRegistry):
        self.type_registry = type_registry
        self.errors: List[DMLError] = []
        self.template_parameters: Dict[str, DMLResolvedType] = {}
    
    def set_template_parameters(self, parameters: Dict[str, DMLResolvedType]) -> None:
        """Set template parameters for resolution."""
        self.template_parameters = parameters
    
    def resolve_type(self, type_ref: DMLType, location_span: ZeroSpan, 
                    scope_context: Optional[str] = None, in_extern: bool = False,
                    typename_hint: Optional[str] = None, allow_void: bool = False) -> DMLResolvedType:
        """Resolve a type reference to a concrete type."""
        
        # Check if it's a template parameter
        if type_ref.name in self.template_parameters:
            return self.template_parameters[type_ref.name]
        
        # Try to find in type registry
        registered_type = self.type_registry.find_type(type_ref.name)
        if registered_type:
            # Convert to resolved type
            if registered_type.is_primitive():
                base_type = DMLBaseType(
                    span=type_ref.span,
                    name=registered_type.name,
                    kind=TemplateTypeKind.CONCRETE
                )
                concrete_type = DMLConcreteType(base_type=base_type)
                return DMLResolvedType.from_concrete(concrete_type)
            else:
                # Handle struct/other types
                # TODO: Implement proper struct type resolution
                base_type = DMLBaseType(
                    span=type_ref.span,
                    name=registered_type.name,
                    kind=TemplateTypeKind.CONCRETE
                )
                concrete_type = DMLConcreteType(base_type=base_type)
                return DMLResolvedType.from_concrete(concrete_type)
        
        # Check for void type
        if type_ref.name == "void":
            if allow_void:
                base_type = DMLBaseType(
                    span=type_ref.span,
                    name="void",
                    kind=TemplateTypeKind.CONCRETE
                )
                concrete_type = DMLConcreteType(base_type=base_type)
                return DMLResolvedType.from_concrete(concrete_type)
            else:
                error = DMLError(
                    kind=DMLErrorKind.TYPE_ERROR,
                    message="Void type not allowed in this context",
                    span=type_ref.span
                )
                self.errors.append(error)
                return DMLResolvedType.dummy(type_ref.span)
        
        # Type not found
        error = DMLError(
            kind=DMLErrorKind.UNDEFINED_SYMBOL,
            message=f"Unknown type: {type_ref.name}",
            span=type_ref.span
        )
        self.errors.append(error)
        return DMLResolvedType.dummy(type_ref.span)
    
    def resolve_type_simple(self, type_ref: DMLType, location_span: ZeroSpan,
                           scope_context: Optional[str] = None) -> DMLResolvedType:
        """Simple type resolution without special options."""
        return self.resolve_type(type_ref, location_span, scope_context, False, None, False)
    
    def create_struct_type(self, name: str, span: ZeroSpan) -> DMLResolvedType:
        """Create a new struct type."""
        struct_type = DMLStructType(span=span, name=name)
        concrete_type = DMLConcreteType(struct_type=struct_type)
        return DMLResolvedType.from_concrete(concrete_type)
    
    def create_base_type(self, name: str, span: ZeroSpan) -> DMLResolvedType:
        """Create a base type."""
        base_type = DMLBaseType(span=span, name=name)
        concrete_type = DMLConcreteType(base_type=base_type)
        return DMLResolvedType.from_concrete(concrete_type)
    
    def get_errors(self) -> List[DMLError]:
        """Get resolution errors."""
        return self.errors


class TemplateTypeChecker:
    """Type checker for template instantiations."""
    
    def __init__(self, resolver: TemplateTypeResolver):
        self.resolver = resolver
        self.errors: List[DMLError] = []
    
    def check_type_compatibility(self, expected: DMLResolvedType, 
                                actual: DMLResolvedType, span: ZeroSpan) -> bool:
        """Check if actual type is compatible with expected type."""
        if expected.equivalent(actual):
            return True
        
        # Allow dummy types to match anything (error recovery)
        if expected.is_dummy() or actual.is_dummy():
            return True
        
        # Type mismatch
        error = DMLError(
            kind=DMLErrorKind.TYPE_ERROR,
            message=f"Type mismatch: expected {expected.get_name()}, got {actual.get_name()}",
            span=span
        )
        self.errors.append(error)
        return False
    
    def check_assignment_compatibility(self, target: DMLResolvedType,
                                     source: DMLResolvedType, span: ZeroSpan) -> bool:
        """Check if source can be assigned to target."""
        # For now, same as type compatibility
        return self.check_type_compatibility(target, source, span)
    
    def check_parameter_compatibility(self, param_types: List[DMLResolvedType],
                                    arg_types: List[DMLResolvedType], span: ZeroSpan) -> bool:
        """Check if argument types match parameter types."""
        if len(param_types) != len(arg_types):
            error = DMLError(
                kind=DMLErrorKind.TYPE_ERROR,
                message=f"Argument count mismatch: expected {len(param_types)}, got {len(arg_types)}",
                span=span
            )
            self.errors.append(error)
            return False
        
        all_compatible = True
        for i, (param_type, arg_type) in enumerate(zip(param_types, arg_types)):
            if not self.check_type_compatibility(param_type, arg_type, span):
                all_compatible = False
        
        return all_compatible
    
    def get_errors(self) -> List[DMLError]:
        """Get type checking errors."""
        return self.errors


def eval_type(ast: DMLType, location_span: ZeroSpan, scope_context: Optional[str],
              in_extern: bool, typename_hint: Optional[str], allow_void: bool,
              resolver: TemplateTypeResolver) -> tuple[List[DMLStructType], DMLConcreteType]:
    """Evaluate a type AST and return struct dependencies and concrete type."""
    
    resolved_type = resolver.resolve_type(ast, location_span, scope_context, 
                                        in_extern, typename_hint, allow_void)
    
    struct_deps = []
    if resolved_type.is_concrete() and resolved_type.concrete_type:
        if resolved_type.concrete_type.is_struct():
            struct_deps.append(resolved_type.concrete_type.struct_type)
        
        return struct_deps, resolved_type.concrete_type
    else:
        # Return dummy concrete type
        dummy_base = DMLBaseType(
            span=location_span,
            name="dummy",
            kind=TemplateTypeKind.DUMMY
        )
        dummy_concrete = DMLConcreteType(base_type=dummy_base)
        return struct_deps, dummy_concrete


def eval_type_simple(ast: DMLType, location_span: ZeroSpan, scope_context: Optional[str],
                    resolver: TemplateTypeResolver) -> tuple[List[DMLStructType], DMLConcreteType]:
    """Simple type evaluation."""
    return eval_type(ast, location_span, scope_context, False, None, False, resolver)


def create_primitive_resolved_type(primitive: PrimitiveType, span: ZeroSpan) -> DMLResolvedType:
    """Helper to create resolved primitive types."""
    base_type = DMLBaseType(
        span=span,
        name=primitive.value,
        kind=TemplateTypeKind.CONCRETE
    )
    concrete_type = DMLConcreteType(base_type=base_type)
    return DMLResolvedType.from_concrete(concrete_type)


def create_void_resolved_type(span: ZeroSpan) -> DMLResolvedType:
    """Helper to create void resolved type."""
    base_type = DMLBaseType(
        span=span,
        name="void",
        kind=TemplateTypeKind.CONCRETE
    )
    concrete_type = DMLConcreteType(base_type=base_type)
    return DMLResolvedType.from_concrete(concrete_type)


__all__ = [
    'TemplateTypeKind', 'DMLBaseType', 'DMLStructType', 'DMLConcreteType', 'DMLResolvedType',
    'TemplateTypeResolver', 'TemplateTypeChecker', 'eval_type', 'eval_type_simple',
    'create_primitive_resolved_type', 'create_void_resolved_type'
]