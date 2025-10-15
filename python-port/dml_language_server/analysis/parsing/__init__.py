"""
DML parsing module.

Provides lexical analysis and parsing for DML code.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import re
import logging
from typing import List, Optional, Dict, Any, Iterator, NamedTuple
from enum import Enum
from dataclasses import dataclass

from ...span import ZeroSpan, ZeroPosition, ZeroRange, SpanBuilder
from ...lsp_data import DMLSymbol, DMLSymbolKind, DMLLocation
from .. import DMLError, DMLErrorKind

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of DML tokens."""
    # Literals
    IDENTIFIER = "identifier"
    NUMBER = "number"
    STRING = "string"
    
    # Keywords
    DML = "dml"
    DEVICE = "device"
    BANK = "bank"
    REGISTER = "register"
    FIELD = "field"
    METHOD = "method"
    PARAMETER = "parameter"
    ATTRIBUTE = "attribute"
    TEMPLATE = "template"
    CONNECT = "connect"
    INTERFACE = "interface"
    PORT = "port"
    IMPLEMENT = "implement"
    IMPORT = "import"
    LIBRARY = "library"
    TYPEDEF = "typedef"
    STRUCT = "struct"
    BITORDER = "bitorder"
    LAYOUT = "layout"
    
    # Operators and punctuation
    EQUALS = "="
    SEMICOLON = ";"
    COLON = ":"
    COMMA = ","
    DOT = "."
    LBRACE = "{"
    RBRACE = "}"
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    
    # Special
    NEWLINE = "newline"
    WHITESPACE = "whitespace"
    COMMENT = "comment"
    EOF = "eof"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """A token from DML source code."""
    type: TokenType
    value: str
    span: ZeroSpan
    
    def __str__(self) -> str:
        return f"{self.type.value}({self.value!r}) at {self.span}"


class DMLLexer:
    """Lexical analyzer for DML code."""
    
    # Keywords mapping
    KEYWORDS = {
        'dml': TokenType.DML,
        'device': TokenType.DEVICE,
        'bank': TokenType.BANK,
        'register': TokenType.REGISTER,
        'field': TokenType.FIELD,
        'method': TokenType.METHOD,
        'parameter': TokenType.PARAMETER,
        'attribute': TokenType.ATTRIBUTE,
        'template': TokenType.TEMPLATE,
        'connect': TokenType.CONNECT,
        'interface': TokenType.INTERFACE,
        'port': TokenType.PORT,
        'implement': TokenType.IMPLEMENT,
        'import': TokenType.IMPORT,
        'library': TokenType.LIBRARY,
        'typedef': TokenType.TYPEDEF,
        'struct': TokenType.STRUCT,
        'bitorder': TokenType.BITORDER,
        'layout': TokenType.LAYOUT,
    }
    
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path
        self.position = 0
        self.line = 0
        self.column = 0
        self.span_builder = SpanBuilder(file_path)
        self.span_builder.set_content(content)
        
    def tokenize(self) -> List[Token]:
        """Tokenize the content into a list of tokens."""
        tokens = []
        
        while self.position < len(self.content):
            token = self._next_token()
            if token:
                # Skip whitespace and comments for now
                if token.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
                    tokens.append(token)
        
        # Add EOF token
        eof_pos = ZeroPosition(self.line, self.column)
        eof_span = ZeroSpan(self.file_path, ZeroRange(eof_pos, eof_pos))
        tokens.append(Token(TokenType.EOF, "", eof_span))
        
        return tokens
    
    def _next_token(self) -> Optional[Token]:
        """Get the next token from the input."""
        if self.position >= len(self.content):
            return None
            
        # Skip whitespace
        if self._current_char().isspace():
            return self._read_whitespace()
        
        # Comments
        if self._current_char() == '/' and self._peek_char() == '/':
            return self._read_line_comment()
        if self._current_char() == '/' and self._peek_char() == '*':
            return self._read_block_comment()
        
        # String literals
        if self._current_char() == '"':
            return self._read_string()
        
        # Numbers
        if self._current_char().isdigit():
            return self._read_number()
        
        # Identifiers and keywords
        if self._current_char().isalpha() or self._current_char() == '_':
            return self._read_identifier()
        
        # Single character tokens
        single_char_tokens = {
            '=': TokenType.EQUALS,
            ';': TokenType.SEMICOLON,
            ':': TokenType.COLON,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
        }
        
        char = self._current_char()
        if char in single_char_tokens:
            start_pos = ZeroPosition(self.line, self.column)
            self._advance()
            end_pos = ZeroPosition(self.line, self.column)
            span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
            return Token(single_char_tokens[char], char, span)
        
        # Unknown character
        start_pos = ZeroPosition(self.line, self.column)
        self._advance()
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.UNKNOWN, char, span)
    
    def _current_char(self) -> str:
        """Get the current character."""
        if self.position >= len(self.content):
            return '\0'
        return self.content[self.position]
    
    def _peek_char(self) -> str:
        """Peek at the next character."""
        if self.position + 1 >= len(self.content):
            return '\0'
        return self.content[self.position + 1]
    
    def _advance(self) -> None:
        """Advance to the next character."""
        if self.position < len(self.content):
            if self.content[self.position] == '\n':
                self.line += 1
                self.column = 0
            else:
                self.column += 1
            self.position += 1
    
    def _read_whitespace(self) -> Token:
        """Read whitespace characters."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        while self.position < len(self.content) and self._current_char().isspace():
            value += self._current_char()
            self._advance()
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.WHITESPACE, value, span)
    
    def _read_line_comment(self) -> Token:
        """Read a line comment."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        while self.position < len(self.content) and self._current_char() != '\n':
            value += self._current_char()
            self._advance()
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.COMMENT, value, span)
    
    def _read_block_comment(self) -> Token:
        """Read a block comment."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        # Skip /*
        value += self._current_char()
        self._advance()
        value += self._current_char()
        self._advance()
        
        while self.position < len(self.content):
            if self._current_char() == '*' and self._peek_char() == '/':
                value += self._current_char()
                self._advance()
                value += self._current_char()
                self._advance()
                break
            value += self._current_char()
            self._advance()
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.COMMENT, value, span)
    
    def _read_string(self) -> Token:
        """Read a string literal."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        # Skip opening quote
        value += self._current_char()
        self._advance()
        
        while self.position < len(self.content) and self._current_char() != '"':
            if self._current_char() == '\\':
                value += self._current_char()
                self._advance()
                if self.position < len(self.content):
                    value += self._current_char()
                    self._advance()
            else:
                value += self._current_char()
                self._advance()
        
        # Skip closing quote
        if self.position < len(self.content):
            value += self._current_char()
            self._advance()
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.STRING, value, span)
    
    def _read_number(self) -> Token:
        """Read a number literal."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        while (self.position < len(self.content) and 
               (self._current_char().isdigit() or self._current_char() in '.xX')):
            value += self._current_char()
            self._advance()
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(TokenType.NUMBER, value, span)
    
    def _read_identifier(self) -> Token:
        """Read an identifier or keyword."""
        start_pos = ZeroPosition(self.line, self.column)
        value = ""
        
        while (self.position < len(self.content) and 
               (self._current_char().isalnum() or self._current_char() == '_')):
            value += self._current_char()
            self._advance()
        
        # Check if it's a keyword
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return Token(token_type, value, span)


class DMLParser:
    """Parser for DML code."""
    
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path
        self.lexer = DMLLexer(content, file_path)
        self.tokens = self.lexer.tokenize()
        self.position = 0
        self.errors: List[DMLError] = []
        self.symbols: List[DMLSymbol] = []
        self.imports: List[str] = []
        self.dml_version: Optional[str] = None
        
        # Parse the content
        self._parse()
    
    def _parse(self) -> None:
        """Parse the token stream."""
        try:
            while not self._is_at_end():
                self._parse_top_level()
        except Exception as e:
            error = DMLError(
                kind=DMLErrorKind.SYNTAX_ERROR,
                message=f"Parse error: {e}",
                span=self._current_token_span()
            )
            self.errors.append(error)
    
    def _parse_top_level(self) -> None:
        """Parse a top-level declaration."""
        token = self._current_token()
        
        if token.type == TokenType.DML:
            self._parse_dml_version()
        elif token.type == TokenType.IMPORT:
            self._parse_import()
        elif token.type == TokenType.DEVICE:
            self._parse_device()
        elif token.type == TokenType.TEMPLATE:
            self._parse_template()
        elif token.type == TokenType.TYPEDEF:
            self._parse_typedef()
        else:
            # Skip unknown tokens
            self._advance()
    
    def _parse_dml_version(self) -> None:
        """Parse DML version declaration."""
        self._advance()  # Skip 'dml'
        
        if self._current_token().type == TokenType.NUMBER:
            self.dml_version = self._current_token().value
            self._advance()
        
        self._expect(TokenType.SEMICOLON)
    
    def _parse_import(self) -> None:
        """Parse import statement."""
        self._advance()  # Skip 'import'
        
        if self._current_token().type == TokenType.STRING:
            import_path = self._current_token().value.strip('"')
            self.imports.append(import_path)
            self._advance()
        
        self._expect(TokenType.SEMICOLON)
    
    def _parse_device(self) -> None:
        """Parse device declaration."""
        start_token = self._current_token()
        self._advance()  # Skip 'device'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            # Create device symbol
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.DEVICE,
                location=location,
                detail="device"
            )
            self.symbols.append(symbol)
            
            # Parse device body
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
    
    def _parse_template(self) -> None:
        """Parse template declaration."""
        start_token = self._current_token()
        self._advance()  # Skip 'template'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            # Create template symbol
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.TEMPLATE,
                location=location,
                detail="template"
            )
            self.symbols.append(symbol)
            
            # Parse template body
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
    
    def _parse_typedef(self) -> None:
        """Parse typedef declaration."""
        self._advance()  # Skip 'typedef'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            # Create typedef symbol
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.TYPEDEF,
                location=location,
                detail="typedef"
            )
            self.symbols.append(symbol)
        
        self._expect(TokenType.SEMICOLON)
    
    def _parse_block(self, parent_symbol: DMLSymbol) -> None:
        """Parse a block of declarations."""
        self._expect(TokenType.LBRACE)
        
        while not self._is_at_end() and self._current_token().type != TokenType.RBRACE:
            self._parse_block_item(parent_symbol)
        
        self._expect(TokenType.RBRACE)
    
    def _parse_block_item(self, parent_symbol: DMLSymbol) -> None:
        """Parse an item within a block."""
        token = self._current_token()
        
        if token.type == TokenType.BANK:
            self._parse_bank(parent_symbol)
        elif token.type == TokenType.REGISTER:
            self._parse_register(parent_symbol)
        elif token.type == TokenType.FIELD:
            self._parse_field(parent_symbol)
        elif token.type == TokenType.METHOD:
            self._parse_method(parent_symbol)
        elif token.type == TokenType.PARAMETER:
            self._parse_parameter(parent_symbol)
        elif token.type == TokenType.ATTRIBUTE:
            self._parse_attribute(parent_symbol)
        else:
            # Skip unknown tokens
            self._advance()
    
    def _parse_bank(self, parent_symbol: DMLSymbol) -> None:
        """Parse bank declaration."""
        self._advance()  # Skip 'bank'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.BANK,
                location=location,
                detail="bank"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
            
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
    
    def _parse_register(self, parent_symbol: DMLSymbol) -> None:
        """Parse register declaration."""
        self._advance()  # Skip 'register'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.REGISTER,
                location=location,
                detail="register"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
            
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
    
    def _parse_field(self, parent_symbol: DMLSymbol) -> None:
        """Parse field declaration."""
        self._advance()  # Skip 'field'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.FIELD,
                location=location,
                detail="field"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
            
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
            else:
                self._expect(TokenType.SEMICOLON)
    
    def _parse_method(self, parent_symbol: DMLSymbol) -> None:
        """Parse method declaration."""
        self._advance()  # Skip 'method'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.METHOD,
                location=location,
                detail="method"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
            
            if self._current_token().type == TokenType.LBRACE:
                self._parse_block(symbol)
    
    def _parse_parameter(self, parent_symbol: DMLSymbol) -> None:
        """Parse parameter declaration."""
        self._advance()  # Skip 'parameter'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.PARAMETER,
                location=location,
                detail="parameter"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
        
        self._expect(TokenType.SEMICOLON)
    
    def _parse_attribute(self, parent_symbol: DMLSymbol) -> None:
        """Parse attribute declaration."""
        self._advance()  # Skip 'attribute'
        
        if self._current_token().type == TokenType.IDENTIFIER:
            name = self._current_token().value
            name_span = self._current_token().span
            self._advance()
            
            location = DMLLocation(name_span)
            symbol = DMLSymbol(
                name=name,
                kind=DMLSymbolKind.ATTRIBUTE,
                location=location,
                detail="attribute"
            )
            parent_symbol.children.append(symbol)
            self.symbols.append(symbol)
        
        self._expect(TokenType.SEMICOLON)
    
    def _current_token(self) -> Token:
        """Get the current token."""
        if self.position >= len(self.tokens):
            return self.tokens[-1]  # EOF token
        return self.tokens[self.position]
    
    def _current_token_span(self) -> ZeroSpan:
        """Get the span of the current token."""
        return self._current_token().span
    
    def _advance(self) -> Token:
        """Advance to the next token."""
        if not self._is_at_end():
            self.position += 1
        return self._current_token()
    
    def _is_at_end(self) -> bool:
        """Check if we're at the end of tokens."""
        return (self.position >= len(self.tokens) or 
                self._current_token().type == TokenType.EOF)
    
    def _expect(self, expected_type: TokenType) -> Token:
        """Expect a specific token type."""
        token = self._current_token()
        if token.type == expected_type:
            self._advance()
            return token
        else:
            error = DMLError(
                kind=DMLErrorKind.SYNTAX_ERROR,
                message=f"Expected {expected_type.value}, got {token.type.value}",
                span=token.span
            )
            self.errors.append(error)
            return token
    
    def extract_dml_version(self) -> Optional[str]:
        """Extract the DML version from parsing."""
        return self.dml_version
    
    def extract_imports(self) -> List[str]:
        """Extract import statements from parsing."""
        return self.imports
    
    def extract_symbols(self) -> List[DMLSymbol]:
        """Extract symbols from parsing."""
        return self.symbols
    
    def get_errors(self) -> List[DMLError]:
        """Get parsing errors."""
        return self.errors


# Export main classes
__all__ = [
    "DMLLexer",
    "DMLParser", 
    "Token",
    "TokenType"
]