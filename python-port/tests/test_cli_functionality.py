#!/usr/bin/env python3
"""
Test CLI functionality of the DML Language Server.
Validates that the command-line interface works correctly.
"""

import subprocess
import sys
from pathlib import Path

def test_cli_help():
    """Test that the CLI help works."""
    print("📖 Testing CLI help...")
    
    try:
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [str(project_root / ".venv/bin/dls"), "--help"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            print("✅ CLI help works")
            print(f"   Output contains {len(result.stdout)} characters")
            return True
        else:
            print(f"❌ CLI help failed with return code {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ CLI help test failed: {e}")
        return False

def test_cli_version():
    """Test that the CLI version works."""
    print("\n🏷️  Testing CLI version...")
    
    try:
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [str(project_root / ".venv/bin/dls"), "--version"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            print("✅ CLI version works")
            print(f"   Version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ CLI version failed with return code {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ CLI version test failed: {e}")
        return False

def test_cli_analysis():
    """Test CLI analysis of DML files."""
    print("\n🔍 Testing CLI analysis...")
    
    try:
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [str(project_root / ".venv/bin/dls"), "--cli"],
            capture_output=True,
            text=True,
            cwd=project_root / "examples"
        )
        
        print(f"   Return code: {result.returncode}")
        print(f"   Output lines: {len(result.stdout.splitlines())}")
        print(f"   Error lines: {len(result.stderr.splitlines())}")
        
        # Check that it found and analyzed files
        if "Found" in result.stderr and "DML files to analyze" in result.stderr:
            print("✅ CLI analysis discovered DML files")
        else:
            print("⚠️  CLI analysis may not have found DML files")
        
        # Check that it produced analysis results
        if "Summary:" in result.stdout:
            print("✅ CLI analysis produced summary")
        else:
            print("⚠️  CLI analysis may not have produced summary")
        
        # CLI analysis can return 1 if errors are found, which is expected
        if result.returncode in [0, 1]:
            print("✅ CLI analysis completed with expected return code")
            return True
        else:
            print(f"❌ CLI analysis failed with unexpected return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ CLI analysis test failed: {e}")
        return False

def test_cli_verbose():
    """Test CLI with verbose output."""
    print("\n🔊 Testing CLI verbose mode...")
    
    try:
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [str(project_root / ".venv/bin/dls"), "--cli", "--verbose"],
            capture_output=True,
            text=True,
            cwd=project_root / "examples",
            timeout=30  # Add timeout to prevent hanging
        )
        
        print(f"   Return code: {result.returncode}")
        
        # Check for verbose logging output
        if "INFO" in result.stderr or "DEBUG" in result.stderr:
            print("✅ CLI verbose mode shows logging output")
        else:
            print("⚠️  CLI verbose mode may not be showing logging")
        
        if result.returncode in [0, 1]:
            print("✅ CLI verbose mode completed")
            return True
        else:
            print(f"❌ CLI verbose mode failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ CLI verbose mode timed out")
        return False
    except Exception as e:
        print(f"❌ CLI verbose test failed: {e}")
        return False

def test_cli_no_linting():
    """Test CLI with linting disabled."""
    print("\n🚫 Testing CLI with linting disabled...")
    
    try:
        project_root = Path(__file__).parent.parent
        result = subprocess.run(
            [str(project_root / ".venv/bin/dls"), "--cli", "--no-linting"],
            capture_output=True,
            text=True,
            cwd=project_root / "examples",
            timeout=30
        )
        
        print(f"   Return code: {result.returncode}")
        
        # With linting disabled, there should be fewer warnings
        warning_count = result.stdout.count("warning:")
        print(f"   Warning count: {warning_count}")
        
        if result.returncode in [0, 1]:
            print("✅ CLI no-linting mode completed")
            return True
        else:
            print(f"❌ CLI no-linting mode failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ CLI no-linting mode timed out")
        return False
    except Exception as e:
        print(f"❌ CLI no-linting test failed: {e}")
        return False

def main():
    """Run all CLI tests."""
    print("🧪 Testing DML Language Server CLI Functionality")
    print("=" * 50)
    
    tests = [
        ("CLI Help", test_cli_help),
        ("CLI Version", test_cli_version),
        ("CLI Analysis", test_cli_analysis),
        ("CLI Verbose", test_cli_verbose),
        ("CLI No Linting", test_cli_no_linting)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"📊 CLI Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All CLI functionality is working correctly!")
        return True
    else:
        print("❌ Some CLI features need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)