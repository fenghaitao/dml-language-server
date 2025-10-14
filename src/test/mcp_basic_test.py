#!/usr/bin/env python3
"""
Basic test script for the DML MCP Server
"""

import json
import subprocess
import sys
import time

def send_json_rpc(proc, method, params=None, id_val=1):
    """Send a JSON-RPC message to the MCP server"""
    message = {
        "jsonrpc": "2.0",
        "method": method,
        "id": id_val
    }
    if params:
        message["params"] = params
    
    message_str = json.dumps(message) + "\n"
    print(f"→ Sending: {message_str.strip()}")
    
    proc.stdin.write(message_str.encode())
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline().decode().strip()
    print(f"← Received: {response_line}")
    
    try:
        return json.loads(response_line)
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return None

def test_mcp_server():
    """Test the DML MCP server"""
    print("🚀 Testing DML MCP Server")
    print("=" * 50)
    
    # Start the MCP server
    try:
        proc = subprocess.Popen(
            ["./target/debug/dml-mcp-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        
        print("✅ MCP server started")
        
        # Test 1: Initialize
        print("\n📋 Test 1: Initialize")
        response = send_json_rpc(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            print("✅ Initialize successful")
            print(f"   Server: {response['result'].get('serverInfo', {}).get('name', 'unknown')}")
            print(f"   Version: {response['result'].get('serverInfo', {}).get('version', 'unknown')}")
        else:
            print("❌ Initialize failed")
            return False
        
        # Test 2: List tools
        print("\n🔧 Test 2: List Tools")
        response = send_json_rpc(proc, "tools/list", {})
        
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
        else:
            print("❌ List tools failed")
            return False
        
        # Test 3: Generate device
        print("\n🎛️  Test 3: Generate Device")
        response = send_json_rpc(proc, "tools/call", {
            "name": "generate_device",
            "arguments": {
                "device_name": "test_peripheral",
                "device_type": "peripheral",
                "registers": [
                    {
                        "name": "control",
                        "size": 4,
                        "offset": "0x00"
                    }
                ]
            }
        })
        
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                print("✅ Device generation successful")
                print("Generated code preview:")
                print("-" * 40)
                print(content[0]["text"][:200] + "..." if len(content[0]["text"]) > 200 else content[0]["text"])
                print("-" * 40)
            else:
                print("❌ No content generated")
        else:
            print("❌ Device generation failed")
        
        # Close the server
        proc.terminate()
        proc.wait(timeout=5)
        print("\n✅ Test completed successfully!")
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Server didn't respond in time")
        proc.kill()
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        if 'proc' in locals():
            proc.terminate()
        return False

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)