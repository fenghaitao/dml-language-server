"""
DML Expression Structure Analysis

Provides analysis and representation of DML expressions, including binary operations,
function calls, member access, and complex expressions. This module corresponds to
the Rust implementation in src/analysis/structure/expressions.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef


class ExpressionKind(Enum):
    """Types of DML expressions."""
    LITERAL = "literal"
    IDENTIFIER = "identifier"
    BINARY = "binary"
    UNARY = "unary"
    CALL = "call"
    MEMBER = "member"
    INDEX = "index"
    TERTIARY = "tertiary"
    CAST = "cast"
    SIZEOF = "sizeof"
    NEW = "new"
    SLICE = "slice"
    INITIALIZER = "initializer"


class LiteralKind(Enum):
    """Types of literal expressions."""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    CHARACTER = "character"
    BOOLEAN = "boolean"
    NULL = "null"
    UNDEFINED = "undefined"


@dataclass
class DMLString:
    """Represents a DML string with source location."""
    value: str
    span: ZeroSpan
    
    @classmethod
    def from_token(cls, token, file_spec) -> 'DMLString':
        """Create DMLString from token."""
        return cls(token.value, token.span)
    
    def __str__(self) -> str:
        return self.value


@dataclass
class LiteralExpression:
    """Literal expression in DML."""
    span: ZeroSpan
    value: Any
    kind: LiteralKind
    
    def get_string_value(self) -> Optional[str]:
        """Get string representation of literal value."""
        if self.kind == LiteralKind.STRING:
            return str(self.value)
        elif self.kind == LiteralKind.INTEGER:
            return str(self.value)
        elif self.kind == LiteralKind.FLOAT:
            return str(self.value)
        elif self.kind == LiteralKind.BOOLEAN:
            return "true" if self.value else "false"
        elif self.kind == LiteralKind.NULL:
            return "NULL"
        elif self.kind == LiteralKind.UNDEFINED:
            return "undefined"
        return None


@dataclass
class IdentifierExpression:
    """Identifier expression in DML."""
    span: ZeroSpan
    name: DMLString
    scope_path: List[str] = field(default_factory=list)
    
    def get_full_name(self) -> str:
        """Get full qualified name."""
        if self.scope_path:
            return ".".join(self.scope_path + [self.name.value])
        return self.name.value


class BinaryOperator(Enum):
    """Binary operators in DML."""
    # Arithmetic
    ADD = "+"
    SUBTRACT = "-" 
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    
    # Comparison
    EQUAL = "=="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    
    # Logical
    LOGICAL_AND = "&&"
    LOGICAL_OR = "||"
    
    # Bitwise
    BITWISE_AND = "&"
    BITWISE_OR = "|"
    BITWISE_XOR = "^"
    LEFT_SHIFT = "<<"
    RIGHT_SHIFT = ">>"
    
    # Assignment
    ASSIGN = "="
    ADD_ASSIGN = "+="
    SUBTRACT_ASSIGN = "-="
    MULTIPLY_ASSIGN = "*="
    DIVIDE_ASSIGN = "/="
    MODULO_ASSIGN = "%="
    AND_ASSIGN = "&="
    OR_ASSIGN = "|="
    XOR_ASSIGN = "^="
    LEFT_SHIFT_ASSIGN = "<<="
    RIGHT_SHIFT_ASSIGN = ">>="


@dataclass
class BinaryExpression:
    """Binary expression in DML."""
    span: ZeroSpan
    left: 'Expression'
    operator: BinaryOperator
    right: 'Expression'
    operator_span: ZeroSpan
    
    def is_assignment(self) -> bool:
        """Check if this is an assignment operation."""
        return self.operator in {
            BinaryOperator.ASSIGN,
            BinaryOperator.ADD_ASSIGN,
            BinaryOperator.SUBTRACT_ASSIGN,
            BinaryOperator.MULTIPLY_ASSIGN,
            BinaryOperator.DIVIDE_ASSIGN,
            BinaryOperator.MODULO_ASSIGN,
            BinaryOperator.AND_ASSIGN,
            BinaryOperator.OR_ASSIGN,
            BinaryOperator.XOR_ASSIGN,
            BinaryOperator.LEFT_SHIFT_ASSIGN,
            BinaryOperator.RIGHT_SHIFT_ASSIGN,
        }
    
    def get_precedence(self) -> int:
        """Get operator precedence."""
        precedence_map = {
            # Assignment (lowest)
            BinaryOperator.ASSIGN: 1,
            BinaryOperator.ADD_ASSIGN: 1,
            BinaryOperator.SUBTRACT_ASSIGN: 1,
            BinaryOperator.MULTIPLY_ASSIGN: 1,
            BinaryOperator.DIVIDE_ASSIGN: 1,
            BinaryOperator.MODULO_ASSIGN: 1,
            BinaryOperator.AND_ASSIGN: 1,
            BinaryOperator.OR_ASSIGN: 1,
            BinaryOperator.XOR_ASSIGN: 1,
            BinaryOperator.LEFT_SHIFT_ASSIGN: 1,
            BinaryOperator.RIGHT_SHIFT_ASSIGN: 1,
            
            # Logical OR
            BinaryOperator.LOGICAL_OR: 2,
            
            # Logical AND
            BinaryOperator.LOGICAL_AND: 3,
            
            # Bitwise OR
            BinaryOperator.BITWISE_OR: 4,
            
            # Bitwise XOR
            BinaryOperator.BITWISE_XOR: 5,
            
            # Bitwise AND
            BinaryOperator.BITWISE_AND: 6,
            
            # Equality
            BinaryOperator.EQUAL: 7,
            BinaryOperator.NOT_EQUAL: 7,
            
            # Relational
            BinaryOperator.LESS_THAN: 8,
            BinaryOperator.LESS_EQUAL: 8,
            BinaryOperator.GREATER_THAN: 8,
            BinaryOperator.GREATER_EQUAL: 8,
            
            # Shift
            BinaryOperator.LEFT_SHIFT: 9,
            BinaryOperator.RIGHT_SHIFT: 9,
            
            # Additive
            BinaryOperator.ADD: 10,
            BinaryOperator.SUBTRACT: 10,
            
            # Multiplicative (highest)
            BinaryOperator.MULTIPLY: 11,
            BinaryOperator.DIVIDE: 11,
            BinaryOperator.MODULO: 11,
        }
        return precedence_map.get(self.operator, 0)


class UnaryOperator(Enum):
    """Unary operators in DML."""
    PLUS = "+"
    MINUS = "-"
    LOGICAL_NOT = "!"
    BITWISE_NOT = "~"
    PRE_INCREMENT = "++"
    PRE_DECREMENT = "--"
    POST_INCREMENT = "++"
    POST_DECREMENT = "--"
    ADDRESS_OF = "&"
    DEREFERENCE = "*"


@dataclass
class UnaryExpression:
    """Unary expression in DML."""
    span: ZeroSpan
    operator: UnaryOperator
    operand: 'Expression'
    operator_span: ZeroSpan
    is_postfix: bool = False


@dataclass
class CallExpression:
    """Function/method call expression."""
    span: ZeroSpan
    callee: 'Expression'
    arguments: List['Expression']
    
    def get_method_name(self) -> Optional[str]:
        """Get method name if this is a simple method call."""
        if isinstance(self.callee, IdentifierExpression):
            return self.callee.name.value
        elif isinstance(self.callee, MemberExpression):
            return self.callee.member.value
        return None


@dataclass
class MemberExpression:
    """Member access expression (obj.member)."""
    span: ZeroSpan
    object: 'Expression'
    member: DMLString
    operator_span: ZeroSpan  # Location of '.' or '->'
    is_arrow: bool = False  # True for '->', False for '.'


@dataclass
class IndexExpression:
    """Array/index access expression."""
    span: ZeroSpan
    object: 'Expression'
    index: 'Expression'


@dataclass
class TertiaryExpression:
    """Tertiary/conditional expression (condition ? true_expr : false_expr)."""
    span: ZeroSpan
    condition: 'Expression'
    true_expr: 'Expression'
    false_expr: 'Expression'
    question_span: ZeroSpan
    colon_span: ZeroSpan


@dataclass
class SliceExpression:
    """Bit slice expression ([high:low])."""
    span: ZeroSpan
    object: 'Expression'
    high: Optional['Expression']
    low: Optional['Expression']
    
    def is_single_bit(self) -> bool:
        """Check if this is a single bit access."""
        return self.low is None and self.high is not None


@dataclass
class CastExpression:
    """Type cast expression."""
    span: ZeroSpan
    target_type: 'TypeExpression'
    expression: 'Expression'


@dataclass
class SizeofExpression:
    """Sizeof expression."""
    span: ZeroSpan
    target: Union['Expression', 'TypeExpression']


@dataclass
class NewExpression:
    """New expression for object creation."""
    span: ZeroSpan
    type_expr: 'TypeExpression'
    arguments: List['Expression']
    
    def get_type_name(self) -> Optional[str]:
        """Get the type name being instantiated."""
        if hasattr(self.type_expr, 'name'):
            return self.type_expr.name
        return None


@dataclass
class InitializerExpression:
    """Initializer expression for structs/arrays."""
    span: ZeroSpan
    elements: List['InitializerElement']


@dataclass
class InitializerElement:
    """Element in an initializer expression."""
    span: ZeroSpan
    designator: Optional[Union[str, int]]  # Field name or array index
    value: 'Expression'


@dataclass
class TypeExpression:
    """Type expression for casts and declarations."""
    span: ZeroSpan
    name: str
    is_const: bool = False
    is_volatile: bool = False
    pointer_count: int = 0
    array_dimensions: List[Optional['Expression']] = field(default_factory=list)


# Union type for all expressions
Expression = Union[
    LiteralExpression,
    IdentifierExpression,
    BinaryExpression,
    UnaryExpression,
    CallExpression,
    MemberExpression,
    IndexExpression,
    TertiaryExpression,
    SliceExpression,
    CastExpression,
    SizeofExpression,
    NewExpression,
    InitializerExpression,
    TypeExpression,
]


class ExpressionAnalyzer:
    """Analyzes DML expressions for semantic information."""
    
    def __init__(self):
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
    
    def analyze_expression(self, expr: Expression) -> None:
        """Analyze an expression for semantic information."""
        if isinstance(expr, IdentifierExpression):
            self._analyze_identifier(expr)
        elif isinstance(expr, BinaryExpression):
            self._analyze_binary(expr)
        elif isinstance(expr, UnaryExpression):
            self._analyze_unary(expr)
        elif isinstance(expr, CallExpression):
            self._analyze_call(expr)
        elif isinstance(expr, MemberExpression):
            self._analyze_member(expr)
        elif isinstance(expr, IndexExpression):
            self._analyze_index(expr)
        elif isinstance(expr, TertiaryExpression):
            self._analyze_tertiary(expr)
        elif isinstance(expr, SliceExpression):
            self._analyze_slice(expr)
        elif isinstance(expr, CastExpression):
            self._analyze_cast(expr)
        elif isinstance(expr, NewExpression):
            self._analyze_new(expr)
        elif isinstance(expr, InitializerExpression):
            self._analyze_initializer(expr)
        # LiteralExpression and TypeExpression don't need special analysis
    
    def _analyze_identifier(self, expr: IdentifierExpression) -> None:
        """Analyze identifier expression."""
        # Create reference for identifier
        node_ref = NodeRef(expr.name.value, expr.span, expr.scope_path)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.VARIABLE,  # Default, may be refined later
            location=expr.span
        )
        self.references.append(reference)
    
    def _analyze_binary(self, expr: BinaryExpression) -> None:
        """Analyze binary expression."""
        self.analyze_expression(expr.left)
        self.analyze_expression(expr.right)
        
        # Check for type compatibility (basic checks)
        if expr.operator in {BinaryOperator.ADD, BinaryOperator.SUBTRACT, 
                           BinaryOperator.MULTIPLY, BinaryOperator.DIVIDE}:
            # Arithmetic operations should have compatible operands
            pass  # TODO: Implement type checking
    
    def _analyze_unary(self, expr: UnaryExpression) -> None:
        """Analyze unary expression."""
        self.analyze_expression(expr.operand)
    
    def _analyze_call(self, expr: CallExpression) -> None:
        """Analyze call expression."""
        self.analyze_expression(expr.callee)
        for arg in expr.arguments:
            self.analyze_expression(arg)
        
        # Add method reference if this is a method call
        method_name = expr.get_method_name()
        if method_name:
            node_ref = NodeRef(method_name, expr.span)
            reference = SymbolReference(
                node_ref=node_ref,
                kind=ReferenceKind.METHOD,
                location=expr.span
            )
            self.references.append(reference)
    
    def _analyze_member(self, expr: MemberExpression) -> None:
        """Analyze member access expression."""
        self.analyze_expression(expr.object)
        
        # Add reference for member access
        node_ref = NodeRef(expr.member.value, expr.member.span)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.VARIABLE,  # Could be field, parameter, etc.
            location=expr.member.span
        )
        self.references.append(reference)
    
    def _analyze_index(self, expr: IndexExpression) -> None:
        """Analyze index expression."""
        self.analyze_expression(expr.object)
        self.analyze_expression(expr.index)
    
    def _analyze_tertiary(self, expr: TertiaryExpression) -> None:
        """Analyze tertiary expression."""
        self.analyze_expression(expr.condition)
        self.analyze_expression(expr.true_expr)
        self.analyze_expression(expr.false_expr)
    
    def _analyze_slice(self, expr: SliceExpression) -> None:
        """Analyze slice expression."""
        self.analyze_expression(expr.object)
        if expr.high:
            self.analyze_expression(expr.high)
        if expr.low:
            self.analyze_expression(expr.low)
    
    def _analyze_cast(self, expr: CastExpression) -> None:
        """Analyze cast expression."""
        self.analyze_expression(expr.expression)
        # TODO: Validate cast target type
    
    def _analyze_new(self, expr: NewExpression) -> None:
        """Analyze new expression."""
        for arg in expr.arguments:
            self.analyze_expression(arg)
        
        # Add type reference
        type_name = expr.get_type_name()
        if type_name:
            node_ref = NodeRef(type_name, expr.span)
            reference = SymbolReference(
                node_ref=node_ref,
                kind=ReferenceKind.TYPE,
                location=expr.span
            )
            self.references.append(reference)
    
    def _analyze_initializer(self, expr: InitializerExpression) -> None:
        """Analyze initializer expression."""
        for element in expr.elements:
            self.analyze_expression(element.value)
    
    def get_errors(self) -> List[DMLError]:
        """Get analysis errors."""
        return self.errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get symbol references found."""
        return self.references


def create_literal_expression(span: ZeroSpan, value: Any, kind: LiteralKind) -> LiteralExpression:
    """Helper to create literal expressions."""
    return LiteralExpression(span=span, value=value, kind=kind)


def create_identifier_expression(span: ZeroSpan, name: str) -> IdentifierExpression:
    """Helper to create identifier expressions."""
    dml_string = DMLString(name, span)
    return IdentifierExpression(span=span, name=dml_string)


def create_binary_expression(span: ZeroSpan, left: Expression, operator: BinaryOperator, 
                           right: Expression, operator_span: ZeroSpan) -> BinaryExpression:
    """Helper to create binary expressions."""
    return BinaryExpression(
        span=span,
        left=left,
        operator=operator,
        right=right,
        operator_span=operator_span
    )


__all__ = [
    'ExpressionKind', 'LiteralKind', 'BinaryOperator', 'UnaryOperator',
    'DMLString', 'LiteralExpression', 'IdentifierExpression', 'BinaryExpression',
    'UnaryExpression', 'CallExpression', 'MemberExpression', 'IndexExpression',
    'TertiaryExpression', 'SliceExpression', 'CastExpression', 'SizeofExpression',
    'NewExpression', 'InitializerExpression', 'InitializerElement', 'TypeExpression',
    'Expression', 'ExpressionAnalyzer',
    'create_literal_expression', 'create_identifier_expression', 'create_binary_expression'
]