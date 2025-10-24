"""
DML Structure Analysis Module

This module provides comprehensive analysis of DML language structures including
expressions, statements, objects, types, and top-level constructs. It corresponds
to the Rust implementation in src/analysis/structure/.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

from .expressions import *
from .statements import *
from .objects import *
from .types import *
from .toplevel import *

__all__ = [
    # From expressions
    'ExpressionKind', 'LiteralKind', 'BinaryOperator', 'UnaryOperator',
    'DMLString', 'LiteralExpression', 'IdentifierExpression', 'BinaryExpression',
    'UnaryExpression', 'CallExpression', 'MemberExpression', 'IndexExpression',
    'TertiaryExpression', 'SliceExpression', 'CastExpression', 'SizeofExpression',
    'NewExpression', 'InitializerExpression', 'InitializerElement', 'TypeExpression',
    'Expression', 'ExpressionAnalyzer',
    
    # From statements
    'StatementKind', 'LogLevel', 'Statement', 'ExpressionStatement', 'BlockStatement',
    'IfStatement', 'WhileStatement', 'DoWhileStatement', 'ForStatement', 'ForeachStatement',
    'SwitchStatement', 'SwitchCase', 'DefaultCase', 'BreakStatement', 'ContinueStatement',
    'ReturnStatement', 'GotoStatement', 'LabelStatement', 'TryCatchStatement', 'CatchClause',
    'ThrowStatement', 'LogStatement', 'AssertStatement', 'AfterStatement', 'HashIfStatement',
    'HashForeachStatement', 'HashSelectStatement', 'HashSelectCase', 'InlineCStatement',
    'StatementAnalyzer',
    
    # From objects
    'ObjectKind', 'Visibility', 'MethodModifier', 'DMLObject', 'Device', 'Template',
    'Bank', 'Register', 'Field', 'Method', 'Parameter', 'FormalParameter', 'Attribute',
    'Connect', 'Interface', 'Port', 'Event', 'Group', 'Data', 'Session', 'Saved',
    'Constant', 'Typedef', 'Variable', 'Hook', 'Subdevice', 'LogGroup', 'Scope',
    'ObjectAnalyzer',
    
    # From types
    'TypeKind', 'PrimitiveType', 'DMLType', 'PrimitiveTypeDecl', 'StructType', 'StructField',
    'UnionType', 'EnumType', 'EnumValue', 'ArrayType', 'PointerType', 'FunctionType',
    'TemplateType', 'VoidType', 'AutoType', 'TypedefType', 'TypeRegistry', 'TypeAnalyzer',
    
    # From toplevel
    'DeclarationKind', 'TopLevelDeclaration', 'DMLVersionDeclaration', 'ImportDeclaration',
    'DeviceDeclaration', 'TemplateDeclaration', 'TypedefDeclaration', 'StructDeclaration',
    'UnionDeclaration', 'EnumDeclaration', 'ConstantDeclaration', 'ExternDeclaration',
    'DMLFile', 'DMLProject', 'TopLevelAnalyzer',
]