"""
DML Statement Structure Analysis

Provides analysis and representation of DML statements, including control flow,
declarations, and compound statements. This module corresponds to the Rust
implementation in src/analysis/structure/statements.rs.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from ...span import ZeroSpan, ZeroPosition, ZeroRange
from ..types import DMLError, DMLErrorKind, ReferenceKind, SymbolReference, NodeRef
from .expressions import Expression, ExpressionAnalyzer


class StatementKind(Enum):
    """Types of DML statements."""
    EXPRESSION = "expression"
    BLOCK = "block"
    IF = "if"
    WHILE = "while"
    FOR = "for"
    FOREACH = "foreach"
    DO_WHILE = "do_while"
    SWITCH = "switch"
    CASE = "case"
    DEFAULT = "default"
    BREAK = "break"
    CONTINUE = "continue"
    RETURN = "return"
    GOTO = "goto"
    LABEL = "label"
    TRY_CATCH = "try_catch"
    THROW = "throw"
    LOG = "log"
    ASSERT = "assert"
    AFTER = "after"
    HASH_IF = "hash_if"
    HASH_ELSE = "hash_else"
    HASH_FOREACH = "hash_foreach"
    HASH_SELECT = "hash_select"
    INLINE_C = "inline_c"


@dataclass
class Statement:
    """Base class for all DML statements."""
    span: ZeroSpan
    kind: StatementKind
    
    def get_child_statements(self) -> List['Statement']:
        """Get child statements for traversal."""
        return []


@dataclass
class ExpressionStatement(Statement):
    """Expression statement."""
    expression: Expression
    
    def __post_init__(self):
        self.kind = StatementKind.EXPRESSION


@dataclass
class BlockStatement(Statement):
    """Block statement containing multiple statements."""
    statements: List[Statement]
    
    def __post_init__(self):
        self.kind = StatementKind.BLOCK
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return self.statements


@dataclass
class IfStatement(Statement):
    """If statement with optional else."""
    condition: Expression
    then_statement: Statement
    else_statement: Optional[Statement] = None
    
    def __post_init__(self):
        self.kind = StatementKind.IF
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        children = [self.then_statement]
        if self.else_statement:
            children.append(self.else_statement)
        return children


@dataclass
class WhileStatement(Statement):
    """While loop statement."""
    condition: Expression
    body: Statement
    
    def __post_init__(self):
        self.kind = StatementKind.WHILE
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return [self.body]


@dataclass
class DoWhileStatement(Statement):
    """Do-while loop statement."""
    body: Statement
    condition: Expression
    
    def __post_init__(self):
        self.kind = StatementKind.DO_WHILE
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return [self.body]


@dataclass
class ForStatement(Statement):
    """For loop statement."""
    initializer: Optional[Statement]
    condition: Optional[Expression]
    increment: Optional[Expression]
    body: Statement
    
    def __post_init__(self):
        self.kind = StatementKind.FOR
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        children = []
        if self.initializer:
            children.append(self.initializer)
        children.append(self.body)
        return children


@dataclass
class ForeachStatement(Statement):
    """Foreach loop statement."""
    variable: str
    iterable: Expression
    body: Statement
    variable_span: ZeroSpan
    
    def __post_init__(self):
        self.kind = StatementKind.FOREACH
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return [self.body]


@dataclass
class SwitchStatement(Statement):
    """Switch statement."""
    expression: Expression
    cases: List['SwitchCase']
    default_case: Optional['DefaultCase'] = None
    
    def __post_init__(self):
        self.kind = StatementKind.SWITCH
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        children = []
        for case in self.cases:
            children.extend(case.statements)
        if self.default_case:
            children.extend(self.default_case.statements)
        return children


@dataclass
class SwitchCase:
    """Case in a switch statement."""
    span: ZeroSpan
    value: Expression
    statements: List[Statement]
    
    @property
    def kind(self) -> StatementKind:
        return StatementKind.CASE


@dataclass
class DefaultCase:
    """Default case in a switch statement."""
    span: ZeroSpan
    statements: List[Statement]
    
    @property
    def kind(self) -> StatementKind:
        return StatementKind.DEFAULT


@dataclass
class BreakStatement(Statement):
    """Break statement."""
    label: Optional[str] = None
    
    def __post_init__(self):
        self.kind = StatementKind.BREAK


@dataclass
class ContinueStatement(Statement):
    """Continue statement."""
    label: Optional[str] = None
    
    def __post_init__(self):
        self.kind = StatementKind.CONTINUE


@dataclass
class ReturnStatement(Statement):
    """Return statement."""
    value: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = StatementKind.RETURN


@dataclass
class GotoStatement(Statement):
    """Goto statement."""
    label: str
    label_span: ZeroSpan
    
    def __post_init__(self):
        self.kind = StatementKind.GOTO


@dataclass
class LabelStatement(Statement):
    """Label statement."""
    label: str
    statement: Optional[Statement] = None
    
    def __post_init__(self):
        self.kind = StatementKind.LABEL
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return [self.statement] if self.statement else []


@dataclass
class TryCatchStatement(Statement):
    """Try-catch statement."""
    try_block: BlockStatement
    catch_clauses: List['CatchClause']
    finally_block: Optional[BlockStatement] = None
    
    def __post_init__(self):
        self.kind = StatementKind.TRY_CATCH
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        children = [self.try_block]
        for clause in self.catch_clauses:
            children.append(clause.handler)
        if self.finally_block:
            children.append(self.finally_block)
        return children


@dataclass
class CatchClause:
    """Catch clause in try-catch."""
    span: ZeroSpan
    exception_type: Optional[str]
    variable_name: Optional[str]
    handler: BlockStatement


@dataclass
class ThrowStatement(Statement):
    """Throw statement."""
    expression: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = StatementKind.THROW


class LogLevel(Enum):
    """Log levels for log statements."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


@dataclass
class LogStatement(Statement):
    """Log statement."""
    level: LogLevel
    message: Expression
    arguments: List[Expression] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = StatementKind.LOG


@dataclass
class AssertStatement(Statement):
    """Assert statement."""
    condition: Expression
    message: Optional[Expression] = None
    
    def __post_init__(self):
        self.kind = StatementKind.ASSERT


@dataclass
class AfterStatement(Statement):
    """After statement for delayed execution."""
    delay: Expression
    body: Statement
    
    def __post_init__(self):
        self.kind = StatementKind.AFTER
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return [self.body]


@dataclass
class HashIfStatement(Statement):
    """Hash if preprocessor statement."""
    condition: Expression
    then_statements: List[Statement]
    else_statements: List[Statement] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = StatementKind.HASH_IF
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return self.then_statements + self.else_statements


@dataclass
class HashForeachStatement(Statement):
    """Hash foreach preprocessor statement."""
    variable: str
    iterable: Expression
    statements: List[Statement]
    variable_span: ZeroSpan
    
    def __post_init__(self):
        self.kind = StatementKind.HASH_FOREACH
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        return self.statements


@dataclass
class HashSelectStatement(Statement):
    """Hash select preprocessor statement."""
    expression: Expression
    cases: List['HashSelectCase']
    default_statements: List[Statement] = field(default_factory=list)
    
    def __post_init__(self):
        self.kind = StatementKind.HASH_SELECT
    
    def get_child_statements(self) -> List[Statement]:
        """Get child statements."""
        children = []
        for case in self.cases:
            children.extend(case.statements)
        children.extend(self.default_statements)
        return children


@dataclass
class HashSelectCase:
    """Case in hash select statement."""
    span: ZeroSpan
    value: Expression
    statements: List[Statement]


@dataclass
class InlineCStatement(Statement):
    """Inline C code statement."""
    code: str
    
    def __post_init__(self):
        self.kind = StatementKind.INLINE_C


class StatementAnalyzer:
    """Analyzes DML statements for semantic information."""
    
    def __init__(self):
        self.errors: List[DMLError] = []
        self.references: List[SymbolReference] = []
        self.expression_analyzer = ExpressionAnalyzer()
        self._loop_depth = 0
        self._switch_depth = 0
        self._try_depth = 0
    
    def analyze_statement(self, stmt: Statement) -> None:
        """Analyze a statement for semantic information."""
        if isinstance(stmt, ExpressionStatement):
            self._analyze_expression_statement(stmt)
        elif isinstance(stmt, BlockStatement):
            self._analyze_block_statement(stmt)
        elif isinstance(stmt, IfStatement):
            self._analyze_if_statement(stmt)
        elif isinstance(stmt, WhileStatement):
            self._analyze_while_statement(stmt)
        elif isinstance(stmt, DoWhileStatement):
            self._analyze_do_while_statement(stmt)
        elif isinstance(stmt, ForStatement):
            self._analyze_for_statement(stmt)
        elif isinstance(stmt, ForeachStatement):
            self._analyze_foreach_statement(stmt)
        elif isinstance(stmt, SwitchStatement):
            self._analyze_switch_statement(stmt)
        elif isinstance(stmt, BreakStatement):
            self._analyze_break_statement(stmt)
        elif isinstance(stmt, ContinueStatement):
            self._analyze_continue_statement(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._analyze_return_statement(stmt)
        elif isinstance(stmt, GotoStatement):
            self._analyze_goto_statement(stmt)
        elif isinstance(stmt, LabelStatement):
            self._analyze_label_statement(stmt)
        elif isinstance(stmt, TryCatchStatement):
            self._analyze_try_catch_statement(stmt)
        elif isinstance(stmt, ThrowStatement):
            self._analyze_throw_statement(stmt)
        elif isinstance(stmt, LogStatement):
            self._analyze_log_statement(stmt)
        elif isinstance(stmt, AssertStatement):
            self._analyze_assert_statement(stmt)
        elif isinstance(stmt, AfterStatement):
            self._analyze_after_statement(stmt)
        elif isinstance(stmt, HashIfStatement):
            self._analyze_hash_if_statement(stmt)
        elif isinstance(stmt, HashForeachStatement):
            self._analyze_hash_foreach_statement(stmt)
        elif isinstance(stmt, HashSelectStatement):
            self._analyze_hash_select_statement(stmt)
        elif isinstance(stmt, InlineCStatement):
            self._analyze_inline_c_statement(stmt)
    
    def _analyze_expression_statement(self, stmt: ExpressionStatement) -> None:
        """Analyze expression statement."""
        self.expression_analyzer.analyze_expression(stmt.expression)
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_block_statement(self, stmt: BlockStatement) -> None:
        """Analyze block statement."""
        for child_stmt in stmt.statements:
            self.analyze_statement(child_stmt)
    
    def _analyze_if_statement(self, stmt: IfStatement) -> None:
        """Analyze if statement."""
        self.expression_analyzer.analyze_expression(stmt.condition)
        self.analyze_statement(stmt.then_statement)
        if stmt.else_statement:
            self.analyze_statement(stmt.else_statement)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_while_statement(self, stmt: WhileStatement) -> None:
        """Analyze while statement."""
        self._loop_depth += 1
        try:
            self.expression_analyzer.analyze_expression(stmt.condition)
            self.analyze_statement(stmt.body)
            
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
        finally:
            self._loop_depth -= 1
    
    def _analyze_do_while_statement(self, stmt: DoWhileStatement) -> None:
        """Analyze do-while statement."""
        self._loop_depth += 1
        try:
            self.analyze_statement(stmt.body)
            self.expression_analyzer.analyze_expression(stmt.condition)
            
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
        finally:
            self._loop_depth -= 1
    
    def _analyze_for_statement(self, stmt: ForStatement) -> None:
        """Analyze for statement."""
        self._loop_depth += 1
        try:
            if stmt.initializer:
                self.analyze_statement(stmt.initializer)
            if stmt.condition:
                self.expression_analyzer.analyze_expression(stmt.condition)
            if stmt.increment:
                self.expression_analyzer.analyze_expression(stmt.increment)
            self.analyze_statement(stmt.body)
            
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
        finally:
            self._loop_depth -= 1
    
    def _analyze_foreach_statement(self, stmt: ForeachStatement) -> None:
        """Analyze foreach statement."""
        self._loop_depth += 1
        try:
            self.expression_analyzer.analyze_expression(stmt.iterable)
            self.analyze_statement(stmt.body)
            
            # Add variable reference
            node_ref = NodeRef(stmt.variable, stmt.variable_span)
            reference = SymbolReference(
                node_ref=node_ref,
                kind=ReferenceKind.VARIABLE,
                location=stmt.variable_span
            )
            self.references.append(reference)
            
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
        finally:
            self._loop_depth -= 1
    
    def _analyze_switch_statement(self, stmt: SwitchStatement) -> None:
        """Analyze switch statement."""
        self._switch_depth += 1
        try:
            self.expression_analyzer.analyze_expression(stmt.expression)
            
            for case in stmt.cases:
                self.expression_analyzer.analyze_expression(case.value)
                for case_stmt in case.statements:
                    self.analyze_statement(case_stmt)
            
            if stmt.default_case:
                for default_stmt in stmt.default_case.statements:
                    self.analyze_statement(default_stmt)
            
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
        finally:
            self._switch_depth -= 1
    
    def _analyze_break_statement(self, stmt: BreakStatement) -> None:
        """Analyze break statement."""
        if self._loop_depth == 0 and self._switch_depth == 0:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Break statement outside of loop or switch",
                span=stmt.span
            )
            self.errors.append(error)
    
    def _analyze_continue_statement(self, stmt: ContinueStatement) -> None:
        """Analyze continue statement."""
        if self._loop_depth == 0:
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Continue statement outside of loop",
                span=stmt.span
            )
            self.errors.append(error)
    
    def _analyze_return_statement(self, stmt: ReturnStatement) -> None:
        """Analyze return statement."""
        if stmt.value:
            self.expression_analyzer.analyze_expression(stmt.value)
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_goto_statement(self, stmt: GotoStatement) -> None:
        """Analyze goto statement."""
        # Add label reference
        node_ref = NodeRef(stmt.label, stmt.label_span)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.VARIABLE,  # Labels are like variables
            location=stmt.label_span
        )
        self.references.append(reference)
    
    def _analyze_label_statement(self, stmt: LabelStatement) -> None:
        """Analyze label statement."""
        if stmt.statement:
            self.analyze_statement(stmt.statement)
    
    def _analyze_try_catch_statement(self, stmt: TryCatchStatement) -> None:
        """Analyze try-catch statement."""
        self._try_depth += 1
        try:
            self.analyze_statement(stmt.try_block)
            
            for clause in stmt.catch_clauses:
                self.analyze_statement(clause.handler)
            
            if stmt.finally_block:
                self.analyze_statement(stmt.finally_block)
        finally:
            self._try_depth -= 1
    
    def _analyze_throw_statement(self, stmt: ThrowStatement) -> None:
        """Analyze throw statement."""
        if self._try_depth == 0:
            # Warning: throw outside try block
            pass
        
        if stmt.expression:
            self.expression_analyzer.analyze_expression(stmt.expression)
            self.references.extend(self.expression_analyzer.get_references())
            self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_log_statement(self, stmt: LogStatement) -> None:
        """Analyze log statement."""
        self.expression_analyzer.analyze_expression(stmt.message)
        for arg in stmt.arguments:
            self.expression_analyzer.analyze_expression(arg)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_assert_statement(self, stmt: AssertStatement) -> None:
        """Analyze assert statement."""
        self.expression_analyzer.analyze_expression(stmt.condition)
        if stmt.message:
            self.expression_analyzer.analyze_expression(stmt.message)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_after_statement(self, stmt: AfterStatement) -> None:
        """Analyze after statement."""
        self.expression_analyzer.analyze_expression(stmt.delay)
        self.analyze_statement(stmt.body)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_hash_if_statement(self, stmt: HashIfStatement) -> None:
        """Analyze hash if statement."""
        self.expression_analyzer.analyze_expression(stmt.condition)
        
        for then_stmt in stmt.then_statements:
            self.analyze_statement(then_stmt)
        
        for else_stmt in stmt.else_statements:
            self.analyze_statement(else_stmt)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_hash_foreach_statement(self, stmt: HashForeachStatement) -> None:
        """Analyze hash foreach statement."""
        self.expression_analyzer.analyze_expression(stmt.iterable)
        
        for child_stmt in stmt.statements:
            self.analyze_statement(child_stmt)
        
        # Add variable reference
        node_ref = NodeRef(stmt.variable, stmt.variable_span)
        reference = SymbolReference(
            node_ref=node_ref,
            kind=ReferenceKind.VARIABLE,
            location=stmt.variable_span
        )
        self.references.append(reference)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_hash_select_statement(self, stmt: HashSelectStatement) -> None:
        """Analyze hash select statement."""
        self.expression_analyzer.analyze_expression(stmt.expression)
        
        for case in stmt.cases:
            self.expression_analyzer.analyze_expression(case.value)
            for case_stmt in case.statements:
                self.analyze_statement(case_stmt)
        
        for default_stmt in stmt.default_statements:
            self.analyze_statement(default_stmt)
        
        self.references.extend(self.expression_analyzer.get_references())
        self.errors.extend(self.expression_analyzer.get_errors())
    
    def _analyze_inline_c_statement(self, stmt: InlineCStatement) -> None:
        """Analyze inline C statement."""
        # Basic validation of C code
        if not stmt.code.strip():
            error = DMLError(
                kind=DMLErrorKind.SEMANTIC_ERROR,
                message="Empty inline C block",
                span=stmt.span
            )
            self.errors.append(error)
    
    def get_errors(self) -> List[DMLError]:
        """Get analysis errors."""
        return self.errors
    
    def get_references(self) -> List[SymbolReference]:
        """Get symbol references found."""
        return self.references


__all__ = [
    'StatementKind', 'LogLevel', 'Statement', 'ExpressionStatement', 'BlockStatement',
    'IfStatement', 'WhileStatement', 'DoWhileStatement', 'ForStatement', 'ForeachStatement',
    'SwitchStatement', 'SwitchCase', 'DefaultCase', 'BreakStatement', 'ContinueStatement',
    'ReturnStatement', 'GotoStatement', 'LabelStatement', 'TryCatchStatement', 'CatchClause',
    'ThrowStatement', 'LogStatement', 'AssertStatement', 'AfterStatement', 'HashIfStatement',
    'HashForeachStatement', 'HashSelectStatement', 'HashSelectCase', 'InlineCStatement',
    'StatementAnalyzer'
]