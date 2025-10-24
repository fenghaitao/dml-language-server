"""
DML Template Traits Analysis

Provides trait analysis for DML templates, including trait definitions,
implementations, and constraint checking. This module corresponds to the
Rust implementation in src/analysis/templating/traits.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from ..structure.expressions import DMLString, Expression
from ..structure.objects import DMLObject, Method, Parameter, MethodModifier
from .types import DMLResolvedType
from .methods import MethodSignature, MethodDeclaration


class TraitKind(Enum):
    """Kinds of traits in DML."""
    INTERFACE = "interface"      # Pure interface trait
    MIXIN = "mixin"             # Trait with implementation
    CONSTRAINT = "constraint"    # Constraint trait for templates
    PROTOCOL = "protocol"       # Protocol trait for communication


@dataclass
class TraitRequirement:
    """Requirement specified by a trait."""
    name: str
    kind: str  # method, parameter, etc.
    signature: Optional[MethodSignature] = None
    constraint: Optional[Expression] = None
    is_optional: bool = False
    
    def matches(self, other: 'TraitRequirement') -> bool:
        """Check if requirements match."""
        if self.name != other.name or self.kind != other.kind:
            return False
        
        if self.signature and other.signature:
            return self.signature.matches(other.signature)
        
        return True


@dataclass
class TraitImplementation:
    """Implementation of a trait requirement."""
    requirement: TraitRequirement
    implementation: Union[MethodDeclaration, Parameter, Any]
    span: ZeroSpan
    is_complete: bool = True
    
    def satisfies_requirement(self) -> bool:
        """Check if implementation satisfies the requirement."""
        return self.is_complete


@dataclass
class TraitDefinition:
    """Definition of a trait."""
    name: DMLString
    kind: TraitKind
    span: ZeroSpan
    requirements: List[TraitRequirement] = field(default_factory=list)
    default_implementations: Dict[str, MethodDeclaration] = field(default_factory=dict)
    supertrait_constraints: List[str] = field(default_factory=list)
    type_parameters: List[str] = field(default_factory=list)
    
    def add_requirement(self, requirement: TraitRequirement) -> None:
        """Add a requirement to the trait."""
        self.requirements.append(requirement)
    
    def add_default_implementation(self, method: MethodDeclaration) -> None:
        """Add a default implementation."""
        self.default_implementations[method.name.value] = method
    
    def get_requirement(self, name: str) -> Optional[TraitRequirement]:
        """Get requirement by name."""
        for req in self.requirements:
            if req.name == name:
                return req
        return None
    
    def has_default_implementation(self, name: str) -> bool:
        """Check if trait has default implementation for requirement."""
        return name in self.default_implementations


class TraitMemberKind:
    """Member of a trait (abstract base)."""
    
    def __init__(self, name: str, span: ZeroSpan):
        self.name = name
        self.span = span
    
    def is_abstract(self) -> bool:
        """Check if member is abstract."""
        return True  # Default to abstract


@dataclass
class TraitMethod(TraitMemberKind):
    """Method member of a trait."""
    signature: MethodSignature
    default_body: Optional[Any] = None  # Statement block
    
    def __post_init__(self):
        super().__init__(self.signature.name, self.span)
    
    def is_abstract(self) -> bool:
        """Check if method is abstract."""
        return self.default_body is None


@dataclass
class TraitParameter(TraitMemberKind):
    """Parameter member of a trait."""
    param_type: DMLResolvedType
    default_value: Optional[Expression] = None
    
    def is_abstract(self) -> bool:
        """Parameters are concrete if they have defaults."""
        return self.default_value is None


@dataclass
class TraitConstraint:
    """Constraint specified by a trait."""
    expression: Expression
    error_message: str
    span: ZeroSpan


class TraitInstance:
    """Instance of a trait applied to an object."""
    
    def __init__(self, trait_def: TraitDefinition, object_name: str, span: ZeroSpan):
        self.trait_def = trait_def
        self.object_name = object_name
        self.span = span
        self.implementations: Dict[str, TraitImplementation] = {}
        self.missing_implementations: List[TraitRequirement] = []
        self.constraint_violations: List[DMLError] = []
    
    def add_implementation(self, impl: TraitImplementation) -> None:
        """Add an implementation for a trait requirement."""
        self.implementations[impl.requirement.name] = impl
    
    def check_completeness(self) -> List[DMLError]:
        """Check if all trait requirements are satisfied."""
        errors = []
        
        for requirement in self.trait_def.requirements:
            if requirement.name not in self.implementations:
                if not requirement.is_optional and not self.trait_def.has_default_implementation(requirement.name):
                    self.missing_implementations.append(requirement)
                    
                    error = DMLError(
                        kind=DMLErrorKind.SEMANTIC_ERROR,
                        message=f"Missing implementation for trait requirement '{requirement.name}'",
                        span=self.span
                    )
                    errors.append(error)
        
        return errors
    
    def is_complete(self) -> bool:
        """Check if trait instance is complete."""
        return len(self.missing_implementations) == 0


class TraitResolver:
    """Resolves trait applications and implementations."""
    
    def __init__(self):
        self.trait_definitions: Dict[str, TraitDefinition] = {}
        self.trait_instances: List[TraitInstance] = []
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
    
    def register_trait(self, trait_def: TraitDefinition) -> None:
        """Register a trait definition."""
        trait_name = trait_def.name.value
        
        if trait_name in self.trait_definitions:
            error = DMLError(
                kind=DMLErrorKind.DUPLICATE_SYMBOL,
                message=f"Duplicate trait definition: {trait_name}",
                span=trait_def.span
            )
            self.errors.append(error)
        else:
            self.trait_definitions[trait_name] = trait_def
    
    def apply_trait(self, trait_name: str, target_object: DMLObject, span: ZeroSpan) -> TraitInstance:
        """Apply a trait to an object."""
        trait_def = self.trait_definitions.get(trait_name)
        
        if not trait_def:
            error = DMLError(
                kind=DMLErrorKind.UNDEFINED_SYMBOL,
                message=f"Unknown trait: {trait_name}",
                span=span
            )
            self.errors.append(error)
            # Create dummy trait definition for error recovery
            trait_def = TraitDefinition(
                name=DMLString(trait_name, span),
                kind=TraitKind.INTERFACE,
                span=span
            )
        
        # Create trait instance
        instance = TraitInstance(trait_def, target_object.name.value, span)
        
        # Check object for trait implementations
        self._check_trait_implementations(instance, target_object)
        
        # Validate completeness
        completeness_errors = instance.check_completeness()
        self.errors.extend(completeness_errors)
        
        self.trait_instances.append(instance)
        
        # Add trait reference
        node_ref = NodeRef(trait_name, span)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.TYPE,  # Traits are type-like
            location=span
        )
        self.references.append(reference)
        
        return instance
    
    def _check_trait_implementations(self, instance: TraitInstance, obj: DMLObject) -> None:
        """Check object for implementations of trait requirements."""
        trait_def = instance.trait_def
        
        # Check method requirements
        for requirement in trait_def.requirements:
            if requirement.kind == "method":
                method_impl = self._find_method_implementation(obj, requirement)
                if method_impl:
                    impl = TraitImplementation(
                        requirement=requirement,
                        implementation=method_impl,
                        span=method_impl.span
                    )
                    instance.add_implementation(impl)
            elif requirement.kind == "parameter":
                param_impl = self._find_parameter_implementation(obj, requirement)
                if param_impl:
                    impl = TraitImplementation(
                        requirement=requirement,
                        implementation=param_impl,
                        span=param_impl.span
                    )
                    instance.add_implementation(impl)
    
    def _find_method_implementation(self, obj: DMLObject, requirement: TraitRequirement) -> Optional[Method]:
        """Find method implementation in object."""
        for child in obj.children:
            if isinstance(child, Method) and child.name.value == requirement.name:
                # Check signature compatibility
                if requirement.signature:
                    # TODO: Compare method signature with requirement
                    pass
                return child
        return None
    
    def _find_parameter_implementation(self, obj: DMLObject, requirement: TraitRequirement) -> Optional[Parameter]:
        """Find parameter implementation in object."""
        return obj.get_parameter(requirement.name)
    
    def check_trait_constraints(self, instance: TraitInstance) -> List[DMLError]:
        """Check trait constraints for an instance."""
        constraint_errors = []
        
        # TODO: Implement constraint checking
        # This would evaluate constraint expressions against the object
        
        return constraint_errors
    
    def resolve_trait_hierarchy(self, trait_name: str) -> List[str]:
        """Resolve trait hierarchy (supertraits)."""
        trait_def = self.trait_definitions.get(trait_name)
        if not trait_def:
            return []
        
        hierarchy = [trait_name]
        
        for supertrait in trait_def.supertrait_constraints:
            if supertrait != trait_name:  # Avoid self-reference
                hierarchy.extend(self.resolve_trait_hierarchy(supertrait))
        
        return hierarchy
    
    def check_trait_compatibility(self, trait1: str, trait2: str) -> bool:
        """Check if two traits are compatible."""
        def1 = self.trait_definitions.get(trait1)
        def2 = self.trait_definitions.get(trait2)
        
        if not def1 or not def2:
            return False
        
        # Check for conflicting requirements
        for req1 in def1.requirements:
            for req2 in def2.requirements:
                if req1.name == req2.name and not req1.matches(req2):
                    return False
        
        return True
    
    def get_trait_requirements(self, trait_name: str) -> List[TraitRequirement]:
        """Get all requirements for a trait."""
        trait_def = self.trait_definitions.get(trait_name)
        return trait_def.requirements if trait_def else []
    
    def get_errors(self) -> List[DMLError]:
        """Get trait resolution errors."""
        return self.errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get trait references."""
        return self.references


def create_trait_method_requirement(name: str, signature: MethodSignature, 
                                  is_optional: bool = False) -> TraitRequirement:
    """Helper to create method requirements."""
    return TraitRequirement(
        name=name,
        kind="method",
        signature=signature,
        is_optional=is_optional
    )


def create_trait_parameter_requirement(name: str, param_type: str,
                                     is_optional: bool = False) -> TraitRequirement:
    """Helper to create parameter requirements."""
    return TraitRequirement(
        name=name,
        kind="parameter",
        is_optional=is_optional
    )


def create_interface_trait(name: str, span: ZeroSpan) -> TraitDefinition:
    """Helper to create interface traits."""
    return TraitDefinition(
        name=DMLString(name, span),
        kind=TraitKind.INTERFACE,
        span=span
    )


__all__ = [
    'TraitKind', 'TraitRequirement', 'TraitImplementation', 'TraitDefinition',
    'TraitMemberKind', 'TraitMethod', 'TraitParameter', 'TraitConstraint',
    'TraitInstance', 'TraitResolver', 'create_trait_method_requirement',
    'create_trait_parameter_requirement', 'create_interface_trait'
]