# Getting Started

<cite>
**Referenced Files in This Document**
- [Cargo.toml](file://Cargo.toml)
- [README.md](file://README.md)
- [USAGE.md](file://USAGE.md)
- [clients.md](file://clients.md)
- [src/main.rs](file://src/main.rs)
- [src/server/mod.rs](file://src/server/mod.rs)
- [src/cmd.rs](file://src/cmd.rs)
- [src/config.rs](file://src/config.rs)
- [example_files/example_lint_cfg.json](file://example_files/example_lint_cfg.json)
- [example_files/watchdog_timer.dml](file://example_files/watchdog_timer.dml)
- [python-port/README.md](file://python-port/README.md)
- [python-port/pyproject.toml](file://python-port/pyproject.toml)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Building the Server](#building-the-server)
5. [Running the Server](#running-the-server)
6. [Basic Setup and Configuration](#basic-setup-and-configuration)
7. [Initial Usage Examples](#initial-usage-examples)
8. [Client Integration](#client-integration)
9. [Verification Steps](#verification-steps)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [Conclusion](#conclusion)

## Introduction
This guide helps you get the DML Language Server (DLS) running quickly. It covers prerequisites, building from source, running the server, configuring it, and integrating with a language client. The DLS provides IDE features for DML 1.4 code, including syntax diagnostics, symbol search, and navigation.

## System Requirements
- Operating system: Windows, Linux, macOS
- Rust toolchain (required for building from source)
- Git (recommended for cloning the repository)
- An editor or IDE that supports the Language Server Protocol (LSP)

Notes:
- The project compiles with the 2018 edition and uses modern Rust features.
- The server communicates over stdin/stdout using the LSP JSON-RPC protocol.

**Section sources**
- [Cargo.toml](file://Cargo.toml#L1-L62)
- [README.md](file://README.md#L22-L24)

## Installation
There are two primary ways to obtain and run the DLS:

- Build from source using the Rust toolchain
- Use the Python port (alternative implementation) with Python 3.8+

### Option A: Build from Source (Rust)
1. Install Rust and Cargo (e.g., via rustup).
2. Clone the repository and navigate to the root directory.
3. Build the release binary using Cargo.

Key references:
- Building instructions are documented in the repository’s README.
- The Cargo manifest defines the binaries and dependencies.

**Section sources**
- [README.md](file://README.md#L22-L24)
- [Cargo.toml](file://Cargo.toml#L18-L31)

### Option B: Python Port (Alternative)
The repository includes a Python port of the DLS. If you prefer Python or want to explore an alternative implementation:

- Install Python 3.8+.
- Install the package in development mode from the python-port directory.

This path is documented in the Python port README and pyproject.toml.

**Section sources**
- [python-port/README.md](file://python-port/README.md#L17-L31)
- [python-port/pyproject.toml](file://python-port/pyproject.toml#L14-L42)

## Building the Server
To build the DLS from source:

1. Open a terminal in the repository root.
2. Run the release build command.

After building, the server binary will be available under the target directory.

**Section sources**
- [README.md](file://README.md#L22-L24)
- [Cargo.toml](file://Cargo.toml#L10-L11)

## Running the Server
The DLS runs as an LSP server over stdin/stdout. You can start it directly or use the command-line interface mode.

### Start the LSP Server
- Launch the compiled binary. It expects to communicate over stdin/stdout.
- Point your editor’s LSP client to use the binary.

Important behavior:
- The server initializes on the first initialize request and responds with capabilities.
- It supports workspace folders and configuration updates.

**Section sources**
- [src/server/mod.rs](file://src/server/mod.rs#L68-L84)
- [src/server/mod.rs](file://src/server/mod.rs#L207-L288)

### Command-Line Interface Mode
The server can also run in a simple CLI mode for quick tests and scripted interactions. In this mode, you can issue commands like opening files, querying symbols, and setting device contexts.

- Use the CLI flag to start in CLI mode.
- Provide optional compile info and lint configuration paths.

Commands available in CLI mode include:
- open FILENAME
- def FILENAME ROW COL
- symbol QUERY
- document FILENAME
- workspace DIR...
- context-mode MODE
- contexts PATHS...
- set-contexts PATHS...
- wait MILLISECONDS
- help
- quit

These are defined and implemented in the CLI module.

**Section sources**
- [src/main.rs](file://src/main.rs#L30-L42)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/cmd.rs](file://src/cmd.rs#L405-L443)

## Basic Setup and Configuration
The DLS supports configuration via initialization options and workspace configuration. You can control linting, analysis behavior, and include paths.

### Configuration Options
The server exposes a configuration structure with the following categories:
- Linting controls (enable/disable, configuration file path)
- Analysis behavior (save-triggered analysis, context modes)
- Include paths and compile info for resolving imports
- Debug logging level

Defaults and detailed option names are defined in the configuration module.

Practical tips:
- Enable linting by default; disable if needed.
- Provide a compile commands file to help resolve imports and flags.
- Adjust device context modes depending on your project layout.

**Section sources**
- [src/config.rs](file://src/config.rs#L120-L140)
- [src/config.rs](file://src/config.rs#L209-L227)
- [README.md](file://README.md#L36-L57)

### Lint Configuration Example
You can supply a lint configuration file to customize lint rules and thresholds. The example file shows typical rule configurations and options.

**Section sources**
- [example_files/example_lint_cfg.json](file://example_files/example_lint_cfg.json#L1-L28)

### DML Compile Commands
The compile commands file is a JSON mapping device file paths to include directories and DMLC flags. This helps the server resolve imports and apply correct flags during analysis.

Format:
- Keys are absolute device file paths.
- Values include an includes array and a dmlc_flags array.

**Section sources**
- [README.md](file://README.md#L36-L57)

## Initial Usage Examples
Try these steps to verify the server works:

1. Prepare a small DML device file (see the example device).
2. Optionally prepare a compile commands file pointing to include directories.
3. Start the server in CLI mode and open the device file.
4. Query symbols and definitions to confirm analysis is working.
5. Switch to LSP mode and connect your editor.

Example device file:
- The example device demonstrates device, bank, register, field, and method constructs.

**Section sources**
- [example_files/watchdog_timer.dml](file://example_files/watchdog_timer.dml#L1-L146)
- [src/cmd.rs](file://src/cmd.rs#L230-L246)

## Client Integration
The DLS implements the Language Server Protocol and supports standard LSP features. Clients should:

- Start the server process and communicate over stdin/stdout.
- Send initialize, initialized, and text document open/change/save notifications.
- Handle server capabilities and configuration updates.
- Support workspace folders and configuration requests.

Required LSP messages (selection):
- Notifications: exit, initialized, textDocument/didOpen, textDocument/didChange, textDocument/didSave, workspace/didChangeConfiguration, workspace/didChangeWatchedFiles, cancel
- Requests: shutdown, initialize, textDocument/definition, textDocument/declaration, textDocument/implementation, textDocument/references, textDocument/documentSymbol, textDocument/workspaceSymbol, workspace/symbol
- Server-to-client: client/registerCapability, client/unregisterCapability, textDocument/publishDiagnostics, workspace/configuration

The server publishes experimental capabilities for context control and progress notifications.

**Section sources**
- [clients.md](file://clients.md#L63-L98)
- [clients.md](file://clients.md#L99-L181)
- [src/server/mod.rs](file://src/server/mod.rs#L678-L731)

## Verification Steps
Follow these steps to ensure the server is installed and running correctly:

1. Build the server using the release profile.
2. Confirm the binary exists and is executable.
3. Start the server in CLI mode and observe initialization output.
4. Open a DML file and verify diagnostics and symbol queries.
5. For LSP mode, launch your editor and connect to the server process.
6. Verify workspace folder handling and configuration updates.

**Section sources**
- [README.md](file://README.md#L22-L24)
- [src/cmd.rs](file://src/cmd.rs#L394-L402)
- [src/server/mod.rs](file://src/server/mod.rs#L207-L288)

## Troubleshooting Guide
Common issues and resolutions:

- Cannot find the server binary
  - Ensure you built with the release profile and check the target directory.
  - Reference: [README.md](file://README.md#L22-L24)

- Editor cannot start the server
  - Verify the server executable path and that it can be launched from your shell.
  - Ensure your editor is configured to use the LSP client and connect to stdin/stdout.

- Linting not working
  - Provide a lint configuration file path via CLI or initialization options.
  - Confirm linting is enabled in configuration.

- Imports not resolved
  - Provide a compile commands file with correct include paths and flags.
  - Ensure device files are reachable and the paths match the file system.

- Unknown or duplicated configuration keys
  - The server reports unknown and duplicated keys; adjust your configuration accordingly.
  - Reference: [src/server/mod.rs](file://src/server/mod.rs#L109-L205)

- Device context mode issues
  - Use the CLI to query and set active contexts for specific paths.
  - Reference: [src/cmd.rs](file://src/cmd.rs#L299-L323)

**Section sources**
- [README.md](file://README.md#L22-L24)
- [src/server/mod.rs](file://src/server/mod.rs#L109-L205)
- [src/cmd.rs](file://src/cmd.rs#L299-L323)

## Conclusion
You now have the essentials to build, run, and integrate the DML Language Server. Start with the release build, verify with the CLI mode, and connect your editor using the LSP. Use the compile commands file and lint configuration to tailor the server to your project. For advanced scenarios, explore device context control and workspace configuration.