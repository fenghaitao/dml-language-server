# Template Methods

<cite>
**Referenced Files in This Document**
- [methods.rs](file://src/analysis/templating/methods.rs)
- [mod.rs](file://src/analysis/templating/mod.rs)
- [types.rs](file://src/analysis/templating/types.rs)
- [traits.rs](file://src/analysis/templating/traits.rs)
- [objects.rs](file://src/analysis/structure/objects.rs)
- [mod.rs](file://src/analysis/mod.rs)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py)
- [watchdog_timer.dml](file://example_files/watchdog_timer.dml)
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
This document explains how template method handling is implemented in the DML template processing system. It covers method resolution algorithms, parameter binding for templated methods, inheritance and override mechanisms, signature validation, overload resolution, and virtual method dispatch for templated constructs. It also provides concrete examples of method instantiation workflows, parameter substitution, and method resolution order, along with performance considerations and debugging techniques.

## Project Structure
The template method system spans both the Rust implementation under src/analysis/templating and a Python port under python-port/dml_language_server/analysis/templating. The Rust side focuses on type resolution, method declarations, and trait integration, while the Python port mirrors the core concepts for testing and prototyping.

```mermaid
graph TB
subgraph "Rust Implementation"
RS_Methods["src/analysis/templating/methods.rs"]
RS_Types["src/analysis/templating/types.rs"]
RS_Traits["src/analysis/templating/traits.rs"]
RS_StructObjects["src/analysis/structure/objects.rs"]
RS_AnalysisMod["src/analysis/mod.rs"]
end
subgraph "Python Port"
PY_Methods["python-port/.../templating/methods.py"]
PY_Types["python-port/.../templating/types.py"]
PY_Traits["python-port/.../templating/traits.py"]
end
RS_Methods --> RS_Types
RS_Methods --> RS_Traits
RS_Methods --> RS_StructObjects
RS_AnalysisMod --> RS_Methods
PY_Methods --> PY_Types
PY_Methods --> PY_Traits
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L1-L491)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [traits.rs](file://src/analysis/templating/traits.rs#L1-L677)
- [objects.rs](file://src/analysis/structure/objects.rs#L1-L800)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1259)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L1-L423)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L1-L372)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L1-L491)
- [mod.rs](file://src/analysis/templating/mod.rs#L1-L31)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [traits.rs](file://src/analysis/templating/traits.rs#L1-L677)
- [objects.rs](file://src/analysis/structure/objects.rs#L1-L800)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1259)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L1-L423)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L1-L372)

## Core Components
- Method argument representation and equivalence
- Method declaration model with abstract/concrete distinction
- Method reference union supporting trait methods and concrete methods
- Concrete method wrapper with default-call chaining
- Signature validation and override checking
- Trait-based method resolution and inheritance
- Type resolution for method parameters and return types

Key responsibilities:
- Normalize method argument types and detect inline vs typed arguments
- Build method signatures and enforce override compatibility
- Track method definitions and declarations across inheritance
- Integrate with traits for shared method resolution
- Provide type-safe evaluation of method return types

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L20-L115)
- [methods.rs](file://src/analysis/templating/methods.rs#L117-L163)
- [methods.rs](file://src/analysis/templating/methods.rs#L290-L346)
- [methods.rs](file://src/analysis/templating/methods.rs#L420-L491)
- [types.rs](file://src/analysis/templating/types.rs#L46-L72)

## Architecture Overview
Template method handling integrates with the broader analysis pipeline. Method declarations are evaluated during template processing, validated against trait constraints, and symbolized for lookup. The analysis module resolves references within method scopes and supports “default” dispatch for method chaining.

```mermaid
sequenceDiagram
participant Parser as "Parser"
participant Templating as "Templating Layer"
participant Traits as "Traits Module"
participant Analysis as "Analysis Engine"
participant Symbols as "Symbolizer"
Parser->>Templating : "Parse method declarations"
Templating->>Templating : "Evaluate method args and returns"
Templating->>Traits : "Register shared methods in traits"
Traits-->>Templating : "Trait method maps and overrides"
Templating->>Analysis : "Provide MethodDecl/MaybeAbstract"
Analysis->>Symbols : "Build method scopes and args"
Symbols-->>Analysis : "Symbol tables for lookup"
Analysis-->>Parser : "Resolved references and diagnostics"
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L62-L115)
- [traits.rs](file://src/analysis/templating/traits.rs#L378-L496)
- [mod.rs](file://src/analysis/mod.rs#L1675-L1874)

## Detailed Component Analysis

### Method Argument and Return Evaluation
- Method arguments are normalized into typed or inline forms. Typed arguments are resolved via type evaluation, with checks against anonymous struct types.
- Return types are evaluated similarly, generating resolved types or dummy placeholders for error recovery.

```mermaid
flowchart TD
Start(["Evaluate Method Args"]) --> Iterate["Iterate Arguments"]
Iterate --> IsTyped{"Typed?"}
IsTyped --> |Yes| EvalType["eval_type_simple()"]
EvalType --> CheckAnon{"Anonymous struct?"}
CheckAnon --> |Yes| ReportErr["Report error and mark as dummy"]
CheckAnon --> |No| KeepType["Use resolved type"]
IsTyped --> |No| Inline["Inline argument"]
KeepType --> Collect["Collect typed arg"]
ReportErr --> Collect
Inline --> Collect
Collect --> End(["Return Vec<DMLMethodArg>"])
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L62-L93)
- [types.rs](file://src/analysis/templating/types.rs#L80-L92)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L62-L115)
- [types.rs](file://src/analysis/templating/types.rs#L80-L92)

### Method Declaration Model and Abstractness
- MethodDecl encapsulates name, modifiers, independence, default flag, throws, arguments, returns, body, and span.
- Abstractness is derived from whether the body is empty; concrete methods carry executable bodies.

```mermaid
classDiagram
class MethodDecl {
+string name
+MethodModifier modifier
+bool independent
+bool default
+bool throws
+Vec~DMLMethodArg~ method_args
+Vec~DMLResolvedType~ return_types
+Statement body
+ZeroSpan span
+is_abstract() bool
+fully_typed() bool
+check_override(overridden, report)
}
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L117-L163)
- [methods.rs](file://src/analysis/templating/methods.rs#L137-L142)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L117-L163)
- [methods.rs](file://src/analysis/templating/methods.rs#L137-L142)

### Method Reference and Dispatch
- DMLMethodRef unions trait methods and concrete methods, enabling polymorphic dispatch.
- Concrete methods can chain to default calls, supporting “default” keyword resolution within method bodies.

```mermaid
classDiagram
class DMLMethodRef {
<<union>>
+get_decl() MethodDecl
+get_default() Option~DMLMethodRef~
+get_all_defs() Vec~ZeroSpan~
+get_all_decls() Vec~ZeroSpan~
+get_base() MethodDecl
}
class DMLConcreteMethod {
+MethodDecl decl
+Option~DMLMethodRef~ default_call
+get_all_defs() Vec~ZeroSpan~
+get_all_decls() Vec~ZeroSpan~
}
DMLMethodRef <|-- DMLConcreteMethod
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L290-L346)
- [methods.rs](file://src/analysis/templating/methods.rs#L420-L491)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L290-L346)
- [methods.rs](file://src/analysis/templating/methods.rs#L420-L491)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1120)

### Override Validation and Compatibility
- Overriding enforces throws compatibility, argument count/type parity, and return type compatibility.
- Equivalent argument and return types are checked using structural equivalence.

```mermaid
flowchart TD
Start(["Override Check"]) --> Throws["Compare throws()"]
Throws --> |Mismatch| ThrowErr["Report error"]
Throws --> |Match| ArgLen["Compare arg lengths"]
ArgLen --> |Mismatch| ArgErr["Report error"]
ArgLen --> |Match| ArgEq["Compare arg types equivalent()"]
ArgEq --> |Mismatch| ArgErr
ArgEq --> RetLen["Compare return lengths"]
RetLen --> |Mismatch| RetErr["Report error"]
RetLen --> |Match| RetEq["Compare return types equivalent()"]
RetEq --> |Mismatch| RetErr
RetEq --> Done(["Override OK"])
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L178-L252)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L178-L252)

### Trait-Based Method Resolution and Inheritance
- Traits aggregate shared method declarations and enforce override soundness across ancestors.
- Merging implementation maps detects ambiguous or conflicting definitions and reports diagnostics.

```mermaid
sequenceDiagram
participant Trait as "DMLTrait"
participant Parents as "Parent Traits"
participant Report as "Error Reporter"
Trait->>Parents : "Collect impl maps"
Parents-->>Trait : "Impl maps"
Trait->>Trait : "Merge maps and detect conflicts"
alt Ambiguous or conflicting
Trait->>Report : "Emit diagnostics"
end
Trait-->>Trait : "Build ancestor_map and reserved_symbols"
```

**Diagram sources**
- [traits.rs](file://src/analysis/templating/traits.rs#L500-L624)

**Section sources**
- [traits.rs](file://src/analysis/templating/traits.rs#L500-L624)

### Python Port: Method Signatures and Overload Resolution
- The Python port models method signatures with name, parameter types, return type, and modifiers.
- Overload resolution selects best match by exact or compatible parameter type matching.

```mermaid
classDiagram
class MethodSignature {
+string name
+Vec~DMLResolvedType~ parameter_types
+DMLResolvedType return_type
+Set~MethodModifier~ modifiers
+matches(other) bool
+is_compatible_override(base) bool
+get_signature_string() string
}
class MethodOverload {
+MethodDeclaration[] methods
+add_method(method)
+find_best_match(arg_types) MethodDeclaration
+has_abstract_methods() bool
}
class MethodAnalyzer {
+register_method(method)
+find_method(name, arg_types) MethodDeclaration
+check_method_call(name, arg_types, call_span) MethodDeclaration
+validate_method_overrides(object_name)
+get_errors() List
}
```

**Diagram sources**
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L37-L85)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L113-L162)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)

**Section sources**
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L37-L85)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L113-L162)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)

### Example: Method Instantiation Workflow in DML
- Example device file demonstrates method declarations inside registers, including typed parameters and return types.
- The analysis pipeline evaluates these methods during template processing and symbolization.

```mermaid
sequenceDiagram
participant DML as "watchdog_timer.dml"
participant Parser as "Parser"
participant Templating as "Templating Layer"
participant Types as "Type Resolver"
participant Analyzer as "Analyzer"
DML->>Parser : "Parse register methods"
Parser->>Templating : "Create Method AST"
Templating->>Types : "Resolve parameter and return types"
Types-->>Templating : "Resolved types"
Templating->>Analyzer : "Register method declarations"
Analyzer-->>DML : "Validation and diagnostics"
```

**Diagram sources**
- [watchdog_timer.dml](file://example_files/watchdog_timer.dml#L79-L92)

**Section sources**
- [watchdog_timer.dml](file://example_files/watchdog_timer.dml#L79-L92)

## Dependency Analysis
- Method evaluation depends on type resolution for arguments and returns.
- Method references depend on trait definitions for shared methods and on concrete method wrappers for default dispatch.
- The analysis module depends on method references for symbolization and scope resolution.

```mermaid
graph TB
Methods["methods.rs"] --> Types["types.rs"]
Methods --> Traits["traits.rs"]
Methods --> Objects["structure/objects.rs"]
Analysis["analysis/mod.rs"] --> Methods
PyMethods["templating/methods.py"] --> PyTypes["templating/types.py"]
PyMethods --> PyTraits["templating/traits.py"]
```

**Diagram sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L1-L491)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [traits.rs](file://src/analysis/templating/traits.rs#L1-L677)
- [objects.rs](file://src/analysis/structure/objects.rs#L1-L800)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1259)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L1-L423)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L1-L372)

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L1-L491)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [traits.rs](file://src/analysis/templating/traits.rs#L1-L677)
- [objects.rs](file://src/analysis/structure/objects.rs#L1-L800)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1259)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L1-L423)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L1-L372)

## Performance Considerations
- Method signature matching: Linear scan over overload sets; consider indexing by name and arity for large overload sets.
- Type equivalence: Current implementation uses a conservative equivalence that avoids false negatives; refine to precise structural equality to reduce ambiguity.
- Trait merging: O(P) per trait for P parents; cache merged maps to avoid recomputation.
- Symbolization: Method scope creation and argument symbolization occur per method; batch operations where possible.
- Dummy types: Used for error recovery; minimize unnecessary dummy allocations and comparisons.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Anonymous struct in argument or return type: Detected during type evaluation; fix by using named types or removing anonymous structs.
- Override mismatch: Throws compatibility, argument count/type, or return type mismatches trigger errors; align signatures with base.
- Conflicting trait definitions: Ambiguous or conflicting method definitions reported with related spans; choose appropriate inheritance order or remove duplicates.
- “default” keyword resolution: Ensure a default call exists; otherwise “default” references are unresolved.
- Missing method signatures in Python port: Overload resolution prefers exact matches; ensure argument counts and types match exactly.

**Section sources**
- [methods.rs](file://src/analysis/templating/methods.rs#L62-L115)
- [methods.rs](file://src/analysis/templating/methods.rs#L178-L252)
- [traits.rs](file://src/analysis/templating/traits.rs#L580-L621)
- [mod.rs](file://src/analysis/mod.rs#L1060-L1120)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L121-L157)

## Conclusion
The DML template method system provides robust support for method declaration, parameter binding, override validation, and trait-based inheritance. The Rust implementation offers precise type resolution and symbolization, while the Python port mirrors core concepts for development and testing. By leveraging method references, trait maps, and strict override checks, the system ensures reliable method resolution and dispatch across templated constructs.