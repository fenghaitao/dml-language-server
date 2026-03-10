# MCP Server Implementation

<cite>
**Referenced Files in This Document**
- [src/mcp/main.rs](file://src/mcp/main.rs)
- [src/mcp/mod.rs](file://src/mcp/mod.rs)
- [src/mcp/server.rs](file://src/mcp/server.rs)
- [src/mcp/tools.rs](file://src/mcp/tools.rs)
- [src/mcp/generation.rs](file://src/mcp/generation.rs)
- [src/mcp/templates.rs](file://src/mcp/templates.rs)
- [Cargo.toml](file://Cargo.toml)
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

## Introduction
This document provides a comprehensive technical deep dive into the DML MCP (Model Context Protocol) Server implementation. It explains the server architecture, lifecycle management, asynchronous message handling, tool registration, integration with the DML analysis engine, and operational best practices. The MCP server enables AI agents and IDEs to discover tools, invoke DML code generation, and integrate with the broader DML ecosystem through a standards-compliant JSON-RPC interface over stdin/stdout.

## Project Structure
The MCP server resides under the `src/mcp/` module and integrates with the broader DML language server ecosystem. The key files include the entry point, server implementation, tool registry, generation engine, and template library.

```mermaid
graph TB
subgraph "MCP Module"
MAIN["src/mcp/main.rs<br/>Binary entry point"]
MOD["src/mcp/mod.rs<br/>Exports and constants"]
SERVER["src/mcp/server.rs<br/>JSON-RPC over stdio"]
TOOLS["src/mcp/tools.rs<br/>Tool registry and tools"]
GEN["src/mcp/generation.rs<br/>Code generation engine"]
TEMPLATES["src/mcp/templates.rs<br/>Template library"]
end
MAIN --> SERVER
SERVER --> TOOLS
TOOLS --> GEN
TOOLS --> TEMPLATES
MOD --> SERVER
MOD --> TOOLS
MOD --> GEN
MOD --> TEMPLATES
```

**Diagram sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L1-L23)
- [src/mcp/mod.rs](file://src/mcp/mod.rs#L1-L54)
- [src/mcp/server.rs](file://src/mcp/server.rs#L1-L229)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L1-L399)
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L1-L411)
- [src/mcp/templates.rs](file://src/mcp/templates.rs#L1-L428)

**Section sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L1-L23)
- [src/mcp/mod.rs](file://src/mcp/mod.rs#L1-L54)

## Core Components
- DMLMCPServer: Implements the MCP JSON-RPC over stdio, handles initialize, tools/list, and tools/call requests, and routes messages to the ToolRegistry.
- ToolRegistry: Manages built-in tools, validates tool invocation parameters, and executes tool implementations asynchronously.
- DMLTools: Trait abstraction for tools with standardized metadata and async execution.
- DMLGenerator: Advanced code generation engine supporting configurable formatting, documentation generation, and validation hooks.
- DMLTemplates: Rich template library for common device patterns (CPU, memory, peripheral, bus interface) and design patterns.

Key capabilities:
- MCP 2024-11-05 protocol compliance
- Async/await with Tokio for non-blocking IO
- Structured error responses per JSON-RPC 2.0
- Configurable generation settings (indentation, line endings, validation)
- Extensible tool system with JSON schema validation

**Section sources**
- [src/mcp/server.rs](file://src/mcp/server.rs#L36-L229)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L36-L121)
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L52-L310)
- [src/mcp/templates.rs](file://src/mcp/templates.rs#L8-L359)

## Architecture Overview
The MCP server follows a clean separation of concerns:
- Entry point initializes logging and spawns the server
- Server reads JSON-RPC messages from stdin, parses them, and dispatches to handlers
- Handlers delegate tool execution to the ToolRegistry
- Tools may leverage the DMLGenerator and DMLTemplates for code generation
- Responses are written to stdout with proper JSON-RPC framing

```mermaid
sequenceDiagram
participant Client as "MCP Client"
participant Server as "DMLMCPServer"
participant Registry as "ToolRegistry"
participant Tool as "DMLTool"
participant Gen as "DMLGenerator"
Client->>Server : "initialize" JSON-RPC
Server-->>Client : "initialize" response
Client->>Server : "tools/list" JSON-RPC
Server->>Registry : list_tools()
Registry-->>Server : tool definitions
Server-->>Client : "tools/list" response
Client->>Server : "tools/call" {name, arguments}
Server->>Registry : call_tool(arguments)
Registry->>Tool : execute(arguments)
Tool->>Gen : generate code (optional)
Gen-->>Tool : GeneratedCode
Tool-->>Registry : ToolResult
Registry-->>Server : ToolResult
Server-->>Client : "tools/call" response
```

**Diagram sources**
- [src/mcp/server.rs](file://src/mcp/server.rs#L57-L132)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L101-L120)
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L66-L111)

## Detailed Component Analysis

### DMLMCPServer Lifecycle and Message Handling
- Initialization: Creates ToolRegistry, logs startup, and enters the main loop
- Message Loop: Reads lines from stdin, trims whitespace, and handles EOF gracefully
- Routing: Parses JSON-RPC, matches method, and constructs appropriate responses
- Error Handling: Logs parse failures, unknown methods, and internal tool errors with structured JSON-RPC error objects
- Shutdown: Exits cleanly on EOF or read errors

```mermaid
flowchart TD
Start(["Server.start"]) --> New["DMLMCPServer::new()"]
New --> Run["Server.run()"]
Run --> Read["Read line from stdin"]
Read --> EOF{"EOF?"}
EOF --> |Yes| Shutdown["Graceful shutdown"]
EOF --> |No| Parse["Parse JSON-RPC"]
Parse --> Valid{"Valid?"}
Valid --> |No| LogErr["Log parse error"] --> Read
Valid --> |Yes| Route["Route by method"]
Route --> Init["initialize"]
Route --> List["tools/list"]
Route --> Call["tools/call"]
Route --> Unknown["Unknown method"]
Init --> Respond["Send response"]
List --> Respond
Call --> Respond
Unknown --> Respond
Respond --> Flush["Flush stdout"]
Flush --> Read
```

**Diagram sources**
- [src/mcp/server.rs](file://src/mcp/server.rs#L57-L132)

**Section sources**
- [src/mcp/server.rs](file://src/mcp/server.rs#L43-L132)

### Tool Registration and Execution Workflow
- ToolRegistry.new(): Loads default Config, registers built-in tools, logs counts
- Built-in tools include device generation, register generation, method generation, project analysis, code validation, template generation, and pattern application
- Tool execution validates presence of name and arguments, resolves tool by name, and executes with cloned input
- Results are serialized to ToolResult with content arrays and optional error flags

```mermaid
classDiagram
class ToolRegistry {
-tools : HashMap<String, Box<dyn DMLTool>>
-config : Config
+new() Result<Self>
+register_builtin_tools() Result<void>
+register_tool(tool) Result<void>
+list_tools() Vec<ToolDefinition>
+call_tool(params) Result<Value>
}
class DMLTool {
<<trait>>
+name() &str
+description() &str
+input_schema() Value
+execute(input) async Result<ToolResult>
}
class GenerateDeviceTool {
+name() "generate_device"
+input_schema() Value
+execute(input) async Result<ToolResult>
}
class GenerateRegisterTool {
+name() "generate_register"
+input_schema() Value
+execute(input) async Result<ToolResult>
}
ToolRegistry --> DMLTool : "manages"
GenerateDeviceTool ..|> DMLTool
GenerateRegisterTool ..|> DMLTool
```

**Diagram sources**
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L46-L121)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L125-L203)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L205-L280)

**Section sources**
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L46-L121)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L125-L280)

### Code Generation Engine and Templates
- DMLGenerator: Accepts a GenerationContext with device name, namespace, imports, templates, and GenerationConfig
- Supports generating devices, banks, registers, fields, and methods with configurable formatting and documentation
- GenerationConfig supports indent styles (spaces/tabs), line endings, max line length, documentation generation, and output validation
- DMLTemplates: Provides built-in device templates (CPU, memory, peripheral, bus interface) and common design patterns
- TemplateRegistry: Placeholder for loading built-in templates

```mermaid
classDiagram
class DMLGenerator {
+context : GenerationContext
-templates : TemplateRegistry
+new(context) Self
+generate_device(spec) async Result<GeneratedCode>
+generate_register(spec) async Result<String>
+generate_method(spec) Result<String>
-generate_header() Result<String>
-generate_device_declaration(spec) Result<String>
-generate_bank(bank) async Result<String>
-generate_interface(iface) Result<String>
-generate_field(field) Result<String>
+get_indent() String
-validate_generated_code(generated) async Result<void>
}
class GenerationContext {
+device_name : String
+namespace : String
+imports : Vec<String>
+templates : Vec<String>
+config : GenerationConfig
}
class GenerationConfig {
+indent_style : IndentStyle
+line_ending : LineEnding
+max_line_length : usize
+generate_docs : bool
+validate_output : bool
}
class TemplateRegistry {
-templates : HashMap<String, CodeTemplate>
+new() Self
-load_builtin_templates()
}
DMLGenerator --> GenerationContext : "uses"
DMLGenerator --> GenerationConfig : "uses"
DMLGenerator --> TemplateRegistry : "uses"
```

**Diagram sources**
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L52-L310)
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L8-L50)

**Section sources**
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L52-L310)
- [src/mcp/templates.rs](file://src/mcp/templates.rs#L8-L359)

### Server Initialization and Configuration
- Entry point: Initializes env_logger with INFO level by default, logs version, creates DMLMCPServer via DMLMCPServer::new(), and runs server.run()
- DMLMCPServer::new(): Builds ToolRegistry, sets default ServerInfo and ServerCapabilities
- ServerCapabilities: Enables tools and logging; resources/prompts disabled by default
- MCP_VERSION: "2024-11-05"

```mermaid
sequenceDiagram
participant Main as "main()"
participant Server as "DMLMCPServer"
participant Registry as "ToolRegistry"
Main->>Main : init env_logger
Main->>Server : DMLMCPServer : : new()
Server->>Registry : ToolRegistry : : new()
Registry-->>Server : ToolRegistry
Server-->>Main : DMLMCPServer
Main->>Server : run()
Server->>Server : enter message loop
```

**Diagram sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [src/mcp/server.rs](file://src/mcp/server.rs#L43-L55)
- [src/mcp/mod.rs](file://src/mcp/mod.rs#L17-L54)

**Section sources**
- [src/mcp/main.rs](file://src/mcp/main.rs#L11-L23)
- [src/mcp/server.rs](file://src/mcp/server.rs#L43-L55)
- [src/mcp/mod.rs](file://src/mcp/mod.rs#L17-L54)

## Dependency Analysis
External dependencies relevant to the MCP server:
- tokio: async runtime for stdio handling
- serde/serde_json: JSON serialization/deserialization
- log/env_logger: structured logging
- anyhow: error handling abstraction

```mermaid
graph TB
MCP_MAIN["src/mcp/main.rs"] --> TOKIO["tokio"]
MCP_MAIN --> ENVLOG["env_logger"]
MCP_MAIN --> ANYHOW["anyhow"]
MCP_SERVER["src/mcp/server.rs"] --> SERDE["serde / serde_json"]
MCP_SERVER --> TOKIO
MCP_TOOLS["src/mcp/tools.rs"] --> SERDE
MCP_TOOLS --> ANYHOW
MCP_GEN["src/mcp/generation.rs"] --> SERDE
MCP_TEMPLATES["src/mcp/templates.rs"] --> SERDE
```

**Diagram sources**
- [Cargo.toml](file://Cargo.toml#L33-L62)
- [src/mcp/main.rs](file://src/mcp/main.rs#L6-L10)
- [src/mcp/server.rs](file://src/mcp/server.rs#L3-L10)
- [src/mcp/tools.rs](file://src/mcp/tools.rs#L3-L11)
- [src/mcp/generation.rs](file://src/mcp/generation.rs#L3-L7)
- [src/mcp/templates.rs](file://src/mcp/templates.rs#L3-L7)

**Section sources**
- [Cargo.toml](file://Cargo.toml#L33-L62)

## Performance Considerations
- Asynchronous IO: Uses Tokio for non-blocking stdin/stdout handling, enabling concurrent request processing without blocking the main thread
- Minimal allocations: Reuses buffers and avoids unnecessary cloning during message parsing and response construction
- Configurable generation: GenerationConfig allows tuning formatting and validation overhead to balance quality and performance
- Scalability: The ToolRegistry pattern supports adding new tools without modifying core server logic, facilitating horizontal scaling through external tool integrations
- Memory management: Leverages Rust ownership semantics to prevent leaks and ensure deterministic cleanup

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Parse errors: Invalid JSON-RPC messages trigger structured error responses (-32700 "Parse error")
- Unknown methods: Unrecognized method names return -32601 "Method not found"
- Invalid params: Missing tool name or arguments yield -32602 "Invalid params"
- Internal errors: Tool execution failures produce -32603 "Internal error" with details
- Logging: Configure env_logger filter via environment variable for debug-level insights
- EOF handling: Graceful shutdown on stdin EOF; verify client closes properly

Operational checks:
- Verify MCP 2024-11-05 protocol compliance
- Confirm tools/list returns expected tool definitions
- Validate tool schemas via input_schema for each tool
- Monitor logs for warnings and errors during generation

**Section sources**
- [src/mcp/server.rs](file://src/mcp/server.rs#L104-L132)
- [src/mcp/server.rs](file://src/mcp/server.rs#L188-L205)
- [src/mcp/server.rs](file://src/mcp/server.rs#L208-L228)

## Conclusion
The DML MCP Server provides a robust, standards-compliant foundation for AI-assisted DML development. Its modular design, asynchronous IO, and extensible tool system enable seamless integration with modern AI agents and IDEs. The combination of a powerful code generation engine and rich template library accelerates development workflows while maintaining high code quality and performance. The implementation demonstrates production readiness with comprehensive error handling, logging, and test coverage.