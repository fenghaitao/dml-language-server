#!/usr/bin/env python3
"""
Advanced test script for DML MCP Server showcasing complex device generation
"""

import json
import subprocess
import sys

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
    proc.stdin.write(message_str.encode())
    proc.stdin.flush()
    
    # Read response
    response_line = proc.stdout.readline().decode().strip()
    
    try:
        return json.loads(response_line)
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return None

def test_advanced_generation():
    """Test advanced DML device generation"""
    print("🚀 Advanced DML MCP Server Test")
    print("=" * 60)
    
    try:
        proc = subprocess.Popen(
            ["./target/debug/dml-mcp-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        
        # Initialize
        send_json_rpc(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "advanced-test", "version": "1.0.0"}
        })
        
        # Test: Generate complex peripheral device
        print("🎛️  Generating Complex Peripheral Device")
        response = send_json_rpc(proc, "tools/call", {
            "name": "generate_device",
            "arguments": {
                "device_name": "uart_controller",
                "device_type": "peripheral",
                "template_base": "peripheral_device",
                "registers": [
                    {
                        "name": "data",
                        "size": 1,
                        "offset": "0x00"
                    },
                    {
                        "name": "status", 
                        "size": 1,
                        "offset": "0x01"
                    },
                    {
                        "name": "control",
                        "size": 2,
                        "offset": "0x02"
                    }
                ],
                "interfaces": ["io_memory", "signal"]
            }
        })
        
        if response and "result" in response:
            content = response["result"]["content"][0]["text"]
            print("✅ Complex device generated successfully!")
            print("\n" + "="*60)
            print("GENERATED DML CODE:")
            print("="*60)
            print(content)
            print("="*60)
        
        # Test: Generate register with fields
        print("\n🔧 Generating Register with Fields")
        response = send_json_rpc(proc, "tools/call", {
            "name": "generate_register",
            "arguments": {
                "name": "interrupt_control",
                "size": 4,
                "offset": "0x10",
                "documentation": "Interrupt control register",
                "fields": [
                    {
                        "name": "enable",
                        "bits": "0",
                        "access": "rw"
                    },
                    {
                        "name": "pending",
                        "bits": "7:1", 
                        "access": "ro"
                    },
                    {
                        "name": "priority",
                        "bits": "15:8",
                        "access": "rw"
                    }
                ]
            }
        })
        
        if response and "result" in response:
            content = response["result"]["content"][0]["text"]
            print("✅ Register with fields generated!")
            print("\n" + "-"*40)
            print("GENERATED REGISTER:")
            print("-"*40)
            print(content)
            print("-"*40)
        
        # Test: Generate CPU device
        print("\n🖥️  Generating CPU Device")
        response = send_json_rpc(proc, "tools/call", {
            "name": "generate_device",
            "arguments": {
                "device_name": "risc_v_core",
                "device_type": "cpu",
                "template_base": "riscv_cpu",
                "interfaces": ["processor", "cycle", "execute"]
            }
        })
        
        if response and "result" in response:
            content = response["result"]["content"][0]["text"]
            print("✅ CPU device generated!")
            print("\n" + "-"*40)
            print("GENERATED CPU DEVICE:")
            print("-"*40)
            print(content)
            print("-"*40)
        
        # Test: Generate memory device
        print("\n💾 Generating Memory Device")
        response = send_json_rpc(proc, "tools/call", {
            "name": "generate_device",
            "arguments": {
                "device_name": "system_ram",
                "device_type": "memory",
                "interfaces": ["io_memory"]
            }
        })
        
        if response and "result" in response:
            content = response["result"]["content"][0]["text"]
            print("✅ Memory device generated!")
            print("\n" + "-"*40)
            print("GENERATED MEMORY DEVICE:")
            print("-"*40)
            print(content)
            print("-"*40)
        
        proc.terminate()
        proc.wait(timeout=5)
        print("\n✅ Advanced test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Advanced test failed: {e}")
        if 'proc' in locals():
            proc.terminate()
        return False

if __name__ == "__main__":
    success = test_advanced_generation()
    sys.exit(0 if success else 1)