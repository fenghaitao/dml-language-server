# DML Language Server - Python Port

A Python implementation of the DML (Device Modeling Language) Language Server, originally written in Rust. This server provides IDE support for DML files used in Intel Simics device modeling.

## Features

- **Language Server Protocol (LSP)** support for DML files
- **Syntax and semantic analysis** with error reporting
- **Go-to-definition**, **find references**, and **hover** support
- **Symbol navigation** and **completion**
- **Configurable linting** with built-in rules
- **Dependency analysis** and circular dependency detection
- **Code metrics** and analysis reporting
- **MCP (Model Context Protocol)** server for AI-assisted development
- **Command-line tools** for batch analysis

## Installation

### From Source

```bash
cd python-port
pip install -e .
```

### Development Installation

```bash
cd python-port
pip install -e ".[dev]"
```

## Usage

### Language Server

Start the DML Language Server for IDE integration:

```bash
dls
```

For command-line analysis:

```bash
dls --cli --compile-info compile_commands.json
```

### Device File Analyzer (DFA)

Analyze DML files for errors, metrics, and dependencies:

```bash
# Analyze a single file
dfa analyze my_device.dml

# Analyze a directory recursively
dfa analyze -r src/ --format detailed

# Check for circular dependencies
dfa analyze src/ --check-deps

# Generate JSON report
dfa analyze src/ --format json -o report.json

# Show dependencies for a file
dfa deps my_device.dml
```

### MCP Server

Start the MCP server for AI-assisted development:

```bash
dml-mcp-server --compile-info compile_commands.json
```

## Configuration

### Compile Commands

Create a `compile_commands.json` file to specify include paths and compiler flags:

```json
{
  "/path/to/device.dml": {
    "includes": ["/path/to/include1", "/path/to/include2"],
    "dmlc_flags": ["-flag1", "-flag2"]
  }
}
```

### Lint Configuration

Create a `lint_config.json` file to configure linting rules:

```json
{
  "enabled_rules": ["indentation", "spacing", "naming"],
  "disabled_rules": [],
  "rule_configs": {
    "indentation": {
      "indent_size": 4
    },
    "naming": {
      "level": "warning"
    }
  }
}
```

### LSP Initialization Options

Configure the language server through your IDE's LSP settings:

```json
{
  "compile_commands_file": "/path/to/compile_commands.json",
  "linting_enabled": true,
  "lint_config_file": "/path/to/lint_config.json",
  "max_diagnostics_per_file": 100,
  "log_level": "info"
}
```

## IDE Integration

### VS Code

Install a generic LSP extension and configure it to use `dls`:

```json
{
  "languageServerExample.server": {
    "command": "dls",
    "args": [],
    "filetypes": ["dml"]
  }
}
```

### Neovim

Using `nvim-lspconfig`:

```lua
require'lspconfig'.dml_ls.setup{
  cmd = {"dls"},
  filetypes = {"dml"},
  root_dir = require'lspconfig'.util.root_pattern("compile_commands.json", ".git"),
}
```

### Emacs

Using `lsp-mode`:

```elisp
(add-to-list 'lsp-language-id-configuration '(dml-mode . "dml"))

(lsp-register-client
 (make-lsp-client :new-connection (lsp-stdio-connection "dls")
                  :major-modes '(dml-mode)
                  :server-id 'dml-ls))
```

## Architecture

The Python port maintains the same architecture as the original Rust implementation:

- **VFS (Virtual File System)**: Manages file operations and change tracking
- **Analysis Engine**: Performs parsing and semantic analysis
- **LSP Server**: Handles Language Server Protocol communication
- **Lint Engine**: Configurable code quality checks
- **MCP Server**: Model Context Protocol for AI integration
- **CLI Tools**: Batch analysis and reporting

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black dml_language_server/

# Sort imports
isort dml_language_server/

# Type checking
mypy dml_language_server/

# Linting
flake8 dml_language_server/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Differences from Rust Version

While maintaining functional compatibility, this Python port has some differences:

- **Performance**: Python is slower than Rust, but still suitable for most use cases
- **Memory Usage**: Higher memory usage due to Python's runtime
- **Dependencies**: Uses Python ecosystem libraries (pygls, lsprotocol, etc.)
- **Async**: Uses Python's asyncio instead of Rust's tokio
- **Error Handling**: Uses Python exceptions instead of Rust's Result type

## Dependencies

- **Python 3.8+**
- **pygls**: Language Server Protocol implementation
- **lsprotocol**: LSP types and protocol definitions
- **click**: Command-line interface
- **pydantic**: Data validation
- **aiofiles**: Async file operations
- **watchdog**: File system monitoring
- **regex**: Advanced regular expressions

## License

Licensed under either:

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT License ([LICENSE-MIT](LICENSE-MIT))

at your option.

## Acknowledgments

This Python port is based on the original Rust implementation of the DML Language Server developed by Intel Corporation. The architecture and functionality closely follow the original design while adapting to Python idioms and ecosystems.