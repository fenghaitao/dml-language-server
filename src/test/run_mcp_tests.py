#!/usr/bin/env python3
"""
Test runner for DML MCP Server test suite
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_test(test_script):
    """Run a single test script"""
    print(f"\n{'='*60}")
    print(f"Running: {test_script}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_script],
            cwd=Path(__file__).parent.parent.parent,  # Run from project root
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {test_script} PASSED")
            return True
        else:
            print(f"❌ {test_script} FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error running {test_script}: {e}")
        return False

def build_mcp_server():
    """Build the MCP server before running tests"""
    print("🔨 Building DML MCP Server...")
    
    try:
        result = subprocess.run(
            ["cargo", "build", "--bin", "dml-mcp-server"],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Build successful")
            return True
        else:
            print("❌ Build failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def main():
    """Run all MCP tests"""
    print("🧪 DML MCP Server Test Suite")
    print("=" * 60)
    
    # Build first
    if not build_mcp_server():
        print("❌ Cannot run tests without successful build")
        sys.exit(1)
    
    # Test scripts to run
    test_dir = Path(__file__).parent
    tests = [
        test_dir / "mcp_basic_test.py",
        test_dir / "mcp_advanced_test.py",
    ]
    
    # Run tests
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test.exists():
            if run_test(str(test)):
                passed += 1
        else:
            print(f"❌ Test file not found: {test}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()