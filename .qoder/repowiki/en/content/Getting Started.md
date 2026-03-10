# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [USAGE.md](file://USAGE.md)
- [Cargo.toml](file://Cargo.toml)
- [clients.md](file://clients.md)
- [src/main.rs](file://src/main.rs)
- [src/cmd.rs](file://src/cmd.rs)
- [src/config.rs](file://src/config.rs)
- [src/lint/mod.rs](file://src/lint/mod.rs)
- [example_files/watchdog_timer.dml](file://example_files/watchdog_timer.dml)
- [example_files/example_lint_cfg.json](file://example_files/example_lint_cfg.json)
- [example_files/example_lint_cfg.README](file://example_files/example_lint_cfg.README)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Basic Configuration](#basic-configuration)
5. [Initial Usage](#initial-usage)
6. [DML Compile Commands File Format](#dml-compile-commands-file-format)
7. [Lint Configuration](#lint-configuration)
8. [IDE Integration](#ide-integration)
9. [Practical Examples](#practical-examples)
10. [Verification and Testing](#verification-and-testing)
11. [Troubleshooting](#troubleshooting)
12. [Conclusion](#conclusion)

## Introduction
This guide helps you install, configure, and use the DML Language Server (DLS). It covers building from source, configuring compile commands and linting, integrating with an editor via the Language Server Protocol (LSP), and verifying your setup with sample DML files.

Key capabilities include:
- Syntax diagnostics
- Symbol search and navigation (go-to-definition, references, implementations)
- Basic configurable linting
- MCP (Model Context Protocol) server for AI-assisted development

Important note: DLS supports DML 1.4 only.

**Section sources**
- [README.md](file://README.md#L1-L57)
- [USAGE.md](file://USAGE.md#L1-L120)

## Prerequisites
- Install Rust toolchain (stable) to build the server from source.
- Basic understanding of the Language Server Protocol (LSP).
- Familiarity with DML language constructs and DML 1.4 syntax.
- An editor or IDE that speaks LSP (e.g., VS Code, Neovim, Emacs).

**Section sources**
- [README.md](file://README.md#L18-L21)

## Installation
Build the DML Language Server in release mode using Cargo.

- Build command:
  - cargo build --release

This produces the dls binary in target/release/. You can run it directly or integrate it with your editor as an LSP server.

Notes:
- The project defines multiple binaries: dls (main LSP server), dfa (device file analyzer), and dml-mcp-server (MCP server).
- The LSP server communicates over stdio using the Language Server Protocol.

**Section sources**
- [README.md](file://README.md#L22-L24)
- [Cargo.toml](file://Cargo.toml#L18-L31)
- [src/main.rs](file://src/main.rs#L15-L59)

## Basic Configuration
The DLS accepts configuration via LSP initialization options and runtime configuration updates. The configuration object includes fields for linting, compile info, analysis behavior, and device context modes.

Key configuration areas:
- Linting enablement and configuration file path
- Compile info file path for import resolution
- Analysis retention duration and context modes
- Debug logging level

Configuration fields and defaults are defined in the configuration module. The LSP client should send workspace/didChangeConfiguration when settings change.

**Section sources**
- [src/config.rs](file://src/config.rs#L120-L227)
- [clients.md](file://clients.md#L32-L38)

## Initial Usage
There are two primary ways to use the DLS:
- As an LSP server integrated into your editor
- In command-line mode for interactive analysis

LSP server:
- Start the dls binary; it listens on stdio for LSP messages.
- Configure your editor to launch dls and point it at your DML project root.

Command-line mode:
- Start dls with --cli to enter interactive mode.
- Use commands like open, def, symbol, document, workspace, context-mode, contexts, set-contexts, wait, help, and quit.

Interactive commands overview:
- open <file>: Open a DML file to trigger initial analysis.
- def <file> <row> <col>: Resolve go-to-definition at a position.
- symbol <query>: Search workspace symbols.
- document <file>: List document symbols.
- workspace <dir...>: Add workspace folders.
- context-mode <mode>: Set device context mode.
- contexts <paths...>: Query known contexts.
- set-contexts <paths...>: Activate specific contexts.
- wait <ms>: Pause to let analysis complete.
- help/quit: Show help or exit.

**Section sources**
- [src/main.rs](file://src/main.rs#L21-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [src/cmd.rs](file://src/cmd.rs#L405-L443)

## DML Compile Commands File Format
The DML compile commands file is a JSON document used to provide per-device import resolution and DMLC flags. It enables the server to locate included files and pass appropriate flags during analysis.

Format:
- Root object maps absolute device file paths to entries.
- Each entry has:
  - includes: Array of absolute include directory paths
  - dmlc_flags: Array of flags passed to DMLC invocations

Typical generation:
- Auto-generated by CMake when exporting compile commands. Set the environment variable to enable export before invoking CMake.

How it is used:
- The server reads this file to augment include search paths and to apply device-specific flags for accurate import resolution and analysis.

**Section sources**
- [README.md](file://README.md#L36-L57)

## Lint Configuration
The DLS supports configurable linting with a JSON configuration file. You can enable/disable rules, adjust rule parameters, and annotate diagnostics with the rule name.

Configuration file:
- example_files/example_lint_cfg.json demonstrates a comprehensive set of rules and parameters.
- example_files/example_lint_cfg.README explains how to structure the file and interpret defaults.

Inline lint control:
- You can suppress specific rules for a file or a single line using in-line comments in DML files. Supported commands:
  - allow-file=<rule>: Suppress a rule for the entire file.
  - allow=<rule>: Suppress a rule for the next line without leading text, or for the current line if declared outside a leading comment.

Default behavior:
- The server ships with a default lint configuration. If you do not specify a lint config file, the defaults are applied.

Lint parsing and validation:
- The server parses the lint configuration file and reports unknown fields.
- It applies indentation and line-length settings consistently across the codebase.

**Section sources**
- [USAGE.md](file://USAGE.md#L87-L120)
- [src/lint/mod.rs](file://src/lint/mod.rs#L49-L76)
- [src/lint/mod.rs](file://src/lint/mod.rs#L135-L184)
- [example_files/example_lint_cfg.json](file://example_files/example_lint_cfg.json#L1-L28)
- [example_files/example_lint_cfg.README](file://example_files/example_lint_cfg.README#L1-L32)

## IDE Integration
The DLS implements the Language Server Protocol and can be integrated into editors that support LSP. The repository provides guidance for implementing clients and lists required LSP messages and optional extensions.

Steps:
- Ensure your editor has LSP support or a library that implements LSP.
- Launch the DLS binary and point your editor’s LSP client to it.
- Send workspace/didChangeConfiguration when settings change.
- Optionally, use the MCP server for AI-assisted development.

Required LSP messages (selected):
- Notifications: exit, initialized, textDocument/didOpen, textDocument/didChange, textDocument/didSave, workspace/didChangeConfiguration, workspace/didChangeWatchedFiles, cancel
- Requests: shutdown, initialize, textDocument/definition, textDocument/declaration, textDocument/implementation, textDocument/references, textDocument/documentSymbol, textDocument/workspaceSymbol, workspace/symbol
- Server-to-client: client/registerCapability, client/unregisterCapability, textDocument/publishDiagnostics, workspace/configuration (pull-style), window/progress

Optional extensions:
- $/changeActiveContexts and $/getKnownContexts for controlling active device contexts and semantic analysis scopes.

Client implementation guidance:
- Review the clients.md guide for detailed requirements and recommended client-side configuration.

**Section sources**
- [clients.md](file://clients.md#L63-L98)
- [clients.md](file://clients.md#L99-L181)

## Practical Examples
Use the sample DML file and lint configuration to validate your setup.

Sample DML file:
- example_files/watchdog_timer.dml is a complete DML 1.4 device with banks, registers, and methods. Open this file in your editor to trigger diagnostics and symbol queries.

Lint configuration:
- example_files/example_lint_cfg.json provides a baseline configuration. Copy it to your project and adjust parameters as needed.
- example_files/example_lint_cfg.README explains how to enable/disable rules and configure indentation and line length.

Inline lint control:
- Add in-line comments in DML files to temporarily suppress specific rules for demonstration or exceptional cases.

**Section sources**
- [example_files/watchdog_timer.dml](file://example_files/watchdog_timer.dml#L1-L146)
- [example_files/example_lint_cfg.json](file://example_files/example_lint_cfg.json#L1-L28)
- [example_files/example_lint_cfg.README](file://example_files/example_lint_cfg.README#L1-L32)
- [USAGE.md](file://USAGE.md#L87-L120)

## Verification and Testing
Confirm successful installation and basic functionality:

- Build verification:
  - cargo build --release completes without errors and produces the dls binary.

- LSP server verification:
  - Start dls; it should accept LSP initialize and respond with capabilities.
  - Open a DML file in your editor; expect diagnostics and symbol navigation to work.

- Command-line mode verification:
  - Run dls --cli to enter interactive mode.
  - Use open <file> to load a DML file.
  - Use def <file> <row> <col> to resolve definitions.
  - Use symbol <query> and document <file> to explore symbols.
  - Use context-mode, contexts, and set-contexts to manage device contexts.

- Lint verification:
  - Point the server to a lint configuration file via configuration.
  - Confirm that lint warnings appear and that inline annotations suppress warnings as intended.

- MCP server verification (optional):
  - Build and run the MCP server using the MCP_SERVER_GUIDE.md instructions.
  - Test tool listing and generation commands to validate AI-assisted development features.

**Section sources**
- [README.md](file://README.md#L22-L24)
- [src/main.rs](file://src/main.rs#L21-L59)
- [src/cmd.rs](file://src/cmd.rs#L46-L140)
- [USAGE.md](file://USAGE.md#L87-L120)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L9-L33)

## Troubleshooting
Common setup issues and resolutions:

- Missing Rust toolchain:
  - Ensure Rust (stable) is installed and up to date. Rebuild with cargo build --release.

- Editor cannot connect to LSP:
  - Verify the dls binary path in your editor’s LSP configuration.
  - Ensure the editor sends workspace/didChangeConfiguration when settings change.

- Diagnostics not appearing:
  - Confirm the DML file declares dml 1.4.
  - Ensure the compile commands file is present and correctly formatted.
  - Check that include paths in the compile commands file point to actual directories.

- Lint configuration not applied:
  - Validate the lint configuration JSON syntax.
  - Confirm the lint configuration file path is provided to the server via configuration.
  - Use workspace/configuration or didChangeConfiguration to refresh settings.

- Inline lint annotations not working:
  - Ensure the comment syntax is exactly // dls-lint: <command>=<target>.
  - Place the comment on its own line or immediately after the code line for allow behavior.

- MCP server issues:
  - Follow the MCP_SERVER_GUIDE.md steps to build and run the MCP server.
  - Use the provided test commands to validate server capabilities and tool execution.

**Section sources**
- [USAGE.md](file://USAGE.md#L87-L120)
- [clients.md](file://clients.md#L32-L38)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L9-L33)

## Conclusion
You now have the essentials to install, configure, and use the DML Language Server. Start with cargo build --release, set up your compile commands and lint configuration, integrate with your editor via LSP, and verify functionality using the sample DML file. For advanced AI-assisted development, explore the MCP server as documented.

**Section sources**
- [README.md](file://README.md#L1-L57)
- [USAGE.md](file://USAGE.md#L1-L120)
- [MCP_SERVER_GUIDE.md](file://MCP_SERVER_GUIDE.md#L1-L280)