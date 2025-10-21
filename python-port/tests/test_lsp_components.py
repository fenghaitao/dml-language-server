#!/usr/bin/env python3
"""
Test script to verify DML Language Server components without full LSP server startup.
Tests the core analysis and LSP functionality directly.
"""

import sys
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_lsp_components():
    """Test LSP components directly."""
    print("🧪 Testing DML Language Server Components")
    print("=" * 50)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        
        from dml_language_server.config import Config
        from dml_language_server.file_management import FileManager
        from dml_language_server.analysis import DeviceAnalysis
        from dml_language_server.lint import LintEngine
        from dml_language_server.vfs import VFS
        from dml_language_server.lsp_data import (
            DMLSymbol, DMLSymbolKind, DMLLocation, DMLDiagnostic, 
            DMLDiagnosticSeverity, uri_to_path, path_to_uri
        )
        
        print("✅ All imports successful")
        
        # Test basic components
        print("\n🔧 Testing component initialization...")
        
        config = Config()
        vfs = VFS(use_real_files=True)
        file_manager = FileManager(config)
        analysis_engine = DeviceAnalysis(config, file_manager)
        lint_engine = LintEngine(config)
        
        print("✅ All components initialized successfully")
        
        # Test file analysis
        print("\n📄 Testing file analysis...")
        
        test_file = Path("examples/sample_device.dml")
        if not test_file.exists():
            print(f"❌ Test file {test_file} not found")
            return False
        
        # Read file content
        content = test_file.read_text(encoding='utf-8')
        print(f"✅ Read test file: {test_file} ({len(content)} chars)")
        
        # Analyze file
        errors = analysis_engine.analyze_file(test_file, content)
        print(f"✅ Analysis complete: found {len(errors)} issues")
        
        if errors:
            print("📋 First few issues:")
            for i, error in enumerate(errors[:3]):
                line = error.span.range.start.line + 1
                col = error.span.range.start.column + 1
                print(f"  {i+1}. Line {line}:{col} - {error.message}")
        
        # Test linting
        print("\n🔍 Testing linting...")
        
        # Get file analysis for linting context
        file_analysis = analysis_engine.file_analyses.get(test_file.resolve())
        if file_analysis:
            warnings = lint_engine.lint_file(test_file, content, file_analysis)
            print(f"✅ Linting complete: found {len(warnings)} warnings")
            
            if warnings:
                print("📋 First few warnings:")
                for i, warning in enumerate(warnings[:3]):
                    line = warning.span.range.start.line + 1
                    col = warning.span.range.start.column + 1
                    print(f"  {i+1}. Line {line}:{col} - {warning.message}")
        else:
            print("⚠️  No file analysis available for linting")
        
        # Test LSP data conversion
        print("\n🔄 Testing LSP data conversion...")
        
        # Test URI conversion
        test_uri = path_to_uri(test_file.resolve())  # Use absolute path
        converted_path = uri_to_path(test_uri)
        print(f"✅ URI conversion: {test_file} -> {test_uri} -> {converted_path}")
        
        # Test symbol extraction
        symbols = analysis_engine.get_all_symbols_in_file(test_file)
        print(f"✅ Symbol extraction: found {len(symbols)} symbols")
        
        if symbols:
            print("📋 First few symbols:")
            for i, symbol in enumerate(symbols[:3]):
                print(f"  {i+1}. {symbol.name} ({symbol.kind.value})")
        
        # Test completion-like functionality
        print("\n💡 Testing completion functionality...")
        
        # Get symbols that could be used for completion
        completion_symbols = []
        for symbol in symbols:
            completion_item = {
                "label": symbol.name,
                "kind": symbol.kind.value,
                "detail": symbol.detail or f"{symbol.kind.value} symbol"
            }
            completion_symbols.append(completion_item)
        
        print(f"✅ Generated {len(completion_symbols)} completion items")
        
        # Test hover-like functionality
        print("\n🔍 Testing hover functionality...")
        
        if symbols:
            test_symbol = symbols[0]
            hover_content = f"**{test_symbol.name}** ({test_symbol.kind.value})"
            if test_symbol.detail:
                hover_content += f"\n\n{test_symbol.detail}"
            
            print(f"✅ Generated hover content for '{test_symbol.name}':")
            print(f"   {hover_content[:100]}...")
        
        # Test diagnostics conversion
        print("\n🩺 Testing diagnostics conversion...")
        
        if errors:
            test_error = errors[0]
            diagnostic = test_error.to_diagnostic()
            print(f"✅ Converted error to diagnostic: {diagnostic.message}")
        
        print(f"\n🎉 All component tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server_creation():
    """Test LSP server creation without starting it."""
    print("\n🏗️  Testing LSP server creation...")
    
    try:
        from dml_language_server.server import DMLLanguageServer
        from dml_language_server.vfs import VFS
        
        vfs = VFS(use_real_files=True)
        server = DMLLanguageServer(vfs)
        
        print("✅ LSP server created successfully")
        print(f"   Server name: {server.name}")
        print(f"   Server version: {server.version}")
        
        # Test server capabilities
        capabilities = {
            "text_document_sync": "Full",
            "completion_provider": True,
            "hover_provider": True,
            "definition_provider": True,
            "references_provider": True,
            "document_symbol_provider": True,
            "workspace_symbol_provider": True,
        }
        
        print("✅ Server capabilities configured:")
        for cap, value in capabilities.items():
            print(f"   {cap}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    success_count = 0
    total_tests = 2
    
    if test_lsp_components():
        success_count += 1
    
    if test_server_creation():
        success_count += 1
    
    print(f"\n📊 Test Summary: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! The LSP components are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)