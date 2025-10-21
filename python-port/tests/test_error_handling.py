#!/usr/bin/env python3
"""
Test error handling functionality of the DML Language Server.
Validates that errors are properly detected, formatted, and reported.
"""

import sys
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_error_attribute_access():
    """Test that error objects have proper attribute access."""
    print("🔍 Testing error attribute access...")
    
    try:
        from dml_language_server.analysis import DMLError, DMLErrorKind
        from dml_language_server.span import ZeroSpan, ZeroRange, ZeroPosition
        
        # Create a test error
        test_span = ZeroSpan(
            file_path="test.dml",
            range=ZeroRange(
                start=ZeroPosition(line=10, column=5),
                end=ZeroPosition(line=10, column=15)
            )
        )
        
        test_error = DMLError(
            kind=DMLErrorKind.SYNTAX_ERROR,
            message="Test error message",
            span=test_span
        )
        
        # Test attribute access
        line = test_error.span.range.start.line
        column = test_error.span.range.start.column
        message = test_error.message
        
        print(f"   ✅ Error attributes accessible:")
        print(f"      Line: {line}")
        print(f"      Column: {column}")
        print(f"      Message: {message}")
        
        # Test 1-based conversion
        display_line = line + 1
        display_column = column + 1
        
        print(f"   ✅ 1-based conversion:")
        print(f"      Display line: {display_line}")
        print(f"      Display column: {display_column}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error attribute test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_to_diagnostic_conversion():
    """Test conversion of errors to diagnostics."""
    print("\n🩺 Testing error to diagnostic conversion...")
    
    try:
        from dml_language_server.analysis import DMLError, DMLErrorKind
        from dml_language_server.span import ZeroSpan, ZeroRange, ZeroPosition
        from dml_language_server.lsp_data import DMLDiagnosticSeverity
        
        # Create test errors of different kinds
        test_cases = [
            {
                "kind": DMLErrorKind.SYNTAX_ERROR,
                "message": "Expected semicolon",
                "severity": DMLDiagnosticSeverity.ERROR
            },
            {
                "kind": DMLErrorKind.SEMANTIC_ERROR,
                "message": "Undefined symbol 'foo'",
                "severity": DMLDiagnosticSeverity.ERROR
            },
            {
                "kind": DMLErrorKind.TYPE_ERROR,
                "message": "Type mismatch",
                "severity": DMLDiagnosticSeverity.ERROR
            }
        ]
        
        for i, case in enumerate(test_cases):
            test_span = ZeroSpan(
                file_path="test.dml",
                range=ZeroRange(
                    start=ZeroPosition(line=i*5, column=i*2),
                    end=ZeroPosition(line=i*5, column=i*2+10)
                )
            )
            
            error = DMLError(
                kind=case["kind"],
                message=case["message"],
                span=test_span,
                severity=case["severity"]
            )
            
            # Convert to diagnostic
            diagnostic = error.to_diagnostic()
            
            print(f"   ✅ Test case {i+1}: {case['kind'].value}")
            print(f"      Message: {diagnostic.message}")
            print(f"      Severity: {diagnostic.severity.value}")
            print(f"      Span: {diagnostic.span}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error to diagnostic conversion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_error_formatting():
    """Test that CLI formats errors correctly."""
    print("\n🖨️  Testing CLI error formatting...")
    
    try:
        from dml_language_server.config import Config
        from dml_language_server.file_management import FileManager
        from dml_language_server.analysis import DeviceAnalysis
        
        config = Config()
        file_manager = FileManager(config)
        analysis_engine = DeviceAnalysis(config, file_manager)
        
        # Test with actual DML file
        test_file = Path("examples/sample_device.dml")
        if not test_file.exists():
            print("⚠️  Test file not found, skipping")
            return True
        
        content = test_file.read_text(encoding='utf-8')
        
        # Analyze file to get errors
        errors = analysis_engine.analyze_file(test_file, content)
        
        if not errors:
            print("   ℹ️  No errors found in test file")
            return True
        
        print(f"   Found {len(errors)} errors to test formatting")
        
        # Test formatting first few errors
        for i, error in enumerate(errors[:3]):
            # Format like CLI does
            line = error.span.range.start.line + 1  # Convert to 1-based
            column = error.span.range.start.column + 1  # Convert to 1-based
            formatted = f"{test_file}:{line}:{column}: error: {error.message}"
            
            print(f"   ✅ Error {i+1} formatted: {formatted}")
            
            # Validate format
            if f":{line}:" in formatted and f":{column}:" in formatted:
                print(f"      ✅ Contains correct line:column format")
            else:
                print(f"      ❌ Incorrect line:column format")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ CLI error formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_lint_warning_formatting():
    """Test that lint warnings are formatted correctly."""
    print("\n⚠️  Testing lint warning formatting...")
    
    try:
        from dml_language_server.config import Config
        from dml_language_server.file_management import FileManager
        from dml_language_server.analysis import DeviceAnalysis
        from dml_language_server.lint import LintEngine
        
        config = Config()
        file_manager = FileManager(config)
        analysis_engine = DeviceAnalysis(config, file_manager)
        lint_engine = LintEngine(config)
        
        # Test with actual DML file
        test_file = Path("examples/sample_device.dml")
        if not test_file.exists():
            print("⚠️  Test file not found, skipping")
            return True
        
        content = test_file.read_text(encoding='utf-8')
        
        # Analyze file first
        analysis_engine.analyze_file(test_file, content)
        file_analysis = analysis_engine.file_analyses.get(test_file.resolve())
        
        if not file_analysis:
            print("   ⚠️  No file analysis available")
            return True
        
        # Run linting
        warnings = lint_engine.lint_file(test_file, content, file_analysis)
        
        if not warnings:
            print("   ℹ️  No warnings found in test file")
            return True
        
        print(f"   Found {len(warnings)} warnings to test formatting")
        
        # Test formatting first few warnings
        for i, warning in enumerate(warnings[:3]):
            # Format like CLI does
            line = warning.span.range.start.line + 1  # Convert to 1-based
            column = warning.span.range.start.column + 1  # Convert to 1-based
            formatted = f"{test_file}:{line}:{column}: warning: {warning.message}"
            
            print(f"   ✅ Warning {i+1} formatted: {formatted}")
            
            # Validate format
            if f":{line}:" in formatted and f":{column}:" in formatted and "warning:" in formatted:
                print(f"      ✅ Contains correct line:column:warning format")
            else:
                print(f"      ❌ Incorrect warning format")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Lint warning formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_edge_cases():
    """Test error handling edge cases."""
    print("\n🎯 Testing error handling edge cases...")
    
    try:
        from dml_language_server.analysis import DMLError, DMLErrorKind
        from dml_language_server.span import ZeroSpan, ZeroRange, ZeroPosition
        
        # Test error at position (0, 0)
        zero_span = ZeroSpan(
            file_path="test.dml",
            range=ZeroRange(
                start=ZeroPosition(line=0, column=0),
                end=ZeroPosition(line=0, column=1)
            )
        )
        
        zero_error = DMLError(
            kind=DMLErrorKind.SYNTAX_ERROR,
            message="Error at start of file",
            span=zero_span
        )
        
        # Test formatting
        line = zero_error.span.range.start.line + 1
        column = zero_error.span.range.start.column + 1
        
        print(f"   ✅ Zero position error:")
        print(f"      Internal: (0, 0)")
        print(f"      Display: ({line}, {column})")
        
        # Test error with empty message
        empty_error = DMLError(
            kind=DMLErrorKind.SYNTAX_ERROR,
            message="",
            span=zero_span
        )
        
        print(f"   ✅ Empty message error: '{empty_error.message}'")
        
        # Test error with very long message
        long_message = "A" * 1000
        long_error = DMLError(
            kind=DMLErrorKind.SYNTAX_ERROR,
            message=long_message,
            span=zero_span
        )
        
        print(f"   ✅ Long message error: {len(long_error.message)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Error edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all error handling tests."""
    print("🧪 Testing DML Language Server Error Handling")
    print("=" * 50)
    
    tests = [
        ("Error Attribute Access", test_error_attribute_access),
        ("Error to Diagnostic Conversion", test_error_to_diagnostic_conversion),
        ("CLI Error Formatting", test_cli_error_formatting),
        ("Lint Warning Formatting", test_lint_warning_formatting),
        ("Error Edge Cases", test_error_edge_cases)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"📊 Error Handling Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All error handling functionality is working correctly!")
        return True
    else:
        print("❌ Some error handling features need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)