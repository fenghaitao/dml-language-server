# Command Line Tools

<cite>
**Referenced Files in This Document**
- [src/main.rs](file://src/main.rs)
- [src/cmd.rs](file://src/cmd.rs)
- [src/config.rs](file://src/config.rs)
- [src/dfa/main.rs](file://src/dfa/main.rs)
- [src/mcp/main.rs](file://src/mcp/main.rs)
- [python-port/dml_language_server/cmd.py](file://python-port/dml_language_server/cmd.py)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py)
- [Cargo.toml](file://Cargo.toml)
- [README.md](file://README.md)
- [USAGE.md](file://USAGE.md)
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
This document explains the command-line interface tools provided by the DML Language Server project. It covers:
- The main dls binary and its CLI mode for interactive analysis
- The DFA (Device File Analyzer) tool for standalone device analysis, dependency tracking, and report generation
- The MCP server command-line interface for AI-assisted development workflows
- Practical usage patterns, automation scripts, and CI/CD integration
- Performance optimization, memory usage considerations, and debugging techniques
- Shared configuration options between CLI tools and the language server, and migration paths between analysis modes

## Project Structure
The CLI tools are implemented across two layers:
- A native Rust implementation with a language server and supporting utilities
- A Python port that mirrors the Rust functionality for environments where Python is preferred

Key binaries and entry points:
- dls: Native language server with optional CLI mode
- dfa: Standalone device file analyzer
- dml-mcp-server: MCP server for AI-assisted development

```mermaid
graph TB
subgraph "Native (Rust)"
MAIN["src/main.rs<br/>CLI entry"]
CMD["src/cmd.rs<br/>CLI runner"]
CFG["src/config.rs<br/>Shared config"]
DFA_BIN["src/dfa/main.rs<br/>DFA standalone"]
MCP_BIN["src/mcp/main.rs<br/>MCP server"]
end
subgraph "Python Port"
PY_CMD["python-port/dml_language_server/cmd.py<br/>CLI runner"]
PY_DFA["python-port/dml_language_server/dfa/main.py<br/>DFA analyzer"]
PY_MCP["python-port/dml_language_server/mcp/main.py<br/>MCP server"]
PY_CFG["python-port/dml_language_server/config.py<br/>Python config"]
end
MAIN --> CMD
MAIN --> CFG
DFA_BIN --> CFG
MCP_BIN --> CFG
PY_CMD --> PY_CFG
PY_DFA --> PY_CFG
PY_MCP --> PY_CFG
```

**Diagram sources**
- [src/main.rs](file://src/main.rs#L15-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/config.rs](file://src/config.rs#L120-L139)
- [src/dfa/main.rs](file://src/dfa/main.rs#L21-L192)
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [python-port/dml_language_server/cmd.py](file://python-port/dml_language_server/cmd.py#L21-L162)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py#L89-L311)

**Section sources**
- [Cargo.toml](file://Cargo.toml#L18-L31)
- [README.md](file://README.md#L22-L34)

## Core Components
- dls (native): Supports both server mode and CLI mode. In CLI mode, it exposes a REPL-like interface for interactive queries and analysis.
- dfa (native): Non-interactive analyzer that runs the DLS against one or more DML files and prints diagnostics.
- dfa (Python): Feature-rich analyzer with multiple analysis types, dependency checks, orphans detection, and report generation in multiple formats.
- dml-mcp-server (native): MCP server that integrates with AI assistants via JSON-RPC over stdin/stdout.
- dml-mcp-server (Python): Python-side MCP server with protocol handler and CLI options.

**Section sources**
- [src/main.rs](file://src/main.rs#L21-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/dfa/main.rs](file://src/dfa/main.rs#L44-L122)
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [python-port/dml_language_server/cmd.py](file://python-port/dml_language_server/cmd.py#L21-L162)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)

## Architecture Overview
The CLI tools share a common configuration model and can either run as standalone binaries or integrate with the language server.

```mermaid
graph TB
subgraph "CLI Modes"
DLS_CLI["dls --cli<br/>Interactive REPL"]
DFA_NATIVE["dfa (native)<br/>Non-interactive"]
DFA_PY["dfa (Python)<br/>Rich analysis + reports"]
MCP_NATIVE["dml-mcp-server (native)<br/>JSON-RPC over stdio"]
MCP_PY["dml-mcp-server (Python)<br/>Protocol handler"]
end
subgraph "Shared Config"
CFG_RUST["src/config.rs<br/>Config, DeviceContextMode"]
CFG_PY["python-port/.../config.py<br/>CompileInfo, LintConfig, Init options"]
end
DLS_CLI --> CFG_RUST
DFA_NATIVE --> CFG_RUST
DFA_PY --> CFG_PY
MCP_NATIVE --> CFG_RUST
MCP_PY --> CFG_PY
```

**Diagram sources**
- [src/config.rs](file://src/config.rs#L120-L139)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [src/main.rs](file://src/main.rs#L44-L59)
- [src/dfa/main.rs](file://src/dfa/main.rs#L124-L192)
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [python-port/dml_language_server/cmd.py](file://python-port/dml_language_server/cmd.py#L21-L162)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)

## Detailed Component Analysis

### dls Binary (CLI Mode)
The dls binary supports a CLI mode that runs the language server in-process and exposes a simple command-driven interface. It initializes the server, accepts commands, and prints results.

Key behaviors:
- Parses CLI flags for enabling CLI mode, compile-info path, and linting options
- Initializes the server with VFS and configuration
- Provides a REPL with commands for definition lookup, symbol queries, document symbols, workspace management, and context configuration
- Uses a channel-based message passing mechanism to communicate with the server

```mermaid
sequenceDiagram
participant User as "User"
participant DLS as "dls main"
participant CLI as "CLI runner (cmd)"
participant Svc as "LsService"
participant Out as "PrintlnOutput"
User->>DLS : "--cli [--compile-info] [--linting] [--lint-cfg]"
DLS->>CLI : run(compile_info, linting, cfg)
CLI->>Svc : initialize(root)
Svc-->>CLI : InitializeResult
loop REPL
User->>CLI : "def|symbol|document|open|workspace|context-mode|contexts|set-contexts|wait|help|quit"
CLI->>Svc : Request/Notification
Svc-->>Out : response/print
end
User->>CLI : "quit"
CLI->>Svc : shutdown + exit
```

**Diagram sources**
- [src/main.rs](file://src/main.rs#L44-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/cmd.rs](file://src/cmd.rs#L189-L195)
- [src/cmd.rs](file://src/cmd.rs#L197-L228)
- [src/cmd.rs](file://src/cmd.rs#L230-L246)
- [src/cmd.rs](file://src/cmd.rs#L248-L274)
- [src/cmd.rs](file://src/cmd.rs#L276-L297)
- [src/cmd.rs](file://src/cmd.rs#L299-L323)
- [src/cmd.rs](file://src/cmd.rs#L334-L347)

Configuration options exposed by CLI mode:
- --cli: Enables CLI mode
- --compile-info: Path to compile-commands file
- --linting: Enable/disable linting
- --lint-cfg: Path to lint configuration file

Output formatting:
- JSON responses from the server are printed to stdout
- The CLI runner prints human-friendly messages for certain operations

Practical usage patterns:
- Interactive exploration: Use commands like def, symbol, document, open, workspace
- Batch-style analysis: Use wait to allow analysis to complete, then capture stdout
- Context management: Use context-mode and contexts/set-contexts to control device context behavior

**Section sources**
- [src/main.rs](file://src/main.rs#L21-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/cmd.rs](file://src/cmd.rs#L405-L443)
- [src/config.rs](file://src/config.rs#L120-L139)

### DFA (Device File Analyzer) Tool
There are two DFA implementations: a native standalone analyzer and a Python-rich analyzer.

#### Native DFA (src/dfa/main.rs)
- Accepts a DLS binary path and one or more DML files
- Optional workspace roots, compile-info, linting enablement, lint-cfg, zero-indexed diagnostics, and quiet mode
- Starts a client that communicates with the DLS binary, opens files, waits for analysis, and optionally prints diagnostics
- Supports suppressing imports and test mode (exits with error if diagnostics are present)

```mermaid
flowchart TD
Start(["Start DFA"]) --> Parse["Parse args:<br/>DLS binary, files, workspace, compile-info,<br/>suppress-imports, zero-indexed, linting, lint-cfg, test, quiet"]
Parse --> Root["Determine root workspace"]
Root --> StartClient["Start DLS client with linting"]
StartClient --> SetCfg["Set Config (compile_info, suppress_imports, linting, lint_cfg)"]
SetCfg --> OpenFiles["Open each DML file"]
OpenFiles --> Wait["Wait for analysis completion"]
Wait --> Output{"Quiet mode?"}
Output --> |No| Diagnostics["Print diagnostics (zero-indexed if requested)"]
Output --> |Yes| Skip["Skip diagnostics"]
Diagnostics --> Test{"Test mode?"}
Skip --> Test
Test --> |Yes & errors| Exit1["Exit with error"]
Test --> |No| Exit0["Exit successfully"]
```

**Diagram sources**
- [src/dfa/main.rs](file://src/dfa/main.rs#L44-L122)
- [src/dfa/main.rs](file://src/dfa/main.rs#L124-L192)

Usage examples:
- Analyze multiple files with linting enabled and suppress imports
- Use test mode to fail builds on diagnostics
- Provide compile-info to resolve includes and flags

#### Python DFA (python-port/dml_language_server/dfa/main.py)
- Provides a CLI group with analyze and deps subcommands
- Supports recursive directory scanning, multiple analysis types (syntax, semantic, dependencies, symbols, metrics, all), compile-info loading, output formats (summary, detailed, json), verbosity, quiet mode, circular dependency checks, orphans detection, and errors-only filtering
- Generates structured reports and exits with non-zero status if errors are found

```mermaid
sequenceDiagram
participant User as "User"
participant CLI as "dfa main()"
participant Analyzer as "DMLAnalyzer"
participant Report as "ReportGenerator"
User->>CLI : "analyze [paths...] [options]"
CLI->>CLI : Parse options (types, compile-info, format, flags)
CLI->>Analyzer : Initialize with Config
CLI->>Analyzer : Discover files (recursive if requested)
loop For each file
Analyzer->>Analyzer : analyze_file(file, types)
end
CLI->>CLI : Optional special analyses (deps/orphans)
CLI->>Report : Generate report (format=json|detailed|summary)
Report-->>CLI : Report text
CLI-->>User : Print/report + exit code
```

**Diagram sources**
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L282-L334)

Usage examples:
- Analyze all files in a directory recursively with detailed report
- Generate JSON report for CI consumption
- Show dependencies for a specific file in text, dot, or JSON formats

**Section sources**
- [src/dfa/main.rs](file://src/dfa/main.rs#L44-L122)
- [src/dfa/main.rs](file://src/dfa/main.rs#L124-L192)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L282-L334)

### MCP Server CLI (AI-Assisted Development)
The MCP server provides AI-assisted DML code generation and analysis via the Model Context Protocol over stdin/stdout.

#### Native MCP Server (src/mcp/main.rs)
- Entry point initializes logging and starts the DMLMCPServer
- Runs asynchronously using Tokio runtime

```mermaid
sequenceDiagram
participant User as "User/AI Client"
participant MCP as "dml-mcp-server main"
participant Server as "DMLMCPServer"
User->>MCP : Start process
MCP->>Server : new().await
MCP->>Server : run().await
loop JSON-RPC over stdio
User->>Server : {"jsonrpc" : "2.0","method" : "...", "params" : {...}, "id" : N}
Server-->>User : {"jsonrpc" : "2.0","result/error" : ..., "id" : N}
end
```

**Diagram sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)

#### Python MCP Server (python-port/dml_language_server/mcp/main.py)
- Provides a CLI with options for verbose logging, compile-info loading, and log file redirection
- Implements a protocol handler that reads JSON-RPC messages from stdin, handles requests, and writes responses to stdout
- Uses asyncio.StreamReader/Writer over stdio

```mermaid
flowchart TD
Start(["Start dml-mcp-server"]) --> Parse["Parse CLI options"]
Parse --> Init["Create DMLMCPServer"]
Init --> Load["Load compile-info if provided"]
Load --> Handler["Create MCPProtocolHandler"]
Handler --> Loop["Read stdin line (JSON-RPC)"]
Loop --> ParseJSON["Parse JSON"]
ParseJSON --> Handle["server.handle_request()"]
Handle --> Respond["Write JSON-RPC response to stdout"]
Respond --> Loop
```

**Diagram sources**
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L22-L96)

Usage examples:
- Build and run the native MCP server
- Pipe JSON-RPC messages to the server for tool discovery and code generation
- Configure AI desktop clients to connect to the MCP server

**Section sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L98-L166)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L9-L33)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L163-L170)

### Shared Configuration Options and Migration Paths
Both CLI tools and the language server share configuration concepts:
- Compile commands: Provide include paths and compiler flags per device
- Linting: Enable/disable linting and supply lint configuration
- Device context modes: Control when new device contexts are activated
- Zero-indexed diagnostics: Toggle diagnostic index origin

Migration paths:
- From native dls CLI mode to native DFA for non-interactive batch analysis
- From Python DFA analyze to native DFA for performance-sensitive scenarios
- From Python MCP server to native MCP server for production deployments
- Use compile-info consistently across tools to ensure uniform resolution of imports and flags

**Section sources**
- [src/config.rs](file://src/config.rs#L120-L139)
- [src/config.rs](file://src/config.rs#L100-L118)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py#L131-L224)
- [README.md](file://README.md#L36-L57)
- [USAGE.md](file://USAGE.md#L15-L48)

## Dependency Analysis
The CLI tools depend on shared configuration and analysis components. The native and Python implementations expose similar options and behaviors, enabling interoperability and migration.

```mermaid
graph LR
DLS["dls (binary)"] --> CFG["Config (shared)"]
DFA_N["dfa (native)"] --> CFG
DFA_P["dfa (Python)"] --> CFG_P["Python Config"]
MCP_N["mcp (native)"] --> CFG
MCP_P["mcp (Python)"] --> CFG_P
CFG --> LINT["Linting options"]
CFG --> COMP["Compile info"]
CFG --> DC["Device context mode"]
CFG_P --> LINT_P["Linting options"]
CFG_P --> COMP_P["Compile info"]
```

**Diagram sources**
- [src/config.rs](file://src/config.rs#L120-L139)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [src/dfa/main.rs](file://src/dfa/main.rs#L143-L158)
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L142-L156)

**Section sources**
- [src/config.rs](file://src/config.rs#L120-L139)
- [python-port/dml_language_server/config.py](file://python-port/dml_language_server/config.py#L89-L311)
- [src/dfa/main.rs](file://src/dfa/main.rs#L143-L158)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L134-L140)

## Performance Considerations
- Large-scale analysis: Prefer native binaries (dls, dfa, dml-mcp-server) for speed and lower overhead compared to Python implementations
- Memory usage: Use suppress-imports in DFA to reduce analysis scope; disable linting when not needed; limit concurrent analysis in CI
- Batch operations: Use DFA test mode to fail fast on errors; leverage compile-info to avoid redundant include scanning
- Device context modes: Choose appropriate DeviceContextMode to minimize unnecessary context activation and improve responsiveness
- Output control: Use quiet mode in DFA to reduce I/O overhead; generate JSON reports for downstream processing

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and remedies:
- CLI hangs or slow responses: Use wait in dls CLI mode to allow analysis to complete; increase wait duration for large workspaces
- Missing imports or incorrect includes: Provide compile-info to resolve include paths and flags
- Excessive diagnostics: Disable linting or tune lint configuration; use errors-only filtering in Python DFA
- MCP server not responding: Verify JSON-RPC messages are valid; check protocol handler logs; redirect logs to a file when stdout is reserved for protocol traffic
- Permission or path issues: Ensure DLS binary path is correct; normalize paths to avoid UNC issues; validate file permissions

**Section sources**
- [src/cmd.rs](file://src/cmd.rs#L445-L456)
- [python-port/dml_language_server/mcp/main.py](file://python-port/dml_language_server/mcp/main.py#L122-L138)

## Conclusion
The DML Language Server project provides a comprehensive suite of CLI tools for interactive analysis, batch processing, dependency tracking, and AI-assisted development. By leveraging shared configuration and consistent options across native and Python implementations, users can choose the most suitable tool for their workflow, scale analysis to large projects, and integrate seamlessly with CI/CD and AI assistants.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Practical Usage Patterns and Automation Scripts
- Interactive exploration with dls CLI mode:
  - Start dls in CLI mode and issue commands like def, symbol, document, open, workspace, context-mode, contexts, set-contexts, wait, help, quit
- Batch analysis with native DFA:
  - Run dfa with a DLS binary, target files, and options like --compile-info, --linting-enabled, --suppress-imports, --test, --quiet
- Rich reporting with Python DFA:
  - Use analyze with --recursive, --analysis-type, --compile-info, --output, --format, --errors-only, --check-deps, --find-orphans
- CI/CD integration:
  - Use DFA test mode to gate PRs on diagnostics
  - Generate JSON reports for artifact storage and downstream analysis
- MCP server integration:
  - Build and run dml-mcp-server; configure AI desktop clients to connect via the MCP configuration
  - Use tools/list and generate_device/generate_register/etc. for automated code generation

**Section sources**
- [src/cmd.rs](file://src/cmd.rs#L405-L443)
- [src/dfa/main.rs](file://src/dfa/main.rs#L44-L122)
- [python-port/dml_language_server/dfa/main.py](file://python-port/dml_language_server/dfa/main.py#L78-L280)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L9-L33)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L163-L170)