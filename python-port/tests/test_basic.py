"""
Basic tests for the DML Language Server Python port.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import pytest
from pathlib import Path
import tempfile

from dml_language_server import version, internal_error
from dml_language_server.config import Config
from dml_language_server.vfs import VFS
from dml_language_server.span import Position, Range, Span, ZeroIndexed, OneIndexed
from dml_language_server.analysis.parsing import DMLLexer, DMLParser, TokenType


class TestBasicFunctionality:
    """Test basic functionality of the DML Language Server."""
    
    def test_version(self):
        """Test version information."""
        ver = version()
        assert ver == "0.9.14"
        assert isinstance(ver, str)
    
    def test_internal_error(self, caplog):
        """Test internal error logging."""
        internal_error("Test error message")
        assert "Internal Error: Test error message" in caplog.text
    
    def test_config_creation(self):
        """Test configuration creation."""
        config = Config()
        assert config.workspace_root is None
        assert config.initialization_options is None
        assert config.is_linting_enabled() is True
    
    def test_vfs_creation(self):
        """Test VFS creation."""
        vfs = VFS(use_real_files=False)
        stats = vfs.get_cache_stats()
        assert stats["cached_files"] == 0
        assert stats["dirty_files"] == 0
    
    def test_span_creation(self):
        """Test span creation and conversion."""
        # Test zero-indexed position
        zero_pos = Position[ZeroIndexed](line=5, column=10)
        assert zero_pos.line == 5
        assert zero_pos.column == 10
        
        # Test conversion to one-indexed
        one_pos = zero_pos.to_one_indexed()
        assert one_pos.line == 6
        assert one_pos.column == 11
        
        # Test range creation
        start_pos = Position[ZeroIndexed](line=1, column=0)
        end_pos = Position[ZeroIndexed](line=1, column=5)
        range_obj = Range[ZeroIndexed](start_pos, end_pos)
        
        # Test span creation
        span = Span[ZeroIndexed]("test.dml", range_obj)
        assert span.file_path == "test.dml"
        assert span.start == start_pos
        assert span.end == end_pos


class TestDMLLexer:
    """Test DML lexer functionality."""
    
    def test_simple_tokenization(self):
        """Test basic tokenization."""
        content = "dml 1.4;\ndevice MyDevice {\n}"
        lexer = DMLLexer(content, "test.dml")
        tokens = lexer.tokenize()
        
        # Check that we get expected tokens
        token_types = [token.type for token in tokens]
        assert TokenType.DML in token_types
        assert TokenType.NUMBER in token_types
        assert TokenType.SEMICOLON in token_types
        assert TokenType.DEVICE in token_types
        assert TokenType.IDENTIFIER in token_types
        assert TokenType.LBRACE in token_types
        assert TokenType.RBRACE in token_types
        assert TokenType.EOF in token_types
    
    def test_keyword_recognition(self):
        """Test keyword recognition."""
        keywords = ["dml", "device", "bank", "register", "field", "method"]
        for keyword in keywords:
            lexer = DMLLexer(keyword, "test.dml")
            tokens = lexer.tokenize()
            assert len(tokens) >= 2  # keyword + EOF
            assert tokens[0].value == keyword
            assert tokens[0].type != TokenType.IDENTIFIER  # Should be recognized as keyword
    
    def test_string_literal(self):
        """Test string literal tokenization."""
        content = 'import "library.dml";'
        lexer = DMLLexer(content, "test.dml")
        tokens = lexer.tokenize()
        
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) == 1
        assert string_tokens[0].value == '"library.dml"'
    
    def test_comments(self):
        """Test comment handling."""
        content = """
        // Line comment
        device Test { /* block comment */ }
        """
        lexer = DMLLexer(content, "test.dml")
        tokens = lexer.tokenize()
        
        # Comments should be filtered out in tokenize()
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comment_tokens) == 0


class TestDMLParser:
    """Test DML parser functionality."""
    
    def test_simple_device_parsing(self):
        """Test parsing a simple device."""
        content = """
        dml 1.4;
        
        device SimpleDevice {
            register status @ 0x00 {
                field ready @ [0];
            }
        }
        """
        
        parser = DMLParser(content, "test.dml")
        
        # Check DML version
        assert parser.extract_dml_version() == "1.4"
        
        # Check symbols
        symbols = parser.extract_symbols()
        symbol_names = [s.name for s in symbols]
        assert "SimpleDevice" in symbol_names
        assert "status" in symbol_names
        assert "ready" in symbol_names
        
        # Check for no parse errors
        errors = parser.get_errors()
        assert len(errors) == 0
    
    def test_import_parsing(self):
        """Test import statement parsing."""
        content = """
        dml 1.4;
        import "library.dml";
        import "another.dml";
        """
        
        parser = DMLParser(content, "test.dml")
        imports = parser.extract_imports()
        
        assert "library.dml" in imports
        assert "another.dml" in imports
    
    def test_syntax_error_handling(self):
        """Test syntax error detection."""
        content = """
        dml 1.4;
        device Test {
            register bad_syntax @  // Missing address
        }
        """
        
        parser = DMLParser(content, "test.dml")
        errors = parser.get_errors()
        
        # Should detect syntax errors
        assert len(errors) > 0


class TestFileOperations:
    """Test file operations with VFS."""
    
    def test_memory_file_operations(self):
        """Test VFS with memory files."""
        vfs = VFS(use_real_files=False)
        
        # Test writing and reading
        test_path = Path("test.dml")
        test_content = "dml 1.4;\ndevice Test {}"
        
        vfs.write_file(test_path, test_content)
        assert vfs.is_dirty(test_path)
        
        # Note: For memory VFS, we need to implement read_file to work with memory
        # This would require enhancing the MemoryFileLoader
    
    def test_real_file_operations(self):
        """Test VFS with real files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vfs = VFS(use_real_files=True)
            
            test_path = Path(temp_dir) / "test.dml"
            test_content = "dml 1.4;\ndevice Test {}"
            
            # Write to real file
            test_path.write_text(test_content)
            
            # VFS should be able to detect and read it
            assert vfs.file_exists(test_path)


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations."""
    
    async def test_vfs_async_read(self):
        """Test async file reading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vfs = VFS(use_real_files=True)
            
            test_path = Path(temp_dir) / "test.dml"
            test_content = "dml 1.4;\ndevice Test {}"
            
            # Write test file
            test_path.write_text(test_content)
            
            # Read with VFS
            content = await vfs.read_file(test_path)
            assert content == test_content


if __name__ == "__main__":
    pytest.main([__file__])