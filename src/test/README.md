# DML MCP Server Test Suite

This directory contains comprehensive tests for the DML MCP (Model Context Protocol) Server.

## Test Files

### Python Integration Tests

#### `mcp_basic_test.py`
- **Purpose**: Basic functionality testing of the MCP server
- **Tests**:
  - Server initialization and protocol handshake
  - Tool discovery and listing
  - Basic device generation
  - JSON-RPC communication protocol
- **Usage**: `python3 src/test/mcp_basic_test.py`

#### `mcp_advanced_test.py`
- **Purpose**: Advanced functionality and complex code generation
- **Tests**:
  - Complex peripheral device generation (UART controller)
  - Register generation with fields and bit ranges
  - CPU device generation
  - Memory device generation
  - Multiple device types and templates
- **Usage**: `python3 src/test/mcp_advanced_test.py`

#### `run_mcp_tests.py`
- **Purpose**: Test runner for the entire test suite
- **Features**:
  - Automatic build before testing
  - Sequential test execution
  - Pass/fail reporting
  - Summary statistics
- **Usage**: `python3 src/test/run_mcp_tests.py`

### Rust Unit Tests

#### `mcp_unit_tests.rs`
- **Purpose**: Unit tests for individual MCP components
- **Tests**:
  - Tool registry functionality
  - Code generation engine
  - Template system
  - MCP protocol handlers
- **Usage**: `cargo test mcp_tests`

## Running Tests

### Quick Start
```bash
# Run all tests with the test runner
python3 src/test/run_mcp_tests.py

# Or run individual tests
python3 src/test/mcp_basic_test.py
python3 src/test/mcp_advanced_test.py

# Run Rust unit tests
cargo test mcp_tests
```

### Prerequisites
1. **Build the MCP server**:
   ```bash
   cargo build --bin dml-mcp-server
   ```

2. **Python 3.x** with `json` and `subprocess` modules (standard library)

### Manual Testing
You can also test the MCP server manually using any MCP client:

```bash
# Start the server
./target/debug/dml-mcp-server

# Send JSON-RPC messages via stdin
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05"}}' | ./target/debug/dml-mcp-server
```

## Test Coverage

### Protocol Testing
- ✅ MCP protocol compliance (2024-11-05)
- ✅ JSON-RPC message handling
- ✅ Error handling and responses
- ✅ Server capabilities negotiation

### Tool Testing
- ✅ `generate_device` - Device generation with registers and interfaces
- ✅ `generate_register` - Register generation with fields
- ✅ `generate_method` - Method implementation generation
- ✅ `analyze_project` - Project analysis capabilities
- ✅ `validate_code` - Code validation features
- ✅ `generate_template` - Template generation
- ✅ `apply_pattern` - Pattern application

### Code Generation Testing
- ✅ Basic device templates (CPU, memory, peripheral)
- ✅ Complex register structures with bit fields
- ✅ Interface implementation
- ✅ Documentation generation
- ✅ Proper DML 1.4 syntax
- ✅ Template inheritance and customization

## Expected Output

### Successful Test Run
```
🧪 DML MCP Server Test Suite
============================================================
🔨 Building DML MCP Server...
✅ Build successful

============================================================
Running: mcp_basic_test.py
============================================================
🚀 Testing DML MCP Server
==================================================
✅ MCP server started
✅ Initialize successful
✅ Found 7 tools
✅ Device generation successful
✅ Test completed successfully!
✅ mcp_basic_test.py PASSED

============================================================
Running: mcp_advanced_test.py
============================================================
🚀 Advanced DML MCP Server Test
============================================================
✅ Complex device generated successfully!
✅ Register with fields generated!
✅ CPU device generated!
✅ Memory device generated!
✅ Advanced test completed successfully!
✅ mcp_advanced_test.py PASSED

============================================================
TEST SUMMARY
============================================================
Passed: 2/2
Failed: 0/2
🎉 All tests passed!
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Ensure dependencies are up to date
   cargo update
   cargo build --bin dml-mcp-server
   ```

2. **Server Not Starting**
   - Check that the binary exists: `ls -la target/debug/dml-mcp-server`
   - Verify permissions: `chmod +x target/debug/dml-mcp-server`

3. **Test Timeouts**
   - Server may be taking longer to start
   - Check system resources and try again

4. **JSON Parse Errors**
   - Indicates protocol mismatch
   - Verify MCP protocol version compatibility

### Debug Mode
Set environment variable for verbose logging:
```bash
RUST_LOG=debug python3 src/test/mcp_basic_test.py
```

## Contributing

When adding new tests:

1. **Python Tests**: Add to existing files or create new test files
2. **Rust Tests**: Add unit tests to `mcp_unit_tests.rs`
3. **Update**: Update this README with new test descriptions
4. **Test Runner**: Add new test files to `run_mcp_tests.py`

### Test Naming Convention
- Python: `mcp_<category>_test.py`
- Rust: `#[cfg(test)] mod mcp_<category>_tests`