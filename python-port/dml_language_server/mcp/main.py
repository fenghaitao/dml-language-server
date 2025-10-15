"""
Main entry point for the DML MCP server.

© 2024 Intel Corporation
SPDX-License-Identifier: Apache-2.0 and MIT
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any

import click

from . import DMLMCPServer, MCPRequest, MCPResponse
from .. import version

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """Handler for MCP protocol communication over stdio."""
    
    def __init__(self, server: DMLMCPServer):
        self.server = server
        self.running = True
    
    async def run(self) -> None:
        """Run the MCP protocol handler."""
        logger.info("Starting DML MCP server")
        
        try:
            # Read from stdin and write to stdout
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
            
            while self.running:
                try:
                    # Read a line from stdin
                    line = await reader.readline()
                    if not line:
                        break
                    
                    # Parse JSON-RPC message
                    try:
                        message = json.loads(line.decode('utf-8').strip())
                        request = MCPRequest(
                            method=message.get('method'),
                            params=message.get('params'),
                            id=message.get('id')
                        )
                        
                        # Handle the request
                        response = await self.server.handle_request(request)
                        
                        # Send response
                        if response.result is not None or response.error is not None:
                            response_message = {
                                'jsonrpc': '2.0',
                                'id': response.id
                            }
                            
                            if response.result is not None:
                                response_message['result'] = response.result
                            else:
                                response_message['error'] = response.error
                            
                            output = json.dumps(response_message) + '\n'
                            sys.stdout.write(output)
                            sys.stdout.flush()
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {e}")
                        error_response = {
                            'jsonrpc': '2.0',
                            'id': None,
                            'error': {
                                'code': -32700,
                                'message': 'Parse error'
                            }
                        }
                        output = json.dumps(error_response) + '\n'
                        sys.stdout.write(output)
                        sys.stdout.flush()
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Protocol handler error: {e}")
        finally:
            logger.info("DML MCP server stopped")


@click.command()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.option(
    "--compile-info",
    type=click.Path(exists=True),
    help="Path to DML compile commands file"
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path (default: stderr)"
)
@click.version_option(version=version())
def main(verbose: bool, compile_info: str, log_file: str) -> None:
    """
    DML MCP (Model Context Protocol) server.
    
    Provides intelligent code generation and analysis tools for DML files
    through the Model Context Protocol.
    """
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            filename=log_file
        )
    else:
        # Log to stderr to avoid interfering with MCP protocol on stdout
        logging.basicConfig(
            level=log_level,
            format=log_format,
            stream=sys.stderr
        )
    
    logger.info("Starting DML MCP server")
    
    try:
        # Create MCP server
        server = DMLMCPServer()
        
        # Load compile commands if provided
        if compile_info:
            from pathlib import Path
            server.config.load_compile_commands(Path(compile_info))
            logger.info(f"Loaded compile commands from {compile_info}")
        
        # Create protocol handler
        protocol_handler = MCPProtocolHandler(server)
        
        # Run the server
        asyncio.run(protocol_handler.run())
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()