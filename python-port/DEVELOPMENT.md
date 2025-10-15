# Development Guide

This document provides guidance for developing and contributing to the DML Language Server Python port.

## Project Structure

```
python-port/
├── dml_language_server/          # Main package
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # Main CLI entry point
│   ├── config.py                 # Configuration management
│   ├── cmd.py                    # CLI commands
│   ├── file_management.py        # File discovery and management
│   ├── lsp_data.py              # LSP data structures
│   ├── analysis/                 # Analysis engine
│   │   ├── __init__.py          # Core analysis logic
│   │   └── parsing/             # DML parsing
│   │       ├── __init__.py      # Lexer and parser
│   │       └── parser.py        # (additional parsing logic)
│   ├── lint/                    # Linting engine
│   │   └── __init__.py          # Lint rules and engine
│   ├── server/                  # LSP server
│   │   └── __init__.py          # Language server implementation
│   ├── span/                    # Position and range handling
│   │   └── __init__.py          # Span utilities
│   ├── vfs/                     # Virtual file system
│   │   └── __init__.py          # File caching and watching
│   ├── mcp/                     # Model Context Protocol
│   │   ├── __init__.py          # MCP server implementation
│   │   └── main.py              # MCP CLI entry point
│   └── dfa/                     # Device File Analyzer
│       ├── __init__.py          # Analysis tools
│       └── main.py              # DFA CLI entry point
├── tests/                       # Test suite
├── examples/                    # Example files
├── pyproject.toml              # Project configuration
├── README.md                   # Main documentation
└── DEVELOPMENT.md              # This file
```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- git

### Installation for Development

1. Clone the repository:
```bash
git clone <repository-url>
cd dml-language-server/python-port
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e ".[dev]"
```

4. Verify installation:
```bash
python test_installation.py
```

## Development Workflow

### Code Style

The project uses several tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

Run all checks:
```bash
# Format code
black dml_language_server/
isort dml_language_server/

# Check formatting (without changing)
black --check dml_language_server/
isort --check-only dml_language_server/

# Lint code
flake8 dml_language_server/

# Type checking
mypy dml_language_server/
```

### Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dml_language_server

# Run specific test file
pytest tests/test_basic.py

# Run with verbose output
pytest -v
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks:
```bash
pre-commit install
```

This will run black, isort, flake8, and mypy before each commit.

## Architecture Overview

### Core Components

1. **VFS (Virtual File System)**: Manages file operations, caching, and change detection
2. **Analysis Engine**: Performs parsing, semantic analysis, and symbol resolution
3. **LSP Server**: Handles Language Server Protocol communication
4. **Lint Engine**: Configurable code quality checking
5. **MCP Server**: Model Context Protocol for AI integration
6. **CLI Tools**: Command-line interfaces for batch operations

### Key Design Principles

- **Async-first**: Uses Python's asyncio for concurrent operations
- **Modular**: Components are loosely coupled and testable
- **Configurable**: Extensive configuration options
- **Performance**: Efficient caching and incremental analysis
- **Extensible**: Plugin architecture for lint rules and analysis

### Data Flow

1. **File Change** → VFS detects change → Invalidates cache
2. **LSP Request** → Server → Analysis Engine → Response
3. **Analysis** → Parser → Symbol Table → Diagnostics
4. **Linting** → Lint Engine → Rules → Warnings/Errors

## Adding New Features

### Adding a New Lint Rule

1. Create a new rule class in `lint/__init__.py`:

```python
class MyCustomRule(LintRule):
    def __init__(self):
        super().__init__(
            name="my_custom_rule",
            description="Description of what this rule checks",
            level=LintRuleLevel.WARNING
        )
    
    def check(self, file_path: Path, content: str, analysis: IsolatedAnalysis) -> List[DMLError]:
        errors = []
        # Rule implementation here
        return errors
```

2. Register the rule in `LintEngine._register_default_rules()`:

```python
def _register_default_rules(self) -> None:
    self.rules = [
        IndentationRule(),
        SpacingRule(),
        NamingConventionRule(),
        MyCustomRule(),  # Add your rule here
    ]
```

3. Add tests in `tests/test_lint.py`
4. Update documentation

### Adding a New LSP Feature

1. Add the capability to `ServerCapabilities` in `server/__init__.py`
2. Implement the handler in `DMLLanguageServer._register_handlers()`
3. Add corresponding data structures in `lsp_data.py` if needed
4. Add tests

### Adding a New MCP Tool

1. Add the tool method to `DMLMCPServer` in `mcp/__init__.py`
2. Register it in the `tools` dictionary
3. Add tool info to `_handle_tools_list()`
4. Add tests

## Debugging

### Enable Debug Logging

```bash
# Language server
dls --verbose

# DFA tool
dfa analyze --verbose sample.dml

# MCP server
dml-mcp-server --verbose --log-file debug.log
```

### IDE Integration Testing

Test the language server with a real editor:

1. Start the server manually:
```bash
dls --verbose 2> debug.log
```

2. Configure your IDE to connect to stdin/stdout
3. Check `debug.log` for diagnostics

### Common Issues

- **Import errors**: Check Python path and virtual environment
- **Async issues**: Use `asyncio.run()` for testing async functions
- **File watching**: Ensure proper cleanup of file watchers
- **Memory leaks**: Clear caches and close resources properly

## Performance Considerations

### Caching Strategy

- **File cache**: VFS caches file contents
- **Analysis cache**: Parsed symbols and errors cached per file
- **Dependency cache**: File dependency graph cached
- **Invalidation**: Smart invalidation based on file changes

### Optimization Tips

- Use incremental parsing when possible
- Limit diagnostic count per file
- Implement request cancellation for LSP
- Use efficient data structures for symbol lookups

## Testing Strategy

### Test Categories

1. **Unit tests**: Individual component testing
2. **Integration tests**: Component interaction testing
3. **LSP tests**: Protocol compliance testing
4. **Performance tests**: Benchmarking and profiling
5. **Example tests**: Real-world usage testing

### Test Data

- Use `examples/` directory for test files
- Create minimal reproducible test cases
- Test both valid and invalid DML syntax
- Test error conditions and edge cases

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run the full test suite: `pytest`
5. Run code quality checks: `black`, `isort`, `flake8`, `mypy`
6. Commit with descriptive messages
7. Push to your fork and create a pull request

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: feat, fix, docs, style, refactor, test, chore

Examples:
- `feat(parser): add support for DML 1.5 syntax`
- `fix(vfs): resolve file watching memory leak`
- `docs(readme): update installation instructions`

### Code Review Guidelines

- All code must be reviewed before merging
- Tests must pass and coverage should not decrease
- Follow established patterns and conventions
- Document public APIs and complex logic
- Consider performance and security implications

## Release Process

1. Update version in `pyproject.toml` and `__init__.py`
2. Update `CHANGELOG.md` with new features and fixes
3. Create release branch: `git checkout -b release/v0.9.15`
4. Run full test suite and quality checks
5. Create tag: `git tag v0.9.15`
6. Push tag and create GitHub release
7. Build and publish to PyPI (if applicable)

## Troubleshooting

### Common Development Issues

**Import circular dependencies**:
- Check import order in `__init__.py` files
- Use delayed imports when necessary

**Async/await issues**:
- Ensure async functions are awaited
- Use `asyncio.run()` for top-level async calls

**LSP protocol errors**:
- Check JSON-RPC message format
- Validate against LSP specification
- Use LSP client debugging tools

**Performance problems**:
- Profile with `cProfile` or `py-spy`
- Check for unnecessary file system operations
- Optimize hot code paths

### Getting Help

- Check the issue tracker for similar problems
- Read the original Rust implementation for reference
- Consult LSP and MCP specifications
- Ask questions in development discussions