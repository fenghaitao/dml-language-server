"""
DML Template Object Resolution

Provides object resolution and instantiation for DML templates, including template
application, object composition, and inheritance resolution. This module corresponds
to the Rust implementation in src/analysis/templating/objects.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set, Tuple, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from ..structure.expressions import DMLString, Expression
from ..structure.objects import (
    DMLObject, ObjectKind, Device, Template, Bank, Register, Field, Method,
    Parameter, MethodModifier, Scope
)
from .types import DMLResolvedType, TemplateTypeResolver
from .methods import MethodAnalyzer, MethodDeclaration


T = TypeVar('T')


class ObjectResolutionKind(Enum):
    """Kinds of object resolution."""
    CONCRETE = "concrete"
    ABSTRACT = "abstract"
    TEMPLATE = "template"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class ObjectSpec:
    """Specification for object creation/resolution."""
    name: str
    kind: ObjectKind
    span: ZeroSpan
    template_applications: List[str] = field(default_factory=list)
    parameters: Dict[str, Expression] = field(default_factory=dict)
    
    def has_template_applications(self) -> bool:
        """Check if object applies templates."""
        return len(self.template_applications) > 0


@dataclass
class DMLResolvedObject:
    """Resolved DML object with template instantiation."""
    original: DMLObject
    spec: ObjectSpec
    resolved_type: ObjectResolutionKind
    children: List['DMLResolvedObject'] = field(default_factory=list)
    methods: Dict[str, MethodDeclaration] = field(default_factory=dict)
    parameters: Dict[str, DMLResolvedType] = field(default_factory=dict)
    template_instances: List['TemplateInstance'] = field(default_factory=list)
    errors: List[DMLError] = field(default_factory=list)
    
    def is_concrete(self) -> bool:
        """Check if object is fully resolved and concrete."""
        return self.resolved_type == ObjectResolutionKind.CONCRETE
    
    def is_abstract(self) -> bool:
        """Check if object is abstract."""
        return self.resolved_type == ObjectResolutionKind.ABSTRACT
    
    def has_errors(self) -> bool:
        """Check if resolution had errors."""
        return len(self.errors) > 0 or self.resolved_type == ObjectResolutionKind.ERROR
    
    def add_child(self, child: 'DMLResolvedObject') -> None:
        """Add a child resolved object."""
        self.children.append(child)
    
    def find_child(self, name: str) -> Optional['DMLResolvedObject']:
        """Find child by name."""
        for child in self.children:
            if child.original.name.value == name:
                return child
        return None
    
    def get_method(self, name: str) -> Optional[MethodDeclaration]:
        """Get method by name."""
        return self.methods.get(name)
    
    def add_method(self, method: MethodDeclaration) -> None:
        """Add a method to this object."""
        self.methods[method.name.value] = method


@dataclass
class TemplateInstance:
    """Instance of a template applied to an object."""
    template: Template
    application_span: ZeroSpan
    parameter_bindings: Dict[str, DMLResolvedType] = field(default_factory=dict)
    instantiated_methods: List[MethodDeclaration] = field(default_factory=list)
    instantiated_objects: List[DMLResolvedObject] = field(default_factory=list)
    
    def get_parameter_binding(self, param_name: str) -> Optional[DMLResolvedType]:
        """Get parameter binding for template parameter."""
        return self.parameter_bindings.get(param_name)


class DMLShallowObjectVariant(Enum):
    """Variants of shallow object analysis."""
    DEVICE = "device"
    TEMPLATE = "template" 
    BANK = "bank"
    REGISTER = "register"
    FIELD = "field"
    METHOD = "method"
    PARAMETER = "parameter"
    UNKNOWN = "unknown"


@dataclass
class DMLAmbiguousDef(Generic[T]):
    """Represents an ambiguous definition that needs resolution."""
    name: str
    span: ZeroSpan
    candidates: List[T] = field(default_factory=list)
    resolution_errors: List[DMLError] = field(default_factory=list)
    
    def is_ambiguous(self) -> bool:
        """Check if definition is ambiguous."""
        return len(self.candidates) > 1
    
    def is_resolved(self) -> bool:
        """Check if definition is resolved."""
        return len(self.candidates) == 1 and len(self.resolution_errors) == 0
    
    def get_resolved(self) -> Optional[T]:
        """Get resolved definition if unique."""
        if self.is_resolved():
            return self.candidates[0]
        return None
    
    def add_candidate(self, candidate: T) -> None:
        """Add a candidate definition."""
        self.candidates.append(candidate)


class DMLCompositeObject:
    """Composite object built from templates and inheritance."""
    
    def __init__(self, base_object: DMLObject):
        self.base_object = base_object
        self.applied_templates: List[TemplateInstance] = []
        self.resolved_methods: Dict[str, MethodDeclaration] = {}
        self.resolved_parameters: Dict[str, DMLResolvedType] = {}
        self.resolved_children: List[DMLResolvedObject] = []
        self.composition_errors: List[DMLError] = []
    
    def apply_template(self, template_instance: TemplateInstance) -> None:
        """Apply a template to this composite object."""
        self.applied_templates.append(template_instance)
        
        # Merge template methods
        for method in template_instance.instantiated_methods:
            method_name = method.name.value
            
            if method_name in self.resolved_methods:
                # Check for override compatibility
                existing_method = self.resolved_methods[method_name]
                if not method.signature.is_compatible_override(existing_method.signature):
                    error = DMLError(
                        kind=DMLErrorKind.TEMPLATE_ERROR,
                        message=f"Template method '{method_name}' conflicts with existing method",
                        span=method.span
                    )
                    self.composition_errors.append(error)
            
            # Override or add method
            self.resolved_methods[method_name] = method
        
        # Merge template objects
        for obj in template_instance.instantiated_objects:
            self.resolved_children.append(obj)
    
    def get_final_object(self) -> DMLResolvedObject:
        """Get the final resolved object."""
        spec = ObjectSpec(
            name=self.base_object.name.value,
            kind=self.base_object.kind,
            span=self.base_object.span,
            template_applications=[t.template.name.value for t in self.applied_templates]
        )
        
        resolution_kind = ObjectResolutionKind.CONCRETE
        if self.composition_errors:
            resolution_kind = ObjectResolutionKind.ERROR
        elif any(method.is_abstract for method in self.resolved_methods.values()):
            resolution_kind = ObjectResolutionKind.ABSTRACT
        
        resolved_obj = DMLResolvedObject(
            original=self.base_object,
            spec=spec,
            resolved_type=resolution_kind,
            children=self.resolved_children,
            methods=self.resolved_methods,
            parameters=self.resolved_parameters,
            template_instances=self.applied_templates,
            errors=self.composition_errors
        )
        
        return resolved_obj


class ObjectResolver:
    """Resolves DML objects with template application."""
    
    def __init__(self, type_resolver: TemplateTypeResolver):
        self.type_resolver = type_resolver
        self.method_analyzer = MethodAnalyzer(type_resolver)
        self.template_registry: Dict[str, Template] = {}
        self.object_cache: Dict[str, DMLResolvedObject] = {}
        self.resolution_stack: List[str] = []
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
    
    def register_template(self, template: Template) -> None:
        """Register a template for resolution."""
        self.template_registry[template.name.value] = template
    
    def resolve_object(self, obj: DMLObject, context_path: str = "") -> DMLResolvedObject:
        """Resolve an object with template applications."""
        object_path = f"{context_path}.{obj.name.value}" if context_path else obj.name.value
        
        # Check for circular dependencies
        if object_path in self.resolution_stack:
            error = DMLError(
                kind=DMLErrorKind.CIRCULAR_DEPENDENCY,
                message=f"Circular dependency in object resolution: {object_path}",
                span=obj.span
            )
            self.errors.append(error)
            return self._create_error_object(obj)
        
        # Check cache
        if object_path in self.object_cache:
            return self.object_cache[object_path]
        
        # Begin resolution
        self.resolution_stack.append(object_path)
        
        try:
            resolved_obj = self._resolve_object_impl(obj, object_path)
            self.object_cache[object_path] = resolved_obj
            return resolved_obj
        finally:
            self.resolution_stack.pop()
    
    def _resolve_object_impl(self, obj: DMLObject, object_path: str) -> DMLResolvedObject:
        """Implementation of object resolution."""
        # Create composite object
        composite = DMLCompositeObject(obj)
        
        # Apply templates
        for template_name in obj.templates:
            template = self.template_registry.get(template_name)
            if template:
                instance = self._instantiate_template(template, obj.span)
                composite.apply_template(instance)
                
                # Add template reference
                node_ref = NodeRef(template_name, obj.span)
                reference = SymbolReference(
                    node_ref=node_ref,
                    kind=ReferenceKind.TEMPLATE,
                    location=obj.span
                )
                self.references.append(reference)
            else:
                error = DMLError(
                    kind=DMLErrorKind.TEMPLATE_ERROR,
                    message=f"Template not found: {template_name}",
                    span=obj.span
                )
                self.errors.append(error)
        
        # Analyze object's own methods
        for child in obj.children:
            if isinstance(child, Method):
                method_decl = self.method_analyzer.analyze_method(child, object_path)
                composite.resolved_methods[child.name.value] = method_decl
        
        # Resolve child objects
        for child in obj.children:
            if not isinstance(child, Method):
                child_resolved = self.resolve_object(child, object_path)
                composite.resolved_children.append(child_resolved)
        
        return composite.get_final_object()
    
    def _instantiate_template(self, template: Template, application_span: ZeroSpan) -> TemplateInstance:
        """Instantiate a template."""
        instance = TemplateInstance(
            template=template,
            application_span=application_span
        )
        
        # Instantiate template methods
        for child in template.children:
            if isinstance(child, Method):
                method_decl = self.method_analyzer.analyze_method(child, template.name.value)
                instance.instantiated_methods.append(method_decl)
        
        # Instantiate template objects
        for child in template.children:
            if not isinstance(child, Method):
                child_resolved = self.resolve_object(child, template.name.value)
                instance.instantiated_objects.append(child_resolved)
        
        return instance
    
    def _create_error_object(self, obj: DMLObject) -> DMLResolvedObject:
        """Create an error object for failed resolution."""
        spec = ObjectSpec(
            name=obj.name.value,
            kind=obj.kind,
            span=obj.span
        )
        
        return DMLResolvedObject(
            original=obj,
            spec=spec,
            resolved_type=ObjectResolutionKind.ERROR
        )
    
    def resolve_device(self, device: Device) -> DMLResolvedObject:
        """Resolve a device object."""
        return self.resolve_object(device)
    
    def check_template_compatibility(self, template: Template, target_object: DMLObject) -> List[DMLError]:
        """Check if template is compatible with target object."""
        compatibility_errors = []
        
        # Check if template can be applied to this object kind
        if template.kind != ObjectKind.TEMPLATE:
            error = DMLError(
                kind=DMLErrorKind.TEMPLATE_ERROR,
                message=f"Cannot apply non-template object as template",
                span=template.span
            )
            compatibility_errors.append(error)
        
        # TODO: Add more sophisticated compatibility checking
        # - Parameter requirements
        # - Method signature compatibility
        # - Object hierarchy constraints
        
        return compatibility_errors
    
    def get_all_resolved_objects(self) -> List[DMLResolvedObject]:
        """Get all resolved objects."""
        return list(self.object_cache.values())
    
    def get_errors(self) -> List[DMLError]:
        """Get all resolution errors."""
        method_errors = self.method_analyzer.get_errors()
        return self.errors + method_errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get all object references."""
        method_references = self.method_analyzer.get_references()
        return self.references + method_references


def make_device(path: str, name: str, span: ZeroSpan, templates: List[str] = None) -> ObjectSpec:
    """Helper to create device specifications."""
    return ObjectSpec(
        name=name,
        kind=ObjectKind.DEVICE,
        span=span,
        template_applications=templates or []
    )


def create_resolved_object(obj: DMLObject, resolution_kind: ObjectResolutionKind) -> DMLResolvedObject:
    """Helper to create resolved objects."""
    spec = ObjectSpec(
        name=obj.name.value,
        kind=obj.kind,
        span=obj.span,
        template_applications=obj.templates
    )
    
    return DMLResolvedObject(
        original=obj,
        spec=spec,
        resolved_type=resolution_kind
    )


__all__ = [
    'ObjectResolutionKind', 'ObjectSpec', 'DMLResolvedObject', 'TemplateInstance',
    'DMLShallowObjectVariant', 'DMLAmbiguousDef', 'DMLCompositeObject', 'ObjectResolver',
    'make_device', 'create_resolved_object'
]