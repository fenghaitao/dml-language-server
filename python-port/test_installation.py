#!/usr/bin/env python3
"""
Test script to verify the DML Language Server Python port installation.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import sys
import asyncio
from pathlib import Path

# Add the current directory to Python path for testing
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        import dml_language_server
        print(f"✓ Main module imported, version: {dml_language_server.version()}")
        
        from dml_language_server.config import Config
        print("✓ Config module")
        
        from dml_language_server.vfs import VFS
        print("✓ VFS module")
        
        from dml_language_server.span import Position, Range, Span, ZeroIndexed
        print("✓ Span module")
        
        from dml_language_server.analysis import DeviceAnalysis
        print("✓ Analysis module")
        
        from dml_language_server.analysis.parsing import DMLLexer, DMLParser
        print("✓ Parsing module")
        
        from dml_language_server.lint import LintEngine
        print("✓ Lint module")
        
        from dml_language_server.server import DMLLanguageServer
        print("✓ Server module")
        
        from dml_language_server.mcp import DMLMCPServer
        print("✓ MCP module")
        
        from dml_language_server.dfa import DMLAnalyzer
        print("✓ DFA module")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")
    
    try:
        from dml_language_server.config import Config
        from dml_language_server.analysis.parsing import DMLLexer, DMLParser
        
        # Test configuration
        config = Config()
        print("✓ Config creation")
        
        # Test lexer
        sample_dml = "dml 1.4;\ndevice Test {}"
        lexer = DMLLexer(sample_dml, "test.dml")
        tokens = lexer.tokenize()
        print(f"✓ Lexer tokenized {len(tokens)} tokens")
        
        # Test parser
        parser = DMLParser(sample_dml, "test.dml")
        version = parser.extract_dml_version()
        symbols = parser.extract_symbols()
        print(f"✓ Parser found DML version {version} and {len(symbols)} symbols")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False


async def test_async_functionality():
    """Test async functionality."""
    print("\nTesting async functionality...")
    
    try:
        from dml_language_server.vfs import VFS
        import tempfile
        
        # Test VFS with temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dml', delete=False) as f:
            f.write("dml 1.4;\ndevice AsyncTest {}")
            temp_path = Path(f.name)
        
        try:
            vfs = VFS(use_real_files=True)
            content = await vfs.read_file(temp_path)
            print(f"✓ VFS async read: {len(content)} characters")
            
            # Test write
            vfs.write_file(temp_path, content + "\n// Modified")
            print("✓ VFS write")
            
            return True
            
        finally:
            temp_path.unlink(missing_ok=True)
            
    except Exception as e:
        print(f"✗ Async functionality test failed: {e}")
        return False


def test_sample_file_analysis():
    """Test analysis of the sample DML file."""
    print("\nTesting sample file analysis...")
    
    try:
        from dml_language_server.config import Config
        from dml_language_server.file_management import FileManager
        from dml_language_server.analysis import DeviceAnalysis
        
        sample_file = Path(__file__).parent / "examples" / "sample_device.dml"
        
        if not sample_file.exists():
            print(f"⚠ Sample file not found: {sample_file}")
            return True  # Not a failure, just skip
        
        # Set up analysis
        config = Config()
        file_manager = FileManager(config)
        analysis_engine = DeviceAnalysis(config, file_manager)
        
        # Read and analyze
        content = sample_file.read_text(encoding='utf-8')
        errors = analysis_engine.analyze_file(sample_file, content)
        symbols = analysis_engine.get_all_symbols_in_file(sample_file)
        
        print(f"✓ Analyzed sample file: {len(errors)} errors, {len(symbols)} symbols")
        
        # Show some symbols
        if symbols:
            device_symbols = [s for s in symbols if s.kind.value == 'device']
            register_symbols = [s for s in symbols if s.kind.value == 'register']
            print(f"  - {len(device_symbols)} devices, {len(register_symbols)} registers")
        
        return True
        
    except Exception as e:
        print(f"✗ Sample file analysis failed: {e}")
        return False


def test_cli_interfaces():
    """Test CLI interface imports."""
    print("\nTesting CLI interfaces...")
    
    try:
        from dml_language_server.main import main_inner
        print("✓ Main CLI interface")
        
        from dml_language_server.dfa.main import main as dfa_main
        print("✓ DFA CLI interface")
        
        from dml_language_server.mcp.main import main as mcp_main
        print("✓ MCP CLI interface")
        
        return True
        
    except Exception as e:
        print(f"✗ CLI interface test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("DML Language Server Python Port - Installation Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Async Functionality", test_async_functionality),
        ("Sample File Analysis", test_sample_file_analysis),
        ("CLI Interfaces", test_cli_interfaces),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Installation appears to be working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)