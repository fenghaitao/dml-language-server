"""
DML Object Structure Analysis

Provides analysis and representation of DML objects including devices, templates,
banks, registers, fields, methods, and other DML constructs. This module corresponds
to the Rust implementation in src/analysis/structure/objects.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from .expressions import Expression, DMLString
from .statements import Statement, BlockStatement


class ObjectKind(Enum):
    """Types of DML objects."""
    DEVICE = "device"
    TEMPLATE = "template"
    BANK = "bank"
    REGISTER = "register"
    FIELD = "field"
    METHOD = "method"
    PARAMETER = "parameter"
    ATTRIBUTE = "attribute"
    CONNECT = "connect"
    INTERFACE = "interface"
    PORT = "port"
    EVENT = "event"
    GROUP = "group"
    DATA = "data"
    SESSION = "session"
    SAVED = "saved"
    CONSTANT = "constant"
    TYPEDEF = "typedef"
    VARIABLE = "variable"
    HOOK = "hook"
    SUBDEVICE = "subdevice"
    LOGGROUP = "loggroup"


class Visibility(Enum):
    """Visibility levels for DML objects."""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"


class MethodModifier(Enum):
    """Method modifiers."""
    INLINE = "inline"
    SHARED = "shared"
    INDEPENDENT = "independent"
    STARTUP = "startup"
    MEMOIZED = "memoized"
    THROWS = "throws"
    DEFAULT = "default"


@dataclass
class DMLObject:
    """Base class for all DML objects."""
    span: ZeroSpan
    name: DMLString
    kind: ObjectKind
    visibility: Visibility = Visibility.PUBLIC
    parent: Optional['DMLObject'] = None
    children: List['DMLObject'] = field(default_factory=list)
    parameters: Dict[str, 'Parameter'] = field(default_factory=dict)
    templates: List[str] = field(default_factory=list)
    
    def get_full_name(self) -> str:
        """Get fully qualified name."""
        if self.parent:
            parent_name = self.parent.get_full_name()
            return f"{parent_name}.{self.name.value}"
        return self.name.value
    
    def add_child(self, child: 'DMLObject') -> None:
        """Add a child object."""
        child.parent = self
        self.children.append(child)
    
    def find_child(self, name: str) -> Optional['DMLObject']:
        """Find child by name."""
        for child in self.children:
            if child.name.value == name:
                return child
        return None
    
    def get_children_of_kind(self, kind: ObjectKind) -> List['DMLObject']:
        """Get children of specific kind."""
        return [child for child in self.children if child.kind == kind]
    
    def add_parameter(self, param: 'Parameter') -> None:
        """Add a parameter to this object."""
        self.parameters[param.name.value] = param
    
    def get_parameter(self, name: str) -> Optional['Parameter']:
        """Get parameter by name."""
        return self.parameters.get(name)
    
    def is_abstract(self) -> bool:
        """Check if this object is abstract."""
        return False  # Default implementation


@dataclass
class Device(DMLObject):
    """Device object."""
    version: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.DEVICE


@dataclass
class Template(DMLObject):
    """Template object."""
    type_parameters: List[str] = field(default_factory=list)
    is_abstract: bool = False
    
    def __post_init__(self):
        self.kind = ObjectKind.TEMPLATE
    
    def is_abstract(self) -> bool:
        """Check if this template is abstract."""
        return self.is_abstract


@dataclass
class Bank(DMLObject):
    """Bank object."""
    size: Optional[Expression] = None
    offset: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.BANK


@dataclass
class Register(DMLObject):
    """Register object."""
    size: Optional[Expression] = None
    offset: Optional[Expression] = None
    is_array: bool = False
    array_size: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.REGISTER


@dataclass
class Field(DMLObject):
    """Field object."""
    bit_range: Optional[tuple[Expression, Expression]] = None  # (high, low)
    size: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.FIELD
    
    def get_bit_width(self) -> Optional[int]:
        """Get bit width if statically determinable."""
        if self.bit_range:
            # TODO: Evaluate expressions to get actual bit width
            pass
        return None


@dataclass
class Method(DMLObject):
    """Method object."""
    return_type: Optional[str] = None
    formal_parameters: List['FormalParameter'] = field(default_factory=list)
    body: Optional[BlockStatement] = None
    modifiers: Set[MethodModifier] = field(default_factory=set)
    is_extern: bool = False
    
    def __post_init__(self):
        self.kind = ObjectKind.METHOD
    
    def has_modifier(self, modifier: MethodModifier) -> bool:
        """Check if method has specific modifier."""
        return modifier in self.modifiers
    
    def add_modifier(self, modifier: MethodModifier) -> None:
        """Add method modifier."""
        self.modifiers.add(modifier)
    
    def get_signature(self) -> str:
        """Get method signature string."""
        param_strs = []
        for param in self.formal_parameters:
            param_str = f"{param.param_type} {param.name.value}"
            param_strs.append(param_str)
        params = ", ".join(param_strs)
        return_type = self.return_type or "void"
        return f"{return_type} {self.name.value}({params})"


@dataclass
class Parameter(DMLObject):
    """Parameter object."""
    param_type: Optional[str] = None
    default_value: Optional[Expression] = None
    is_template_parameter: bool = False
    
    def __post_init__(self):
        self.kind = ObjectKind.PARAMETER
    
    def has_default(self) -> bool:
        """Check if parameter has default value."""
        return self.default_value is not None


@dataclass
class FormalParameter:
    """Formal parameter in method signature."""
    span: ZeroSpan
    name: DMLString
    param_type: str
    default_value: Optional[Expression] = None
    is_const: bool = False
    is_ref: bool = False
    
    def get_signature_string(self) -> str:
        """Get parameter signature string."""
        type_str = self.param_type
        if self.is_const:
            type_str = f"const {type_str}"
        if self.is_ref:
            type_str = f"{type_str}&"
        return f"{type_str} {self.name.value}"


@dataclass
class Attribute(DMLObject):
    """Attribute object."""
    attr_type: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.ATTRIBUTE


@dataclass
class Connect(DMLObject):
    """Connect object."""
    interface_name: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.CONNECT


@dataclass
class Interface(DMLObject):
    """Interface object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.INTERFACE


@dataclass
class Port(DMLObject):
    """Port object."""
    interface_name: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.PORT


@dataclass
class Event(DMLObject):
    """Event object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.EVENT


@dataclass
class Group(DMLObject):
    """Group object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.GROUP


@dataclass
class Data(DMLObject):
    """Data object."""
    data_type: Optional[str] = None
    initializer: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.DATA


@dataclass
class Session(DMLObject):
    """Session object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.SESSION


@dataclass
class Saved(DMLObject):
    """Saved object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.SAVED


@dataclass
class Constant(DMLObject):
    """Constant object."""
    const_type: Optional[str] = None
    value: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.CONSTANT


@dataclass
class Typedef(DMLObject):
    """Typedef object."""
    target_type: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.TYPEDEF


@dataclass
class Variable(DMLObject):
    """Variable object."""
    var_type: Optional[str] = None
    initializer: Optional[Expression] = None
    is_local: bool = False
    
    def __post_init__(self):
        self.kind = ObjectKind.VARIABLE


@dataclass
class Hook(DMLObject):
    """Hook object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.HOOK


@dataclass
class Subdevice(DMLObject):
    """Subdevice object."""
    device_type: Optional[str] = None
    
    def __post_init__(self):
        self.kind = ObjectKind.SUBDEVICE


@dataclass
class LogGroup(DMLObject):
    """Log group object."""
    
    def __post_init__(self):
        self.kind = ObjectKind.LOGGROUP


class Scope:
    """Represents a scope containing DML objects."""
    
    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.objects: Dict[str, DMLObject] = {}
        self.child_scopes: List['Scope'] = []
    
    def add_object(self, obj: DMLObject) -> None:
        """Add object to this scope."""
        self.objects[obj.name.value] = obj
    
    def find_object(self, name: str) -> Optional[DMLObject]:
        """Find object in this scope or parent scopes."""
        if name in self.objects:
            return self.objects[name]
        
        if self.parent:
            return self.parent.find_object(name)
        
        return None
    
    def find_local_object(self, name: str) -> Optional[DMLObject]:
        """Find object only in this scope."""
        return self.objects.get(name)
    
    def get_all_objects(self) -> List[DMLObject]:
        """Get all objects in this scope."""
        return list(self.objects.values())
    
    def create_child_scope(self) -> 'Scope':
        """Create a child scope."""
        child = Scope(parent=self)
        self.child_scopes.append(child)
        return child


class ObjectAnalyzer:
    """Analyzes DML objects for semantic information."""
    
    def __init__(self):
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
        self.root_scope = Scope()
        self.current_scope = self.root_scope
        self.object_hierarchy: List[DMLObject] = []
    
    def analyze_object(self, obj: DMLObject) -> None:
        """Analyze a DML object."""
        # Enter object scope
        self.object_hierarchy.append(obj)
        object_scope = self.current_scope.create_child_scope()
        old_scope = self.current_scope
        self.current_scope = object_scope
        
        try:
            # Add object to parent scope
            old_scope.add_object(obj)
            
            # Analyze object-specific content
            if isinstance(obj, Device):
                self._analyze_device(obj)
            elif isinstance(obj, Template):
                self._analyze_template(obj)
            elif isinstance(obj, Bank):
                self._analyze_bank(obj)
            elif isinstance(obj, Register):
                self._analyze_register(obj)
            elif isinstance(obj, Field):
                self._analyze_field(obj)
            elif isinstance(obj, Method):
                self._analyze_method(obj)
            elif isinstance(obj, Parameter):
                self._analyze_parameter(obj)
            
            # Analyze children
            for child in obj.children:
                self.analyze_object(child)
                
        finally:
            # Exit object scope
            self.current_scope = old_scope
            self.object_hierarchy.pop()
    
    def _analyze_device(self, device: Device) -> None:
        """Analyze device object."""
        # Validate device structure
        if not device.children:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Device has no banks or other child objects",
                span=device.span
            )
            self.errors.append(error)
        
        # Check for required parameters
        # TODO: Add device-specific validation
    
    def _analyze_template(self, template: Template) -> None:
        """Analyze template object."""
        # Check template validity
        if template.is_abstract and template.children:
            # Abstract templates can have partial implementations
            pass
        
        # Validate template parameters
        for param_name in template.type_parameters:
            if not param_name.isidentifier():
                error = DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"Invalid template parameter name: {param_name}",
                    span=template.span
                )
                self.errors.append(error)
    
    def _analyze_bank(self, bank: Bank) -> None:
        """Analyze bank object."""
        # Check for registers
        registers = bank.get_children_of_kind(ObjectKind.REGISTER)
        if not registers:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Bank has no registers",
                span=bank.span
            )
            self.errors.append(error)
    
    def _analyze_register(self, register: Register) -> None:
        """Analyze register object."""
        # Validate register size and offset
        if register.size is None:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Register missing size specification",
                span=register.span
            )
            self.errors.append(error)
        
        # Check field coverage
        fields = register.get_children_of_kind(ObjectKind.FIELD)
        if fields:
            self._check_field_coverage(register, fields)
    
    def _analyze_field(self, field: Field) -> None:
        """Analyze field object."""
        # Validate bit range
        if field.bit_range:
            high, low = field.bit_range
            # TODO: Validate that high >= low and ranges are valid
            pass
    
    def _analyze_method(self, method: Method) -> None:
        """Analyze method object."""
        # Check for conflicting modifiers
        if (method.has_modifier(MethodModifier.INLINE) and 
            method.has_modifier(MethodModifier.SHARED)):
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Method cannot be both inline and shared",
                span=method.span
            )
            self.errors.append(error)
        
        # Check parameter names for duplicates
        param_names = set()
        for param in method.formal_parameters:
            if param.name.value in param_names:
                error = DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"Duplicate parameter name: {param.name.value}",
                    span=param.span
                )
                self.errors.append(error)
            param_names.add(param.name.value)
    
    def _analyze_parameter(self, parameter: Parameter) -> None:
        """Analyze parameter object."""
        # Check parameter type validity
        if parameter.param_type:
            # TODO: Validate parameter type exists
            pass
    
    def _check_field_coverage(self, register: Register, fields: List[DMLObject]) -> None:
        """Check that fields properly cover register bits."""
        # TODO: Implement field coverage analysis
        pass
    
    def resolve_template_applications(self, obj: DMLObject) -> None:
        """Resolve template applications for an object."""
        for template_name in obj.templates:
            template = self._find_template(template_name)
            if template:
                # Apply template to object
                self._apply_template(obj, template)
            else:
                error = DMLError(
                    kind=DMLErrorKind.TEMPLATE_ERROR,
                    message=f"Template not found: {template_name}",
                    span=obj.span
                )
                self.errors.append(error)
                
                # Add template reference
                node_ref = NodeRef(template_name, obj.span)
                reference = SymbolReference(
                    node_ref=node_ref,
                    kind=ReferenceKind.TEMPLATE,
                    location=obj.span
                )
                self.references.append(reference)
    
    def _find_template(self, name: str) -> Optional[Template]:
        """Find template by name."""
        obj = self.root_scope.find_object(name)
        if obj and isinstance(obj, Template):
            return obj
        return None
    
    def _apply_template(self, obj: DMLObject, template: Template) -> None:
        """Apply template to object."""
        # Copy template parameters to object
        for param_name, param in template.parameters.items():
            if param_name not in obj.parameters:
                obj.add_parameter(param)
        
        # Copy template children (methods, etc.) that aren't overridden
        for child in template.children:
            if not obj.find_child(child.name.value):
                # Create copy of template child
                child_copy = self._copy_object(child)
                obj.add_child(child_copy)
    
    def _copy_object(self, obj: DMLObject) -> DMLObject:
        """Create a copy of an object."""
        # TODO: Implement deep copy of DML objects
        # This is a simplified version
        if isinstance(obj, Method):
            return Method(
                span=obj.span,
                name=obj.name,
                return_type=obj.return_type,
                formal_parameters=obj.formal_parameters.copy(),
                body=obj.body,
                modifiers=obj.modifiers.copy(),
                is_extern=obj.is_extern
            )
        # Add other object types as needed
        return obj
    
    def get_errors(self) -> List[DMLError]:
        """Get analysis errors."""
        return self.errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get symbol references found."""
        return self.references
    
    def get_objects_by_kind(self, kind: ObjectKind) -> List[DMLObject]:
        """Get all objects of a specific kind."""
        result = []
        self._collect_objects_by_kind(self.root_scope, kind, result)
        return result
    
    def _collect_objects_by_kind(self, scope: Scope, kind: ObjectKind, result: List[DMLObject]) -> None:
        """Recursively collect objects of specific kind."""
        for obj in scope.get_all_objects():
            if obj.kind == kind:
                result.append(obj)
        
        for child_scope in scope.child_scopes:
            self._collect_objects_by_kind(child_scope, kind, result)


def create_device(span: ZeroSpan, name: str, version: Optional[str] = None) -> Device:
    """Helper to create device objects."""
    dml_name = DMLString(name, span)
    return Device(span=span, name=dml_name, kind=ObjectKind.DEVICE, version=version)


def create_template(span: ZeroSpan, name: str, is_abstract: bool = False) -> Template:
    """Helper to create template objects."""
    dml_name = DMLString(name, span)
    return Template(span=span, name=dml_name, kind=ObjectKind.TEMPLATE, is_abstract=is_abstract)


def create_method(span: ZeroSpan, name: str, return_type: Optional[str] = None) -> Method:
    """Helper to create method objects."""
    dml_name = DMLString(name, span)
    return Method(span=span, name=dml_name, kind=ObjectKind.METHOD, return_type=return_type)


__all__ = [
    'ObjectKind', 'Visibility', 'MethodModifier', 'DMLObject', 'Device', 'Template',
    'Bank', 'Register', 'Field', 'Method', 'Parameter', 'FormalParameter', 'Attribute',
    'Connect', 'Interface', 'Port', 'Event', 'Group', 'Data', 'Session', 'Saved',
    'Constant', 'Typedef', 'Variable', 'Hook', 'Subdevice', 'LogGroup', 'Scope',
    'ObjectAnalyzer', 'create_device', 'create_template', 'create_method'
]