"""
Enhanced DML Parser with comprehensive grammar support.

Provides full DML language parsing including expressions, statements, and template systems.
Ported concepts from the Rust implementation for maximum compatibility.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import re
import logging
from typing import List, Optional, Dict, Any, Union, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange, SpanBuilder
from ...lsp_data import DMLSymbol, DMLSymbolKind, DMLLocation
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef

logger = logging.getLogger(__name__)


class DMLTokenType(Enum):
    """Enhanced DML token types covering full language grammar."""
    
    # Literals
    IDENTIFIER = "identifier"
    NUMBER = "number"
    STRING = "string"
    CHARACTER = "character"
    
    # DML Keywords
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
    HOOK = "hook"
    EXPORT = "export"
    FOOTER = "footer"
    HEADER = "header"
    ASYNC = "async"
    AWAIT = "await"
    IS = "is"
    EACH = "each"
    AFTER = "after"
    CALL = "call"
    CAST = "cast"
    DEFINED = "defined"
    ERROR = "error"
    SELECT = "select"
    SIZEOFTYPE = "sizeoftype"
    TYPEOF = "typeof"
    UNDEFINED = "undefined"
    VECT = "vect"
    WHERE = "where"
    PROVISIONAL = "provisional"
    
    # Advanced DML constructs
    SESSION = "session"
    SAVED = "saved"
    CONSTANT = "constant"
    DATA = "data"
    EVENT = "event"
    GROUP = "group"
    SUBDEVICE = "subdevice"
    LOGGROUP = "loggroup"
    INDEPENDENT = "independent"
    MEMOIZED = "memoized"
    THROWS = "throws"
    STARTUP = "startup"
    
    # Control flow
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    FOR = "for"
    FOREACH = "foreach"
    IN = "in"
    DO = "do"
    BREAK = "break"
    CONTINUE = "continue"
    RETURN = "return"
    GOTO = "goto"
    
    # Types
    INT = "int"
    UINT = "uint"
    BOOL = "bool"
    CHAR = "char"
    VOID = "void"
    FLOAT = "float"
    DOUBLE = "double"
    SHORT = "short"
    LONG = "long"
    SIGNED = "signed"
    UNSIGNED = "unsigned"
    AUTO = "auto"
    CONST = "const"
    STATIC = "static"
    EXTERN = "extern"
    INLINE = "inline"
    VOLATILE = "volatile"
    
    # Additional keywords
    THIS = "this"
    NEW = "new"
    DELETE = "delete"
    SIZEOF = "sizeof"
    SIZE = "size"
    TRY = "try"
    CATCH = "catch"
    THROW = "throw"
    LOG = "log"
    ASSERT = "assert"
    LOCAL = "local"
    DEFAULT = "default"
    CASE = "case"
    SWITCH = "switch"
    THEN = "then"
    AS = "as"
    BITFIELDS = "bitfields"
    SEQUENCE = "sequence"
    STRINGIFY = "stringify"
    WITH = "with"
    SHARED = "shared"
    TRUE = "true"
    FALSE = "false"
    NULL = "null"
    
    # Operators
    ASSIGN = "="
    PLUS_ASSIGN = "+="
    MINUS_ASSIGN = "-="
    MULT_ASSIGN = "*="
    DIV_ASSIGN = "/="
    MOD_ASSIGN = "%="
    AND_ASSIGN = "&="
    OR_ASSIGN = "|="
    XOR_ASSIGN = "^="
    LSHIFT_ASSIGN = "<<="
    RSHIFT_ASSIGN = ">>="
    
    EQUALS = "=="
    NOT_EQUALS = "!="
    LESS = "<"
    LESS_EQUAL = "<="
    GREATER = ">"
    GREATER_EQUAL = ">="
    
    LOGICAL_AND = "&&"
    LOGICAL_OR = "||"
    LOGICAL_NOT = "!"
    
    BITWISE_AND = "&"
    BITWISE_OR = "|"
    BITWISE_XOR = "^"
    BITWISE_NOT = "~"
    LEFT_SHIFT = "<<"
    RIGHT_SHIFT = ">>"
    
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    
    INCREMENT = "++"
    DECREMENT = "--"
    
    ARROW = "->"
    DOT = "."
    QUESTION = "?"
    COLON = ":"
    SCOPE = "::"
    
    # Punctuation
    SEMICOLON = ";"
    COMMA = ","
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    
    # Special
    HASH = "#"
    DOLLAR = "$"
    AT = "@"
    ELLIPSIS = "..."
    
    # Hash directives
    HASH_IF = "#if"
    HASH_ELSE = "#else"
    HASH_FOREACH = "#foreach"
    HASH_SELECT = "#select"
    HASH_COND_OP = "#?"
    HASH_COLON = "#:"
    
    # C-block
    CBLOCK = "%{...%}"
    
    # Meta
    EOF = "EOF"
    NEWLINE = "\\n"
    WHITESPACE = "whitespace"
    COMMENT = "comment"
    INVALID = "invalid"


@dataclass
class DMLToken:
    """Enhanced token with additional metadata."""
    type: DMLTokenType
    value: str
    span: ZeroSpan
    leading_trivia: List[str] = field(default_factory=list)  # Comments, whitespace before token
    trailing_trivia: List[str] = field(default_factory=list)  # Comments, whitespace after token


class DMLLexer:
    """Enhanced lexer for complete DML language support."""
    
    # DML Reserved words mapping
    KEYWORDS = {
        # Core DML
        'dml': DMLTokenType.DML,
        'device': DMLTokenType.DEVICE,
        'bank': DMLTokenType.BANK,
        'register': DMLTokenType.REGISTER,
        'field': DMLTokenType.FIELD,
        'method': DMLTokenType.METHOD,
        'param': DMLTokenType.PARAMETER,  # DML uses 'param', not 'parameter'
        'parameter': DMLTokenType.PARAMETER,  # Keep for compatibility
        'attribute': DMLTokenType.ATTRIBUTE,
        'template': DMLTokenType.TEMPLATE,
        'connect': DMLTokenType.CONNECT,
        'interface': DMLTokenType.INTERFACE,
        'port': DMLTokenType.PORT,
        'implement': DMLTokenType.IMPLEMENT,
        'import': DMLTokenType.IMPORT,
        'library': DMLTokenType.LIBRARY,
        'typedef': DMLTokenType.TYPEDEF,
        'struct': DMLTokenType.STRUCT,
        'bitorder': DMLTokenType.BITORDER,
        'layout': DMLTokenType.LAYOUT,
        'hook': DMLTokenType.HOOK,
        'export': DMLTokenType.EXPORT,
        'footer': DMLTokenType.FOOTER,
        'header': DMLTokenType.HEADER,
        'async': DMLTokenType.ASYNC,
        'await': DMLTokenType.AWAIT,
        'is': DMLTokenType.IS,
        'each': DMLTokenType.EACH,
        'after': DMLTokenType.AFTER,
        'call': DMLTokenType.CALL,
        'cast': DMLTokenType.CAST,
        'defined': DMLTokenType.DEFINED,
        'error': DMLTokenType.ERROR,
        'select': DMLTokenType.SELECT,
        'sizeoftype': DMLTokenType.SIZEOFTYPE,
        'typeof': DMLTokenType.TYPEOF,
        'undefined': DMLTokenType.UNDEFINED,
        'vect': DMLTokenType.VECT,
        'where': DMLTokenType.WHERE,
        'provisional': DMLTokenType.PROVISIONAL,
        
        # Advanced constructs
        'session': DMLTokenType.SESSION,
        'saved': DMLTokenType.SAVED,
        'constant': DMLTokenType.CONSTANT,
        'data': DMLTokenType.DATA,
        'event': DMLTokenType.EVENT,
        'group': DMLTokenType.GROUP,
        'subdevice': DMLTokenType.SUBDEVICE,
        'loggroup': DMLTokenType.LOGGROUP,
        'independent': DMLTokenType.INDEPENDENT,
        'memoized': DMLTokenType.MEMOIZED,
        'throws': DMLTokenType.THROWS,
        'startup': DMLTokenType.STARTUP,
        
        # Control flow
        'if': DMLTokenType.IF,
        'else': DMLTokenType.ELSE,
        'while': DMLTokenType.WHILE,
        'for': DMLTokenType.FOR,
        'foreach': DMLTokenType.FOREACH,
        'in': DMLTokenType.IN,
        'do': DMLTokenType.DO,
        'break': DMLTokenType.BREAK,
        'continue': DMLTokenType.CONTINUE,
        'return': DMLTokenType.RETURN,
        'goto': DMLTokenType.GOTO,
        
        # Types
        'int': DMLTokenType.INT,
        'uint': DMLTokenType.UINT,
        'bool': DMLTokenType.BOOL,
        'char': DMLTokenType.CHAR,
        'void': DMLTokenType.VOID,
        'float': DMLTokenType.FLOAT,
        'double': DMLTokenType.DOUBLE,
        'short': DMLTokenType.SHORT,
        'long': DMLTokenType.LONG,
        'signed': DMLTokenType.SIGNED,
        'unsigned': DMLTokenType.UNSIGNED,
        'auto': DMLTokenType.AUTO,
        'const': DMLTokenType.CONST,
        'static': DMLTokenType.STATIC,
        'extern': DMLTokenType.EXTERN,
        'inline': DMLTokenType.INLINE,
        'volatile': DMLTokenType.VOLATILE,
        
        # Additional keywords
        'this': DMLTokenType.THIS,
        'new': DMLTokenType.NEW,
        'delete': DMLTokenType.DELETE,
        'sizeof': DMLTokenType.SIZEOF,
        'size': DMLTokenType.SIZE,
        'try': DMLTokenType.TRY,
        'catch': DMLTokenType.CATCH,
        'throw': DMLTokenType.THROW,
        'log': DMLTokenType.LOG,
        'assert': DMLTokenType.ASSERT,
        'local': DMLTokenType.LOCAL,
        'default': DMLTokenType.DEFAULT,
        'case': DMLTokenType.CASE,
        'switch': DMLTokenType.SWITCH,
        'then': DMLTokenType.THEN,
        'as': DMLTokenType.AS,
        'bitfields': DMLTokenType.BITFIELDS,
        'sequence': DMLTokenType.SEQUENCE,
        'stringify': DMLTokenType.STRINGIFY,
        'with': DMLTokenType.WITH,
        'shared': DMLTokenType.SHARED,
        'true': DMLTokenType.TRUE,
        'false': DMLTokenType.FALSE,
        'null': DMLTokenType.NULL,
    }
    
    # Operator patterns (order matters - longer operators first)
    OPERATORS = [
        ('...' , DMLTokenType.ELLIPSIS),
        ('<<=' , DMLTokenType.LSHIFT_ASSIGN),
        ('>>=' , DMLTokenType.RSHIFT_ASSIGN),
        ('+=' , DMLTokenType.PLUS_ASSIGN),
        ('-=' , DMLTokenType.MINUS_ASSIGN),
        ('*=' , DMLTokenType.MULT_ASSIGN),
        ('/=' , DMLTokenType.DIV_ASSIGN),
        ('%=' , DMLTokenType.MOD_ASSIGN),
        ('&=' , DMLTokenType.AND_ASSIGN),
        ('|=' , DMLTokenType.OR_ASSIGN),
        ('^=' , DMLTokenType.XOR_ASSIGN),
        ('==' , DMLTokenType.EQUALS),
        ('!=' , DMLTokenType.NOT_EQUALS),
        ('<=' , DMLTokenType.LESS_EQUAL),
        ('>=' , DMLTokenType.GREATER_EQUAL),
        ('&&' , DMLTokenType.LOGICAL_AND),
        ('||' , DMLTokenType.LOGICAL_OR),
        ('<<' , DMLTokenType.LEFT_SHIFT),
        ('>>' , DMLTokenType.RIGHT_SHIFT),
        ('++' , DMLTokenType.INCREMENT),
        ('--' , DMLTokenType.DECREMENT),
        ('->' , DMLTokenType.ARROW),
        ('::' , DMLTokenType.SCOPE),
        ('=' , DMLTokenType.ASSIGN),
        ('+' , DMLTokenType.PLUS),
        ('-' , DMLTokenType.MINUS),
        ('*' , DMLTokenType.MULTIPLY),
        ('/' , DMLTokenType.DIVIDE),
        ('%' , DMLTokenType.MODULO),
        ('<' , DMLTokenType.LESS),
        ('>' , DMLTokenType.GREATER),
        ('!' , DMLTokenType.LOGICAL_NOT),
        ('&' , DMLTokenType.BITWISE_AND),
        ('|' , DMLTokenType.BITWISE_OR),
        ('^' , DMLTokenType.BITWISE_XOR),
        ('~' , DMLTokenType.BITWISE_NOT),
        ('.' , DMLTokenType.DOT),
        ('?' , DMLTokenType.QUESTION),
        (':' , DMLTokenType.COLON),
    ]
    
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path
        self.position = 0
        self.line = 0
        self.column = 0
        self.tokens: List[DMLToken] = []
    
    def tokenize(self) -> List[DMLToken]:
        """Tokenize the input content."""
        while self.position < len(self.content):
            self._skip_whitespace_and_comments()
            
            if self.position >= len(self.content):
                break
                
            token = self._next_token()
            if token:
                self.tokens.append(token)
        
        # Add EOF token
        eof_pos = ZeroPosition(self.line, self.column)
        eof_span = ZeroSpan(self.file_path, ZeroRange(eof_pos, eof_pos))
        self.tokens.append(DMLToken(DMLTokenType.EOF, "", eof_span))
        
        return self.tokens
    
    def _skip_whitespace_and_comments(self) -> None:
        """Skip whitespace and comments."""
        while self.position < len(self.content):
            char = self.content[self.position]
            
            if char.isspace():
                if char == '\n':
                    self.line += 1
                    self.column = 0
                else:
                    self.column += 1
                self.position += 1
            elif char == '/' and self.position + 1 < len(self.content):
                next_char = self.content[self.position + 1]
                if next_char == '/':
                    # Single-line comment
                    self._skip_line_comment()
                elif next_char == '*':
                    # Multi-line comment
                    self._skip_block_comment()
                else:
                    break
            else:
                break
    
    def _skip_line_comment(self) -> None:
        """Skip single-line comment."""
        while self.position < len(self.content) and self.content[self.position] != '\n':
            self.position += 1
            self.column += 1
    
    def _skip_block_comment(self) -> None:
        """Skip block comment."""
        self.position += 2  # Skip /*
        self.column += 2
        
        while self.position + 1 < len(self.content):
            if self.content[self.position] == '*' and self.content[self.position + 1] == '/':
                self.position += 2
                self.column += 2
                break
            elif self.content[self.position] == '\n':
                self.line += 1
                self.column = 0
                self.position += 1
            else:
                self.position += 1
                self.column += 1
    
    def _next_token(self) -> Optional[DMLToken]:
        """Get the next token."""
        if self.position >= len(self.content):
            return None
        
        start_pos = ZeroPosition(self.line, self.column)
        char = self.content[self.position]
        
        # Hash directives
        if char == '#':
            if self.content[self.position:].startswith('#if'):
                return self._read_hash_directive(start_pos, '#if', DMLTokenType.HASH_IF)
            elif self.content[self.position:].startswith('#else'):
                return self._read_hash_directive(start_pos, '#else', DMLTokenType.HASH_ELSE)
            elif self.content[self.position:].startswith('#foreach'):
                return self._read_hash_directive(start_pos, '#foreach', DMLTokenType.HASH_FOREACH)
            elif self.content[self.position:].startswith('#select'):
                return self._read_hash_directive(start_pos, '#select', DMLTokenType.HASH_SELECT)
            elif self.content[self.position:].startswith('#?'):
                return self._read_hash_directive(start_pos, '#?', DMLTokenType.HASH_COND_OP)
            elif self.content[self.position:].startswith('#:'):
                return self._read_hash_directive(start_pos, '#:', DMLTokenType.HASH_COLON)
        
        # C-blocks
        if char == '%' and self.position + 1 < len(self.content) and self.content[self.position + 1] == '{':
            return self._read_cblock(start_pos)
        
        # String literals
        if char == '"':
            return self._read_string_literal(start_pos)
        
        # Character literals  
        if char == "'":
            return self._read_character_literal(start_pos)
        
        # Numbers
        if char.isdigit() or (char == '.' and self.position + 1 < len(self.content) and self.content[self.position + 1].isdigit()):
            return self._read_number(start_pos)
        
        # Identifiers and keywords
        if char.isalpha() or char == '_':
            return self._read_identifier(start_pos)
        
        # Operators
        for op_str, op_type in self.OPERATORS:
            if self.content[self.position:].startswith(op_str):
                self.position += len(op_str)
                self.column += len(op_str)
                end_pos = ZeroPosition(self.line, self.column)
                span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
                return DMLToken(op_type, op_str, span)
        
        # Punctuation
        punctuation_map = {
            ';': DMLTokenType.SEMICOLON,
            ',': DMLTokenType.COMMA,
            '(': DMLTokenType.LEFT_PAREN,
            ')': DMLTokenType.RIGHT_PAREN,
            '{': DMLTokenType.LEFT_BRACE,
            '}': DMLTokenType.RIGHT_BRACE,
            '[': DMLTokenType.LEFT_BRACKET,
            ']': DMLTokenType.RIGHT_BRACKET,
            '#': DMLTokenType.HASH,
            '$': DMLTokenType.DOLLAR,
            '@': DMLTokenType.AT,
        }
        
        if char in punctuation_map:
            self.position += 1
            self.column += 1
            end_pos = ZeroPosition(self.line, self.column)
            span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
            return DMLToken(punctuation_map[char], char, span)
        
        # Invalid character
        self.position += 1
        self.column += 1
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(DMLTokenType.INVALID, char, span)
    
    def _read_string_literal(self, start_pos: ZeroPosition) -> DMLToken:
        """Read a string literal."""
        value = ""
        self.position += 1  # Skip opening quote
        self.column += 1
        
        while self.position < len(self.content):
            char = self.content[self.position]
            
            if char == '"':
                self.position += 1
                self.column += 1
                break
            elif char == '\\' and self.position + 1 < len(self.content):
                # Escape sequence
                self.position += 1
                self.column += 1
                next_char = self.content[self.position]
                if next_char in 'nrtbf\\"\'':
                    escape_map = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', '\\': '\\', '"': '"', "'": "'"}
                    value += escape_map.get(next_char, next_char)
                else:
                    value += next_char
                self.position += 1
                self.column += 1
            else:
                if char == '\n':
                    self.line += 1
                    self.column = 0
                else:
                    self.column += 1
                value += char
                self.position += 1
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(DMLTokenType.STRING, value, span)
    
    def _read_character_literal(self, start_pos: ZeroPosition) -> DMLToken:
        """Read a character literal."""
        value = ""
        self.position += 1  # Skip opening quote
        self.column += 1
        
        while self.position < len(self.content):
            char = self.content[self.position]
            
            if char == "'":
                self.position += 1
                self.column += 1
                break
            elif char == '\\' and self.position + 1 < len(self.content):
                # Escape sequence
                self.position += 1
                self.column += 1
                next_char = self.content[self.position]
                if next_char in 'nrtbf\\"\'':
                    escape_map = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', '\\': '\\', '"': '"', "'": "'"}
                    value += escape_map.get(next_char, next_char)
                else:
                    value += next_char
                self.position += 1
                self.column += 1
            else:
                value += char
                self.position += 1
                self.column += 1
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(DMLTokenType.CHARACTER, value, span)
    
    def _read_number(self, start_pos: ZeroPosition) -> DMLToken:
        """Read a numeric literal."""
        value = ""
        
        # Handle hex numbers
        if (self.content[self.position] == '0' and 
            self.position + 1 < len(self.content) and 
            self.content[self.position + 1].lower() == 'x'):
            value += self.content[self.position:self.position + 2]
            self.position += 2
            self.column += 2
            
            while (self.position < len(self.content) and 
                   (self.content[self.position].isdigit() or 
                    self.content[self.position].lower() in 'abcdef')):
                value += self.content[self.position]
                self.position += 1
                self.column += 1
        else:
            # Decimal number
            while (self.position < len(self.content) and 
                   (self.content[self.position].isdigit() or self.content[self.position] == '.')):
                value += self.content[self.position]
                self.position += 1
                self.column += 1
            
            # Scientific notation
            if (self.position < len(self.content) and 
                self.content[self.position].lower() == 'e'):
                value += self.content[self.position]
                self.position += 1
                self.column += 1
                
                if (self.position < len(self.content) and 
                    self.content[self.position] in '+-'):
                    value += self.content[self.position]
                    self.position += 1
                    self.column += 1
                
                while (self.position < len(self.content) and 
                       self.content[self.position].isdigit()):
                    value += self.content[self.position]
                    self.position += 1
                    self.column += 1
        
        # Suffixes (u, l, f, etc.)
        while (self.position < len(self.content) and 
               self.content[self.position].lower() in 'ulf'):
            value += self.content[self.position]
            self.position += 1
            self.column += 1
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(DMLTokenType.NUMBER, value, span)
    
    def _read_identifier(self, start_pos: ZeroPosition) -> DMLToken:
        """Read an identifier or keyword."""
        value = ""
        
        while (self.position < len(self.content) and 
               (self.content[self.position].isalnum() or self.content[self.position] == '_')):
            value += self.content[self.position]
            self.position += 1
            self.column += 1
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        
        # Check if it's a keyword
        token_type = self.KEYWORDS.get(value, DMLTokenType.IDENTIFIER)
        return DMLToken(token_type, value, span)
    
    def _read_hash_directive(self, start_pos: ZeroPosition, directive: str, token_type: DMLTokenType) -> DMLToken:
        """Read a hash directive."""
        self.position += len(directive)
        self.column += len(directive)
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(token_type, directive, span)
    
    def _read_cblock(self, start_pos: ZeroPosition) -> DMLToken:
        """Read a C-block %{...%}."""
        value = ""
        self.position += 2  # Skip %{
        self.column += 2
        
        while self.position + 1 < len(self.content):
            if self.content[self.position] == '%' and self.content[self.position + 1] == '}':
                self.position += 2
                self.column += 2
                break
            elif self.content[self.position] == '\n':
                self.line += 1
                self.column = 0
                value += self.content[self.position]
                self.position += 1
            else:
                value += self.content[self.position]
                self.position += 1
                self.column += 1
        
        end_pos = ZeroPosition(self.line, self.column)
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        return DMLToken(DMLTokenType.CBLOCK, value, span)


# AST Node Types
class ASTNode(ABC):
    """Base class for all AST nodes."""
    
    def __init__(self, span: ZeroSpan):
        self.span = span
    
    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for traversal."""
        pass


class DMLExpression(ASTNode):
    """Base class for all DML expressions."""
    
    def __init__(self, span: ZeroSpan):
        super().__init__(span)


class DMLStatement(ASTNode):
    """Base class for all DML statements."""
    
    def __init__(self, span: ZeroSpan):
        super().__init__(span)


class DMLDeclaration(ASTNode):
    """Base class for all DML declarations."""
    
    def __init__(self, span: ZeroSpan, name: str):
        super().__init__(span)
        self.name = name
    
    def accept(self, visitor):
        return visitor.visit_declaration(self)


# Expression types
class IdentifierExpression(DMLExpression):
    """Identifier expression."""
    
    def __init__(self, span: ZeroSpan, name: str):
        super().__init__(span)
        self.name = name
    
    def accept(self, visitor):
        return visitor.visit_identifier(self)


class LiteralExpression(DMLExpression):
    """Literal expression."""
    
    def __init__(self, span: ZeroSpan, value: Any, literal_type: str):
        super().__init__(span)
        self.value = value
        self.literal_type = literal_type
    
    def accept(self, visitor):
        return visitor.visit_literal(self)


@dataclass
class BinaryExpression(DMLExpression):
    """Binary expression."""
    span: ZeroSpan
    left: DMLExpression
    operator: DMLToken
    right: DMLExpression
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_binary(self)


@dataclass
class UnaryExpression(DMLExpression):
    """Unary expression."""
    span: ZeroSpan
    operator: DMLToken
    operand: DMLExpression
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_unary(self)


@dataclass
class CallExpression(DMLExpression):
    """Function/method call expression."""
    span: ZeroSpan
    callee: DMLExpression
    arguments: List[DMLExpression]
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_call(self)


@dataclass
class MemberExpression(DMLExpression):
    """Member access expression (obj.member)."""
    span: ZeroSpan
    object: DMLExpression
    member: str
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_member(self)


@dataclass
class IndexExpression(DMLExpression):
    """Array/index access expression."""
    span: ZeroSpan
    object: DMLExpression
    index: DMLExpression
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_index(self)


@dataclass
class TertiaryExpression(DMLExpression):
    """Tertiary/conditional expression (condition ? true_expr : false_expr)."""
    span: ZeroSpan
    condition: DMLExpression
    true_expr: DMLExpression
    false_expr: DMLExpression
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_tertiary(self)


# Statement types
@dataclass
class ExpressionStatement(DMLStatement):
    """Expression statement."""
    span: ZeroSpan
    expression: DMLExpression
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_expression_statement(self)


class BlockStatement(DMLStatement):
    """Block statement."""
    
    def __init__(self, span: ZeroSpan, statements: List[DMLStatement]):
        super().__init__(span)
        self.statements = statements
    
    def accept(self, visitor):
        return visitor.visit_block(self)


@dataclass
class IfStatement(DMLStatement):
    """If statement."""
    span: ZeroSpan
    condition: DMLExpression
    then_statement: DMLStatement
    else_statement: Optional[DMLStatement] = None
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_if(self)


@dataclass
class WhileStatement(DMLStatement):
    """While statement."""
    span: ZeroSpan
    condition: DMLExpression
    body: DMLStatement
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_while(self)


@dataclass
class ForStatement(DMLStatement):
    """For statement."""
    span: ZeroSpan
    initializer: Optional[DMLStatement]
    condition: Optional[DMLExpression]
    increment: Optional[DMLExpression]
    body: DMLStatement
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_for(self)


@dataclass
class ReturnStatement(DMLStatement):
    """Return statement."""
    span: ZeroSpan
    value: Optional[DMLExpression] = None
    
    def __post_init__(self):
        super().__init__(self.span)
    
    def accept(self, visitor):
        return visitor.visit_return(self)


# Declaration types
class ParameterDeclaration(DMLDeclaration):
    """Parameter declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameter_type: Optional[str] = None, default_value: Optional[DMLExpression] = None):
        super().__init__(span, name)
        self.parameter_type = parameter_type
        self.default_value = default_value
    
    def accept(self, visitor):
        return visitor.visit_parameter(self)


class MethodDeclaration(DMLDeclaration):
    """Method declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List['VariableDeclaration'], 
                 return_type: Optional[str] = None, body: Optional[BlockStatement] = None,
                 modifier: Optional[str] = None, independent: bool = False, 
                 startup: bool = False, memoized: bool = False, 
                 throws: bool = False, default: bool = False):
        super().__init__(span, name)
        self.parameters = parameters
        self.return_type = return_type
        self.body = body
        self.modifier = modifier  # 'inline' or 'shared'
        self.independent = independent
        self.startup = startup
        self.memoized = memoized
        self.throws = throws
        self.default = default
    
    def accept(self, visitor):
        return visitor.visit_method(self)


class VariableDeclaration(DMLDeclaration):
    """Variable declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, variable_type: str, initializer: Optional[DMLExpression] = None):
        super().__init__(span, name)
        self.variable_type = variable_type
        self.initializer = initializer
    
    def accept(self, visitor):
        return visitor.visit_variable(self)


class FieldDeclaration(DMLDeclaration):
    """Field declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, size: Optional[DMLExpression] = None, parameters: List[ParameterDeclaration] = None, methods: List[MethodDeclaration] = None):
        super().__init__(span, name)
        self.size = size
        self.parameters = parameters or []
        self.methods = methods or []
    
    def accept(self, visitor):
        return visitor.visit_field(self)


class RegisterDeclaration(DMLDeclaration):
    """Register declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, size: Optional[DMLExpression] = None, offset: Optional[DMLExpression] = None, parameters: List[ParameterDeclaration] = None, fields: List[FieldDeclaration] = None, methods: List[MethodDeclaration] = None):
        super().__init__(span, name)
        self.size = size
        self.offset = offset
        self.parameters = parameters or []
        self.fields = fields or []
        self.methods = methods or []
    
    def accept(self, visitor):
        return visitor.visit_register(self)


class BankDeclaration(DMLDeclaration):
    """Bank declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None, registers: List[RegisterDeclaration] = None, methods: List[MethodDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
        self.registers = registers or []
        self.methods = methods or []
    
    def accept(self, visitor):
        return visitor.visit_bank(self)


class TemplateDeclaration(DMLDeclaration):
    """Template declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None, methods: List[MethodDeclaration] = None, fields: List[FieldDeclaration] = None, registers: List[RegisterDeclaration] = None, banks: List[BankDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
        self.methods = methods or []
        self.fields = fields or []
        self.registers = registers or []
        self.banks = banks or []
    
    def accept(self, visitor):
        return visitor.visit_template(self)


class DeviceDeclaration(DMLDeclaration):
    """Device declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None, banks: List[BankDeclaration] = None, methods: List[MethodDeclaration] = None, templates: List[str] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
        self.banks = banks or []
        self.methods = methods or []
        self.templates = templates or []
    
    def accept(self, visitor):
        return visitor.visit_device(self)


class ImportDeclaration(DMLDeclaration):
    """Import declaration."""
    
    def __init__(self, span: ZeroSpan, module_name: str):
        super().__init__(span, "import")
        self.module_name = module_name
    
    def accept(self, visitor):
        return visitor.visit_import(self)


class DMLVersionDeclaration(DMLDeclaration):
    """DML version declaration."""
    
    def __init__(self, span: ZeroSpan, version: str):
        super().__init__(span, "dml")
        self.version = version
    
    def accept(self, visitor):
        return visitor.visit_dml_version(self)


class ConnectDeclaration(DMLDeclaration):
    """Connect declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_connect(self)


class InterfaceDeclaration(DMLDeclaration):
    """Interface declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_interface(self)


class PortDeclaration(DMLDeclaration):
    """Port declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_port(self)


class AttributeDeclaration(DMLDeclaration):
    """Attribute declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_attribute(self)


class EventDeclaration(DMLDeclaration):
    """Event declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_event(self)


class GroupDeclaration(DMLDeclaration):
    """Group declaration."""
    
    def __init__(self, span: ZeroSpan, name: str, parameters: List[ParameterDeclaration] = None):
        super().__init__(span, name)
        self.parameters = parameters or []
    
    def accept(self, visitor):
        return visitor.visit_group(self)


class EnhancedDMLParser:
    """Enhanced DML parser with comprehensive grammar support."""
    
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path
        self.lexer = DMLLexer(content, file_path)
        self.tokens = self.lexer.tokenize()
        self.position = 0
        self.errors: List[DMLError] = []
        self.symbols: List[DMLSymbol] = []
        self.references: List[SymbolReference] = []
        self.imports: List[str] = []
        self.dml_version: Optional[str] = None
        self.ast: List[DMLDeclaration] = []
        
        # Recovery state
        self._in_recovery = False
        self._recovery_tokens = {DMLTokenType.SEMICOLON, DMLTokenType.RIGHT_BRACE}
    
    def parse(self) -> List[DMLDeclaration]:
        """Parse the token stream and return AST."""
        try:
            while not self._is_at_end():
                if decl := self._parse_top_level_declaration():
                    self.ast.append(decl)
                    
                    # Extract symbols from declarations
                    self._extract_symbols_from_declaration(decl)
        except Exception as e:
            if not self._in_recovery:
                self._error(f"Parse error: {e}")
        
        return self.ast
    
    def get_errors(self) -> List[DMLError]:
        """Get parsing errors."""
        return self.errors
    
    def get_symbols(self) -> List[DMLSymbol]:
        """Get extracted symbols."""
        return self.symbols
    
    def get_references(self) -> List[SymbolReference]:
        """Get symbol references."""
        return self.references
    
    # Token management
    def _current_token(self) -> DMLToken:
        """Get current token."""
        if self.position >= len(self.tokens):
            return self.tokens[-1]  # EOF token
        return self.tokens[self.position]
    
    def _peek_token(self, offset: int = 1) -> DMLToken:
        """Peek at token ahead."""
        pos = self.position + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # EOF token
        return self.tokens[pos]
    
    def _advance(self) -> DMLToken:
        """Advance to next token."""
        if not self._is_at_end():
            self.position += 1
        return self._previous_token()
    
    def _previous_token(self) -> DMLToken:
        """Get previous token."""
        return self.tokens[self.position - 1]
    
    def _is_at_end(self) -> bool:
        """Check if at end of tokens."""
        return self._current_token().type == DMLTokenType.EOF
    
    def _check(self, token_type: DMLTokenType) -> bool:
        """Check if current token matches type."""
        if self._is_at_end():
            return False
        return self._current_token().type == token_type
    
    def _match(self, *token_types: DMLTokenType) -> bool:
        """Check if current token matches any of the types."""
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False
    
    def _consume(self, token_type: DMLTokenType, message: str) -> DMLToken:
        """Consume token of expected type or error."""
        if self._check(token_type):
            return self._advance()
        
        self._error(message)
        return self._current_token()
    
    def _error(self, message: str) -> None:
        """Report parsing error."""
        token = self._current_token()
        error = DMLError(
            kind=DMLErrorKind.SYNTAX_ERROR,
            message=message,
            span=token.span
        )
        self.errors.append(error)
        self._synchronize()
    
    def _synchronize(self) -> None:
        """Synchronize after parse error."""
        self._in_recovery = True
        self._advance()
        
        while not self._is_at_end():
            if self._previous_token().type == DMLTokenType.SEMICOLON:
                self._in_recovery = False
                return
            
            if self._current_token().type in {
                DMLTokenType.DEVICE, DMLTokenType.TEMPLATE, DMLTokenType.BANK,
                DMLTokenType.REGISTER, DMLTokenType.FIELD, DMLTokenType.METHOD,
                DMLTokenType.PARAMETER, DMLTokenType.IMPORT, DMLTokenType.DML
            }:
                self._in_recovery = False
                return
            
            self._advance()
        
        self._in_recovery = False
    
    # Top-level parsing methods
    def _parse_top_level_declaration(self) -> Optional[DMLDeclaration]:
        """Parse a top-level declaration."""
        if self._match(DMLTokenType.DML):
            return self._parse_dml_version()
        elif self._match(DMLTokenType.IMPORT):
            return self._parse_import()
        elif self._match(DMLTokenType.DEVICE):
            return self._parse_device()
        elif self._match(DMLTokenType.TEMPLATE):
            return self._parse_template()
        elif self._match(DMLTokenType.TYPEDEF):
            return self._parse_typedef()
        elif self._match(DMLTokenType.PARAMETER):
            return self._parse_parameter()
        elif self._match(DMLTokenType.CONNECT):
            return self._parse_connect()
        elif self._match(DMLTokenType.BANK):
            return self._parse_bank()
        elif self._match(DMLTokenType.ATTRIBUTE):
            return self._parse_attribute()
        elif self._match(DMLTokenType.EVENT):
            return self._parse_event()
        elif self._match(DMLTokenType.GROUP):
            return self._parse_group()
        elif self._match(DMLTokenType.CONSTANT):
            return self._parse_constant()
        else:
            # Skip unknown tokens and try to recover
            self._advance()
            return None
    
    def _parse_dml_version(self) -> DMLVersionDeclaration:
        """Parse DML version declaration."""
        start_span = self._previous_token().span
        
        version_token = self._consume(DMLTokenType.NUMBER, "Expected version number after 'dml'")
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after DML version")
        
        self.dml_version = version_token.value
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return DMLVersionDeclaration(combined_span, version_token.value)
    
    def _parse_import(self) -> ImportDeclaration:
        """Parse import declaration."""
        start_span = self._previous_token().span
        
        module_token = self._consume(DMLTokenType.STRING, "Expected module name after 'import'")
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after import")
        
        self.imports.append(module_token.value)
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return ImportDeclaration(combined_span, module_token.value)
    
    def _parse_device(self) -> DeviceDeclaration:
        """Parse device declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected device name")
        
        # Parse optional template applications (is template_name)
        templates = []
        if self._match(DMLTokenType.IS):
            template_token = self._consume(DMLTokenType.IDENTIFIER, "Expected template name after 'is'")
            templates.append(template_token.value)
            
            # Multiple templates: is template1, template2
            while self._match(DMLTokenType.COMMA):
                template_token = self._consume(DMLTokenType.IDENTIFIER, "Expected template name after ','")
                templates.append(template_token.value)
        
        # Device declarations in DML 1.4 are terminated with semicolon, not braces
        # Example: device watchdog_timer;
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after device declaration")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        # Device body is defined elsewhere in the file, not inline
        parameters = []
        banks = []
        methods = []
        
        return DeviceDeclaration(combined_span, name_token.value, parameters, banks, methods, templates)
    
    def _parse_template(self) -> TemplateDeclaration:
        """Parse template declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected template name")
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after template name")
        
        # Parse template body
        parameters = []
        methods = []
        fields = []
        registers = []
        banks = []
        
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            elif self._match(DMLTokenType.METHOD):
                methods.append(self._parse_method())
            elif self._match(DMLTokenType.FIELD):
                fields.append(self._parse_field())
            elif self._match(DMLTokenType.REGISTER):
                registers.append(self._parse_register())
            elif self._match(DMLTokenType.BANK):
                banks.append(self._parse_bank())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after template body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return TemplateDeclaration(combined_span, name_token.value, parameters, methods, fields, registers, banks)
    
    def _parse_parameter(self) -> ParameterDeclaration:
        """Parse parameter declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected parameter name")
        
        # Optional type
        parameter_type = None
        if self._match(DMLTokenType.COLON):
            type_token = self._consume(DMLTokenType.IDENTIFIER, "Expected parameter type")
            parameter_type = type_token.value
        
        # Optional default value
        default_value = None
        if self._match(DMLTokenType.ASSIGN):
            default_value = self._parse_expression()
        
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after parameter")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return ParameterDeclaration(combined_span, name_token.value, parameter_type, default_value)
    
    def _parse_typedef(self) -> Optional[DMLDeclaration]:
        """Parse typedef declaration (basic implementation)."""
        # Skip typedef for now - complex type system
        while not self._check(DMLTokenType.SEMICOLON) and not self._is_at_end():
            self._advance()
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after typedef")
        return None
    
    def _extract_symbols_from_declaration(self, declaration: DMLDeclaration) -> None:
        """Extract symbols from AST declarations."""
        try:
            if isinstance(declaration, DeviceDeclaration):
                # Add device symbol
                device_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.DEVICE,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Device with {len(declaration.parameters)} parameters",
                    documentation=f"DML device {declaration.name}"
                )
                self.symbols.append(device_symbol)
                
                # Add parameter symbols
                for param in declaration.parameters:
                    param_symbol = DMLSymbol(
                        name=param.name,
                        kind=DMLSymbolKind.PARAMETER,
                        location=DMLLocation(span=param.span),
                        detail=f"Device parameter",
                        documentation=f"Parameter {param.name}"
                    )
                    self.symbols.append(param_symbol)
                
                # Add method symbols
                for method in declaration.methods:
                    method_symbol = DMLSymbol(
                        name=method.name,
                        kind=DMLSymbolKind.METHOD,
                        location=DMLLocation(span=method.span),
                        detail=f"Device method",
                        documentation=f"Method {method.name}"
                    )
                    self.symbols.append(method_symbol)
                
                # Add bank symbols
                for bank in declaration.banks:
                    bank_symbol = DMLSymbol(
                        name=bank.name,
                        kind=DMLSymbolKind.BANK,
                        location=DMLLocation(span=bank.span),
                        detail=f"Register bank",
                        documentation=f"Bank {bank.name}"
                    )
                    self.symbols.append(bank_symbol)
            
            elif isinstance(declaration, TemplateDeclaration):
                # Add template symbol
                template_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.TEMPLATE,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Template with {len(declaration.parameters)} parameters",
                    documentation=f"DML template {declaration.name}"
                )
                self.symbols.append(template_symbol)
                
                # Add template parameter symbols
                for param in declaration.parameters:
                    param_symbol = DMLSymbol(
                        name=param.name,
                        kind=DMLSymbolKind.PARAMETER,
                        location=DMLLocation(span=param.span),
                        detail=f"Template parameter",
                        documentation=f"Template parameter {param.name}"
                    )
                    self.symbols.append(param_symbol)
            
            elif isinstance(declaration, ImportDeclaration):
                # Add import symbol - only if module_name is valid
                if declaration.module_name and declaration.module_name.strip():
                    import_symbol = DMLSymbol(
                        name=declaration.module_name,
                        kind=DMLSymbolKind.MODULE,
                        location=DMLLocation(span=declaration.span),
                        detail=f"Imported module",
                        documentation=f"Import {declaration.module_name}"
                    )
                    self.symbols.append(import_symbol)
                else:
                    logger.debug(f"Skipping ImportDeclaration with empty or invalid module_name at {declaration.span}")
            
            elif isinstance(declaration, DMLVersionDeclaration):
                # Add version symbol
                version_symbol = DMLSymbol(
                    name="dml",
                    kind=DMLSymbolKind.CONSTANT,
                    location=DMLLocation(span=declaration.span),
                    detail=f"DML version {declaration.version}",
                    documentation=f"DML language version {declaration.version}"
                )
                self.symbols.append(version_symbol)
            
            elif isinstance(declaration, ConnectDeclaration):
                # Add connect symbol
                connect_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.CONNECT,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Connect with {len(declaration.parameters)} parameters",
                    documentation=f"Connect {declaration.name}"
                )
                self.symbols.append(connect_symbol)
            
            elif isinstance(declaration, BankDeclaration):
                # Add bank symbol
                bank_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.BANK,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Bank with {len(declaration.registers)} registers",
                    documentation=f"Bank {declaration.name}"
                )
                self.symbols.append(bank_symbol)
                
                # Add register symbols from bank
                for register in declaration.registers:
                    register_symbol = DMLSymbol(
                        name=register.name,
                        kind=DMLSymbolKind.REGISTER,
                        location=DMLLocation(span=register.span),
                        detail=f"Register in bank {declaration.name}",
                        documentation=f"Register {register.name}"
                    )
                    self.symbols.append(register_symbol)
                    
                    # Add method symbols from register
                    if hasattr(register, 'methods'):
                        for method in register.methods:
                            method_symbol = DMLSymbol(
                                name=method.name,
                                kind=DMLSymbolKind.METHOD,
                                location=DMLLocation(span=method.span),
                                detail=f"Method in register {register.name}",
                                documentation=f"Method {method.name}"
                            )
                            self.symbols.append(method_symbol)
            
            elif isinstance(declaration, AttributeDeclaration):
                # Add attribute symbol
                attr_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.ATTRIBUTE,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Attribute",
                    documentation=f"Attribute {declaration.name}"
                )
                self.symbols.append(attr_symbol)
            
            elif isinstance(declaration, EventDeclaration):
                # Add event symbol
                event_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.EVENT,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Event",
                    documentation=f"Event {declaration.name}"
                )
                self.symbols.append(event_symbol)
            
            elif isinstance(declaration, GroupDeclaration):
                # Add group symbol
                group_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.GROUP,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Group",
                    documentation=f"Group {declaration.name}"
                )
                self.symbols.append(group_symbol)
            
            elif isinstance(declaration, ParameterDeclaration):
                # Add parameter symbol (top-level parameter)
                param_symbol = DMLSymbol(
                    name=declaration.name,
                    kind=DMLSymbolKind.PARAMETER,
                    location=DMLLocation(span=declaration.span),
                    detail=f"Parameter",
                    documentation=f"Parameter {declaration.name}"
                )
                self.symbols.append(param_symbol)
                
        except Exception as e:
            decl_name = getattr(declaration, 'name', None) or getattr(declaration, 'module_name', 'unknown')
            logger.warning(f"Failed to extract symbols from {type(declaration).__name__} '{decl_name}': {e}")
    
    def _parse_expression(self) -> Optional[DMLExpression]:
        """Parse an expression (basic implementation)."""
        return self._parse_tertiary_expression()
    
    def _parse_tertiary_expression(self) -> Optional[DMLExpression]:
        """Parse tertiary/conditional expressions (condition ? true_expr : false_expr)."""
        condition = self._parse_binary_expression()
        
        if condition is None:
            return None
        
        # Check for tertiary operator
        if self._match(DMLTokenType.QUESTION):
            true_expr = self._parse_expression()
            self._consume(DMLTokenType.COLON, "Expected ':' in tertiary expression")
            false_expr = self._parse_expression()
            
            if true_expr and false_expr:
                combined_span = ZeroSpan(
                    condition.span.file_path,
                    ZeroRange(condition.span.range.start, false_expr.span.range.end)
                )
                return TertiaryExpression(combined_span, condition, true_expr, false_expr)
        
        return condition
    
    def _parse_binary_expression(self) -> Optional[DMLExpression]:
        """Parse binary expressions including bit range operator (:)."""
        left = self._parse_primary()
        
        if left is None:
            return None
        
        # Handle colon operator for bit ranges like [31:16]
        if self._match(DMLTokenType.COLON):
            operator_token = self._previous_token()
            right = self._parse_primary()
            if right is not None:
                # Create a binary expression for the range
                combined_span = ZeroSpan(
                    left.span.file_path,
                    ZeroRange(left.span.range.start, right.span.range.end)
                )
                return BinaryExpression(combined_span, left, operator_token, right)
        
        return left
    
    def _parse_primary(self) -> Optional[DMLExpression]:
        """Parse primary expressions."""
        token = self._current_token()
        
        if token.type == DMLTokenType.NUMBER:
            self._advance()
            return LiteralExpression(token.span, token.value, "number")
        
        elif token.type == DMLTokenType.STRING:
            self._advance()
            return LiteralExpression(token.span, token.value, "string")
        
        elif token.type == DMLTokenType.CHARACTER:
            self._advance()
            return LiteralExpression(token.span, token.value, "character")
        
        elif token.type == DMLTokenType.IDENTIFIER:
            self._advance()
            return IdentifierExpression(token.span, token.value)
        
        elif self._match(DMLTokenType.LEFT_PAREN):
            expr = self._parse_expression()
            self._consume(DMLTokenType.RIGHT_PAREN, "Expected ')' after expression")
            return expr
        
        else:
            # Skip unknown tokens
            self._advance()
            return None
    
    def _parse_block_statement(self) -> BlockStatement:
        """Parse block statement."""
        start_token = self._consume(DMLTokenType.LEFT_BRACE, "Expected '{'")
        statements = []
        
        # Track brace depth to handle nested blocks correctly
        brace_depth = 1  # We already consumed the opening brace
        
        while brace_depth > 0 and not self._is_at_end():
            current = self._current_token()
            if current.type == DMLTokenType.LEFT_BRACE:
                brace_depth += 1
            elif current.type == DMLTokenType.RIGHT_BRACE:
                brace_depth -= 1
                if brace_depth == 0:
                    break  # Don't consume the closing brace yet
            self._advance()
        
        end_token = self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}'")
        
        span = ZeroSpan(
            start_token.span.file_path,
            ZeroRange(start_token.span.range.start, end_token.span.range.end)
        )
        
        return BlockStatement(span, statements)
    
    def _parse_method(self) -> MethodDeclaration:
        """Parse method declaration with modifiers."""
        start_span = self._previous_token().span
        
        # Parse optional modifiers before method name
        modifier = None
        independent = False
        startup = False
        memoized = False
        throws = False
        default = False
        
        # Check for inline/shared modifier
        if self._check(DMLTokenType.INLINE):
            modifier = 'inline'
            self._advance()
        elif self._check(DMLTokenType.SHARED):
            modifier = 'shared'
            self._advance()
        
        # Check for independent
        if self._match(DMLTokenType.INDEPENDENT):
            independent = True
        
        # Check for startup
        if self._match(DMLTokenType.STARTUP):
            startup = True
        
        # Check for memoized
        if self._match(DMLTokenType.MEMOIZED):
            memoized = True
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected method name")
        
        self._consume(DMLTokenType.LEFT_PAREN, "Expected '(' after method name")
        
        # Parse parameters
        parameters = []
        if not self._check(DMLTokenType.RIGHT_PAREN):
            parameters.append(self._parse_variable_declaration())
            
            while self._match(DMLTokenType.COMMA):
                parameters.append(self._parse_variable_declaration())
        
        self._consume(DMLTokenType.RIGHT_PAREN, "Expected ')' after method parameters")
        
        # Optional return type
        return_type = None
        if self._match(DMLTokenType.ARROW):
            if self._match(DMLTokenType.LEFT_PAREN):
                type_token = self._consume(DMLTokenType.IDENTIFIER, "Expected return type")
                self._consume(DMLTokenType.RIGHT_PAREN, "Expected ')' after return type")
                return_type = type_token.value
        
        # Check for throws
        if self._match(DMLTokenType.THROWS):
            throws = True
        
        # Check for default
        if self._check(DMLTokenType.IDENTIFIER) and self._current_token().value == 'default':
            default = True
            self._advance()
        
        # Method body
        body = None
        if self._check(DMLTokenType.LEFT_BRACE):
            body = self._parse_block_statement()
        else:
            self._consume(DMLTokenType.SEMICOLON, "Expected ';' or '{' after method signature")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return MethodDeclaration(combined_span, name_token.value, parameters, return_type, body,
                                modifier, independent, startup, memoized, throws, default)
    
    def _parse_field(self) -> FieldDeclaration:
        """Parse field declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected field name")
        
        # Optional @ [bits] specification for bit range
        size = None
        if self._match(DMLTokenType.AT):
            if self._match(DMLTokenType.LEFT_BRACKET):
                size = self._parse_expression()
                self._consume(DMLTokenType.RIGHT_BRACKET, "Expected ']' after field bit range")
        # Optional size specification (alternative syntax)
        elif self._match(DMLTokenType.LEFT_BRACKET):
            size = self._parse_expression()
            self._consume(DMLTokenType.RIGHT_BRACKET, "Expected ']' after field size")
        
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after field name")
        
        # Parse field body
        parameters = []
        methods = []
        
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            elif self._match(DMLTokenType.METHOD):
                methods.append(self._parse_method())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after field body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return FieldDeclaration(combined_span, name_token.value, size, parameters, methods)
    
    def _parse_register(self) -> RegisterDeclaration:
        """Parse register declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected register name")
        
        # Optional size and offset
        size = None
        offset = None
        
        if self._match(DMLTokenType.LEFT_BRACKET):
            size = self._parse_expression()
            self._consume(DMLTokenType.RIGHT_BRACKET, "Expected ']' after register size")
        
        # Parse @ offset syntax
        if self._match(DMLTokenType.AT):
            offset = self._parse_expression()
        
        # Parse optional template applications: is (template1, template2)
        if self._match(DMLTokenType.IS):
            if self._match(DMLTokenType.LEFT_PAREN):
                # Parse template list
                self._consume(DMLTokenType.IDENTIFIER, "Expected template name")
                while self._match(DMLTokenType.COMMA):
                    self._consume(DMLTokenType.IDENTIFIER, "Expected template name after ','")
                self._consume(DMLTokenType.RIGHT_PAREN, "Expected ')' after template list")
        
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after register declaration")
        
        # Parse register body
        parameters = []
        fields = []
        methods = []
        
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            elif self._match(DMLTokenType.FIELD):
                fields.append(self._parse_field())
            elif self._match(DMLTokenType.METHOD):
                methods.append(self._parse_method())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after register body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return RegisterDeclaration(combined_span, name_token.value, size, offset, parameters, fields, methods)
    
    def _parse_bank(self) -> BankDeclaration:
        """Parse bank declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected bank name")
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after bank name")
        
        # Parse bank body
        parameters = []
        registers = []
        methods = []
        
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            elif self._match(DMLTokenType.REGISTER):
                registers.append(self._parse_register())
            elif self._match(DMLTokenType.METHOD):
                methods.append(self._parse_method())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after bank body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return BankDeclaration(combined_span, name_token.value, parameters, registers, methods)
    
    def _parse_connect(self) -> ConnectDeclaration:
        """Parse connect declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected connect name")
        
        # Optional template application: is (template_name)
        if self._match(DMLTokenType.IS):
            if self._match(DMLTokenType.LEFT_PAREN):
                self._consume(DMLTokenType.IDENTIFIER, "Expected template name")
                self._consume(DMLTokenType.RIGHT_PAREN, "Expected ')' after template name")
        
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after connect name")
        
        # Parse connect body
        parameters = []
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after connect body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return ConnectDeclaration(combined_span, name_token.value, parameters)
    
    def _parse_attribute(self) -> AttributeDeclaration:
        """Parse attribute declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected attribute name")
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after attribute name")
        
        # Parse attribute body
        parameters = []
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after attribute body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return AttributeDeclaration(combined_span, name_token.value, parameters)
    
    def _parse_event(self) -> EventDeclaration:
        """Parse event declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected event name")
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after event name")
        
        # Parse event body
        parameters = []
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after event body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return EventDeclaration(combined_span, name_token.value, parameters)
    
    def _parse_group(self) -> GroupDeclaration:
        """Parse group declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected group name")
        self._consume(DMLTokenType.LEFT_BRACE, "Expected '{' after group name")
        
        # Parse group body
        parameters = []
        while not self._check(DMLTokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(DMLTokenType.PARAMETER):
                parameters.append(self._parse_parameter())
            else:
                self._advance()  # Skip unknown tokens
        
        self._consume(DMLTokenType.RIGHT_BRACE, "Expected '}' after group body")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        return GroupDeclaration(combined_span, name_token.value, parameters)
    
    def _parse_constant(self) -> 'ConstantDeclaration':
        """Parse constant declaration."""
        start_span = self._previous_token().span
        
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected constant name")
        self._consume(DMLTokenType.ASSIGN, "Expected '=' after constant name")
        
        # Parse constant value (simplified - just consume until semicolon)
        value_tokens = []
        while not self._check(DMLTokenType.SEMICOLON) and not self._is_at_end():
            value_tokens.append(self._current_token().value)
            self._advance()
        
        self._consume(DMLTokenType.SEMICOLON, "Expected ';' after constant value")
        
        end_span = self._previous_token().span
        combined_span = ZeroSpan(start_span.file_path, ZeroRange(start_span.range.start, end_span.range.end))
        
        # For now, just store the value as a string
        value = ' '.join(str(v) for v in value_tokens)
        
        # Create a simple constant declaration (we'll need to define this class)
        from dataclasses import dataclass
        @dataclass
        class ConstantDeclaration(DMLDeclaration):
            value: str
            def accept(self, visitor):
                return visitor.visit_constant(self)
        
        return ConstantDeclaration(combined_span, name_token.value, value)
    
    def _parse_variable_declaration(self) -> VariableDeclaration:
        """Parse variable declaration."""
        start_pos = self._current_token().span.range.start
        
        type_token = self._consume(DMLTokenType.IDENTIFIER, "Expected variable type")
        name_token = self._consume(DMLTokenType.IDENTIFIER, "Expected variable name")
        
        # Optional initializer
        initializer = None
        if self._match(DMLTokenType.ASSIGN):
            initializer = self._parse_expression()
        
        end_pos = self._previous_token().span.range.end
        span = ZeroSpan(self.file_path, ZeroRange(start_pos, end_pos))
        
        return VariableDeclaration(span, name_token.value, type_token.value, initializer)