"""
Syntax validation for DML code.

Provides comprehensive validation rules for DML syntax including
declaration order, nesting rules, and structural constraints.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import logging
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ...span import ZeroSpan, ZeroPosition
from ...lsp_data import DMLSymbol, DMLSymbolKind
from ..types import DMLError, DMLErrorKind, DMLDiagnosticSeverity

logger = logging.getLogger(__name__)


class DeclarationContext(Enum):
    """Context where declarations can appear."""
    TOP_LEVEL = "top_level"
    DEVICE = "device"
    TEMPLATE = "template"
    BANK = "bank"
    REGISTER = "register"
    FIELD = "field"
    METHOD = "method"
    GROUP = "group"


@dataclass
class ValidationRule:
    """Base class for validation rules."""
    name: str
    description: str
    severity: DMLDiagnosticSeverity = DMLDiagnosticSeverity.ERROR
    
    def validate(self, symbols: List[DMLSymbol], dml_version: Optional[str]) -> List[DMLError]:
        """Validate and return errors."""
        raise NotImplementedError


class DMLVersionValidator:
    """Validates DML version declarations."""
    
    SUPPORTED_VERSIONS = {"1.2", "1.4"}
    RECOMMENDED_VERSION = "1.4"
    
    def validate_version(self, version: Optional[str], span: ZeroSpan) -> List[DMLError]:
        """Validate DML version."""
        errors = []
        
        if not version:
            errors.append(DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Missing DML version declaration. Add 'dml 1.4;' at the beginning of the file.",
                span=span,
                severity=DMLDiagnosticSeverity.ERROR
            ))
            return errors
        
        if version not in self.SUPPORTED_VERSIONS:
            errors.append(DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message=f"Unsupported DML version '{version}'. Supported versions: {', '.join(self.SUPPORTED_VERSIONS)}",
                span=span,
                severity=DMLDiagnosticSeverity.ERROR
            ))
        elif version != self.RECOMMENDED_VERSION:
            errors.append(DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message=f"DML version '{version}' is deprecated. Consider upgrading to DML {self.RECOMMENDED_VERSION}.",
                span=span,
                severity=DMLDiagnosticSeverity.WARNING
            ))
        
        return errors


class DeclarationOrderValidator:
    """Validates declaration ordering rules."""
    
    # Valid parent-child relationships
    VALID_CHILDREN: Dict[DMLSymbolKind, Set[DMLSymbolKind]] = {
        DMLSymbolKind.DEVICE: {
            DMLSymbolKind.BANK, DMLSymbolKind.REGISTER, DMLSymbolKind.METHOD,
            DMLSymbolKind.PARAMETER, DMLSymbolKind.ATTRIBUTE, DMLSymbolKind.PORT,
            DMLSymbolKind.CONNECT, DMLSymbolKind.INTERFACE
        },
        DMLSymbolKind.TEMPLATE: {
            DMLSymbolKind.BANK, DMLSymbolKind.REGISTER, DMLSymbolKind.FIELD,
            DMLSymbolKind.METHOD, DMLSymbolKind.PARAMETER, DMLSymbolKind.ATTRIBUTE
        },
        DMLSymbolKind.BANK: {
            DMLSymbolKind.REGISTER, DMLSymbolKind.METHOD, DMLSymbolKind.PARAMETER,
            DMLSymbolKind.ATTRIBUTE
        },
        DMLSymbolKind.REGISTER: {
            DMLSymbolKind.FIELD, DMLSymbolKind.METHOD, DMLSymbolKind.PARAMETER,
            DMLSymbolKind.ATTRIBUTE
        },
        DMLSymbolKind.FIELD: {
            DMLSymbolKind.METHOD, DMLSymbolKind.PARAMETER, DMLSymbolKind.ATTRIBUTE
        },
    }
    
    def validate_nesting(self, symbol: DMLSymbol, parent: Optional[DMLSymbol] = None) -> List[DMLError]:
        """Validate that symbol nesting is correct."""
        errors = []
        
        if parent:
            valid_children = self.VALID_CHILDREN.get(parent.kind, set())
            
            if symbol.kind not in valid_children:
                errors.append(DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"{symbol.kind.value.capitalize()} '{symbol.name}' cannot be declared inside {parent.kind.value} '{parent.name}'",
                    span=symbol.location.span,
                    severity=DMLDiagnosticSeverity.ERROR
                ))
        
        # Recursively validate children
        for child in symbol.children:
            errors.extend(self.validate_nesting(child, symbol))
        
        return errors
    
    def validate_duplicate_names(self, symbols: List[DMLSymbol], scope_name: str = "global") -> List[DMLError]:
        """Check for duplicate symbol names in the same scope."""
        errors = []
        seen_names: Dict[str, DMLSymbol] = {}
        
        for symbol in symbols:
            if symbol.name in seen_names:
                prev_symbol = seen_names[symbol.name]
                errors.append(DMLError(
                    kind=DMLErrorKind.SEMANTIC_ERROR,
                    message=f"Duplicate {symbol.kind.value} name '{symbol.name}' in {scope_name} scope. "
                           f"First declared at {prev_symbol.location.span.range.start}",
                    span=symbol.location.span,
                    severity=DMLDiagnosticSeverity.ERROR
                ))
            else:
                seen_names[symbol.name] = symbol
            
            # Recursively check children
            if symbol.children:
                child_errors = self.validate_duplicate_names(
                    symbol.children,
                    f"{symbol.kind.value} '{symbol.name}'"
                )
                errors.extend(child_errors)
        
        return errors


class StructuralValidator:
    """Validates DML structural constraints."""
    
    def validate_device_structure(self, device_symbol: DMLSymbol) -> List[DMLError]:
        """Validate device structure."""
        errors = []
        
        # Check for required elements
        has_bank_or_register = any(
            child.kind in (DMLSymbolKind.BANK, DMLSymbolKind.REGISTER)
            for child in device_symbol.children
        )
        
        if not has_bank_or_register:
            errors.append(DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message=f"Device '{device_symbol.name}' should contain at least one bank or register",
                span=device_symbol.location.span,
                severity=DMLDiagnosticSeverity.WARNING
            ))
        
        return errors
    
    def validate_register_structure(self, register_symbol: DMLSymbol) -> List[DMLError]:
        """Validate register structure."""
        errors = []
        
        # Registers should typically have a size parameter
        has_size = any(
            child.kind == DMLSymbolKind.PARAMETER and child.name == "size"
            for child in register_symbol.children
        )
        
        if not has_size:
            errors.append(DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message=f"Register '{register_symbol.name}' should have a 'size' parameter",
                span=register_symbol.location.span,
                severity=DMLDiagnosticSeverity.WARNING
            ))
        
        return errors
    
    def validate_method_structure(self, method_symbol: DMLSymbol) -> List[DMLError]:
        """Validate method structure."""
        errors = []
        
        # Methods must have valid names (not reserved words)
        reserved_names = {'init', 'new', 'delete', 'reset'}
        
        if method_symbol.name in reserved_names:
            # These are special methods, validate they follow conventions
            pass  # Could add specific validation for special methods
        
        return errors


class SyntaxValidator:
    """Main syntax validator orchestrating all validation rules."""
    
    def __init__(self):
        self.version_validator = DMLVersionValidator()
        self.order_validator = DeclarationOrderValidator()
        self.structural_validator = StructuralValidator()
    
    def validate_file(self, 
                     symbols: List[DMLSymbol], 
                     dml_version: Optional[str],
                     file_span: ZeroSpan) -> List[DMLError]:
        """Validate entire file."""
        errors = []
        
        # Validate DML version
        errors.extend(self.version_validator.validate_version(dml_version, file_span))
        
        # Validate declaration ordering and nesting
        for symbol in symbols:
            errors.extend(self.order_validator.validate_nesting(symbol))
        
        # Check for duplicate names
        errors.extend(self.order_validator.validate_duplicate_names(symbols))
        
        # Validate structural constraints
        for symbol in symbols:
            if symbol.kind == DMLSymbolKind.DEVICE:
                errors.extend(self.structural_validator.validate_device_structure(symbol))
            elif symbol.kind == DMLSymbolKind.REGISTER:
                errors.extend(self.structural_validator.validate_register_structure(symbol))
            elif symbol.kind == DMLSymbolKind.METHOD:
                errors.extend(self.structural_validator.validate_method_structure(symbol))
            
            # Recursively validate children
            if symbol.children:
                child_span = symbol.location.span
                errors.extend(self.validate_symbols_recursive(symbol.children, dml_version))
        
        return errors
    
    def validate_symbols_recursive(self, 
                                   symbols: List[DMLSymbol],
                                   dml_version: Optional[str]) -> List[DMLError]:
        """Recursively validate symbols."""
        errors = []
        
        for symbol in symbols:
            if symbol.kind == DMLSymbolKind.DEVICE:
                errors.extend(self.structural_validator.validate_device_structure(symbol))
            elif symbol.kind == DMLSymbolKind.REGISTER:
                errors.extend(self.structural_validator.validate_register_structure(symbol))
            elif symbol.kind == DMLSymbolKind.METHOD:
                errors.extend(self.structural_validator.validate_method_structure(symbol))
            
            if symbol.children:
                errors.extend(self.validate_symbols_recursive(symbol.children, dml_version))
        
        return errors


# Export main classes
__all__ = [
    'SyntaxValidator',
    'DMLVersionValidator',
    'DeclarationOrderValidator',
    'StructuralValidator',
    'ValidationRule',
    'DeclarationContext'
]
