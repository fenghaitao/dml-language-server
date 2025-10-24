"""
DML Template Method Analysis

Provides analysis and resolution of methods in DML templates, including method
overloading, inheritance, and template method instantiation. This module
corresponds to the Rust implementation in src/analysis/templating/methods.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from ..structure.expressions import DMLString, Expression
from ..structure.statements import Statement, BlockStatement
from ..structure.objects import Method, MethodModifier, FormalParameter, DMLObject
from ..structure.types import DMLType
from .types import DMLResolvedType, TemplateTypeResolver, TemplateTypeChecker


class MethodKind(Enum):
    """Kinds of methods in templates."""
    REGULAR = "regular"
    ABSTRACT = "abstract"
    OVERRIDE = "override"
    FINAL = "final"
    VIRTUAL = "virtual"
    TEMPLATE = "template"
    EXTERN = "extern"


@dataclass
class MethodSignature:
    """Method signature for overload resolution."""
    name: str
    parameter_types: List[DMLResolvedType]
    return_type: DMLResolvedType
    modifiers: Set[MethodModifier] = field(default_factory=set)
    
    def matches(self, other: 'MethodSignature') -> bool:
        """Check if signatures match (for overriding)."""
        if self.name != other.name:
            return False
        
        if len(self.parameter_types) != len(other.parameter_types):
            return False
        
        # Check parameter types
        for self_param, other_param in zip(self.parameter_types, other.parameter_types):
            if not self_param.equivalent(other_param):
                return False
        
        # Check return type
        if not self.return_type.equivalent(other.return_type):
            return False
        
        return True
    
    def is_compatible_override(self, base_signature: 'MethodSignature') -> bool:
        """Check if this signature can override the base signature."""
        # Names must match
        if self.name != base_signature.name:
            return False
        
        # Parameter types must match exactly
        if len(self.parameter_types) != len(base_signature.parameter_types):
            return False
        
        for self_param, base_param in zip(self.parameter_types, base_signature.parameter_types):
            if not self_param.equivalent(base_param):
                return False
        
        # Return type must be compatible (covariant)
        return self.return_type.equivalent(base_signature.return_type)
    
    def get_signature_string(self) -> str:
        """Get string representation of signature."""
        param_strs = [param.get_name() for param in self.parameter_types]
        params = ", ".join(param_strs)
        return f"{self.return_type.get_name()} {self.name}({params})"


@dataclass
class MethodDeclaration:
    """Template method declaration."""
    span: ZeroSpan
    name: DMLString
    signature: MethodSignature
    body: Optional[BlockStatement] = None
    kind: MethodKind = MethodKind.REGULAR
    is_abstract: bool = False
    is_overridable: bool = True
    declaring_object: Optional[str] = None
    
    def is_concrete(self) -> bool:
        """Check if method has concrete implementation."""
        return self.body is not None and not self.is_abstract
    
    def requires_implementation(self) -> bool:
        """Check if method requires implementation in concrete classes."""
        return self.is_abstract or self.body is None
    
    def can_be_overridden(self) -> bool:
        """Check if method can be overridden."""
        return self.is_overridable and self.kind != MethodKind.FINAL


@dataclass
class MethodOverload:
    """Method overload information."""
    methods: List[MethodDeclaration] = field(default_factory=list)
    
    def add_method(self, method: MethodDeclaration) -> None:
        """Add a method to this overload set."""
        self.methods.append(method)
    
    def find_best_match(self, arg_types: List[DMLResolvedType]) -> Optional[MethodDeclaration]:
        """Find best matching method for given argument types."""
        exact_matches = []
        compatible_matches = []
        
        for method in self.methods:
            if len(method.signature.parameter_types) != len(arg_types):
                continue
            
            is_exact = True
            is_compatible = True
            
            for param_type, arg_type in zip(method.signature.parameter_types, arg_types):
                if param_type.equivalent(arg_type):
                    continue
                else:
                    is_exact = False
                    # TODO: Add type compatibility checking
                    # For now, just check if not dummy
                    if param_type.is_dummy() or arg_type.is_dummy():
                        continue
                    else:
                        is_compatible = False
                        break
            
            if is_exact:
                exact_matches.append(method)
            elif is_compatible:
                compatible_matches.append(method)
        
        # Prefer exact matches
        if exact_matches:
            return exact_matches[0]  # TODO: Handle ambiguity
        elif compatible_matches:
            return compatible_matches[0]  # TODO: Handle ambiguity
        
        return None
    
    def has_abstract_methods(self) -> bool:
        """Check if any methods in this overload are abstract."""
        return any(method.is_abstract for method in self.methods)


class MethodRegistry:
    """Registry for managing methods in template resolution."""
    
    def __init__(self):
        self.methods: Dict[str, MethodOverload] = {}
        self.inheritance_chain: List[str] = []  # Object names in inheritance order
        self.errors: List[DMLError] = []
    
    def register_method(self, method: MethodDeclaration) -> None:
        """Register a method."""
        method_name = method.name.value
        
        if method_name not in self.methods:
            self.methods[method_name] = MethodOverload()
        
        overload = self.methods[method_name]
        
        # Check for signature conflicts
        for existing_method in overload.methods:
            if existing_method.signature.matches(method.signature):
                if existing_method.declaring_object == method.declaring_object:
                    # Same object, same signature - error
                    error = DMLError(
                        kind=DMLErrorKind.DUPLICATE_SYMBOL,
                        message=f"Duplicate method signature: {method.signature.get_signature_string()}",
                        span=method.span
                    )
                    self.errors.append(error)
                else:
                    # Different objects - check if valid override
                    if not method.signature.is_compatible_override(existing_method.signature):
                        error = DMLError(
                            kind=DMLErrorKind.SEMANTIC_ERROR,
                            message=f"Invalid method override: {method.signature.get_signature_string()}",
                            span=method.span
                        )
                        self.errors.append(error)
        
        overload.add_method(method)
    
    def find_method(self, name: str, arg_types: List[DMLResolvedType]) -> Optional[MethodDeclaration]:
        """Find method by name and argument types."""
        if name in self.methods:
            return self.methods[name].find_best_match(arg_types)
        return None
    
    def get_all_methods(self, name: str) -> List[MethodDeclaration]:
        """Get all methods with given name."""
        if name in self.methods:
            return self.methods[name].methods
        return []
    
    def check_abstract_methods(self, object_name: str) -> List[DMLError]:
        """Check for unimplemented abstract methods."""
        errors = []
        
        for method_name, overload in self.methods.items():
            if overload.has_abstract_methods():
                # Check if there's a concrete implementation
                has_concrete = any(method.is_concrete() for method in overload.methods)
                
                if not has_concrete:
                    # Find an abstract method to report error on
                    abstract_method = next(m for m in overload.methods if m.is_abstract)
                    error = DMLError(
                        kind=DMLErrorKind.SEMANTIC_ERROR,
                        message=f"Abstract method '{method_name}' not implemented in {object_name}",
                        span=abstract_method.span
                    )
                    errors.append(error)
        
        return errors
    
    def get_errors(self) -> List[DMLError]:
        """Get registration errors."""
        return self.errors


class MethodAnalyzer:
    """Analyzes methods in template contexts."""
    
    def __init__(self, type_resolver: TemplateTypeResolver):
        self.type_resolver = type_resolver
        self.type_checker = TemplateTypeChecker(type_resolver)
        self.method_registry = MethodRegistry()
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
    
    def analyze_method(self, method: Method, declaring_object: str) -> MethodDeclaration:
        """Analyze a method and create method declaration."""
        
        # Resolve parameter types
        param_types = []
        for param in method.formal_parameters:
            if param.param_type:
                # TODO: Parse type string and resolve
                dummy_type = DMLResolvedType.dummy(param.span)
                param_types.append(dummy_type)
            else:
                # No type specified - error
                error = DMLError(
                    kind=DMLErrorKind.TYPE_ERROR,
                    message=f"Parameter '{param.name.value}' missing type",
                    span=param.span
                )
                self.errors.append(error)
                param_types.append(DMLResolvedType.dummy(param.span))
        
        # Resolve return type
        if method.return_type:
            # TODO: Parse return type string and resolve
            return_type = DMLResolvedType.dummy(method.span)
        else:
            # Default to void
            from .types import create_void_resolved_type
            return_type = create_void_resolved_type(method.span)
        
        # Create signature
        signature = MethodSignature(
            name=method.name.value,
            parameter_types=param_types,
            return_type=return_type,
            modifiers=method.modifiers
        )
        
        # Determine method kind
        kind = MethodKind.REGULAR
        if method.has_modifier(MethodModifier.INDEPENDENT):
            kind = MethodKind.VIRTUAL
        elif method.is_extern:
            kind = MethodKind.EXTERN
        
        # Create method declaration
        method_decl = MethodDeclaration(
            span=method.span,
            name=method.name,
            signature=signature,
            body=method.body,
            kind=kind,
            is_abstract=(method.body is None and not method.is_extern),
            declaring_object=declaring_object
        )
        
        # Register method
        self.method_registry.register_method(method_decl)
        
        # Analyze method body if present
        if method.body and isinstance(method.body, BlockStatement):
            self._analyze_method_body(method.body, signature)
        
        return method_decl
    
    def _analyze_method_body(self, body: BlockStatement, signature: MethodSignature) -> None:
        """Analyze method body for type consistency."""
        # TODO: Implement method body analysis
        # This would involve:
        # - Statement analysis
        # - Return type checking
        # - Variable scope analysis
        # - Expression type checking
        pass
    
    def check_method_call(self, method_name: str, arg_types: List[DMLResolvedType], 
                         call_span: ZeroSpan) -> Optional[MethodDeclaration]:
        """Check a method call and return the resolved method."""
        method = self.method_registry.find_method(method_name, arg_types)
        
        if method is None:
            # No matching method found
            arg_type_names = [arg.get_name() for arg in arg_types]
            args_str = ", ".join(arg_type_names)
            
            error = DMLError(
                kind=DMLErrorKind.UNDEFINED_SYMBOL,
                message=f"No matching method for '{method_name}({args_str})'",
                span=call_span
            )
            self.errors.append(error)
            return None
        
        # Add method reference
        node_ref = NodeRef(method_name, call_span)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.METHOD,
            location=call_span
        )
        self.references.append(reference)
        
        return method
    
    def validate_method_overrides(self, object_name: str) -> None:
        """Validate method overrides for an object."""
        override_errors = self.method_registry.check_abstract_methods(object_name)
        self.errors.extend(override_errors)
    
    def get_method_signature(self, method_name: str) -> List[MethodSignature]:
        """Get all signatures for a method name."""
        methods = self.method_registry.get_all_methods(method_name)
        return [method.signature for method in methods]
    
    def get_errors(self) -> List[DMLError]:
        """Get all analysis errors."""
        registry_errors = self.method_registry.get_errors()
        type_checker_errors = self.type_checker.get_errors()
        return self.errors + registry_errors + type_checker_errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get method references."""
        return self.references


def eval_method_returns(return_types: List[DMLType], 
                       type_resolver: TemplateTypeResolver) -> Tuple[List[DMLError], List[DMLResolvedType]]:
    """Evaluate method return types and check for consistency."""
    errors = []
    resolved_types = []
    
    if not return_types:
        # No return types - default to void
        from .types import create_void_resolved_type
        dummy_span = ZeroSpan("implicit", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        resolved_types.append(create_void_resolved_type(dummy_span))
        return errors, resolved_types
    
    # Resolve all return types
    for return_type in return_types:
        resolved = type_resolver.resolve_type_simple(return_type, return_type.span)
        resolved_types.append(resolved)
    
    # Check consistency - all return types should be the same
    first_type = resolved_types[0]
    for i, ret_type in enumerate(resolved_types[1:], 1):
        if not first_type.equivalent(ret_type):
            error = DMLError(
                kind=DMLErrorKind.TYPE_ERROR,
                message=f"Inconsistent return types: {first_type.get_name()} vs {ret_type.get_name()}",
                span=return_types[i].span
            )
            errors.append(error)
    
    return errors, resolved_types


def create_method_signature(name: str, param_types: List[DMLResolvedType], 
                          return_type: DMLResolvedType, 
                          modifiers: Optional[Set[MethodModifier]] = None) -> MethodSignature:
    """Helper to create method signatures."""
    return MethodSignature(
        name=name,
        parameter_types=param_types,
        return_type=return_type,
        modifiers=modifiers or set()
    )


__all__ = [
    'MethodKind', 'MethodSignature', 'MethodDeclaration', 'MethodOverload', 
    'MethodRegistry', 'MethodAnalyzer', 'eval_method_returns', 'create_method_signature'
]