"""
Tests for syntax validation functionality.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import pytest
from pathlib import Path

from dml_language_server.span import ZeroSpan, ZeroRange, ZeroPosition
from dml_language_server.lsp_data import DMLSymbol, DMLSymbolKind, DMLLocation
from dml_language_server.analysis.parsing.syntax_validator import (
    SyntaxValidator,
    DMLVersionValidator,
    DeclarationOrderValidator,
    StructuralValidator,
)
from dml_language_server.analysis.types import DMLErrorKind, DMLDiagnosticSeverity


class TestDMLVersionValidator:
    """Test DML version validation."""
    
    def test_missing_version(self):
        """Test detection of missing DML version."""
        validator = DMLVersionValidator()
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_version(None, span)
        
        assert len(errors) == 1
        assert "Missing DML version" in errors[0].message
        assert errors[0].severity == DMLDiagnosticSeverity.ERROR
    
    def test_unsupported_version(self):
        """Test detection of unsupported DML version."""
        validator = DMLVersionValidator()
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_version("1.0", span)
        
        assert len(errors) == 1
        assert "Unsupported DML version" in errors[0].message
        assert "1.0" in errors[0].message
    
    def test_deprecated_version(self):
        """Test warning for deprecated DML version."""
        validator = DMLVersionValidator()
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_version("1.2", span)
        
        assert len(errors) == 1
        assert "deprecated" in errors[0].message.lower()
        assert errors[0].severity == DMLDiagnosticSeverity.WARNING
    
    def test_valid_version(self):
        """Test that recommended version passes."""
        validator = DMLVersionValidator()
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_version("1.4", span)
        
        assert len(errors) == 0


class TestDeclarationOrderValidator:
    """Test declaration order and nesting validation."""
    
    def create_symbol(self, name: str, kind: DMLSymbolKind, children=None) -> DMLSymbol:
        """Helper to create a test symbol."""
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 10)))
        symbol = DMLSymbol(
            name=name,
            kind=kind,
            location=DMLLocation(span=span),
            detail=f"Test {kind.value}",
            documentation=f"Test {name}"
        )
        if children:
            symbol.children = children
        return symbol
    
    def test_valid_nesting_device_bank(self):
        """Test that bank inside device is valid."""
        validator = DeclarationOrderValidator()
        
        bank = self.create_symbol("test_bank", DMLSymbolKind.BANK)
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE, [bank])
        
        errors = validator.validate_nesting(bank, device)
        
        assert len(errors) == 0
    
    def test_invalid_nesting_field_in_device(self):
        """Test that field directly in device is invalid."""
        validator = DeclarationOrderValidator()
        
        field = self.create_symbol("test_field", DMLSymbolKind.FIELD)
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE, [field])
        
        errors = validator.validate_nesting(field, device)
        
        assert len(errors) == 1
        assert "cannot be declared inside" in errors[0].message
        assert "field" in errors[0].message.lower()
        assert "device" in errors[0].message.lower()
    
    def test_valid_nesting_field_in_register(self):
        """Test that field inside register is valid."""
        validator = DeclarationOrderValidator()
        
        field = self.create_symbol("test_field", DMLSymbolKind.FIELD)
        register = self.create_symbol("test_register", DMLSymbolKind.REGISTER, [field])
        
        errors = validator.validate_nesting(field, register)
        
        assert len(errors) == 0
    
    def test_duplicate_names_detection(self):
        """Test detection of duplicate symbol names."""
        validator = DeclarationOrderValidator()
        
        symbol1 = self.create_symbol("duplicate", DMLSymbolKind.REGISTER)
        symbol2 = self.create_symbol("duplicate", DMLSymbolKind.REGISTER)
        
        errors = validator.validate_duplicate_names([symbol1, symbol2])
        
        assert len(errors) == 1
        assert "Duplicate" in errors[0].message
        assert "duplicate" in errors[0].message
    
    def test_no_duplicates_different_scopes(self):
        """Test that same names in different scopes are allowed."""
        validator = DeclarationOrderValidator()
        
        # Two different devices can have registers with the same name
        reg1 = self.create_symbol("status", DMLSymbolKind.REGISTER)
        reg2 = self.create_symbol("status", DMLSymbolKind.REGISTER)
        device1 = self.create_symbol("device1", DMLSymbolKind.DEVICE, [reg1])
        device2 = self.create_symbol("device2", DMLSymbolKind.DEVICE, [reg2])
        
        # Should not report duplicates at top level
        errors = validator.validate_duplicate_names([device1, device2])
        
        assert len(errors) == 0
    
    def test_recursive_duplicate_detection(self):
        """Test that duplicates in nested scopes are detected."""
        validator = DeclarationOrderValidator()
        
        field1 = self.create_symbol("data", DMLSymbolKind.FIELD)
        field2 = self.create_symbol("data", DMLSymbolKind.FIELD)
        register = self.create_symbol("test_reg", DMLSymbolKind.REGISTER, [field1, field2])
        
        errors = validator.validate_duplicate_names([register])
        
        assert len(errors) == 1
        assert "Duplicate" in errors[0].message
        assert "data" in errors[0].message


class TestStructuralValidator:
    """Test structural validation rules."""
    
    def create_symbol(self, name: str, kind: DMLSymbolKind, children=None) -> DMLSymbol:
        """Helper to create a test symbol."""
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 10)))
        symbol = DMLSymbol(
            name=name,
            kind=kind,
            location=DMLLocation(span=span),
            detail=f"Test {kind.value}",
            documentation=f"Test {name}"
        )
        if children:
            symbol.children = children
        return symbol
    
    def test_device_without_banks_warning(self):
        """Test warning for device without banks or registers."""
        validator = StructuralValidator()
        
        device = self.create_symbol("empty_device", DMLSymbolKind.DEVICE, [])
        
        errors = validator.validate_device_structure(device)
        
        assert len(errors) == 1
        assert "should contain at least one bank or register" in errors[0].message
        assert errors[0].severity == DMLDiagnosticSeverity.WARNING
    
    def test_device_with_bank_valid(self):
        """Test that device with bank is valid."""
        validator = StructuralValidator()
        
        bank = self.create_symbol("test_bank", DMLSymbolKind.BANK)
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE, [bank])
        
        errors = validator.validate_device_structure(device)
        
        assert len(errors) == 0
    
    def test_register_without_size_warning(self):
        """Test warning for register without size parameter."""
        validator = StructuralValidator()
        
        register = self.create_symbol("test_reg", DMLSymbolKind.REGISTER, [])
        
        errors = validator.validate_register_structure(register)
        
        assert len(errors) == 1
        assert "should have a 'size' parameter" in errors[0].message
        assert errors[0].severity == DMLDiagnosticSeverity.WARNING
    
    def test_register_with_size_valid(self):
        """Test that register with size parameter is valid."""
        validator = StructuralValidator()
        
        size_param = self.create_symbol("size", DMLSymbolKind.PARAMETER)
        register = self.create_symbol("test_reg", DMLSymbolKind.REGISTER, [size_param])
        
        errors = validator.validate_register_structure(register)
        
        assert len(errors) == 0


class TestSyntaxValidator:
    """Test the main syntax validator."""
    
    def create_symbol(self, name: str, kind: DMLSymbolKind, children=None) -> DMLSymbol:
        """Helper to create a test symbol."""
        span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 10)))
        symbol = DMLSymbol(
            name=name,
            kind=kind,
            location=DMLLocation(span=span),
            detail=f"Test {kind.value}",
            documentation=f"Test {name}"
        )
        if children:
            symbol.children = children
        return symbol
    
    def test_validate_complete_file(self):
        """Test validation of a complete file."""
        validator = SyntaxValidator()
        
        # Create a valid device structure
        field = self.create_symbol("ready", DMLSymbolKind.FIELD)
        register = self.create_symbol("status", DMLSymbolKind.REGISTER, [field])
        bank = self.create_symbol("regs", DMLSymbolKind.BANK, [register])
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE, [bank])
        
        file_span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_file([device], "1.4", file_span)
        
        # Should have warnings about missing size parameter
        assert len(errors) >= 1
        # But no critical errors
        critical_errors = [e for e in errors if e.severity == DMLDiagnosticSeverity.ERROR]
        assert len(critical_errors) == 0
    
    def test_validate_file_with_errors(self):
        """Test validation catches multiple errors."""
        validator = SyntaxValidator()
        
        # Create invalid structure: field directly in device
        field = self.create_symbol("bad_field", DMLSymbolKind.FIELD)
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE, [field])
        
        file_span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_file([device], "1.4", file_span)
        
        # Should have nesting error and structure warning
        assert len(errors) >= 2
        
        # Check for nesting error
        nesting_errors = [e for e in errors if "cannot be declared inside" in e.message]
        assert len(nesting_errors) == 1
    
    def test_validate_missing_version(self):
        """Test that missing version is caught."""
        validator = SyntaxValidator()
        
        device = self.create_symbol("test_device", DMLSymbolKind.DEVICE)
        file_span = ZeroSpan("test.dml", ZeroRange(ZeroPosition(0, 0), ZeroPosition(0, 0)))
        
        errors = validator.validate_file([device], None, file_span)
        
        # Should have version error
        version_errors = [e for e in errors if "version" in e.message.lower()]
        assert len(version_errors) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
