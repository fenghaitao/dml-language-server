# DML Language Server Tests

This directory contains comprehensive tests for the DML Language Server functionality.

## Test Files

### `test_lsp_components.py`
Tests the core LSP components without starting a full server:
- Component initialization (Config, VFS, FileManager, Analysis, Lint engines)
- File analysis and symbol extraction
- LSP data conversions (URI handling, diagnostics)
- Server creation and capabilities

**Usage:**
```bash
python tests/test_lsp_components.py
```

### `test_advanced_lsp_features.py`
Tests advanced LSP features with realistic scenarios:
- **Code Completion**: Context-aware suggestions in device, register bank, and field contexts
- **Hover Information**: Rich markdown content with symbol details and documentation
- **Go-to-Definition**: Symbol navigation and cross-file resolution
- **Document Symbols**: File outline and symbol hierarchy extraction

**Usage:**
```bash
python tests/test_advanced_lsp_features.py
```

### `test_cli_functionality.py`
Tests the command-line interface:
- CLI help and version commands
- File analysis in CLI mode
- Verbose logging output
- Linting enable/disable functionality

**Usage:**
```bash
python tests/test_cli_functionality.py
```

### `test_error_handling.py`
Tests error detection, formatting, and reporting:
- Error attribute access and positioning
- Error to diagnostic conversion
- CLI error message formatting
- Lint warning formatting
- Edge case handling

**Usage:**
```bash
python tests/test_error_handling.py
```

## Running All Tests

To run all tests sequentially:

```bash
# Run individual test suites
python tests/test_lsp_components.py
python tests/test_advanced_lsp_features.py
python tests/test_cli_functionality.py
python tests/test_error_handling.py
```

Or run them with pytest if you prefer:

```bash
pytest tests/ -v
```

## Test Requirements

The tests require:
- DML Language Server installed in `.venv/bin/dls`
- Example DML files in `examples/` directory:
  - `examples/sample_device.dml`
  - `examples/utility.dml`
- All dependencies from `pyproject.toml` installed

## Expected Results

All tests should pass with the current implementation:

- **LSP Components**: ✅ 2/2 tests passed
- **Advanced LSP Features**: ✅ 4/4 tests passed  
- **CLI Functionality**: ✅ 5/5 tests passed
- **Error Handling**: ✅ 5/5 tests passed

## Test Coverage

The tests cover:

### Core Functionality
- ✅ Configuration management
- ✅ Virtual file system (VFS)
- ✅ File management and discovery
- ✅ Device analysis engine
- ✅ Lint engine with rules

### LSP Features
- ✅ Intelligent code completion
- ✅ Rich hover information
- ✅ Go-to-definition navigation
- ✅ Document symbol extraction
- ✅ Cross-file symbol resolution
- ✅ Real-time diagnostics

### Analysis Capabilities
- ✅ Syntax and semantic analysis
- ✅ Symbol table generation
- ✅ Error detection and reporting
- ✅ Linting with multiple rule types
- ✅ Position and span tracking

### CLI Interface
- ✅ Command-line argument parsing
- ✅ File discovery and batch analysis
- ✅ Error and warning reporting
- ✅ Verbose logging modes
- ✅ Exit code handling

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention: `test_*.py`
2. Include descriptive docstrings
3. Use emoji indicators for test progress (🧪 🔍 ✅ ❌)
4. Handle exceptions gracefully with detailed error messages
5. Return boolean success/failure for each test function
6. Add the new test file to this README

## Troubleshooting

If tests fail:

1. **Import errors**: Ensure the virtual environment is activated and dependencies are installed
2. **File not found**: Check that example DML files exist in `examples/` directory
3. **Permission errors**: Ensure `.venv/bin/dls` is executable
4. **Path issues**: Tests assume they're run from the project root directory

## Integration with CI/CD

These tests can be integrated into continuous integration pipelines:

```yaml
# Example GitHub Actions step
- name: Run DLS Tests
  run: |
    python tests/test_lsp_components.py
    python tests/test_advanced_lsp_features.py
    python tests/test_cli_functionality.py
    python tests/test_error_handling.py
```