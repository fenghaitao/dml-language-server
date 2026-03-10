# Line Length Rules

<cite>
**Referenced Files in This Document**
- [linelength.rs](file://src/lint/rules/linelength.rs)
- [indentation.rs](file://src/lint/rules/indentation.rs)
- [mod.rs](file://src/lint/mod.rs)
- [break_func_call_open_paren.rs](file://src/lint/rules/tests/linelength/break_func_call_open_paren.rs)
- [break_conditional_expression.rs](file://src/lint/rules/tests/linelength/break_conditional_expression.rs)
- [break_method_output.rs](file://src/lint/rules/tests/linelength/break_method_output.rs)
- [break_before_binary_op.rs](file://src/lint/rules/tests/linelength/break_before_binary_op.rs)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json)
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
This document describes the line length rules subsystem that enforces readable, maintainable line formatting in DML code. It focuses on four targeted rules:
- break_func_call_open_paren: Enforces continuation indentation after an opening parenthesis for function/method calls and casts.
- break_conditional_expression: Enforces proper wrapping of ternary operators to improve readability.
- break_method_output: Enforces line-breaking before the arrow in method signatures with output parameters.
- break_before_binary_op: Enforces placing line breaks before binary operators rather than after.

It explains the underlying algorithms, configuration options, and integration with the broader linting pipeline. It also covers how these rules interact with the global maximum line length enforcement and editor auto-formatting workflows.

## Project Structure
The line length rules live under the linting subsystem and integrate with the broader lint configuration and rule instantiation framework.

```mermaid
graph TB
subgraph "Linting Core"
LintCfg["LintCfg<br/>configuration"]
CurrentRules["CurrentRules<br/>rule instances"]
begin_style_check["begin_style_check<br/>per-line checks"]
end
subgraph "Line Length Rules"
LL_RuleSet["LineLength Ruleset<br/>LL2, LL3, LL5, LL6"]
BreakBinary["break_before_binary_op"]
BreakCond["break_conditional_expression"]
BreakMethodOut["break_method_output"]
BreakFuncOpen["break_func_call_open_paren"]
end
subgraph "Related Rules"
LongLines["long_lines<br/>max_length"]
IndentParen["indent_paren_expr<br/>continuation alignment"]
IndentCont["indent_continuation_line"]
end
LintCfg --> CurrentRules
CurrentRules --> LL_RuleSet
LL_RuleSet --> BreakBinary
LL_RuleSet --> BreakCond
LL_RuleSet --> BreakMethodOut
LL_RuleSet --> BreakFuncOpen
begin_style_check --> LongLines
LL_RuleSet -. "uses shared indentation defaults" .-> IndentParen
LL_RuleSet -. "uses shared indentation defaults" .-> IndentCont
```

**Diagram sources**
- [mod.rs](file://src/lint/mod.rs#L62-L88)
- [linelength.rs](file://src/lint/rules/linelength.rs#L21-L346)
- [indentation.rs](file://src/lint/rules/indentation.rs#L64-L103)

**Section sources**
- [mod.rs](file://src/lint/mod.rs#L62-L88)
- [linelength.rs](file://src/lint/rules/linelength.rs#L21-L346)
- [indentation.rs](file://src/lint/rules/indentation.rs#L64-L103)

## Core Components
- break_before_binary_op (LL2): Detects when a binary expression is broken after the operator and reports a violation, requiring the break to occur before the operator.
- break_conditional_expression (LL3): Ensures proper wrapping of ternary expressions, preferring breaks before the ? and optionally before the : when needed.
- break_method_output (LL5): Requires breaking the method signature before the arrow when output parameters are present, ensuring consistent formatting.
- break_func_call_open_paren (LL6): Enforces continuation indentation immediately after an opening parenthesis for function calls, casts, and method signatures, using a configurable indentation level.

These rules are instantiated from the lint configuration and participate in the AST traversal and per-line checks.

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L21-L346)
- [mod.rs](file://src/lint/mod.rs#L62-L88)

## Architecture Overview
The linting pipeline loads the configuration, instantiates rules, traverses the AST to collect style violations, and performs per-line checks including maximum line length. The line length rules are invoked during AST traversal and rely on token ranges and indentation defaults.

```mermaid
sequenceDiagram
participant Config as "LintCfg"
participant Rules as "CurrentRules"
participant AST as "AST"
participant Checker as "begin_style_check"
participant LL as "LongLinesRule"
Config->>Rules : instantiate_rules(cfg)
AST->>Rules : style_check(acc, rules, AuxParams)
Rules->>Rules : invoke LL2/LL3/LL5/LL6 checks
Checker->>LL : check(row, line, acc)
LL-->>Checker : violations if line > max_length
Checker-->>AST : aggregated DMLStyleError[]
```

**Diagram sources**
- [mod.rs](file://src/lint/mod.rs#L245-L265)
- [indentation.rs](file://src/lint/rules/indentation.rs#L64-L92)

**Section sources**
- [mod.rs](file://src/lint/mod.rs#L245-L265)
- [indentation.rs](file://src/lint/rules/indentation.rs#L64-L92)

## Detailed Component Analysis

### break_before_binary_op (LL2)
Purpose: Prevents breaking binary expressions after the operator. Instead, the line break must occur before the operator.

Algorithm:
- Extract left operand, operator, and right operand ranges from a binary expression.
- Determine if the expression is broken across lines and whether there is a break immediately after the operator.
- Report a violation if both conditions are true.

Smart wrapping strategy:
- Prefer placing the operator at the end of the previous line to keep the continuation clean and readable.

```mermaid
flowchart TD
Start(["Check Binary Expression"]) --> GetRanges["Extract left, operator, right ranges"]
GetRanges --> CheckBroken["Is expression broken across lines?"]
CheckBroken --> |No| End(["No violation"])
CheckBroken --> |Yes| CheckAfterOp["Is there a break immediately after operator?"]
CheckAfterOp --> |No| End
CheckAfterOp --> |Yes| Violation["Report LL2 violation"]
Violation --> End
```

**Diagram sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L222-L274)

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L222-L274)
- [break_before_binary_op.rs](file://src/lint/rules/tests/linelength/break_before_binary_op.rs#L1-L60)

### break_conditional_expression (LL3)
Purpose: Enforce consistent wrapping of ternary expressions. Prefer breaking before the ? and optionally before the : when necessary.

Algorithm:
- Extract ranges for left, left_operation (?), middle, right_operation (:), and right.
- Check for breaks around the ? and : operators.
- Report violations when breaks occur after ? or after : without corresponding breaks before ?.

Smart wrapping strategy:
- Place the ? on its own line when continuing the expression.
- Optionally place the : on its own line for clarity in complex ternary chains.

```mermaid
flowchart TD
Start(["Check Ternary Expression"]) --> GetRanges["Extract left, ?, middle, :, right ranges"]
GetRanges --> CheckQAfter["Break after '?' present?"]
CheckQAfter --> |Yes| ViolationQ["Report LL3 violation for '?'"]
CheckQAfter --> |No| CheckColBefore["Break before ':' present?"]
CheckColBefore --> |Yes| CheckColAfter["Break after ':' present?"]
CheckColAfter --> |Yes| End(["No violation"])
CheckColAfter --> |No| ViolationCol["Report LL3 violation for ':'"]
CheckColBefore --> |No| CheckBoth["Break before '?' present?"]
CheckBoth --> |Yes| End
CheckBoth --> |No| ViolationCol2["Report LL3 violation for ':'"]
ViolationQ --> End
ViolationCol --> End
ViolationCol2 --> End
```

**Diagram sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L276-L345)

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L276-L345)
- [break_conditional_expression.rs](file://src/lint/rules/tests/linelength/break_conditional_expression.rs#L1-L85)

### break_method_output (LL5)
Purpose: Enforce breaking method signatures with output parameters before the arrow (->) to improve readability.

Algorithm:
- Build arguments from the method’s return clause.
- Compare the rows of the arrow and the return type.
- Report a violation if the arrow and return type are not on separate lines.

Smart wrapping strategy:
- Keep the method name and parameter list on the first line, move the arrow and return type to the next line.

```mermaid
flowchart TD
Start(["Check Method Output"]) --> HasReturns{"Has returns?"}
HasReturns --> |No| End(["No violation"])
HasReturns --> |Yes| SameLine{"Arrow and return type on same line?"}
SameLine --> |Yes| Violation["Report LL5 violation"]
SameLine --> |No| End
Violation --> End
```

**Diagram sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L21-L71)

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L21-L71)
- [break_method_output.rs](file://src/lint/rules/tests/linelength/break_method_output.rs#L1-L62)

### break_func_call_open_paren (LL6)
Purpose: Enforce continuation indentation immediately after an opening parenthesis for function calls, casts, and method signatures.

Algorithm:
- Filter tokens to exclude nested parenthesized expressions to avoid double counting.
- Determine if the first argument starts on a different line than the opening parenthesis.
- Compute the expected indentation for continuation lines based on the configured indentation level and nesting depth.
- Report violations when continuation lines are not aligned to the expected column.

Smart wrapping strategy:
- Place the first argument on the same line as the opening parenthesis when possible.
- Otherwise, align subsequent arguments to the expected continuation column.

```mermaid
flowchart TD
Start(["Check Function Call Open Paren"]) --> FilterTokens["Filter out nested parenthesized tokens"]
FilterTokens --> BrokenAfterLParen{"First arg on diff line than '('?"}
BrokenAfterLParen --> |No| End(["No violation"])
BrokenAfterLParen --> |Yes| CalcExpected["Compute expected continuation column"]
CalcExpected --> AlignCheck["Check each continuation line alignment"]
AlignCheck --> Violation["Report LL6 violation"]
AlignCheck --> End
```

**Diagram sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L73-L220)

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L73-L220)
- [break_func_call_open_paren.rs](file://src/lint/rules/tests/linelength/break_func_call_open_paren.rs#L1-L161)

### Configuration and Integration
- Configuration keys:
  - break_func_call_open_paren: accepts indentation_spaces to control continuation indentation.
  - break_conditional_expression: enables LL3.
  - break_method_output: enables LL5.
  - break_before_binary_op: enables LL2.
  - long_lines: controls maximum line length via max_length.
  - indent_size: sets the base indentation level used by various rules.

- Instantiation:
  - CurrentRules aggregates rule instances from LintCfg options.
  - begin_style_check runs per-line checks (including long_lines) and collects violations.

- Editor integration:
  - Example configuration demonstrates enabling all line-length-related rules and setting max_length and indentation_spaces.

**Section sources**
- [mod.rs](file://src/lint/mod.rs#L80-L184)
- [indentation.rs](file://src/lint/rules/indentation.rs#L60-L92)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json#L13-L25)

## Dependency Analysis
The line length rules depend on:
- AST node types for extracting token ranges (function calls, method signatures, binary expressions, ternary expressions).
- Shared indentation defaults (indentation_spaces) for continuation alignment.
- Global long_lines rule for maximum line length enforcement.

```mermaid
graph LR
Linelength["LineLength Rules"] --> ASTNodes["AST Nodes<br/>FunctionCall/Method/Binary/Ternary"]
Linelength --> IndentDefaults["Indentation Defaults<br/>indentation_spaces"]
Linelength --> LongLines["LongLinesRule<br/>max_length"]
Linelength --> CurrentRules["CurrentRules"]
CurrentRules --> LintCfg["LintCfg"]
```

**Diagram sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L1-L14)
- [mod.rs](file://src/lint/mod.rs#L62-L88)
- [indentation.rs](file://src/lint/rules/indentation.rs#L33-L62)

**Section sources**
- [linelength.rs](file://src/lint/rules/linelength.rs#L1-L14)
- [mod.rs](file://src/lint/mod.rs#L62-L88)
- [indentation.rs](file://src/lint/rules/indentation.rs#L33-L62)

## Performance Considerations
- Token filtering: The rules filter out nested parenthesized tokens to avoid redundant checks, reducing unnecessary computation.
- Early exits: Many checks return early when conditions are not met (e.g., same-line arguments, missing breaks).
- Per-line checks: LongLinesRule operates on each line independently, keeping memory usage linear with file size.
- Configuration-driven enablement: Disabling rules reduces overhead when not needed.

Recommendations:
- Keep indentation_spaces reasonable to minimize misalignment checks.
- Prefer enabling only necessary rules to reduce AST traversal cost.
- For very large files, consider incremental linting strategies if applicable.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Violations reported by LL2: Move the binary operator to the end of the previous line to avoid breaking after the operator.
- Violations reported by LL3: Place the ? and optionally the : on their own lines; avoid breaking after ? or after : without corresponding breaks before ?.
- Violations reported by LL5: Ensure the arrow and return type are on a separate line from the parameter list.
- Violations reported by LL6: Align continuation lines to the expected column computed from indentation_spaces and nesting depth.
- Editor auto-formatting: Enable the relevant rules in the lint configuration and ensure the editor invokes the formatter on save or on change.

Integration tips:
- Use the example lint configuration as a baseline and adjust max_length and indentation_spaces to match team standards.
- Combine line length rules with long_lines to enforce both structural wrapping and absolute length limits.

**Section sources**
- [break_before_binary_op.rs](file://src/lint/rules/tests/linelength/break_before_binary_op.rs#L1-L60)
- [break_conditional_expression.rs](file://src/lint/rules/tests/linelength/break_conditional_expression.rs#L1-L85)
- [break_method_output.rs](file://src/lint/rules/tests/linelength/break_method_output.rs#L1-L62)
- [break_func_call_open_paren.rs](file://src/lint/rules/tests/linelength/break_func_call_open_paren.rs#L1-L161)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json#L13-L25)

## Conclusion
The line length rules subsystem provides precise control over how long lines are wrapped in DML code. By enforcing consistent patterns for binary operators, ternary expressions, method output clauses, and function call continuations—and by integrating with global maximum length enforcement—they help maintain readability and consistency. Proper configuration and editor integration further streamline adoption in development workflows.