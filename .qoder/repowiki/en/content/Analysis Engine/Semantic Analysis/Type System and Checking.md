# Type System and Checking

<cite>
**Referenced Files in This Document**
- [types.rs](file://src/analysis/structure/types.rs)
- [types.rs](file://src/analysis/parsing/types.rs)
- [types.rs](file://src/analysis/templating/types.rs)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py)
- [types.py](file://python-port/dml_language_server/analysis/types.py)
- [expressions.rs](file://src/analysis/structure/expressions.rs)
- [statements.rs](file://src/analysis/structure/statements.rs)
- [scope.rs](file://src/analysis/scope.rs)
- [reference.rs](file://src/analysis/reference.rs)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document describes the DML type system and semantic analysis implementation. It explains the type hierarchy, primitive and composite types, generic/template handling, type inference, compatibility and coercion, and type checking for expressions, assignments, and function calls. It also documents the relationship between type definitions and semantic representations, type parameter resolution, and type safety guarantees.

## Project Structure
The type system spans both Rust and Python ports:
- Rust core: parsing/type definitions, semantic structure, and template type evaluation live under src/analysis.
- Python port: shared type abstractions, template type system, and type registry live under python-port/dml_language_server/analysis.

```mermaid
graph TB
subgraph "Rust Analysis"
RS_Types["structure/types.rs<br/>Semantic type model"]
RP_Types["parsing/types.rs<br/>AST type nodes"]
RT_Types["templating/types.rs<br/>Resolved types (Rust)"]
RE_Expr["structure/expressions.rs<br/>Expressions using DMLType"]
STMT["structure/statements.rs<br/>Statements using DMLType"]
SCOPE["scope.rs<br/>Scoping and contexts"]
REF["reference.rs<br/>References and kinds"]
end
subgraph "Python Analysis"
PS_Types["analysis/structure/types.py<br/>Type registry and analyzer"]
PT_Types["analysis/templating/types.py<br/>Template type system"]
PY_Types["analysis/types.py<br/>Error and reference enums"]
end
RS_Types --> RE_Expr
RS_Types --> STMT
RP_Types --> RE_Expr
RP_Types --> STMT
RT_Types --> RE_Expr
RT_Types --> STMT
SCOPE --> REF
PS_Types --> PT_Types
PY_Types --> PT_Types
```

**Diagram sources**
- [types.rs](file://src/analysis/structure/types.rs#L1-L90)
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [expressions.rs](file://src/analysis/structure/expressions.rs#L1-L800)
- [statements.rs](file://src/analysis/structure/statements.rs#L1-L800)
- [scope.rs](file://src/analysis/scope.rs#L1-L257)
- [reference.rs](file://src/analysis/reference.rs#L1-L200)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L1-L571)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [types.py](file://python-port/dml_language_server/analysis/types.py#L1-L84)

**Section sources**
- [types.rs](file://src/analysis/structure/types.rs#L1-L90)
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L1-L571)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [types.py](file://python-port/dml_language_server/analysis/types.py#L1-L84)

## Core Components
- Semantic type model (Python): Provides a rich type hierarchy with primitives, structs, unions, enums, arrays, pointers, functions, templates, void, auto, and typedefs. Includes a type registry and analyzer.
- Parsing type model (Rust): Defines AST nodes for basic types (struct, layout, bitfields, typeof, sequence, hook) and composite type declarations.
- Template type system (Python/Rust): Resolves template parameters and concrete types, performs compatibility checks, and reports type errors.
- Expressions and statements (Rust): Use DMLType in constructs like casts, new expressions, sizeof, and function calls.

Key capabilities:
- Primitive types: signed/unsigned integers, floats, chars, booleans, and sized variants.
- Composite types: structs, unions, enums, arrays, pointers, functions.
- Generic/template types: template types with parameters and specializations.
- Type resolution: from identifiers to concrete types via registries and template resolvers.
- Compatibility checks: structural equivalence and parameter compatibility for function calls.

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L22-L35)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L37-L53)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L547-L571)
- [types.rs](file://src/analysis/parsing/types.rs#L477-L486)
- [types.rs](file://src/analysis/templating/types.rs#L8-L51)
- [expressions.rs](file://src/analysis/structure/expressions.rs#L350-L430)

## Architecture Overview
The type system integrates parsing, semantic modeling, and template resolution:

```mermaid
graph TB
Parser["Parser Types<br/>parsing/types.rs"] --> AST["AST Nodes<br/>BaseType, CTypeDecl"]
AST --> Semantics["Semantic Types<br/>structure/types.py"]
Semantics --> Registry["Type Registry<br/>TypeRegistry"]
Semantics --> Analyzer["Type Analyzer<br/>TypeAnalyzer"]
Registry --> Resolver["Template Resolver<br/>TemplateTypeResolver"]
Analyzer --> Checker["Template Checker<br/>TemplateTypeChecker"]
Resolver --> Checker
Expressions["Expressions<br/>structure/expressions.rs"] --> Semantics
Statements["Statements<br/>structure/statements.rs"] --> Semantics
Scopes["Scopes<br/>scope.rs"] --> References["References<br/>reference.rs"]
References --> Resolver
```

**Diagram sources**
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [expressions.rs](file://src/analysis/structure/expressions.rs#L350-L430)
- [statements.rs](file://src/analysis/structure/statements.rs#L1-L800)
- [scope.rs](file://src/analysis/scope.rs#L1-L257)
- [reference.rs](file://src/analysis/reference.rs#L96-L102)

## Detailed Component Analysis

### Type Hierarchy and Definitions
- Primitive types: Enumerated in Python with explicit sizes; Rust parsing supports identifiers and keywords for basic types.
- Struct/Union/Enum: Defined in Python with field validation and size computation helpers.
- Arrays and Pointers: Constructed from element/target types with computed sizes.
- Functions: Return type plus parameter list; name synthesized from parameters.
- Templates: Parameter lists and specializations; resolution produces concrete types.
- Void/Auto/Typedef: Special forms for void, inference, and aliasing.

```mermaid
classDiagram
class DMLType {
+ZeroSpan span
+TypeKind kind
+string name
+bool is_const
+bool is_volatile
+get_name() string
+is_primitive() bool
+is_pointer() bool
+is_array() bool
+is_function() bool
+get_size() int?
}
class PrimitiveTypeDecl {
+PrimitiveType primitive
+int? bit_width
+get_size() int?
}
class StructType {
+StructField[] fields
+bool is_packed
+add_field(field)
+find_field(name) StructField?
+get_size() int?
}
class UnionType {
+StructField[] fields
+get_size() int?
}
class EnumType {
+EnumValue[] values
+DMLType? underlying_type
+add_value(value)
+find_value(name) EnumValue?
+get_size() int?
}
class ArrayType {
+DMLType element_type
+Expression? size
+int? computed_size
+get_size() int?
}
class PointerType {
+DMLType target_type
+get_size() int?
}
class FunctionType {
+DMLType return_type
+DMLType[] parameter_types
+bool is_variadic
+get_size() int?
}
class TemplateType {
+string[] template_parameters
+Dict~string,DMLType~ specializations
+add_specialization(params, specialized_type)
}
class VoidType {
+get_size() int?
}
class AutoType {
+DMLType? inferred_type
+get_size() int?
}
class TypedefType {
+DMLType target_type
+get_size() int?
}
DMLType <|-- PrimitiveTypeDecl
DMLType <|-- StructType
DMLType <|-- UnionType
DMLType <|-- EnumType
DMLType <|-- ArrayType
DMLType <|-- PointerType
DMLType <|-- FunctionType
DMLType <|-- TemplateType
DMLType <|-- VoidType
DMLType <|-- AutoType
DMLType <|-- TypedefType
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L56-L344)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L22-L35)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L37-L53)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L547-L571)

### Generic and Template Type Handling
- Template types carry parameter lists and specializations.
- TemplateTypeResolver resolves identifiers against:
  - Provided template parameters
  - Global type registry
  - Built-in void handling with allow flag
- TemplateTypeChecker validates:
  - Type compatibility (structural equivalence)
  - Assignment compatibility
  - Parameter counts and compatibility for function calls

```mermaid
sequenceDiagram
participant Expr as "Expression"
participant Resolver as "TemplateTypeResolver"
participant Registry as "TypeRegistry"
participant Checker as "TemplateTypeChecker"
Expr->>Resolver : resolve_type(type_ref, location, scope, in_extern, hint, allow_void)
alt Template parameter match
Resolver-->>Expr : DMLResolvedType
else Registry lookup
Resolver->>Registry : find_type(name)
Registry-->>Resolver : DMLType or None
Resolver-->>Expr : DMLResolvedType or error
else Void disallowed
Resolver-->>Expr : error and dummy resolved type
end
Expr->>Checker : check_type_compatibility(expected, actual, span)
Checker-->>Expr : bool (compatible?)
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L21-L29)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)

### Type Inference and Compatibility
- Auto types represent inferred types; size depends on inferred type when available.
- Compatibility checks:
  - Structural equivalence for resolved types
  - Dummy types allowed to match for error recovery
  - Argument count and per-parameter compatibility for function calls
- Coercion: No explicit coercion logic is present; compatibility relies on structural equivalence and void allowance flags.

```mermaid
flowchart TD
Start(["Compatibility Check"]) --> Compare["Compare expected vs actual"]
Compare --> Equivalent{"Equivalent?"}
Equivalent --> |Yes| Pass["Return true"]
Equivalent --> |No| Dummy{"Any dummy?"}
Dummy --> |Yes| Pass
Dummy --> |No| Mismatch["Report TYPE_ERROR"]
Mismatch --> Fail["Return false"]
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L268)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L318-L331)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L268)

### Type Checking for Expressions, Assignments, and Function Calls
- CastExpression carries a DMLType target and an expression source; resolution occurs during expression construction.
- NewExpression uses a DMLType for allocation and optional size expression.
- FunctionCall stores a function expression and a vector of initializers; compatibility checked by TemplateTypeChecker.
- Assignment compatibility mirrors general compatibility checks.

```mermaid
sequenceDiagram
participant Parser as "Parser"
participant ExprBuilder as "Expression Builder"
participant Resolver as "TemplateTypeResolver"
participant Checker as "TemplateTypeChecker"
Parser->>ExprBuilder : Build Cast/New/Call
ExprBuilder->>Resolver : resolve_type(to_type)
Resolver-->>ExprBuilder : DMLResolvedType
ExprBuilder->>Checker : check_type_compatibility(target, source, span)
Checker-->>ExprBuilder : bool
ExprBuilder-->>Parser : Expression with DMLType
```

**Diagram sources**
- [expressions.rs](file://src/analysis/structure/expressions.rs#L350-L430)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L298)

**Section sources**
- [expressions.rs](file://src/analysis/structure/expressions.rs#L350-L430)
- [expressions.rs](file://src/analysis/structure/expressions.rs#L320-L347)
- [expressions.rs](file://src/analysis/structure/expressions.rs#L406-L430)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L298)

### Relationship Between Type Definitions and Semantic Representations
- Rust parsing types (BaseType, CTypeDecl) define AST nodes for type constructs.
- Python semantic types provide runtime type objects with rich metadata and analysis helpers.
- Template resolvers bridge AST identifiers to semantic types and produce resolved types for checking.

```mermaid
graph LR
P_Base["BaseType (Rust)"] --> S_Type["DMLType (Python)"]
P_CDecl["CTypeDecl (Rust)"] --> S_Type
S_Registry["TypeRegistry (Python)"] --> S_Type
S_Type --> S_Analyzer["TypeAnalyzer (Python)"]
S_Analyzer --> S_Checker["TemplateTypeChecker (Python)"]
```

**Diagram sources**
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L547-L571)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)

**Section sources**
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)

### Type Parameter Resolution and Safety Guarantees
- Template parameters override registry lookups during resolution.
- Errors are accumulated and surfaced as diagnostics; void is only allowed when explicitly permitted.
- Dummy resolved types prevent cascading failures and maintain forward progress.

```mermaid
flowchart TD
ResolveStart["Resolve Type"] --> ParamCheck{"In template params?"}
ParamCheck --> |Yes| ReturnParam["Return param type"]
ParamCheck --> |No| RegistryLookup["Lookup in registry"]
RegistryLookup --> Found{"Found?"}
Found --> |Yes| ReturnConcrete["Return concrete type"]
Found --> |No| VoidCheck{"Is 'void'?"}
VoidCheck --> |Yes| AllowVoid{"allow_void?"}
AllowVoid --> |Yes| ReturnVoid["Return void type"]
AllowVoid --> |No| ReportError["Report UNDEFINED_SYMBOL"]
VoidCheck --> |No| ReportError
ReportError --> Dummy["Return dummy resolved type"]
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L162-L221)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L162-L221)

## Dependency Analysis
- Rust parsing types feed into semantic types and expressions.
- Template resolvers depend on the type registry and produce resolved types consumed by the checker.
- Scopes and references connect type usage sites to definitions.

```mermaid
graph TB
RP["Rust Parsing Types"] --> RSem["Rust Semantic Types"]
RSem --> PySem["Python Semantic Types"]
PySem --> Reg["TypeRegistry"]
Reg --> Res["TemplateTypeResolver"]
Res --> Chk["TemplateTypeChecker"]
Refs["References"] --> Res
Scp["Scope"] --> Refs
```

**Diagram sources**
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.rs](file://src/analysis/structure/types.rs#L1-L90)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [reference.rs](file://src/analysis/reference.rs#L96-L102)
- [scope.rs](file://src/analysis/scope.rs#L1-L257)

**Section sources**
- [types.rs](file://src/analysis/parsing/types.rs#L477-L525)
- [types.rs](file://src/analysis/structure/types.rs#L1-L90)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [reference.rs](file://src/analysis/reference.rs#L96-L102)
- [scope.rs](file://src/analysis/scope.rs#L1-L257)

## Performance Considerations
- Type resolution uses dictionary lookups keyed by type names; ensure minimal redundant lookups by caching resolved types per scope.
- Size computations for aggregates are linear in field count; avoid repeated traversal by memoizing computed sizes.
- Template parameter resolution short-circuits registry lookups, reducing overhead for generic code paths.

## Troubleshooting Guide
Common issues and resolutions:
- Unknown type: Occurs when a type name is not found in the registry. Verify spelling and registration.
- Void used in disallowed context: Ensure allow_void flag is set appropriately for extern or specific constructs.
- Duplicate type/field names: Registering duplicates triggers duplicate symbol errors; rename or remove duplicates.
- Mismatched argument counts or types: TemplateTypeChecker reports argument count and per-parameter mismatches; align function signatures.

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L205-L221)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L276-L293)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L372-L383)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L458-L475)

## Conclusion
The DML type system combines robust Rust parsing types with a rich Python semantic model and template-driven resolution. It supports a comprehensive type hierarchy, template parameterization, and compatibility checking. While explicit coercion is not implemented, structural equivalence and careful error handling provide strong type safety guarantees across expressions, assignments, and function calls.