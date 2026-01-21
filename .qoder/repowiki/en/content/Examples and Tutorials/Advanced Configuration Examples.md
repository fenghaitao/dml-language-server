# Advanced Configuration Examples

<cite>
**Referenced Files in This Document**
- [config.py](file://python-port/dml_language_server/config.py)
- [config.rs](file://src/config.rs)
- [lint_mod.rs](file://src/lint/mod.rs)
- [lint_rules_mod.rs](file://src/lint/rules/mod.rs)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json)
- [lint_config.json](file://python-port/examples/lint_config.json)
- [main.py](file://python-port/dml_language_server/mcp/main.py)
- [mcp_mod.rs](file://src/mcp/mod.rs)
- [vfs_mod.rs](file://src/vfs/mod.rs)
- [work_pool.rs](file://src/actions/work_pool.rs)
- [concurrency.rs](file://src/concurrency.rs)
- [file_management.py](file://python-port/dml_language_server/file_management.py)
- [sample_device.dml](file://python-port/examples/sample_device.dml)
- [utility.dml](file://python-port/examples/utility.dml)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md)
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
10. [Appendices](#appendices)

## Introduction
This document provides advanced configuration examples for complex DML projects and specialized use cases. It covers:
- Comprehensive lint rule configuration with custom parameters, enabling/disabling rules, and per-file overrides
- Multi-device analysis setup for large-scale DML projects with device interdependencies
- MCP server configuration for AI-assisted development workflows
- Advanced VFS configuration for handling large codebases and remote file systems
- Examples of custom analysis tool integration and extended lint rule development
- Performance optimization configurations including parallel processing and memory management

## Project Structure
The DML Language Server supports both a Python port and a native Rust implementation. Configuration is centralized in dedicated modules:
- Python port: configuration, linting engine, MCP server, and file management utilities
- Native Rust: configuration, linting rules, MCP server, VFS, and concurrency primitives

```mermaid
graph TB
subgraph "Python Port"
PY_CFG["config.py<br/>Configuration"]
PY_LINT["lint/__init__.py<br/>Lint Engine"]
PY_MCP["mcp/main.py<br/>MCP Server"]
PY_FM["file_management.py<br/>File Manager"]
end
subgraph "Rust Implementation"
RS_CFG["config.rs<br/>Configuration"]
RS_LINT["lint/mod.rs<br/>Lint Parser & Rules"]
RS_VFS["vfs/mod.rs<br/>Virtual File System"]
RS_MCP["mcp/mod.rs<br/>MCP Server"]
RS_WORK["actions/work_pool.rs<br/>Parallel Work Pool"]
RS_CONC["concurrency.rs<br/>Concurrency Utilities"]
end
PY_CFG --> PY_LINT
PY_CFG --> PY_FM
PY_MCP --> PY_CFG
RS_CFG --> RS_LINT
RS_CFG --> RS_VFS
RS_MCP --> RS_CFG
RS_WORK --> RS_LINT
RS_CONC --> RS_WORK
```

**Diagram sources**
- [config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [config.rs](file://src/config.rs#L120-L319)
- [lint_mod.rs](file://src/lint/mod.rs#L37-L126)
- [vfs_mod.rs](file://src/vfs/mod.rs#L29-L800)
- [mcp_mod.rs](file://src/mcp/mod.rs#L1-L54)
- [work_pool.rs](file://src/actions/work_pool.rs#L22-L104)
- [concurrency.rs](file://src/concurrency.rs#L22-L103)

**Section sources**
- [config.py](file://python-port/dml_language_server/config.py#L1-L311)
- [config.rs](file://src/config.rs#L1-L319)

## Core Components
This section outlines the core configuration components and their roles in advanced scenarios.

- Configuration Management
  - Python port: centralizes compile commands, lint configuration, and initialization options
  - Rust implementation: defines configurable behavior for linting, device contexts, and analysis retention

- Linting Engine
  - Python port: rule registration, configuration application, and per-rule customization
  - Rust implementation: structured lint configuration with per-rule options and per-line overrides

- MCP Server
  - Python port: stdio-based JSON-RPC handler for AI-assisted workflows
  - Rust implementation: modular MCP server with tools, templates, and generation capabilities

- Virtual File System (VFS)
  - Rust implementation: efficient caching, change tracking, and user data association for large codebases

- Concurrency and Parallelism
  - Rust work pool: controlled parallel execution with capacity limits and warnings
  - Concurrency utilities: job tracking and deterministic teardown

**Section sources**
- [config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [config.rs](file://src/config.rs#L120-L319)
- [lint_mod.rs](file://src/lint/mod.rs#L37-L126)
- [main.py](file://python-port/dml_language_server/mcp/main.py#L22-L166)
- [mcp_mod.rs](file://src/mcp/mod.rs#L1-L54)
- [vfs_mod.rs](file://src/vfs/mod.rs#L180-L800)
- [work_pool.rs](file://src/actions/work_pool.rs#L22-L104)
- [concurrency.rs](file://src/concurrency.rs#L22-L103)

## Architecture Overview
The advanced configuration architecture integrates configuration loading, lint rule instantiation, MCP tool execution, and VFS-backed analysis for large-scale DML projects.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Config as "Config Loader"
participant Lint as "Lint Engine"
participant MCP as "MCP Server"
participant VFS as "VFS"
Client->>Config : Load compile commands / lint config
Config-->>Client : Configuration ready
Client->>Lint : Apply lint rules with overrides
Lint-->>Client : Diagnostics with per-line annotations
Client->>MCP : Request tool execution
MCP->>VFS : Access files and templates
MCP-->>Client : Generated DML code
Note over Client,VFS : Large codebase handled via VFS caching and change tracking
```

**Diagram sources**
- [config.py](file://python-port/dml_language_server/config.py#L131-L287)
- [lint_mod.rs](file://src/lint/mod.rs#L181-L229)
- [main.py](file://python-port/dml_language_server/mcp/main.py#L142-L162)
- [vfs_mod.rs](file://src/vfs/mod.rs#L457-L530)

## Detailed Component Analysis

### Advanced Lint Configuration Examples
This section demonstrates comprehensive lint rule configuration with custom parameters, enabling/disabling rules, and per-file overrides.

- Python Port Lint Configuration
  - Example configuration enables specific rules and applies per-rule settings
  - Supports rule-level severity and custom parameters (e.g., indentation size)

- Rust Lint Configuration
  - Structured configuration with per-rule options (e.g., spacing, indentation, long lines)
  - Per-line and per-file lint annotations for targeted rule suppression
  - Unknown field detection and default configuration behavior

```mermaid
flowchart TD
Start(["Load Lint Config"]) --> Parse["Parse JSON Configuration"]
Parse --> ApplyDefaults["Apply Defaults for Missing Options"]
ApplyDefaults --> Instantiate["Instantiate Rules from Config"]
Instantiate --> PerLine["Process Per-Line Annotations"]
PerLine --> RemoveDisabled["Remove Disabled Lints"]
RemoveDisabled --> PostProcess["Post-Process Errors"]
PostProcess --> End(["Lint Complete"])
```

**Diagram sources**
- [lint_mod.rs](file://src/lint/mod.rs#L181-L229)
- [lint_rules_mod.rs](file://src/lint/rules/mod.rs#L43-L64)

**Section sources**
- [lint_config.json](file://python-port/examples/lint_config.json#L1-L25)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json#L1-L23)
- [lint_mod.rs](file://src/lint/mod.rs#L37-L126)
- [lint_rules_mod.rs](file://src/lint/rules/mod.rs#L43-L64)

### Multi-Device Analysis Setup
Large-scale DML projects require coordinated analysis across multiple devices with interdependencies.

- Device Discovery and Dependency Tracking
  - Python port: discovers DML files, categorizes devices/libraries, resolves imports, and maintains dependency graphs
  - Supports transitive dependency resolution and circular dependency detection

- Compile Commands Integration
  - Centralized compile information per device with include paths and compiler flags
  - Global include paths and flags augmentation for device-specific settings

```mermaid
graph TB
FM["File Manager"] --> Discover["Discover DML Files"]
Discover --> Analyze["Analyze File Info"]
Analyze --> Imports["Extract Imports"]
Imports --> Resolve["Resolve Import Paths"]
Resolve --> Graph["Update Dependency Graph"]
Graph --> Deps["Compute Dependencies"]
Deps --> Devices["Identify Device Files"]
```

**Diagram sources**
- [file_management.py](file://python-port/dml_language_server/file_management.py#L42-L304)
- [config.py](file://python-port/dml_language_server/config.py#L131-L224)

**Section sources**
- [file_management.py](file://python-port/dml_language_server/file_management.py#L33-L387)
- [config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [sample_device.dml](file://python-port/examples/sample_device.dml#L1-L188)
- [utility.dml](file://python-port/examples/utility.dml#L1-L77)

### MCP Server Configuration for AI-Assisted Development
The MCP server enables AI-assisted DML development workflows with tool-based code generation.

- Server Capabilities and Tools
  - Built-in tools for device generation, register creation, method generation, project analysis, validation, template generation, and pattern application
  - JSON-RPC over stdio with proper error handling

- Integration Examples
  - Claude Desktop integration via MCP configuration
  - Command-line testing and tool listing

```mermaid
sequenceDiagram
participant User as "User/AI"
participant MCP as "MCP Server"
participant Gen as "Generation Engine"
participant VFS as "VFS"
User->>MCP : tools/list
MCP-->>User : Available tools
User->>MCP : generate_device
MCP->>Gen : Build generation context
Gen->>VFS : Load templates and dependencies
Gen-->>MCP : Generated DML
MCP-->>User : Formatted output
```

**Diagram sources**
- [main.py](file://python-port/dml_language_server/mcp/main.py#L22-L166)
- [mcp_mod.rs](file://src/mcp/mod.rs#L1-L54)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L1-L280)

**Section sources**
- [main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)
- [mcp_mod.rs](file://src/mcp/mod.rs#L17-L54)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L1-L280)

### Advanced VFS Configuration for Large Codebases
The VFS provides efficient caching and change tracking for large DML codebases and remote file systems.

- Key Features
  - In-memory file snapshots with change tracking
  - Coalesced change application and line index maintenance
  - User data association per file for analysis metadata
  - Thread-safe file loading with pending file coordination

- Remote File System Considerations
  - VFS abstraction allows pluggable file loaders
  - Change tracking ensures consistency across remote and local files
  - Snapshot-based operations minimize repeated I/O

```mermaid
classDiagram
class Vfs {
+new() Vfs
+load_file(path) Result
+snapshot_file(path) Result
+on_changes(changes) Result
+get_cached_files() HashMap
+has_changes() bool
}
class TextFile {
+text String
+line_indices Vec
+changed bool
+make_change(changes) Result
+load_line(row) Result
}
class File {
-kind FileKind
-user_data Option
+make_change(changes) Result
+changed() bool
}
Vfs --> TextFile : "manages"
Vfs --> File : "stores"
```

**Diagram sources**
- [vfs_mod.rs](file://src/vfs/mod.rs#L180-L800)

**Section sources**
- [vfs_mod.rs](file://src/vfs/mod.rs#L1-L971)

### Custom Analysis Tool Integration and Extended Lint Rules
Extend the system with custom analysis tools and lint rules tailored to your DML project.

- Custom Lint Rules (Rust)
  - Rule trait with name, description, and type identification
  - RuleType enumeration for rule targeting and per-line annotations
  - Integration with AST traversal and error reporting

- Custom Analysis Tools (Python)
  - Extend the lint engine with new rule classes
  - Leverage analysis results for diagnostics and suggestions

```mermaid
classDiagram
class Rule {
<<trait>>
+name() str
+description() str
+get_rule_type() RuleType
+create_err(range) DMLStyleError
}
class LintEngine {
-config Config
-rules List[LintRule]
+_register_default_rules() void
+_apply_config() void
+lint_file(file_path, content) List[DMLError]
}
class LintRule {
+name str
+description str
+level LintRuleLevel
+enabled bool
+check(file_path, content, analysis) List[DMLError]
}
LintEngine --> LintRule : "manages"
LintRule ..|> Rule : "implements"
```

**Diagram sources**
- [lint_rules_mod.rs](file://src/lint/rules/mod.rs#L66-L143)
- [lint_mod.rs](file://src/lint/mod.rs#L159-L207)

**Section sources**
- [lint_rules_mod.rs](file://src/lint/rules/mod.rs#L1-L143)
- [lint_mod.rs](file://src/lint/mod.rs#L159-L207)

### Performance Optimization Configurations
Optimize performance for large DML projects through parallel processing and memory management.

- Parallel Processing
  - Controlled thread pool with capacity limits and similar work type throttling
  - Work description tracking for monitoring and debugging
  - Panic isolation with channel-based result delivery

- Memory Management
  - VFS change coalescing reduces memory churn during batch updates
  - Line index caching accelerates random access operations
  - Job tracking utilities ensure deterministic cleanup

```mermaid
flowchart TD
Start(["Start Work"]) --> CheckCapacity["Check Work Capacity"]
CheckCapacity --> |Too Many| Reject["Reject New Work"]
CheckCapacity --> |OK| Spawn["Spawn Worker Thread"]
Spawn --> Execute["Execute Work Function"]
Execute --> Complete["Send Result"]
Complete --> Cleanup["Cleanup Work Tracking"]
Reject --> End(["End"])
Cleanup --> End
```

**Diagram sources**
- [work_pool.rs](file://src/actions/work_pool.rs#L53-L103)
- [concurrency.rs](file://src/concurrency.rs#L32-L86)

**Section sources**
- [work_pool.rs](file://src/actions/work_pool.rs#L1-L104)
- [concurrency.rs](file://src/concurrency.rs#L1-L103)
- [vfs_mod.rs](file://src/vfs/mod.rs#L605-L623)

## Dependency Analysis
This section analyzes dependencies between configuration components and their impact on advanced setups.

```mermaid
graph TB
subgraph "Configuration Layer"
PY_CFG["Python Config"]
RS_CFG["Rust Config"]
end
subgraph "Analysis Layer"
PY_LINT["Python Lint Engine"]
RS_LINT["Rust Lint Rules"]
VFS["VFS"]
end
subgraph "Integration Layer"
PY_MCP["Python MCP"]
RS_MCP["Rust MCP"]
end
PY_CFG --> PY_LINT
RS_CFG --> RS_LINT
PY_CFG --> VFS
RS_CFG --> VFS
PY_MCP --> PY_CFG
RS_MCP --> RS_CFG
```

**Diagram sources**
- [config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [config.rs](file://src/config.rs#L120-L319)
- [lint_mod.rs](file://src/lint/mod.rs#L37-L126)
- [vfs_mod.rs](file://src/vfs/mod.rs#L180-L800)
- [main.py](file://python-port/dml_language_server/mcp/main.py#L142-L162)
- [mcp_mod.rs](file://src/mcp/mod.rs#L1-L54)

**Section sources**
- [config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [config.rs](file://src/config.rs#L120-L319)

## Performance Considerations
- Parallel Execution Limits
  - Control maximum concurrent tasks and similar work types to prevent overload
  - Monitor long-running tasks and log warnings for performance tuning

- Memory Efficiency
  - Use VFS change coalescing to minimize memory allocations during batch updates
  - Leverage line indices for efficient random access without repeated parsing

- Scalability
  - Configure device context modes to balance analysis scope and performance
  - Use compile commands to optimize include path resolution and reduce scanning overhead

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions for advanced configurations:

- Lint Configuration Issues
  - Unknown fields in lint config are detected and reported; verify rule names and option names
  - Per-line annotations without effect at end of file indicate unused suppression directives

- MCP Server Problems
  - Verify JSON-RPC protocol compliance and stdio communication
  - Check server capabilities and tool availability

- VFS Errors
  - Out-of-sync files indicate external modifications; refresh or reload
  - Bad locations suggest invalid row/column coordinates; validate editor integration

**Section sources**
- [lint_mod.rs](file://src/lint/mod.rs#L244-L364)
- [main.py](file://python-port/dml_language_server/mcp/main.py#L74-L95)
- [vfs_mod.rs](file://src/vfs/mod.rs#L110-L172)

## Conclusion
This document outlined advanced configuration patterns for complex DML projects, including comprehensive lint rule configuration, multi-device analysis, MCP server integration, VFS optimization, custom tool development, and performance tuning. These configurations enable scalable, maintainable, and AI-assisted DML development workflows.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Appendix A: Configuration Reference Tables

- Python Lint Configuration Fields
  - enabled_rules: list of rule names to enable
  - disabled_rules: list of rule names to disable
  - rule_configs: per-rule configuration with level and parameters

- Rust Lint Configuration Options
  - sp_reserved/sp_brace/sp_punct/sp_binop/sp_ternary/sp_ptrdecl: spacing rule options
  - nsp_funpar/nsp_inparen/nsp_unary/nsp_trailing: negative spacing rule options
  - long_lines: maximum line length configuration
  - indent_size/indent_no_tabs/indent_code_block/indent_closing_brace/indent_paren_expr/indent_switch_case/indent_empty_loop: indentation rule options
  - annotate_lints: whether to prefix diagnostic descriptions with rule identifiers

**Section sources**
- [lint_config.json](file://python-port/examples/lint_config.json#L1-L25)
- [example_lint_cfg.json](file://example_files/example_lint_cfg.json#L1-L23)
- [lint_mod.rs](file://src/lint/mod.rs#L68-L157)