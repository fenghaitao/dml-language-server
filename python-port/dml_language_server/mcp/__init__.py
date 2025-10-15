"""
MCP (Model Context Protocol) server for DML code generation.

This module provides an MCP server that leverages the existing DML analysis
capabilities to offer intelligent code generation tools.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from ..config import Config
from ..file_management import FileManager
from ..analysis import DeviceAnalysis
from ..lsp_data import DMLSymbol, DMLSymbolKind

logger = logging.getLogger(__name__)

# MCP protocol version supported
MCP_VERSION = "2024-11-05"


@dataclass
class ServerInfo:
    """MCP server information."""
    name: str = "dml-mcp-server"
    version: str = "0.9.14"


@dataclass
class ServerCapabilities:
    """MCP server capabilities."""
    tools: bool = True
    resources: bool = False
    prompts: bool = False
    logging: bool = True


@dataclass
class MCPRequest:
    """MCP request message."""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPResponse:
    """MCP response message."""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class ToolInfo:
    """Information about an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class DMLCodeGenerator:
    """Code generator for DML constructs."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_device_template(self, device_name: str, description: str = "") -> str:
        """Generate a basic device template."""
        template = f'''dml 1.4;

device {device_name} {{
    parameter desc = "{description}";
    
    // Device registers
    bank regs {{
        register status @ 0x00 {{
            parameter size = 4;
            field ready @ [0];
            field error @ [1];
        }}
        
        register control @ 0x04 {{
            parameter size = 4;
            field enable @ [0];
            field reset @ [1];
        }}
    }}
    
    // Device methods
    method init() {{
        // Initialize device
    }}
    
    method reset() {{
        // Reset device to initial state
        regs.status.ready = 0;
        regs.status.error = 0;
        regs.control.enable = 0;
        regs.control.reset = 0;
    }}
}}
'''
        return template
    
    def generate_register_template(self, register_name: str, address: str, size: int = 4) -> str:
        """Generate a register template."""
        template = f'''register {register_name} @ {address} {{
    parameter size = {size};
    
    // Add fields here
    field reserved @ [31:1];
    field enable @ [0];
    
    method read() -> (uint{size * 8}) {{
        // Custom read behavior
        return default();
    }}
    
    method write(uint{size * 8} value) {{
        // Custom write behavior
        default(value);
    }}
}}'''
        return template
    
    def generate_field_template(self, field_name: str, bits: str) -> str:
        """Generate a field template."""
        template = f'''field {field_name} @ [{bits}] {{
    method read() -> (uint64) {{
        // Custom field read behavior
        return default();
    }}
    
    method write(uint64 value) {{
        // Custom field write behavior
        default(value);
    }}
}}'''
        return template
    
    def generate_method_template(self, method_name: str, return_type: str = "void", params: List[str] = None) -> str:
        """Generate a method template."""
        if params is None:
            params = []
        
        param_str = ", ".join(params) if params else ""
        template = f'''method {method_name}({param_str}) -> ({return_type}) {{
    // Method implementation
    
}}'''
        return template


class DMLMCPServer:
    """MCP server for DML code generation."""
    
    def __init__(self):
        self.config = Config()
        self.file_manager = FileManager(self.config)
        self.analysis_engine = DeviceAnalysis(self.config, self.file_manager)
        self.code_generator = DMLCodeGenerator(self.config)
        
        # Available tools
        self.tools = {
            "analyze_dml_file": self._analyze_dml_file,
            "generate_device": self._generate_device,
            "generate_register": self._generate_register,
            "generate_field": self._generate_field,
            "generate_method": self._generate_method,
            "list_symbols": self._list_symbols,
            "get_symbol_info": self._get_symbol_info,
        }
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request."""
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"Unknown method: {request.method}"},
                    id=request.id
                )
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return MCPResponse(
                error={"code": -32603, "message": f"Internal error: {str(e)}"},
                id=request.id
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize request."""
        return MCPResponse(
            result={
                "protocolVersion": MCP_VERSION,
                "capabilities": asdict(ServerCapabilities()),
                "serverInfo": asdict(ServerInfo())
            },
            id=request.id
        )
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools list request."""
        tools = [
            ToolInfo(
                name="analyze_dml_file",
                description="Analyze a DML file and return symbols and errors",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the DML file"},
                    },
                    "required": ["file_path"]
                }
            ),
            ToolInfo(
                name="generate_device",
                description="Generate a DML device template",
                input_schema={
                    "type": "object",
                    "properties": {
                        "device_name": {"type": "string", "description": "Name of the device"},
                        "description": {"type": "string", "description": "Device description"}
                    },
                    "required": ["device_name"]
                }
            ),
            ToolInfo(
                name="generate_register",
                description="Generate a DML register template",
                input_schema={
                    "type": "object",
                    "properties": {
                        "register_name": {"type": "string", "description": "Name of the register"},
                        "address": {"type": "string", "description": "Register address"},
                        "size": {"type": "integer", "description": "Register size in bytes", "default": 4}
                    },
                    "required": ["register_name", "address"]
                }
            ),
            ToolInfo(
                name="generate_field",
                description="Generate a DML field template",
                input_schema={
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string", "description": "Name of the field"},
                        "bits": {"type": "string", "description": "Bit range (e.g., '7:0' or '15')"}
                    },
                    "required": ["field_name", "bits"]
                }
            ),
            ToolInfo(
                name="generate_method",
                description="Generate a DML method template",
                input_schema={
                    "type": "object",
                    "properties": {
                        "method_name": {"type": "string", "description": "Name of the method"},
                        "return_type": {"type": "string", "description": "Return type", "default": "void"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "Method parameters"}
                    },
                    "required": ["method_name"]
                }
            ),
            ToolInfo(
                name="list_symbols",
                description="List all symbols in a DML file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the DML file"},
                    },
                    "required": ["file_path"]
                }
            ),
            ToolInfo(
                name="get_symbol_info",
                description="Get detailed information about a symbol",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the DML file"},
                        "symbol_name": {"type": "string", "description": "Name of the symbol"}
                    },
                    "required": ["file_path", "symbol_name"]
                }
            ),
        ]
        
        return MCPResponse(
            result={"tools": [asdict(tool) for tool in tools]},
            id=request.id
        )
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools call request."""
        if not request.params:
            return MCPResponse(
                error={"code": -32602, "message": "Missing parameters"},
                id=request.id
            )
        
        tool_name = request.params.get("name")
        tool_arguments = request.params.get("arguments", {})
        
        if tool_name not in self.tools:
            return MCPResponse(
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"},
                id=request.id
            )
        
        try:
            result = await self.tools[tool_name](**tool_arguments)
            return MCPResponse(result={"content": [{"type": "text", "text": result}]}, id=request.id)
        except Exception as e:
            return MCPResponse(
                error={"code": -32603, "message": f"Tool execution error: {str(e)}"},
                id=request.id
            )
    
    async def _analyze_dml_file(self, file_path: str) -> str:
        """Analyze a DML file."""
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
        
        try:
            content = path.read_text(encoding='utf-8')
            errors = self.analysis_engine.analyze_file(path, content)
            symbols = self.analysis_engine.get_all_symbols_in_file(path)
            
            result = f"Analysis of {file_path}:\n\n"
            
            if errors:
                result += f"Errors ({len(errors)}):\n"
                for error in errors[:10]:  # Limit to first 10 errors
                    result += f"  - {error.message} at {error.span}\n"
                if len(errors) > 10:
                    result += f"  ... and {len(errors) - 10} more errors\n"
                result += "\n"
            else:
                result += "No errors found.\n\n"
            
            if symbols:
                result += f"Symbols ({len(symbols)}):\n"
                for symbol in symbols[:20]:  # Limit to first 20 symbols
                    result += f"  - {symbol.name} ({symbol.kind.value})\n"
                if len(symbols) > 20:
                    result += f"  ... and {len(symbols) - 20} more symbols\n"
            else:
                result += "No symbols found.\n"
            
            return result
            
        except Exception as e:
            return f"Error analyzing file: {str(e)}"
    
    async def _generate_device(self, device_name: str, description: str = "") -> str:
        """Generate a device template."""
        return self.code_generator.generate_device_template(device_name, description)
    
    async def _generate_register(self, register_name: str, address: str, size: int = 4) -> str:
        """Generate a register template."""
        return self.code_generator.generate_register_template(register_name, address, size)
    
    async def _generate_field(self, field_name: str, bits: str) -> str:
        """Generate a field template."""
        return self.code_generator.generate_field_template(field_name, bits)
    
    async def _generate_method(self, method_name: str, return_type: str = "void", parameters: List[str] = None) -> str:
        """Generate a method template."""
        return self.code_generator.generate_method_template(method_name, return_type, parameters)
    
    async def _list_symbols(self, file_path: str) -> str:
        """List symbols in a file."""
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
        
        try:
            content = path.read_text(encoding='utf-8')
            self.analysis_engine.analyze_file(path, content)
            symbols = self.analysis_engine.get_all_symbols_in_file(path)
            
            if not symbols:
                return f"No symbols found in {file_path}"
            
            result = f"Symbols in {file_path}:\n\n"
            
            # Group symbols by kind
            symbol_groups = {}
            for symbol in symbols:
                kind = symbol.kind.value
                if kind not in symbol_groups:
                    symbol_groups[kind] = []
                symbol_groups[kind].append(symbol)
            
            for kind, group_symbols in symbol_groups.items():
                result += f"{kind.capitalize()}s:\n"
                for symbol in group_symbols:
                    location = f"{symbol.location.span.start.line + 1}:{symbol.location.span.start.column + 1}"
                    result += f"  - {symbol.name} at line {location}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"Error listing symbols: {str(e)}"
    
    async def _get_symbol_info(self, file_path: str, symbol_name: str) -> str:
        """Get information about a specific symbol."""
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
        
        try:
            content = path.read_text(encoding='utf-8')
            self.analysis_engine.analyze_file(path, content)
            
            # Find the symbol
            definitions = self.analysis_engine.find_symbol_definitions(symbol_name)
            
            if not definitions:
                return f"Symbol '{symbol_name}' not found in {file_path}"
            
            result = f"Information for symbol '{symbol_name}':\n\n"
            
            for definition in definitions:
                symbol = definition.symbol
                location = f"{symbol.location.span.start.line + 1}:{symbol.location.span.start.column + 1}"
                
                result += f"Type: {symbol.kind.value}\n"
                result += f"Location: {file_path}:{location}\n"
                
                if symbol.detail:
                    result += f"Detail: {symbol.detail}\n"
                
                if symbol.documentation:
                    result += f"Documentation: {symbol.documentation}\n"
                
                if symbol.children:
                    result += f"Children ({len(symbol.children)}):\n"
                    for child in symbol.children:
                        result += f"  - {child.name} ({child.kind.value})\n"
                
                if definition.references:
                    result += f"References ({len(definition.references)}):\n"
                    for ref in definition.references[:10]:  # Limit to first 10
                        ref_location = f"{ref.location.span.start.line + 1}:{ref.location.span.start.column + 1}"
                        result += f"  - {file_path}:{ref_location}\n"
                
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"Error getting symbol info: {str(e)}"


# Export main classes
__all__ = [
    "DMLMCPServer",
    "DMLCodeGenerator",
    "ServerInfo",
    "ServerCapabilities",
    "MCPRequest",
    "MCPResponse",
    "ToolInfo"
]