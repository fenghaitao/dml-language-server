"""
Template System for DML Language Server.

Provides template resolution, inheritance, and composition functionality.
Ported concepts from the Rust implementation.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from typing import List, Optional, Dict, Any, Set, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ...lsp_data import DMLSymbol, DMLSymbolKind, DMLLocation
from ..types import DMLError, DMLErrorKind, SymbolReference
from .enhanced_parser import (
    TemplateDeclaration, DeviceDeclaration, ParameterDeclaration, 
    MethodDeclaration, FieldDeclaration, RegisterDeclaration, BankDeclaration
)

logger = logging.getLogger(__name__)


class TemplateResolutionError(Exception):
    """Exception raised during template resolution."""
    pass


@dataclass
class TemplateParameter:
    """Template parameter with resolved value."""
    name: str
    value: Any
    parameter_type: Optional[str]
    source_template: str
    span: ZeroSpan
    
    def __str__(self) -> str:
        return f"{self.name} = {self.value}"


@dataclass
class TemplateMethod:
    """Template method with metadata."""
    name: str
    declaration: MethodDeclaration
    source_template: str
    override_level: int = 0  # For method resolution order
    
    def __str__(self) -> str:
        return f"{self.name} (from {self.source_template})"


@dataclass
class ResolvedTemplate:
    """A template after resolution and parameter substitution."""
    name: str
    original_declaration: TemplateDeclaration
    resolved_parameters: Dict[str, TemplateParameter]
    resolved_methods: Dict[str, TemplateMethod]
    parent_templates: List[str]
    children_templates: List[str]
    resolution_order: List[str]  # Method resolution order
    
    def get_parameter(self, name: str) -> Optional[TemplateParameter]:
        """Get a resolved parameter by name."""
        return self.resolved_parameters.get(name)
    
    def get_method(self, name: str) -> Optional[TemplateMethod]:
        """Get a resolved method by name."""
        return self.resolved_methods.get(name)
    
    def has_parameter(self, name: str) -> bool:
        """Check if template has a parameter."""
        return name in self.resolved_parameters
    
    def has_method(self, name: str) -> bool:
        """Check if template has a method."""
        return name in self.resolved_methods


class TemplateInheritanceResolver:
    """Resolves template inheritance chains and method resolution order."""
    
    def __init__(self):
        self.templates: Dict[str, TemplateDeclaration] = {}
        self.resolved_templates: Dict[str, ResolvedTemplate] = {}
        self.inheritance_graph: Dict[str, Set[str]] = defaultdict(set)
        self.errors: List[DMLError] = []
    
    def add_template(self, template: TemplateDeclaration) -> None:
        """Add a template declaration."""
        self.templates[template.name] = template
        logger.debug(f"Added template: {template.name}")
    
    def resolve_template(self, template_name: str) -> Optional[ResolvedTemplate]:
        """Resolve a template and its inheritance chain."""
        if template_name in self.resolved_templates:
            return self.resolved_templates[template_name]
        
        if template_name not in self.templates:
            error = DMLError(
                kind=DMLErrorKind.TEMPLATE_ERROR,
                message=f"Template '{template_name}' not found",
                span=ZeroSpan("", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
            )
            self.errors.append(error)
            return None
        
        try:
            resolved = self._resolve_template_recursive(template_name, set())
            self.resolved_templates[template_name] = resolved
            return resolved
        except TemplateResolutionError as e:
            error = DMLError(
                kind=DMLErrorKind.TEMPLATE_ERROR,
                message=str(e),
                span=self.templates[template_name].span
            )
            self.errors.append(error)
            return None
    
    def _resolve_template_recursive(self, template_name: str, visiting: Set[str]) -> ResolvedTemplate:
        """Recursively resolve template inheritance."""
        if template_name in visiting:
            raise TemplateResolutionError(f"Circular template dependency detected: {' -> '.join(visiting)} -> {template_name}")
        
        template_decl = self.templates[template_name]
        visiting.add(template_name)
        
        # Find parent templates (looking for 'is parent_template' syntax)
        parent_templates = self._extract_parent_templates(template_decl)
        
        # Resolve parent templates first
        resolved_parents = []
        for parent_name in parent_templates:
            if parent_name not in self.templates:
                raise TemplateResolutionError(f"Parent template '{parent_name}' not found for template '{template_name}'")
            
            parent_resolved = self._resolve_template_recursive(parent_name, visiting.copy())
            resolved_parents.append(parent_resolved)
        
        visiting.remove(template_name)
        
        # Build method resolution order (linearization)
        resolution_order = self._compute_method_resolution_order(template_name, parent_templates)
        
        # Resolve parameters (merge with parent parameters)
        resolved_parameters = self._resolve_parameters(template_decl, resolved_parents)
        
        # Resolve methods (handle overrides)
        resolved_methods = self._resolve_methods(template_decl, resolved_parents, resolution_order)
        
        return ResolvedTemplate(
            name=template_name,
            original_declaration=template_decl,
            resolved_parameters=resolved_parameters,
            resolved_methods=resolved_methods,
            parent_templates=parent_templates,
            children_templates=[],  # Will be filled in later
            resolution_order=resolution_order
        )
    
    def _extract_parent_templates(self, template_decl: TemplateDeclaration) -> List[str]:
        """Extract parent template names from declaration."""
        # This would need to be enhanced to parse 'is parent_template' syntax
        # For now, return empty list as templates don't explicitly declare inheritance in our simple parser
        return []
    
    def _compute_method_resolution_order(self, template_name: str, parents: List[str]) -> List[str]:
        """Compute method resolution order using C3 linearization."""
        if not parents:
            return [template_name]
        
        # Simplified MRO - just template + parents in order
        # Real C3 linearization would be more complex
        mro = [template_name]
        for parent in parents:
            if parent not in mro:
                mro.append(parent)
        
        return mro
    
    def _resolve_parameters(self, template_decl: TemplateDeclaration, parents: List[ResolvedTemplate]) -> Dict[str, TemplateParameter]:
        """Resolve parameters with inheritance."""
        resolved_params = {}
        
        # Start with parent parameters (in reverse order for proper override)
        for parent in reversed(parents):
            for param_name, param in parent.resolved_parameters.items():
                resolved_params[param_name] = param
        
        # Add/override with current template parameters
        for param_decl in template_decl.parameters:
            template_param = TemplateParameter(
                name=param_decl.name,
                value=param_decl.default_value,  # Would need evaluation
                parameter_type=param_decl.parameter_type,
                source_template=template_decl.name,
                span=param_decl.span
            )
            resolved_params[param_decl.name] = template_param
        
        return resolved_params
    
    def _resolve_methods(self, template_decl: TemplateDeclaration, parents: List[ResolvedTemplate], mro: List[str]) -> Dict[str, TemplateMethod]:
        """Resolve methods with proper override handling."""
        resolved_methods = {}
        
        # Process methods in MRO order (most specific first)
        for template_name in reversed(mro):
            if template_name == template_decl.name:
                # Current template methods
                for method_decl in template_decl.methods:
                    template_method = TemplateMethod(
                        name=method_decl.name,
                        declaration=method_decl,
                        source_template=template_decl.name,
                        override_level=mro.index(template_name)
                    )
                    resolved_methods[method_decl.name] = template_method
            else:
                # Parent template methods
                for parent in parents:
                    if parent.name == template_name:
                        for method_name, method in parent.resolved_methods.items():
                            if method_name not in resolved_methods:
                                resolved_methods[method_name] = method
        
        return resolved_methods
    
    def get_errors(self) -> List[DMLError]:
        """Get template resolution errors."""
        return self.errors


class TemplateApplicator:
    """Applies templates to device objects."""
    
    def __init__(self, resolver: TemplateInheritanceResolver):
        self.resolver = resolver
        self.applied_templates: Dict[str, List[ResolvedTemplate]] = {}
        self.errors: List[DMLError] = []
    
    def apply_templates_to_device(self, device: DeviceDeclaration) -> DeviceDeclaration:
        """Apply templates to a device declaration."""
        applied_templates = []
        
        # Resolve each template applied to the device
        for template_name in device.templates:
            resolved_template = self.resolver.resolve_template(template_name)
            if resolved_template:
                applied_templates.append(resolved_template)
            else:
                error = DMLError(
                    kind=DMLErrorKind.TEMPLATE_ERROR,
                    message=f"Cannot resolve template '{template_name}' for device '{device.name}'",
                    span=device.span
                )
                self.errors.append(error)
        
        self.applied_templates[device.name] = applied_templates
        
        # Apply template parameters and methods to device
        enhanced_device = self._merge_templates_into_device(device, applied_templates)
        
        return enhanced_device
    
    def _merge_templates_into_device(self, device: DeviceDeclaration, templates: List[ResolvedTemplate]) -> DeviceDeclaration:
        """Merge template content into device."""
        # Create new device with merged content
        merged_parameters = list(device.parameters)
        merged_methods = list(device.methods)
        merged_banks = list(device.banks)
        
        # Process templates in application order
        for template in templates:
            # Add template parameters (if not already present in device)
            existing_param_names = {p.name for p in merged_parameters}
            for param_name, template_param in template.resolved_parameters.items():
                if param_name not in existing_param_names:
                    # Convert TemplateParameter back to ParameterDeclaration
                    param_decl = ParameterDeclaration(
                        span=template_param.span,
                        name=param_name,
                        parameter_type=template_param.parameter_type,
                        default_value=template_param.value
                    )
                    merged_parameters.append(param_decl)
                    existing_param_names.add(param_name)
            
            # Add template methods (if not already present in device)
            existing_method_names = {m.name for m in merged_methods}
            for method_name, template_method in template.resolved_methods.items():
                if method_name not in existing_method_names:
                    merged_methods.append(template_method.declaration)
                    existing_method_names.add(method_name)
        
        # Create new device declaration with merged content
        return DeviceDeclaration(
            span=device.span,
            name=device.name,
            parameters=merged_parameters,
            banks=merged_banks,
            methods=merged_methods,
            templates=device.templates
        )
    
    def get_template_symbols(self, object_name: str) -> List[DMLSymbol]:
        """Get symbols contributed by templates to an object."""
        symbols = []
        
        if object_name in self.applied_templates:
            for template in self.applied_templates[object_name]:
                # Add parameter symbols
                for param_name, param in template.resolved_parameters.items():
                    symbol = DMLSymbol(
                        name=param_name,
                        kind=DMLSymbolKind.PARAMETER,
                        location=DMLLocation(span=param.span),
                        detail=f"Parameter from template {template.name}",
                        documentation=f"Type: {param.parameter_type or 'auto'}, Value: {param.value}"
                    )
                    symbols.append(symbol)
                
                # Add method symbols
                for method_name, method in template.resolved_methods.items():
                    symbol = DMLSymbol(
                        name=method_name,
                        kind=DMLSymbolKind.METHOD,
                        location=DMLLocation(span=method.declaration.span),
                        detail=f"Method from template {template.name}",
                        documentation=f"Return type: {method.declaration.return_type or 'void'}"
                    )
                    symbols.append(symbol)
        
        return symbols
    
    def get_errors(self) -> List[DMLError]:
        """Get template application errors."""
        return self.errors


class TemplateSystem:
    """Complete template system for DML language server."""
    
    def __init__(self):
        self.resolver = TemplateInheritanceResolver()
        self.applicator = TemplateApplicator(self.resolver)
        self.template_scope = None
    
    def initialize_template_scope(self, global_scope) -> None:
        """Initialize template scope within global scope."""
        template_span = ZeroSpan("templates", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        # Import SymbolScope here to avoid circular imports
        from .. import SymbolScope
        self.template_scope = SymbolScope("templates", template_span, global_scope)
    
    def add_template(self, template: TemplateDeclaration) -> None:
        """Add a template to the system."""
        self.resolver.add_template(template)
        
        # Add template symbol to scope
        if self.template_scope:
            template_symbol = DMLSymbol(
                name=template.name,
                kind=DMLSymbolKind.TEMPLATE,
                location=DMLLocation(span=template.span),
                detail=f"Template with {len(template.parameters)} parameters",
                documentation=f"Template {template.name}"
            )
            self.template_scope.add_symbol(template_symbol)
    
    def process_device(self, device: DeviceDeclaration) -> DeviceDeclaration:
        """Process a device with template application."""
        if not device.templates:
            return device
        
        logger.debug(f"Applying templates {device.templates} to device {device.name}")
        return self.applicator.apply_templates_to_device(device)
    
    def get_template_completions(self, prefix: str = "") -> List[Dict[str, str]]:
        """Get template names for code completion."""
        completions = []
        
        for template_name in self.resolver.templates.keys():
            if template_name.startswith(prefix):
                template = self.resolver.templates[template_name]
                completions.append({
                    "label": template_name,
                    "kind": "template",
                    "detail": f"Template with {len(template.parameters)} parameters",
                    "documentation": f"DML template {template_name}"
                })
        
        return completions
    
    def resolve_template_reference(self, template_name: str, position: ZeroPosition) -> Optional[DMLLocation]:
        """Resolve a template reference to its definition."""
        if template_name in self.resolver.templates:
            template = self.resolver.templates[template_name]
            return DMLLocation(span=template.span)
        return None
    
    def get_template_hover_info(self, template_name: str) -> Optional[str]:
        """Get hover information for a template."""
        if template_name in self.resolver.templates:
            template = self.resolver.templates[template_name]
            info = f"**Template {template_name}**\n\n"
            
            if template.parameters:
                info += "**Parameters:**\n"
                for param in template.parameters:
                    param_type = param.parameter_type or "auto"
                    info += f"- `{param.name}: {param_type}`\n"
            
            if template.methods:
                info += "\n**Methods:**\n"
                for method in template.methods:
                    return_type = method.return_type or "void"
                    info += f"- `{method.name}() -> {return_type}`\n"
            
            return info
        return None
    
    def validate_template_application(self, device: DeviceDeclaration) -> List[DMLError]:
        """Validate that template application is correct."""
        errors = []
        
        for template_name in device.templates:
            if template_name not in self.resolver.templates:
                error = DMLError(
                    kind=DMLErrorKind.TEMPLATE_ERROR,
                    message=f"Template '{template_name}' not found",
                    span=device.span
                )
                errors.append(error)
        
        return errors
    
    def get_all_errors(self) -> List[DMLError]:
        """Get all template system errors."""
        return self.resolver.get_errors() + self.applicator.get_errors()


# Export main classes
__all__ = [
    "TemplateSystem",
    "TemplateInheritanceResolver", 
    "TemplateApplicator",
    "ResolvedTemplate",
    "TemplateParameter",
    "TemplateMethod"
]