# Template Types

<cite>
**Referenced Files in This Document**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py)
- [types.rs](file://src/analysis/templating/types.rs)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py)
- [types.rs](file://src/analysis/structure/types.rs)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py)
- [methods.rs](file://src/analysis/templating/methods.rs)
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py)
- [objects.rs](file://src/analysis/templating/objects.rs)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py)
- [traits.rs](file://src/analysis/templating/traits.rs)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py)
- [topology.rs](file://src/analysis/templating/topology.rs)
- [__init__.py](file://python-port/dml_language_server/analysis/templating/__init__.py)
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
This document explains template type resolution and type system integration in the DML language server. It focuses on how template types are represented, instantiated, and validated, how generic type parameters are bound, and how type constraints are enforced for templated constructs. It also covers type resolution processes, compatibility checks, and inference for template parameters, with concrete examples and diagrams that map to the actual Python and Rust implementations.

## Project Structure
The template type system spans both Python and Rust implementations:
- Python port: analysis/templating/* provides Python equivalents of the Rust modules, including type resolution, method analysis, object resolution, traits, and topology.
- Rust implementation: src/analysis/templating/* provides the canonical implementation of template analysis, including types, methods, objects, traits, and topology.

```mermaid
graph TB
subgraph "Python Implementation"
PY_TYPES["templating/types.py"]
PY_METHODS["templating/methods.py"]
PY_OBJECTS["templating/objects.py"]
PY_TRAITS["templating/traits.py"]
PY_TOPO["templating/topology.py"]
PY_INIT["templating/__init__.py"]
end
subgraph "Rust Implementation"
RS_TYPES["templating/types.rs"]
RS_METHODS["templating/methods.rs"]
RS_OBJECTS["templating/objects.rs"]
RS_TRAITS["templating/traits.rs"]
RS_TOPO["templating/topology.rs"]
end
PY_TYPES --> RS_TYPES
PY_METHODS --> RS_METHODS
PY_OBJECTS --> RS_OBJECTS
PY_TRAITS --> RS_TRAITS
PY_TOPO --> RS_TOPO
PY_INIT --> PY_TYPES
PY_INIT --> PY_METHODS
PY_INIT --> PY_OBJECTS
PY_INIT --> PY_TRAITS
PY_INIT --> PY_TOPO
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L1-L357)
- [types.rs](file://src/analysis/templating/types.rs#L1-L93)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L1-L423)
- [methods.rs](file://src/analysis/templating/methods.rs#L1-L491)
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L1-L407)
- [objects.rs](file://src/analysis/templating/objects.rs#L1-L800)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L1-L372)
- [traits.rs](file://src/analysis/templating/traits.rs#L1-L677)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L1-L450)
- [topology.rs](file://src/analysis/templating/topology.rs#L1-L853)

**Section sources**
- [__init__.py](file://python-port/dml_language_server/analysis/templating/__init__.py#L1-L61)

## Core Components
This section introduces the central types and resolvers used for template type resolution and integration with the broader type system.

- TemplateTypeKind: Enumerates kinds of template types (concrete, abstract, parametric, specialized, resolved, dummy).
- DMLBaseType/DMLStructType/DMLConcreteType/DMLResolvedType: Represent base types, struct types, concrete resolved types, and resolved types (including dummy fallbacks).
- TemplateTypeResolver: Resolves type references to concrete types using a TypeRegistry and template parameters.
- TemplateTypeChecker: Performs compatibility checks between expected and actual types.
- TypeRegistry: Manages built-in and user-defined types and validates type existence.
- DMLType family: Defines the broader type system (primitives, structs, arrays, functions, templates, etc.) used by template resolution.

Key responsibilities:
- Template instantiation: Binding template parameters to concrete types and validating constraints.
- Type compatibility: Ensuring argument and return types match expectations.
- Error handling: Recording diagnostics for undefined symbols, type mismatches, and circular dependencies.

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L21-L357)
- [types.rs](file://src/analysis/templating/types.rs#L8-L93)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L22-L571)
- [types.rs](file://src/analysis/structure/types.rs#L9-L90)

## Architecture Overview
The template type system integrates with the broader type system and analysis pipeline. The following diagram maps the relationships among core modules:

```mermaid
graph TB
subgraph "Type System"
TR["TypeRegistry<br/>structure/types.py"]
DT["DMLType family<br/>structure/types.py"]
end
subgraph "Template Resolution"
R["TemplateTypeResolver<br/>templating/types.py"]
C["TemplateTypeChecker<br/>templating/types.py"]
ET["eval_type / eval_type_simple<br/>templating/types.py"]
end
subgraph "Template Analysis"
MA["MethodAnalyzer<br/>templating/methods.py"]
OR["ObjectResolver<br/>templating/objects.py"]
TA["TopologyAnalyzer<br/>templating/topology.py"]
TRAIT["TraitResolver<br/>templating/traits.py"]
end
TR --> R
DT --> R
R --> ET
R --> C
MA --> R
OR --> R
TA --> OR
TRAIT --> OR
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L357)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L217-L375)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L270-L398)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L180-L335)

## Detailed Component Analysis

### Template Type Resolver and Checker
The resolver and checker coordinate type resolution and compatibility checks for template contexts.

```mermaid
classDiagram
class TemplateTypeResolver {
+TypeRegistry type_registry
+Dict~str,DMLResolvedType~ template_parameters
+DMLError[] errors
+set_template_parameters(params)
+resolve_type(type_ref,location_span,scope_context,in_extern,typename_hint,allow_void) DMLResolvedType
+resolve_type_simple(type_ref,location_span,scope_context) DMLResolvedType
+create_struct_type(name,span) DMLResolvedType
+create_base_type(name,span) DMLResolvedType
+get_errors() DMLError[]
}
class TemplateTypeChecker {
+TemplateTypeResolver resolver
+DMLError[] errors
+check_type_compatibility(expected,actual,span) bool
+check_assignment_compatibility(target,source,span) bool
+check_parameter_compatibility(param_types,arg_types,span) bool
+get_errors() DMLError[]
}
class TypeRegistry {
+Dict~str,DMLType~ types
+register_type(type_decl)
+find_type(name) DMLType
+get_primitive_type(primitive) PrimitiveTypeDecl
+create_array_type(element_type,size) ArrayType
+create_pointer_type(target_type) PointerType
+create_function_type(return_type,parameter_types) FunctionType
+get_all_types() DMLType[]
+get_errors() DMLError[]
}
TemplateTypeResolver --> TypeRegistry : "uses"
TemplateTypeChecker --> TemplateTypeResolver : "depends on"
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L150-L242)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L244-L298)
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L346-L434)

### Type Evaluation and Compatibility Checking
The evaluation functions convert type ASTs into resolved types and struct dependencies, while the checker enforces compatibility.

```mermaid
sequenceDiagram
participant Client as "Caller"
participant Resolver as "TemplateTypeResolver"
participant Registry as "TypeRegistry"
participant Checker as "TemplateTypeChecker"
Client->>Resolver : resolve_type(ast, location_span, scope_context, in_extern, typename_hint, allow_void)
Resolver->>Registry : find_type(ast.name)
alt Found in registry
Registry-->>Resolver : DMLType
Resolver->>Resolver : Convert to DMLConcreteType/DMLResolvedType
Resolver-->>Client : DMLResolvedType
else Not found
Resolver->>Resolver : Check template parameters
alt Parameter exists
Resolver-->>Client : DMLResolvedType from template_parameters
else Not found
Resolver->>Resolver : Create dummy type
Resolver-->>Client : DMLResolvedType.dummy(span)
end
end
Client->>Checker : check_type_compatibility(expected, actual, span)
Checker->>Checker : Compare names/equivalence
alt Compatible
Checker-->>Client : True
else Incompatible
Checker->>Checker : Record DMLError
Checker-->>Client : False
end
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L162-L226)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L294)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L300-L329)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L251-L294)

### Method Signature Resolution and Overload Matching
Methods in templates maintain signatures and support overload resolution and override compatibility checks.

```mermaid
classDiagram
class MethodSignature {
+string name
+DMLResolvedType[] parameter_types
+DMLResolvedType return_type
+Set~MethodModifier~ modifiers
+matches(other) bool
+is_compatible_override(base_signature) bool
+get_signature_string() string
}
class MethodDeclaration {
+ZeroSpan span
+DMLString name
+MethodSignature signature
+Optional~BlockStatement~ body
+MethodKind kind
+bool is_abstract
+bool is_overridable
+Optional~string~ declaring_object
+is_concrete() bool
+requires_implementation() bool
+can_be_overridden() bool
}
class MethodOverload {
+MethodDeclaration[] methods
+add_method(method)
+find_best_match(arg_types) MethodDeclaration
+has_abstract_methods() bool
}
class MethodAnalyzer {
+TemplateTypeResolver type_resolver
+TemplateTypeChecker type_checker
+MethodRegistry method_registry
+DMLError[] errors
+SymbolReference[] references
+analyze_method(method, declaring_object) MethodDeclaration
+check_method_call(name, arg_types, call_span) MethodDeclaration
+validate_method_overrides(object_name)
+get_method_signature(name) MethodSignature[]
+get_errors() DMLError[]
+get_references() SymbolReference[]
}
MethodAnalyzer --> MethodSignature : "creates"
MethodAnalyzer --> MethodOverload : "manages"
```

**Diagram sources**
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L36-L163)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L164-L240)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)

**Section sources**
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L36-L163)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L164-L240)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)

### Object Resolution and Template Application
Objects in templates are composed by applying templates, merging methods, and resolving child objects.

```mermaid
sequenceDiagram
participant Resolver as "ObjectResolver"
participant Template as "Template"
participant Instance as "TemplateInstance"
participant Composite as "DMLCompositeObject"
participant Child as "Child Object"
Resolver->>Resolver : resolve_object(obj, context_path)
Resolver->>Composite : create DMLCompositeObject(obj)
loop For each template_name in obj.templates
Resolver->>Template : lookup template_registry[template_name]
alt Template found
Resolver->>Instance : _instantiate_template(template, obj.span)
Instance->>Composite : apply_template(instance)
Composite->>Composite : Merge methods and children
else Template not found
Resolver->>Resolver : Record DMLError
end
end
loop For each child in obj.children
alt child is Method
Resolver->>Composite : resolved_methods[child.name] = analyze_method(...)
else child is object
Resolver->>Child : resolve_object(child, object_path)
Child-->>Resolver : resolved child
Resolver->>Composite : resolved_children.append(child)
end
end
Composite->>Resolver : get_final_object()
Resolver-->>Client : DMLResolvedObject
```

**Diagram sources**
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L217-L322)

**Section sources**
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L217-L322)

### Trait Constraints and Implementation Checking
Traits define requirements and default implementations; instances validate completeness and compatibility.

```mermaid
classDiagram
class TraitDefinition {
+DMLString name
+TraitKind kind
+ZeroSpan span
+TraitRequirement[] requirements
+Dict~string,MethodDeclaration~ default_implementations
+string[] supertrait_constraints
+string[] type_parameters
+add_requirement(requirement)
+add_default_implementation(method)
+get_requirement(name) TraitRequirement
+has_default_implementation(name) bool
}
class TraitInstance {
+TraitDefinition trait_def
+string object_name
+ZeroSpan span
+Dict~string,TraitImplementation~ implementations
+TraitRequirement[] missing_implementations
+DMLError[] constraint_violations
+add_implementation(impl)
+check_completeness() DMLError[]
+is_complete() bool
}
class TraitResolver {
+Dict~string,TraitDefinition~ trait_definitions
+TraitInstance[] trait_instances
+DMLError[] errors
+SymbolReference[] references
+register_trait(trait_def)
+apply_trait(trait_name, target_object, span) TraitInstance
+check_trait_constraints(instance) DMLError[]
+resolve_trait_hierarchy(trait_name) string[]
+check_trait_compatibility(trait1, trait2) bool
+get_trait_requirements(trait_name) TraitRequirement[]
+get_errors() DMLError[]
+get_references() SymbolReference[]
}
TraitResolver --> TraitDefinition : "manages"
TraitResolver --> TraitInstance : "creates"
```

**Diagram sources**
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L67-L178)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L180-L335)

**Section sources**
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L67-L178)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L180-L335)

### Template Ranking and Dependency Ordering
Topology analysis computes template ranks and ordering to ensure deterministic instantiation.

```mermaid
flowchart TD
Start(["Start"]) --> AddTemplates["Add templates to graph"]
AddTemplates --> ExtractDeps["Extract dependencies from templates and objects"]
ExtractDeps --> DetectCycles["Detect circular dependencies"]
DetectCycles --> HasCycle{"Has cycles?"}
HasCycle --> |Yes| ReportErrors["Report circular dependency errors"]
HasCycle --> |No| ComputeRanks["Compute ranks based on dependencies"]
ComputeRanks --> TopoSort["Topological sort for instantiation order"]
TopoSort --> End(["End"])
ReportErrors --> End
```

**Diagram sources**
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L270-L398)

**Section sources**
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L270-L398)

## Dependency Analysis
This section examines how template types relate to the broader type system and how dependencies propagate across modules.

```mermaid
graph TB
subgraph "Type System Core"
PRIM["PrimitiveType/TypeKind<br/>structure/types.py"]
ARR["ArrayType/PointerType/FunctionType<br/>structure/types.py"]
REG["TypeRegistry<br/>structure/types.py"]
end
subgraph "Template Types"
K["TemplateTypeKind<br/>templating/types.py"]
RT["DMLResolvedType/DMLConcreteType<br/>templating/types.py"]
RES["TemplateTypeResolver<br/>templating/types.py"]
CHK["TemplateTypeChecker<br/>templating/types.py"]
end
subgraph "Integration"
OBJ["ObjectResolver<br/>templating/objects.py"]
MTH["MethodAnalyzer<br/>templating/methods.py"]
TRAIT["TraitResolver<br/>templating/traits.py"]
TOP["TopologyAnalyzer<br/>templating/topology.py"]
end
PRIM --> REG
ARR --> REG
REG --> RES
RES --> RT
RES --> CHK
RES --> OBJ
RES --> MTH
RES --> TRAIT
TOP --> OBJ
```

**Diagram sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L22-L571)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L21-L357)
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L217-L375)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L180-L335)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L270-L398)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/structure/types.py#L22-L571)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L21-L357)
- [objects.py](file://python-port/dml_language_server/analysis/templating/objects.py#L217-L375)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L242-L374)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L180-L335)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L270-L398)

## Performance Considerations
- Early termination on unknown types: The resolver returns dummy types for undefined symbols to avoid cascading errors and to keep analysis fast.
- Minimal equivalence checks: Compatibility checks rely on name equivalence and dummy-type allowances to reduce overhead.
- Caching in object resolution: ObjectResolver caches resolved objects keyed by path to avoid recomputation.
- Topological sorting: TopologyAnalyzer uses efficient algorithms (DFS-based cycle detection and topological sort) to compute ranks and ordering.
- Lazy trait processing: TraitResolver registers definitions and performs checks on demand to minimize work.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and debugging techniques for template type problems:

- Unknown type or symbol:
  - Symptom: Type resolution returns a dummy type and records an undefined symbol error.
  - Action: Verify the type name exists in the TypeRegistry or is provided via template parameters.
  - Evidence: [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L214-L221)

- Type mismatch:
  - Symptom: Compatibility check fails and records a type error.
  - Action: Ensure argument and return types match expected names or relax constraints intentionally.
  - Evidence: [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L262-L268)

- Circular template dependency:
  - Symptom: Topology analysis reports a cycle and marks templates as incompatible.
  - Action: Break the cycle by adjusting template inheritance or usage.
  - Evidence: [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L140-L183)

- Missing trait implementation:
  - Symptom: Trait instance reports missing implementations or constraint violations.
  - Action: Implement required methods/parameters or provide defaults.
  - Evidence: [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L157-L174)

- Method override conflicts:
  - Symptom: Overridden method signatures are incompatible.
  - Action: Align parameter types and return types with base signatures.
  - Evidence: [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L194-L201)

**Section sources**
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L214-L221)
- [types.py](file://python-port/dml_language_server/analysis/templating/types.py#L262-L268)
- [topology.py](file://python-port/dml_language_server/analysis/templating/topology.py#L140-L183)
- [traits.py](file://python-port/dml_language_server/analysis/templating/traits.py#L157-L174)
- [methods.py](file://python-port/dml_language_server/analysis/templating/methods.py#L194-L201)

## Conclusion
The template type system integrates tightly with the broader DML type system to support template instantiation, parameter binding, and constraint validation. The Python and Rust implementations mirror each other closely, ensuring consistent behavior across platforms. By leveraging resolvers, checkers, analyzers, and topology tools, the system provides robust type resolution, compatibility enforcement, and error reporting for templated constructs.